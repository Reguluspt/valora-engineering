"""S15-R-001 tests for durable jobs, leases, fencing and retries."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.ai_governance_security.models import SecurityEvent
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
    cancel_job,
    claim_job_lease,
    claim_next_job,
    complete_job,
    enqueue_durable_job,
    fail_job,
    renew_job_lease,
)


@pytest.fixture
def db_session() -> Session:
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
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed_dossier(db: Session, slug: str = "jobs") -> tuple[User, object, object]:
    organization = OrganizationProfile(
        legal_name=f"Organization {slug}",
        organization_slug=slug,
        status=OrganizationStatus.ACTIVE,
    )
    role = Role(
        code=f"job-creator-{slug}",
        display_name=f"Job creator {slug}",
        permissions=["document_intelligence:job:create"],
    )
    db.add_all([organization, role])
    db.commit()
    actor = User(
        organization_id=organization.id,
        email=f"creator-{slug}@example.test",
        full_name=f"Creator {slug}",
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
    return actor, bundle, sources[1]


def _enqueue(
    db: Session,
    *,
    actor: User,
    bundle: object,
    source: object,
    key: str,
    max_attempts: int = 3,
) -> TaskJob:
    return enqueue_durable_job(
        db,
        actor=actor,
        org_id=actor.organization_id,
        job_type="document_extraction",
        idempotency_key=key,
        payload={
            "dossier_bundle_id": str(bundle.id),
            "source_file_id": str(source.id),
        },
        max_attempts=max_attempts,
        correlation_id=f"corr-{key}",
    )


def test_enqueue_is_transactional_and_exactly_idempotent(db_session: Session) -> None:
    actor, bundle, source = _seed_dossier(db_session, "outbox")
    job = _enqueue(
        db_session,
        actor=actor,
        bundle=bundle,
        source=source,
        key="job-outbox-001",
    )
    assert job.id is not None
    assert db_session.query(AuditEvent).filter_by(event_name="TaskJobQueued").count() == 1

    db_session.rollback()
    assert db_session.query(TaskJob).count() == 0
    assert db_session.query(AuditEvent).filter_by(event_name="TaskJobQueued").count() == 0

    first = _enqueue(
        db_session,
        actor=actor,
        bundle=bundle,
        source=source,
        key="job-outbox-001",
    )
    db_session.commit()
    second = _enqueue(
        db_session,
        actor=actor,
        bundle=bundle,
        source=source,
        key="job-outbox-001",
    )
    assert second.id == first.id
    db_session.rollback()

    with pytest.raises(HTTPException) as exc_info:
        enqueue_durable_job(
            db_session,
            actor=actor,
            org_id=actor.organization_id,
            job_type="dossier_alignment",
            idempotency_key="job-outbox-001",
            payload={"dossier_bundle_id": str(bundle.id)},
            correlation_id="corr-job-outbox-001",
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error_code"] == "job_idempotency_conflict"
    db_session.rollback()


def test_claim_is_idempotent_for_owner_and_fences_other_workers(db_session: Session) -> None:
    actor, bundle, source = _seed_dossier(db_session, "claim")
    job = _enqueue(
        db_session, actor=actor, bundle=bundle, source=source, key="job-claim"
    )
    db_session.commit()

    claimed, attempt = claim_job_lease(
        db_session,
        worker_id="worker-1",
        job_id=job.id,
        org_id=actor.organization_id,
        lease_duration_seconds=60,
    )
    repeated, repeated_attempt = claim_job_lease(
        db_session,
        worker_id="worker-1",
        job_id=job.id,
        org_id=actor.organization_id,
        lease_duration_seconds=60,
    )
    assert repeated.id == claimed.id
    assert repeated_attempt.id == attempt.id
    assert repeated.attempt_count == 1
    assert repeated.generation_token == 1

    with pytest.raises(HTTPException) as exc_info:
        claim_job_lease(
            db_session,
            worker_id="worker-2",
            job_id=job.id,
            org_id=actor.organization_id,
            lease_duration_seconds=60,
        )
    assert exc_info.value.detail["error_code"] == "active_lease_conflict"
    assert (
        db_session.query(AuditEvent)
        .filter_by(event_name="TaskJobWorkerMutationRejected", entity_id=job.id)
        .count()
        == 1
    )


def test_expired_lease_times_out_attempt_and_stale_completion_is_rejected(
    db_session: Session,
) -> None:
    actor, bundle, source = _seed_dossier(db_session, "reclaim")
    job = _enqueue(
        db_session, actor=actor, bundle=bundle, source=source, key="job-reclaim"
    )
    db_session.commit()
    first_job, first_attempt = claim_job_lease(
        db_session,
        worker_id="worker-old",
        job_id=job.id,
        org_id=actor.organization_id,
        lease_duration_seconds=60,
    )
    expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    first_job.lease_expires_at = expired_at
    first_attempt.lease_expires_at = expired_at
    db_session.commit()

    reclaimed, second_attempt = claim_job_lease(
        db_session,
        worker_id="worker-new",
        job_id=job.id,
        org_id=actor.organization_id,
        lease_duration_seconds=60,
    )
    db_session.refresh(first_attempt)
    assert first_attempt.status == "timed_out"
    assert second_attempt.attempt_no == 2
    assert reclaimed.generation_token == 2

    with pytest.raises(HTTPException) as stale_error:
        complete_job(
            db_session,
            worker_id="worker-old",
            job_id=job.id,
            org_id=actor.organization_id,
            attempt_id=first_attempt.id,
            generation_token=1,
            result_payload={"status": "stale"},
        )
    assert stale_error.value.detail["error_code"] == "stale_or_invalid_lease"

    completed = complete_job(
        db_session,
        worker_id="worker-new",
        job_id=job.id,
        org_id=actor.organization_id,
        attempt_id=second_attempt.id,
        generation_token=2,
        result_payload={"status": "done"},
    )
    assert completed.status == "completed"
    replay = complete_job(
        db_session,
        worker_id="worker-new",
        job_id=job.id,
        org_id=actor.organization_id,
        attempt_id=second_attempt.id,
        generation_token=2,
        result_payload={"status": "done"},
    )
    assert replay.id == completed.id


def test_failure_uses_backoff_then_dead_letters(db_session: Session) -> None:
    actor, bundle, source = _seed_dossier(db_session, "retry")
    job = _enqueue(
        db_session,
        actor=actor,
        bundle=bundle,
        source=source,
        key="job-retry",
        max_attempts=2,
    )
    db_session.commit()
    claimed, attempt = claim_job_lease(
        db_session,
        worker_id="worker-retry",
        job_id=job.id,
        org_id=actor.organization_id,
    )
    retrying = fail_job(
        db_session,
        worker_id="worker-retry",
        job_id=job.id,
        org_id=actor.organization_id,
        attempt_id=attempt.id,
        generation_token=claimed.generation_token,
        error_code="extract_failed",
        error_message="Parser failed deterministically.",
        retry_base_seconds=5,
    )
    assert retrying.status == "pending"
    assert retrying.available_at > retrying.updated_at
    replayed_failure = fail_job(
        db_session,
        worker_id="worker-retry",
        job_id=job.id,
        org_id=actor.organization_id,
        attempt_id=attempt.id,
        generation_token=claimed.generation_token,
        error_code="extract_failed",
        error_message="Parser failed deterministically.",
        retry_base_seconds=5,
    )
    assert replayed_failure.id == retrying.id
    assert db_session.query(TaskJobAttempt).filter_by(job_id=job.id).count() == 1

    with pytest.raises(HTTPException) as early_retry:
        claim_job_lease(
            db_session,
            worker_id="worker-retry",
            job_id=job.id,
            org_id=actor.organization_id,
        )
    assert early_retry.value.detail["error_code"] == "retry_not_ready"

    retrying.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()
    claimed_again, attempt_again = claim_job_lease(
        db_session,
        worker_id="worker-retry",
        job_id=job.id,
        org_id=actor.organization_id,
    )
    dead = fail_job(
        db_session,
        worker_id="worker-retry",
        job_id=job.id,
        org_id=actor.organization_id,
        attempt_id=attempt_again.id,
        generation_token=claimed_again.generation_token,
        error_code="extract_failed",
        error_message="Parser failed again.",
    )
    assert dead.status == "dead_letter"
    assert dead.lease_owner is None
    assert db_session.query(TaskJobAttempt).filter_by(job_id=job.id).count() == 2


def test_renew_cancel_and_claim_next(db_session: Session) -> None:
    actor, bundle, source = _seed_dossier(db_session, "lifecycle")
    first = _enqueue(
        db_session, actor=actor, bundle=bundle, source=source, key="job-lifecycle-1"
    )
    second = _enqueue(
        db_session, actor=actor, bundle=bundle, source=source, key="job-lifecycle-2"
    )
    db_session.commit()

    claimed = claim_next_job(db_session, worker_id="worker-next", lease_duration_seconds=30)
    assert claimed is not None
    job, attempt = claimed
    before = job.lease_expires_at
    renewed_job, renewed_attempt = renew_job_lease(
        db_session,
        worker_id="worker-next",
        job_id=job.id,
        org_id=actor.organization_id,
        attempt_id=attempt.id,
        generation_token=job.generation_token,
        lease_duration_seconds=60,
    )
    assert renewed_job.lease_expires_at > before
    assert renewed_attempt.lease_expires_at == renewed_job.lease_expires_at

    cancelled = cancel_job(
        db_session,
        actor=actor,
        org_id=actor.organization_id,
        job_id=job.id,
    )
    assert cancelled.status == "cancelled"
    assert cancelled.lease_owner is None
    db_session.refresh(attempt)
    assert attempt.status == "cancelled"

    remaining = claim_next_job(db_session, worker_id="worker-next")
    assert remaining is not None
    assert remaining[0].id in {first.id, second.id} - {job.id}


def test_job_target_cannot_cross_tenant_or_trust_client_context(db_session: Session) -> None:
    actor_a, bundle_a, source_a = _seed_dossier(db_session, "job-tenant-a")
    actor_b, bundle_b, source_b = _seed_dossier(db_session, "job-tenant-b")

    with pytest.raises(HTTPException) as context_error:
        enqueue_durable_job(
            db_session,
            actor=actor_a,
            org_id=actor_a.organization_id,
            job_type="document_extraction",
            idempotency_key="client-context",
            payload={
                "organization_id": str(actor_b.organization_id),
                "dossier_bundle_id": str(bundle_a.id),
                "source_file_id": str(source_a.id),
            },
        )
    assert context_error.value.detail["error_code"] == "client_security_context_forbidden"
    db_session.rollback()

    with pytest.raises(HTTPException) as tenant_error:
        enqueue_durable_job(
            db_session,
            actor=actor_a,
            org_id=actor_a.organization_id,
            job_type="document_extraction",
            idempotency_key="cross-tenant-target",
            payload={
                "dossier_bundle_id": str(bundle_b.id),
                "source_file_id": str(source_b.id),
            },
        )
    assert tenant_error.value.status_code == 404
    assert db_session.query(SecurityEvent).filter_by(event_type="cross_tenant_access_attempt").count() == 1
    assert actor_b.organization_id != actor_a.organization_id
