"""PostgreSQL migration, idempotency races, and Project-lock serialization for G1.1B."""

from __future__ import annotations

import threading
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.modules.project_master_data.application import preliminary_project_lifecycle_service as service
from app.modules.project_master_data.models import (
    AuditEvent,
    PreliminaryProjectLifecycleCommandReceipt,
    Project,
    ProjectOfficialIntakeCommit,
    User,
)
from tests.test_g11a_foundation_postgresql import (
    _alembic, _must_alembic, _seed_prior_minimal,
)
from tests.test_g11b_lifecycle_service import _batch, _bind, _intake, _seed_case
from tests.test_pr01_official_intake_postgresql import _wait_for_project_row_lock_wait


pytest_plugins = ("tests.test_g11a_foundation_postgresql",)


PRIOR = "e4f5a6b7c8d9"
CURRENT = "f5a6b7c8d9e0"


def _session_factory(url):
    engine = create_engine(url, pool_pre_ping=True)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _run_competitors(SessionLocal, calls):
    barrier = threading.Barrier(2, timeout=20)
    results = []
    errors = []

    def worker(call):
        with SessionLocal() as db:
            try:
                barrier.wait(timeout=20)
                results.append(call(db))
            except BaseException as exc:  # thread transports the failure to the test
                errors.append(exc)

    threads = [threading.Thread(target=worker, args=(call,), daemon=True) for call in calls]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert all(not thread.is_alive() for thread in threads)
    return results, errors


def _assert_conflict(error):
    assert isinstance(error, HTTPException)
    assert error.status_code == 409


def test_receipt_migration_roundtrip_and_nonempty_downgrade_refusal(pg_database):
    _must_alembic(pg_database, "upgrade", PRIOR)
    engine = create_engine(pg_database)
    with engine.begin() as conn:
        org_id, customer_id, project_id, batches = _seed_prior_minimal(conn, batches=1)
        conn.execute(text(
            "UPDATE projects SET current_preliminary_import_batch_id=:batch WHERE id=:project"
        ), {"batch": batches[0], "project": project_id})
    _must_alembic(pg_database, "upgrade", CURRENT)
    inspector = inspect(engine)
    table = "preliminary_project_lifecycle_command_receipts"
    assert table in inspector.get_table_names()
    assert "uq_preliminary_lifecycle_idempotency" in {
        row["name"] for row in inspector.get_unique_constraints(table)
    }
    assert {
        "fk_preliminary_lifecycle_project_tenant",
        "fk_preliminary_lifecycle_actor_tenant",
        "fk_preliminary_lifecycle_customer_tenant",
        "fk_preliminary_lifecycle_target_batch_tenant",
        "fk_preliminary_lifecycle_previous_batch_tenant",
    } <= {row["name"] for row in inspector.get_foreign_keys(table)}
    with engine.connect() as conn:
        assert conn.execute(text(
            "SELECT customer_id, current_preliminary_import_batch_id FROM projects WHERE id=:id"
        ), {"id": project_id}).one() == (customer_id, batches[0])
    _must_alembic(pg_database, "downgrade", PRIOR)
    assert table not in inspect(engine).get_table_names()
    _must_alembic(pg_database, "upgrade", CURRENT)
    with engine.connect() as conn:
        assert conn.execute(text(
            "SELECT customer_id, current_preliminary_import_batch_id FROM projects WHERE id=:id"
        ), {"id": project_id}).one() == (customer_id, batches[0])

    with Session(engine) as db:
        seeded = _seed_case(db)
        _bind(db, seeded, version=seeded["project"].row_version)
        receipt_id = db.query(PreliminaryProjectLifecycleCommandReceipt.id).one()[0]
    refused = _alembic(pg_database, "downgrade", PRIOR)
    assert refused.returncode != 0
    assert "committed lifecycle receipts cannot be discarded" in refused.stderr
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == CURRENT
        assert conn.execute(text(
            "SELECT 1 FROM preliminary_project_lifecycle_command_receipts WHERE id=:id"
        ), {"id": receipt_id}).scalar_one() == 1
    engine.dispose()


def test_postgresql_bind_and_null_history_official_intake(pg_database):
    _must_alembic(pg_database, "upgrade", CURRENT)
    engine, SessionLocal = _session_factory(pg_database)
    with SessionLocal() as db:
        seeded = _seed_case(db)
        before = seeded["project"].row_version
        receipt = _bind(db, seeded, version=before)
        assert receipt.committed_project_version == before + 1
        assert seeded["artifact"].customer_id is None
        committed = _intake(db, seeded, version=before + 1)
        assert committed.customer_id == seeded["customer"].id
        assert db.query(ProjectOfficialIntakeCommit).count() == 1
        assert db.query(AuditEvent).filter_by(
            event_name="PreliminaryProjectCustomerBound"
        ).count() == 1
        assert db.query(AuditEvent).filter_by(
            event_name="ProjectOfficialIntakeCommitted"
        ).count() == 1
    engine.dispose()


def test_postgresql_competing_binds_and_global_receipt_key(pg_database):
    _must_alembic(pg_database, "upgrade", CURRENT)
    engine, SessionLocal = _session_factory(pg_database)
    with SessionLocal() as setup:
        seeded = _seed_case(setup)
        org_id, actor_id, project_id, customer_id = (
            seeded["org"].id, seeded["actor"].id,
            seeded["project"].id, seeded["customer"].id,
        )
        before = seeded["project"].row_version

    def bind_call(key):
        def call(db):
            return service.bind_preliminary_project_customer(
                db, actor=db.get(User, actor_id), org_id=org_id,
                project_id=project_id, customer_id=customer_id,
                expected_project_version=before, idempotency_key=key,
            )
        return call

    results, errors = _run_competitors(
        SessionLocal, [bind_call("bind-race-one"), bind_call("bind-race-two")]
    )
    assert len(results) == 1 and len(errors) == 1
    _assert_conflict(errors[0])
    with SessionLocal() as db:
        assert db.get(Project, project_id).row_version == before + 1
        assert db.query(PreliminaryProjectLifecycleCommandReceipt).count() == 1
        assert db.query(AuditEvent).filter_by(
            event_name="PreliminaryProjectCustomerBound"
        ).count() == 1
        sibling = Project(
            organization_id=org_id, customer_id=None,
            code=f"G11B-RACE-{uuid.uuid4().hex[:8]}", name="Receipt race sibling",
            created_by=actor_id,
        )
        db.add(sibling)
        db.commit()
        sibling_id, sibling_version = sibling.id, sibling.row_version

    def bind_same_key(project):
        def call(db):
            return service.bind_preliminary_project_customer(
                db, actor=db.get(User, actor_id), org_id=org_id,
                project_id=project, customer_id=customer_id,
                expected_project_version=sibling_version,
                idempotency_key="shared-cross-project-key",
            )
        return call

    # The first Project is already bound, so use two new unbound Projects in one tenant.
    with SessionLocal() as db:
        another = Project(
            organization_id=org_id, customer_id=None,
            code=f"G11B-RACE-{uuid.uuid4().hex[:8]}", name="Receipt race other",
            created_by=actor_id,
        )
        db.add(another)
        db.commit()
        another_id = another.id
    results, errors = _run_competitors(
        SessionLocal, [bind_same_key(sibling_id), bind_same_key(another_id)]
    )
    assert len(results) == 1 and len(errors) == 1
    _assert_conflict(errors[0])
    with SessionLocal() as db:
        assert db.query(PreliminaryProjectLifecycleCommandReceipt).filter_by(
            organization_id=org_id, idempotency_key="shared-cross-project-key"
        ).count() == 1
        bound_count = sum(
            db.get(Project, project).customer_id is not None
            for project in (sibling_id, another_id)
        )
        assert bound_count == 1
    engine.dispose()


def test_postgresql_concurrent_same_key_bind_replays_one_receipt(pg_database):
    _must_alembic(pg_database, "upgrade", CURRENT)
    engine, SessionLocal = _session_factory(pg_database)
    with SessionLocal() as setup:
        seeded = _seed_case(setup)
        org_id, actor_id, project_id, customer_id = (
            seeded["org"].id, seeded["actor"].id,
            seeded["project"].id, seeded["customer"].id,
        )
        before = seeded["project"].row_version

    def bind_same_key(db):
        return service.bind_preliminary_project_customer(
            db, actor=db.get(User, actor_id), org_id=org_id,
            project_id=project_id, customer_id=customer_id,
            expected_project_version=before, idempotency_key="same-key-bind-race",
        )

    results, errors = _run_competitors(SessionLocal, [bind_same_key, bind_same_key])
    assert not errors
    assert len(results) == 2 and results[0].id == results[1].id
    with SessionLocal() as db:
        assert db.get(Project, project_id).row_version == before + 1
        assert db.query(PreliminaryProjectLifecycleCommandReceipt).count() == 1
        assert db.query(AuditEvent).filter_by(
            event_name="PreliminaryProjectCustomerBound"
        ).count() == 1
    engine.dispose()


def test_postgresql_competing_switches_only_one_pointer_wins(pg_database):
    _must_alembic(pg_database, "upgrade", CURRENT)
    engine, SessionLocal = _session_factory(pg_database)
    with SessionLocal() as setup:
        seeded = _seed_case(setup, unbound=False)
        second, third = _batch(setup, seeded), _batch(setup, seeded)
        org_id, actor_id, project_id = (
            seeded["org"].id, seeded["actor"].id, seeded["project"].id
        )
        old_id, before = seeded["batch"].id, seeded["project"].row_version
        targets = (second.id, third.id)

    def switch_call(target_id, key):
        def call(db):
            return service.switch_current_preliminary_import_batch(
                db, actor=db.get(User, actor_id), org_id=org_id,
                project_id=project_id, target_import_batch_id=target_id,
                expected_current_import_batch_id=old_id,
                expected_project_version=before, idempotency_key=key,
            )
        return call

    results, errors = _run_competitors(SessionLocal, [
        switch_call(targets[0], "switch-race-one"),
        switch_call(targets[1], "switch-race-two"),
    ])
    assert len(results) == 1 and len(errors) == 1
    _assert_conflict(errors[0])
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        assert project.row_version == before + 1
        assert project.current_preliminary_import_batch_id in targets
        assert db.query(PreliminaryProjectLifecycleCommandReceipt).count() == 1
        assert db.query(AuditEvent).filter_by(
            event_name="CurrentPreliminaryImportBatchSwitched"
        ).count() == 1
    engine.dispose()


@pytest.mark.parametrize("command", ["bind", "switch"])
def test_postgresql_lifecycle_command_serializes_with_official_intake(
    pg_database, monkeypatch, command,
):
    _must_alembic(pg_database, "upgrade", CURRENT)
    engine, SessionLocal = _session_factory(pg_database)
    with SessionLocal() as setup:
        seeded = _seed_case(setup, unbound=command == "bind")
        target = _batch(setup, seeded) if command == "switch" else None
        org_id, actor_id, project_id = (
            seeded["org"].id, seeded["actor"].id, seeded["project"].id
        )
        customer_id, artifact_id = seeded["customer"].id, seeded["artifact"].id
        old_id, version = seeded["batch"].id, seeded["project"].row_version
        target_id = target.id if target is not None else None

    held = threading.Event()
    release = threading.Event()
    waiter_ready = threading.Event()
    holder_pid = []
    waiter_pid = []
    holder_result = []
    waiter_result = []
    failures = []
    original_audit = service.log_audit_event

    def paused_audit(*args, **kwargs):
        held.set()
        assert release.wait(timeout=20)
        return original_audit(*args, **kwargs)

    monkeypatch.setattr(service, "log_audit_event", paused_audit)

    def holder():
        with SessionLocal() as db:
            try:
                holder_pid.append(db.execute(text("SELECT pg_backend_pid()")).scalar_one())
                actor = db.get(User, actor_id)
                if command == "bind":
                    result = service.bind_preliminary_project_customer(
                        db, actor=actor, org_id=org_id, project_id=project_id,
                        customer_id=customer_id, expected_project_version=version,
                        idempotency_key=f"g11b-{command}-holder",
                    )
                else:
                    result = service.switch_current_preliminary_import_batch(
                        db, actor=actor, org_id=org_id, project_id=project_id,
                        target_import_batch_id=target_id,
                        expected_current_import_batch_id=old_id,
                        expected_project_version=version,
                        idempotency_key=f"g11b-{command}-holder",
                    )
                holder_result.append(result.id)
            except BaseException as exc:
                failures.append(exc)

    def waiter():
        with SessionLocal() as db:
            try:
                waiter_pid.append(db.execute(text("SELECT pg_backend_pid()")).scalar_one())
                actor = db.get(User, actor_id)
                waiter_ready.set()
                result = commit_project_official_intake(
                    db, actor=actor, org_id=org_id, project_id=project_id,
                    preliminary_result_artifact_id=artifact_id,
                    expected_project_version=version + 1,
                    expected_preliminary_result_version=1,
                    idempotency_key=f"g11b-{command}-intake",
                    confirmed=True,
                )
                waiter_result.append(result.id)
            except BaseException as exc:
                failures.append(exc)

    # Import here to keep the test's dependency on the exact production command visible.
    from app.modules.project_master_data.application.official_intake_service import (
        commit_project_official_intake,
    )

    holder_thread = threading.Thread(target=holder, daemon=True)
    waiter_thread = threading.Thread(target=waiter, daemon=True)
    try:
        holder_thread.start()
        assert held.wait(timeout=20)
        waiter_thread.start()
        assert waiter_ready.wait(timeout=20)
        _wait_for_project_row_lock_wait(
            engine, holder_pid=holder_pid[0], waiter_pid=waiter_pid[0], timeout=20
        )
    finally:
        release.set()
        holder_thread.join(timeout=30)
        waiter_thread.join(timeout=30)
    assert not holder_thread.is_alive() and not waiter_thread.is_alive()
    assert len(holder_result) == 1
    if command == "bind":
        assert not failures
        assert len(waiter_result) == 1
    else:
        assert len(waiter_result) == 0
        assert len(failures) == 1
        assert isinstance(failures[0], HTTPException)
        assert failures[0].status_code == 409
        assert failures[0].detail["error_code"] == "preliminary_result_not_current"
    with SessionLocal() as db:
        assert db.get(Project, project_id).row_version == version + 1
        assert db.query(PreliminaryProjectLifecycleCommandReceipt).count() == 1
        assert db.query(ProjectOfficialIntakeCommit).count() == (1 if command == "bind" else 0)
    engine.dispose()
