"""PostgreSQL-only concurrency and lock-order proof for PR-01a official intake."""
from __future__ import annotations

import os
import re
import threading
import time
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.modules.project_master_data.application.official_intake_service import (
    commit_project_official_intake,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    Customer,
    OrganizationProfile,
    PreliminaryResultArtifact,
    Project,
    ProjectAssetLine,
    ProjectOfficialIntakeCommit,
    Role,
    User,
    UserRole,
)
from tests.test_pr01_official_intake_service import _seed


def _postgres_engine_or_skip():
    url = os.getenv("TEST_DATABASE_URL")
    if not url or not url.startswith("postgres"):
        if os.getenv("CI") == "true":
            pytest.fail("CI=true requires PostgreSQL TEST_DATABASE_URL for PR-01a")
        pytest.skip("PR-01a concurrency proof requires PostgreSQL TEST_DATABASE_URL")
    engine = create_engine(url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT to_regclass('project_official_intake_commits')")
        ).scalar_one()
    if exists is None:
        engine.dispose()
        if os.getenv("CI") == "true":
            pytest.fail("CI PostgreSQL is not migrated to the PR-01a head")
        pytest.skip("PostgreSQL is not migrated to the PR-01a head")
    return engine


def _cleanup(SessionLocal, org_id: uuid.UUID) -> None:
    db: Session = SessionLocal()
    try:
        user_ids = [row[0] for row in db.query(User.id).filter_by(organization_id=org_id)]
        role_ids = [
            row[0]
            for row in db.query(UserRole.role_id).filter(UserRole.user_id.in_(user_ids))
        ]
        db.query(AuditEvent).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(ProjectOfficialIntakeCommit).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(PreliminaryResultArtifact).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        project_ids = [
            row[0] for row in db.query(Project.id).filter_by(organization_id=org_id)
        ]
        if project_ids:
            db.query(ProjectAssetLine).filter(
                ProjectAssetLine.project_id.in_(project_ids)
            ).delete(synchronize_session=False)
        db.query(Project).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(Customer).filter_by(organization_id=org_id).delete(synchronize_session=False)
        if user_ids:
            db.query(UserRole).filter(UserRole.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )
        db.query(User).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(OrganizationProfile).filter_by(id=org_id).delete(synchronize_session=False)
        if role_ids:
            db.query(Role).filter(Role.id.in_(role_ids)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _command(
    db: Session,
    *,
    ids: dict[str, uuid.UUID],
    actor_id: uuid.UUID,
    idempotency_key: str,
) -> ProjectOfficialIntakeCommit:
    actor = db.get(User, actor_id)
    assert actor is not None
    return commit_project_official_intake(
        db,
        actor=actor,
        org_id=ids["org"],
        project_id=ids["project"],
        preliminary_result_artifact_id=ids["artifact"],
        expected_project_version=1,
        expected_preliminary_result_version=1,
        idempotency_key=idempotency_key,
        confirmed=True,
        correlation_id="corr-pr01a-postgresql",
    )


def _run_pair(
    SessionLocal,
    *,
    ids: dict[str, uuid.UUID],
    work: list[tuple[uuid.UUID, str]],
) -> tuple[list[uuid.UUID], list[BaseException]]:
    barrier = threading.Barrier(2, timeout=30)
    results: list[uuid.UUID] = []
    errors: list[BaseException] = []

    def worker(actor_id: uuid.UUID, idempotency_key: str) -> None:
        db: Session = SessionLocal()
        try:
            barrier.wait(timeout=30)
            committed = _command(
                db,
                ids=ids,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
            )
            results.append(committed.id)
        except BaseException as exc:  # thread transports evidence to parent assertion
            errors.append(exc)
        finally:
            db.close()

    threads = [
        threading.Thread(
            target=worker,
            args=item,
            name=f"official-intake-worker-{index}",
            daemon=True,
        )
        for index, item in enumerate(work)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert all(not thread.is_alive() for thread in threads)
    return results, errors


def _seed_ids(setup: Session, *, suffix: str) -> tuple[dict[str, uuid.UUID], dict]:
    seeded = _seed(setup, suffix=suffix)
    return (
        {
            "org": seeded["org"].id,
            "actor": seeded["actor"].id,
            "project": seeded["project"].id,
            "artifact": seeded["artifact"].id,
        },
        seeded,
    )


def _assert_one_fact_and_audit(SessionLocal, ids: dict[str, uuid.UUID]) -> None:
    verify: Session = SessionLocal()
    try:
        assert verify.query(ProjectOfficialIntakeCommit).filter_by(
            organization_id=ids["org"], project_id=ids["project"]
        ).count() == 1
        assert verify.query(AuditEvent).filter_by(
            organization_id=ids["org"],
            event_name="ProjectOfficialIntakeCommitted",
        ).count() == 1
    finally:
        verify.close()


def _classify_completed_official_intake_sql(statement: str) -> tuple[str, str] | None:
    """Classify only the three completed SQL steps that define the lock order."""
    sql = " ".join(statement.lower().replace('"', "").split())

    def selects_from(table_name: str) -> bool:
        return (
            re.search(
                rf"\bfrom\s+(?:[a-z0-9_]+\.)?{re.escape(table_name)}(?=\s|,|$)",
                sql,
            )
            is not None
        )

    if selects_from("projects") and re.search(r"\bfor\s+update\b", sql):
        return "project_lock", sql
    if selects_from("preliminary_result_artifacts") and re.search(
        r"\bfor\s+update\b", sql
    ):
        return "artifact_lock", sql
    if selects_from("project_official_intake_commits"):
        where_clause = sql.partition(" where ")[2]
        if re.search(r"(?:\b[a-z_][a-z0-9_]*\.)?idempotency_key\s*=", where_clause):
            return "idempotency_resolution", sql
    return None


def _wait_for_project_row_lock_wait(
    engine,
    *,
    holder_pid: int,
    waiter_pid: int,
    timeout: float = 30.0,
) -> dict[str, object]:
    """Observe the waiter blocked by the holder while executing Project FOR UPDATE."""
    deadline = time.monotonic() + timeout
    last = None
    statement = text(
        """
        SELECT activity.wait_event_type,
               activity.wait_event,
               activity.state,
               activity.query,
               pg_blocking_pids(activity.pid) AS blocking_pids,
               EXISTS (
                   SELECT 1
                   FROM pg_locks waiting
                   JOIN pg_locks holding
                     ON holding.locktype = waiting.locktype
                    AND holding.database IS NOT DISTINCT FROM waiting.database
                    AND holding.relation IS NOT DISTINCT FROM waiting.relation
                    AND holding.page IS NOT DISTINCT FROM waiting.page
                    AND holding.tuple IS NOT DISTINCT FROM waiting.tuple
                    AND holding.virtualxid IS NOT DISTINCT FROM waiting.virtualxid
                    AND holding.transactionid IS NOT DISTINCT FROM waiting.transactionid
                    AND holding.classid IS NOT DISTINCT FROM waiting.classid
                    AND holding.objid IS NOT DISTINCT FROM waiting.objid
                    AND holding.objsubid IS NOT DISTINCT FROM waiting.objsubid
                    AND holding.granted
                   WHERE waiting.pid = :waiter_pid
                     AND holding.pid = :holder_pid
                     AND NOT waiting.granted
               ) AS matching_lock_edge,
               EXISTS (
                   SELECT 1
                   FROM pg_locks relation_lock
                   JOIN pg_class relation
                     ON relation.oid = relation_lock.relation
                  WHERE relation_lock.pid = :waiter_pid
                    AND relation_lock.granted
                    AND relation.relname = 'projects'
                    AND relation_lock.mode = 'RowShareLock'
               ) AS waiter_holds_project_relation_lock
          FROM pg_stat_activity activity
         WHERE activity.pid = :waiter_pid
        """
    )
    while time.monotonic() < deadline:
        with engine.connect() as connection:
            last = connection.execute(
                statement,
                {"holder_pid": holder_pid, "waiter_pid": waiter_pid},
            ).mappings().first()
        if last is not None:
            query = " ".join(str(last["query"]).lower().split())
            blockers = list(last["blocking_pids"] or [])
            if (
                last["wait_event_type"] == "Lock"
                and "from projects" in query
                and "for update" in query
                and holder_pid in blockers
                and last["matching_lock_edge"]
                and last["waiter_holds_project_relation_lock"]
            ):
                return dict(last)
        time.sleep(0.05)
    raise AssertionError(
        "waiter was not observed on the holder's Project FOR UPDATE row-lock edge; "
        f"holder_pid={holder_pid}, waiter_pid={waiter_pid}, last={last}"
    )


def test_postgresql_concurrent_same_request_observes_lock_order_and_replays() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    setup: Session = SessionLocal()
    ids = None
    holder_thread = None
    waiter_thread = None
    holder_project_lock_returned = threading.Event()
    release_holder = threading.Event()
    holder_pid_ready = threading.Event()
    waiter_pid_ready = threading.Event()
    holder_pid: list[int] = []
    waiter_pid: list[int] = []
    holder_results: list[uuid.UUID] = []
    waiter_results: list[uuid.UUID] = []
    errors: list[tuple[str, BaseException]] = []
    completed_sql_traces: dict[str, list[tuple[str, str]]] = {
        "holder": [],
        "waiter": [],
    }
    holder_pause_armed = True

    def record_completed_sql_and_pause_holder(
        conn, cursor, statement, parameters, context, executemany
    ) -> None:
        nonlocal holder_pause_armed
        del conn, cursor, parameters, context, executemany
        label_by_thread = {
            "official-intake-lock-holder": "holder",
            "official-intake-lock-waiter": "waiter",
        }
        label = label_by_thread.get(threading.current_thread().name)
        if label is None:
            return
        completed = _classify_completed_official_intake_sql(statement)
        if completed is None:
            return
        completed_sql_traces[label].append(completed)
        if label == "holder" and holder_pause_armed and completed[0] == "project_lock":
            holder_pause_armed = False
            holder_project_lock_returned.set()
            assert release_holder.wait(timeout=30), "holder release was not signaled"

    def run_worker(
        *,
        label: str,
        pid_box: list[int],
        pid_ready: threading.Event,
        result_box: list[uuid.UUID],
    ) -> None:
        db: Session = SessionLocal()
        try:
            pid_box.append(db.execute(text("SELECT pg_backend_pid()")).scalar_one())
            pid_ready.set()
            committed = _command(
                db,
                ids=ids,
                actor_id=ids["actor"],
                idempotency_key="pg-same-request",
            )
            result_box.append(committed.id)
        except BaseException as exc:  # thread transports evidence to parent assertion
            errors.append((label, exc))
        finally:
            db.close()

    event.listen(engine, "after_cursor_execute", record_completed_sql_and_pause_holder)
    try:
        ids, _ = _seed_ids(setup, suffix=f"pg-same-{uuid.uuid4().hex[:8]}")
        setup.close()

        holder_thread = threading.Thread(
            target=run_worker,
            kwargs={
                "label": "holder",
                "pid_box": holder_pid,
                "pid_ready": holder_pid_ready,
                "result_box": holder_results,
            },
            name="official-intake-lock-holder",
            daemon=True,
        )
        holder_thread.start()
        assert holder_pid_ready.wait(timeout=5), "holder did not publish its backend pid"
        assert holder_project_lock_returned.wait(
            timeout=30
        ), "holder did not acquire and return from Project FOR UPDATE"

        waiter_thread = threading.Thread(
            target=run_worker,
            kwargs={
                "label": "waiter",
                "pid_box": waiter_pid,
                "pid_ready": waiter_pid_ready,
                "result_box": waiter_results,
            },
            name="official-intake-lock-waiter",
            daemon=True,
        )
        waiter_thread.start()
        assert waiter_pid_ready.wait(timeout=5), "waiter did not publish its backend pid"

        observed = _wait_for_project_row_lock_wait(
            engine,
            holder_pid=holder_pid[0],
            waiter_pid=waiter_pid[0],
        )
        assert observed["wait_event_type"] == "Lock"
        assert holder_pid[0] in observed["blocking_pids"]

        release_holder.set()
        holder_thread.join(timeout=60)
        waiter_thread.join(timeout=60)
        assert not holder_thread.is_alive() and not waiter_thread.is_alive()
        assert errors == []
        assert len(holder_results) == len(waiter_results) == 1
        assert holder_results[0] == waiter_results[0]
        expected_prefix = [
            "project_lock",
            "artifact_lock",
            "idempotency_resolution",
        ]
        assert [kind for kind, _sql in completed_sql_traces["holder"]][:3] == (
            expected_prefix
        ), completed_sql_traces["holder"]
        assert [kind for kind, _sql in completed_sql_traces["waiter"]][:3] == (
            expected_prefix
        ), completed_sql_traces["waiter"]
        _assert_one_fact_and_audit(SessionLocal, ids)
    finally:
        release_holder.set()
        if holder_thread is not None:
            holder_thread.join(timeout=60)
        if waiter_thread is not None:
            waiter_thread.join(timeout=60)
        event.remove(
            engine,
            "after_cursor_execute",
            record_completed_sql_and_pause_holder,
        )
        setup.close()
        if ids is not None:
            _cleanup(SessionLocal, ids["org"])
        engine.dispose()


def test_postgresql_concurrent_same_key_different_digest_is_typed_reuse() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    setup: Session = SessionLocal()
    ids = None
    try:
        ids, seeded = _seed_ids(setup, suffix=f"pg-reuse-{uuid.uuid4().hex[:8]}")
        second_actor = User(
            organization_id=ids["org"],
            email=f"pg-reuse-peer-{uuid.uuid4().hex[:8]}@example.com",
            full_name="PostgreSQL Official Intake Peer",
        )
        setup.add(second_actor)
        setup.flush()
        setup.add(
            UserRole(
                user_id=second_actor.id,
                role_id=seeded["role"].id,
                is_active=True,
            )
        )
        setup.commit()
        second_actor_id = second_actor.id
        setup.close()

        results, errors = _run_pair(
            SessionLocal,
            ids=ids,
            work=[
                (ids["actor"], "pg-reused-key"),
                (second_actor_id, "pg-reused-key"),
            ],
        )

        assert len(results) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], HTTPException)
        assert errors[0].status_code == 409
        assert errors[0].detail["error_code"] == "idempotency_key_reused"
        _assert_one_fact_and_audit(SessionLocal, ids)
    finally:
        setup.close()
        if ids is not None:
            _cleanup(SessionLocal, ids["org"])
        engine.dispose()


def test_postgresql_concurrent_different_keys_have_one_typed_already_committed() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    setup: Session = SessionLocal()
    ids = None
    try:
        ids, _ = _seed_ids(setup, suffix=f"pg-project-{uuid.uuid4().hex[:8]}")
        setup.close()

        results, errors = _run_pair(
            SessionLocal,
            ids=ids,
            work=[
                (ids["actor"], "pg-project-key-a"),
                (ids["actor"], "pg-project-key-b"),
            ],
        )

        assert len(results) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], HTTPException)
        assert errors[0].status_code == 409
        assert errors[0].detail["error_code"] == "official_intake_already_committed"
        _assert_one_fact_and_audit(SessionLocal, ids)
    finally:
        setup.close()
        if ids is not None:
            _cleanup(SessionLocal, ids["org"])
        engine.dispose()
