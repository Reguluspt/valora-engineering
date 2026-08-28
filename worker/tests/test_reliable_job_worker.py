"""End-to-end SQLite tests for the reliable job consumer."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.document_engine_intelligence.application.dossier_bundle_service import (
    DossierSourceSpec,
    create_paired_dossier_bundle,
)
from app.modules.excel_import.models import TaskJob, TaskJobAttempt
from app.modules.project_master_data.models import (
    AuditEvent,
    Customer,
    OrganizationProfile,
    OrganizationStatus,
    Role,
    User,
    UserRole,
    UserStatus,
)
from app.modules.workflow_workbench.application.reliable_job_service import (
    enqueue_durable_job,
)
from worker.runtime import JobExecutionContext, ReliableJobWorker


@dataclass(frozen=True)
class RuntimeSeed:
    session_factory: sessionmaker[Session]
    job_id: object


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


def _seed_job(
    factory: sessionmaker[Session], *, slug: str, max_attempts: int = 3
) -> RuntimeSeed:
    with factory() as db:
        organization = OrganizationProfile(
            legal_name=f"Organization {slug}",
            organization_slug=slug,
            status=OrganizationStatus.ACTIVE,
        )
        role = Role(
            code=f"worker-role-{slug}",
            display_name=f"Worker role {slug}",
            permissions=["document_intelligence:job:create"],
        )
        db.add_all([organization, role])
        db.commit()
        actor = User(
            organization_id=organization.id,
            email=f"actor-{slug}@example.test",
            full_name=f"Actor {slug}",
            status=UserStatus.ACTIVE,
        )
        db.add(actor)
        db.commit()
        db.add(UserRole(user_id=actor.id, role_id=role.id, is_active=True))
        db.commit()
        customer = Customer(
            organization_id=organization.id,
            legal_name=f"Customer {slug}",
            status="active",
            created_by=actor.id,
        )
        db.add(customer)
        db.commit()
        bundle, sources = create_paired_dossier_bundle(
            db,
            actor=actor,
            org_id=organization.id,
            customer_id=customer.id,
            project_id=None,
            bundle_code=f"HS-{slug}",
            files=[
                DossierSourceSpec(
                    file_role="customer_asset_list",
                    file_name="assets.xlsx",
                    file_size_bytes=100,
                    checksum_sha256="a" * 64,
                    storage_object_key=f"verified/{slug}/assets.xlsx",
                ),
                DossierSourceSpec(
                    file_role="final_appraisal_report",
                    file_name="report.docx",
                    file_size_bytes=200,
                    checksum_sha256="b" * 64,
                    storage_object_key=f"verified/{slug}/report.docx",
                ),
            ],
        )
        job = enqueue_durable_job(
            db,
            actor=actor,
            org_id=organization.id,
            job_type="document_extraction",
            idempotency_key=f"worker-job-{slug}",
            payload={
                "dossier_bundle_id": str(bundle.id),
                "source_file_id": str(sources[1].id),
            },
            max_attempts=max_attempts,
        )
        db.commit()
        return RuntimeSeed(factory, job.id)


def test_worker_claims_dispatches_and_completes(
    session_factory: sessionmaker[Session],
) -> None:
    seed = _seed_job(session_factory, slug="success")
    seen: list[JobExecutionContext] = []

    def handler(context: JobExecutionContext) -> dict[str, object]:
        seen.append(context)
        return {"processed": True, "source_file_id": context.payload["source_file_id"]}

    worker = ReliableJobWorker(
        session_factory=session_factory,
        handlers={"document_extraction": handler},
        worker_id="worker-success",
        lease_duration_seconds=30,
        heartbeat_interval_seconds=10,
    )
    assert worker.run_once() is True
    assert worker.run_once() is False
    assert len(seen) == 1

    with session_factory() as db:
        job = db.query(TaskJob).filter_by(id=seed.job_id).one()
        attempt = db.query(TaskJobAttempt).filter_by(job_id=seed.job_id).one()
        assert job.status == "completed"
        assert job.result_payload["processed"] is True
        assert attempt.status == "succeeded"
        assert attempt.worker_id == "worker-success"
        assert (
            db.query(AuditEvent)
            .filter_by(entity_id=seed.job_id, event_name="TaskJobCompleted")
            .count()
            == 1
        )


def test_worker_failure_is_recorded_and_dead_lettered(
    session_factory: sessionmaker[Session],
) -> None:
    seed = _seed_job(session_factory, slug="failure", max_attempts=1)

    def failing_handler(_context: JobExecutionContext) -> dict[str, object]:
        raise RuntimeError("deterministic parser failure")

    worker = ReliableJobWorker(
        session_factory=session_factory,
        handlers={"document_extraction": failing_handler},
        worker_id="worker-failure",
        lease_duration_seconds=30,
        heartbeat_interval_seconds=10,
    )
    assert worker.run_once() is True

    with session_factory() as db:
        job = db.query(TaskJob).filter_by(id=seed.job_id).one()
        attempt = db.query(TaskJobAttempt).filter_by(job_id=seed.job_id).one()
        assert job.status == "dead_letter"
        assert job.last_error_code == "job_handler_failed"
        assert attempt.status == "failed"
        assert attempt.error_code == "job_handler_failed"
        assert "deterministic parser failure" in attempt.error_message
