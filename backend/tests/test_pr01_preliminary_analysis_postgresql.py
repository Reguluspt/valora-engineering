"""PostgreSQL-only concurrency and lock-order proof for PR-01 preliminary analysis."""
from __future__ import annotations

import os
import threading
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.modules.project_master_data.application.preliminary_analysis_service import (
    finalize_preliminary_analysis,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    PreliminaryAnalysisSnapshot,
    User,
    UserRole,
)
from tests.test_pr01_preliminary_analysis_service import _seed


def _postgres_engine_or_skip():
    url = os.getenv("TEST_DATABASE_URL")
    if not url or not url.startswith("postgres"):
        if os.getenv("CI") == "true":
            pytest.fail("CI=true requires PostgreSQL TEST_DATABASE_URL for PR-01 preliminary analysis")
        pytest.skip("PR-01 preliminary analysis concurrency proof requires PostgreSQL TEST_DATABASE_URL")
    engine = create_engine(url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT to_regclass('preliminary_analysis_snapshots')")
        ).scalar_one()
    if exists is None:
        engine.dispose()
        if os.getenv("CI") == "true":
            pytest.fail("CI PostgreSQL is not migrated to the PR-01 preliminary analysis head")
        pytest.skip("PostgreSQL is not migrated to the PR-01 preliminary analysis head")
    return engine


def _command(
    db: Session,
    *,
    ids: dict[str, uuid.UUID],
    actor_id: uuid.UUID,
    idempotency_key: str,
    line_manifest: list[dict] | None = None,
) -> PreliminaryAnalysisSnapshot:
    from tests.test_pr01_preliminary_analysis_service import _line
    actor = db.get(User, actor_id)
    assert actor is not None
    return finalize_preliminary_analysis(
        db,
        actor=actor,
        org_id=ids["org"],
        project_id=ids["project"],
        expected_project_version=1,
        import_batch_id=ids["batch"],
        source_artifact_id=ids["artifact"],
        structure_snapshot_id=ids["structure"],
        mapping_decision_id=ids["decision"],
        mapping_profile_usage_id=ids["usage"],
        mapping_decision_digest_sha256=ids["decision_digest"],
        profile_usage_mapping_digest_sha256=ids["usage_digest"],
        line_manifest=line_manifest if line_manifest is not None else [_line()],
        idempotency_key=idempotency_key,
        confirmed=True,
        correlation_id="corr-pr01-preliminary-analysis-postgresql",
    )


def _run_pair(
    SessionLocal,
    *,
    ids: dict[str, uuid.UUID],
    work: list[tuple[uuid.UUID, str, list[dict] | None]],
) -> tuple[list[uuid.UUID], list[BaseException]]:
    barrier = threading.Barrier(2, timeout=30)
    results: list[uuid.UUID] = []
    errors: list[BaseException] = []

    def worker(actor_id: uuid.UUID, idempotency_key: str, line_manifest) -> None:
        db: Session = SessionLocal()
        try:
            barrier.wait(timeout=30)
            snapshot = _command(
                db,
                ids=ids,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                line_manifest=line_manifest,
            )
            results.append(snapshot.id)
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [
        threading.Thread(
            target=worker,
            args=item,
            name=f"preliminary-analysis-worker-{index}",
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


def _seed_ids(setup: Session, *, suffix: str) -> tuple[dict[str, object], dict]:
    seeded = _seed(setup, suffix=suffix)
    return (
        {
            "org": seeded["org"].id,
            "actor": seeded["actor"].id,
            "project": seeded["project"].id,
            "batch": seeded["batch"].id,
            "artifact": seeded["artifact"].id,
            "structure": seeded["structure"].id,
            "decision": seeded["decision"].id,
            "usage": seeded["usage"].id,
            "decision_digest": seeded["decision"].mapping_digest_sha256,
            "usage_digest": seeded["usage"].mapping_digest_sha256,
        },
        seeded,
    )


def _assert_one_fact_and_audit(SessionLocal, ids: dict[str, uuid.UUID]) -> None:
    verify: Session = SessionLocal()
    try:
        assert verify.query(PreliminaryAnalysisSnapshot).filter_by(
            organization_id=ids["org"], project_id=ids["project"]
        ).count() == 1
        assert verify.query(AuditEvent).filter_by(
            organization_id=ids["org"],
            event_name="PreliminaryAnalysisSnapshotFinalized",
        ).count() == 1
    finally:
        verify.close()


def test_postgresql_concurrent_same_request_replays_with_one_fact() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    setup: Session = SessionLocal()
    ids = None
    try:
        ids, _ = _seed_ids(setup, suffix=f"pg-same-{uuid.uuid4().hex[:8]}")
        setup.close()

        results, errors = _run_pair(
            SessionLocal,
            ids=ids,
            work=[
                (ids["actor"], "pg-same-request", None),
                (ids["actor"], "pg-same-request", None),
            ],
        )

        assert errors == []
        assert len(results) == 2
        assert results[0] == results[1]
        _assert_one_fact_and_audit(SessionLocal, ids)
    finally:
        setup.close()
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
            full_name="PostgreSQL Preliminary Analysis Peer",
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

        from tests.test_pr01_preliminary_analysis_service import _line
        results, errors = _run_pair(
            SessionLocal,
            ids=ids,
            work=[
                (ids["actor"], "pg-reused-key", None),
                (second_actor_id, "pg-reused-key", [_line(transport_percentage=10.0)]),
            ],
        )

        assert len(results) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], HTTPException)
        assert errors[0].status_code == 409
        assert errors[0].detail["error_code"] == "preliminary_analysis_idempotency_key_reused"
        _assert_one_fact_and_audit(SessionLocal, ids)
    finally:
        setup.close()
        engine.dispose()


def test_postgresql_concurrent_different_keys_have_one_typed_already_finalized() -> None:
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
                (ids["actor"], "pg-project-key-a", None),
                (ids["actor"], "pg-project-key-b", None),
            ],
        )

        assert len(results) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], HTTPException)
        assert errors[0].status_code == 409
        assert errors[0].detail["error_code"] == "preliminary_analysis_already_finalized"
        _assert_one_fact_and_audit(SessionLocal, ids)
    finally:
        setup.close()
        engine.dispose()
