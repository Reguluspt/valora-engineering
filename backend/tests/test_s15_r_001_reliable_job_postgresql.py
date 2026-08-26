"""PostgreSQL-only evidence for S15-R-001 constraints and SKIP LOCKED claims."""
from __future__ import annotations

import os
import threading
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.modules.ai_governance_security.models import (
    SecurityAuditLog,
    SecurityEvent,
    TenantBoundaryCheck,
)
from app.modules.excel_import.models import (
    DossierBundle,
    DossierSourceFile,
    TaskJob,
    TaskJobAttempt,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    Customer,
    OrganizationProfile,
    Role,
    User,
    UserRole,
)
from app.modules.workflow_workbench.application.reliable_job_service import (
    claim_next_job,
    enqueue_durable_job,
)
from tests.test_s15_pr_002_reliable_job_outbox import _seed_dossier

_EXPECTED_HEAD = "b0c1d2e3f4a5"


def _postgres_engine_or_skip():
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url or not url.startswith("postgres"):
        if os.getenv("CI") == "true":
            pytest.fail("CI=true requires PostgreSQL TEST_DATABASE_URL for S15-R-001")
        pytest.skip("PostgreSQL is required for S15-R-001 concurrency proof")
    engine = create_engine(url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)
    with engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    if version != _EXPECTED_HEAD:
        engine.dispose()
        if os.getenv("CI") == "true":
            pytest.fail(f"CI PostgreSQL is not at S15-R-001 head: {version}")
        pytest.skip(f"PostgreSQL is not at S15-R-001 head: {version}")
    return engine


def _cleanup(SessionLocal, *, org_id: uuid.UUID) -> None:
    db: Session = SessionLocal()
    try:
        user_ids = [row[0] for row in db.query(User.id).filter_by(organization_id=org_id)]
        role_ids = [
            row[0]
            for row in db.query(UserRole.role_id).filter(UserRole.user_id.in_(user_ids)).all()
        ]
        db.query(AuditEvent).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(TenantBoundaryCheck).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(SecurityAuditLog).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(SecurityEvent).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(TaskJobAttempt).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(TaskJob).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(DossierSourceFile).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(DossierBundle).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
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


def test_postgresql_reliable_job_constraints_are_installed() -> None:
    engine = _postgres_engine_or_skip()
    try:
        inspector = inspect(engine)
        job_fks = {item["name"] for item in inspector.get_foreign_keys("task_jobs")}
        attempt_fks = {
            item["name"] for item in inspector.get_foreign_keys("task_job_attempts")
        }
        job_checks = {
            item["name"] for item in inspector.get_check_constraints("task_jobs")
        }
        attempt_checks = {
            item["name"]
            for item in inspector.get_check_constraints("task_job_attempts")
        }
        dossier_fks = {
            item["name"] for item in inspector.get_foreign_keys("dossier_bundles")
        }
        assert "fk_task_job_creator_tenant" in job_fks
        assert "fk_task_job_attempt_job_tenant" in attempt_fks
        assert {
            "chk_task_job_lease_shape",
            "chk_task_job_attempt_bounds",
            "chk_task_job_completed_shape",
            "chk_task_job_cancelled_shape",
        } <= job_checks
        assert {
            "chk_task_job_attempt_status",
            "chk_task_job_attempt_finished_shape",
        } <= attempt_checks
        assert {
            "fk_dossier_bundle_customer_tenant",
            "fk_dossier_bundle_project_tenant",
            "fk_dossier_bundle_creator_tenant",
        } <= dossier_fks
        columns = {item["name"]: item for item in inspector.get_columns("task_jobs")}
        assert str(columns["payload"]["type"]).upper() == "JSONB"
        assert str(columns["result_payload"]["type"]).upper() == "JSONB"
    finally:
        engine.dispose()


def test_postgresql_skip_locked_allows_only_one_claim_for_one_job() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    setup = SessionLocal()
    org_id = None
    try:
        actor, bundle, source = _seed_dossier(setup, f"pg-jobs-{uuid.uuid4().hex[:8]}")
        org_id = actor.organization_id
        job = enqueue_durable_job(
            setup,
            actor=actor,
            org_id=org_id,
            job_type="document_extraction",
            idempotency_key=f"pg-claim-{uuid.uuid4()}",
            payload={
                "dossier_bundle_id": str(bundle.id),
                "source_file_id": str(source.id),
            },
        )
        setup.commit()
        job_id = job.id
    finally:
        setup.close()

    barrier = threading.Barrier(2, timeout=30)
    results: list[tuple[uuid.UUID, uuid.UUID] | None] = []
    errors: list[BaseException] = []

    def claim(worker_id: str) -> None:
        db = SessionLocal()
        try:
            barrier.wait(timeout=30)
            claimed = claim_next_job(
                db,
                worker_id=worker_id,
                lease_duration_seconds=60,
            )
            results.append(None if claimed is None else (claimed[0].id, claimed[1].id))
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [
        threading.Thread(target=claim, args=(f"pg-worker-{index}",), daemon=True)
        for index in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    try:
        assert all(not thread.is_alive() for thread in threads)
        assert errors == []
        claimed_results = [item for item in results if item is not None]
        assert len(claimed_results) == 1
        assert claimed_results[0][0] == job_id
        verify = SessionLocal()
        try:
            persisted = verify.query(TaskJob).filter_by(id=job_id).one()
            assert persisted.status == "claimed"
            assert persisted.attempt_count == 1
            assert verify.query(TaskJobAttempt).filter_by(job_id=job_id).count() == 1
        finally:
            verify.close()
    finally:
        if org_id is not None:
            _cleanup(SessionLocal, org_id=org_id)
        engine.dispose()
