"""S15-PR-002 unit tests for Reliable Task Job and Transactional Outbox Foundation."""
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.db import Base
import app.modules.excel_import.models  # noqa: F401
from app.modules.workflow_workbench.application.reliable_job_service import (
    claim_job_lease,
    complete_job,
    create_durable_job,
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_create_durable_job_idempotency(db_session: Session):
    """Verify transactional outbox job creation and idempotency key deduplication."""
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    key = "job-key-001"

    job1 = create_durable_job(
        db_session,
        actor_id=actor_id,
        org_id=org_id,
        job_type="document_extraction",
        idempotency_key=key,
        payload={"file": "test.docx"},
    )

    job2 = create_durable_job(
        db_session,
        actor_id=actor_id,
        org_id=org_id,
        job_type="document_extraction",
        idempotency_key=key,
        payload={"file": "test.docx"},
    )

    assert job1.id == job2.id
    assert job1.status == "pending"


def test_claim_lease_and_stale_generation_rejection(db_session: Session):
    """Verify lease claiming and stale generation token rejection (ADR 0032)."""
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    key = "job-key-002"

    job = create_durable_job(
        db_session,
        actor_id=actor_id,
        org_id=org_id,
        job_type="document_extraction",
        idempotency_key=key,
        payload={"file": "test.docx"},
    )

    claimed_job, attempt = claim_job_lease(
        db_session,
        worker_id="worker-node-1",
        job_id=job.id,
        org_id=org_id,
        lease_duration_seconds=60,
    )

    assert claimed_job.status == "claimed"
    assert claimed_job.lease_owner == "worker-node-1"
    assert attempt.attempt_no == 1

    # Attempt complete with invalid (stale) generation token should raise 409
    with pytest.raises(HTTPException) as exc_info:
        complete_job(
            db_session,
            worker_id="worker-node-1",
            job_id=job.id,
            org_id=org_id,
            attempt_id=attempt.id,
            generation_token=999,  # Invalid token
            result_payload={"status": "done"},
        )
    assert exc_info.value.status_code == 409

    # Complete with valid generation token succeeds
    done_job = complete_job(
        db_session,
        worker_id="worker-node-1",
        job_id=job.id,
        org_id=org_id,
        attempt_id=attempt.id,
        generation_token=claimed_job.generation_token,
        result_payload={"status": "done"},
    )
    assert done_job.status == "completed"


def test_claim_lease_conflict_and_expired_reclaim(db_session: Session):
    """Verify active lease conflict and safe reclaim after lease expiry."""
    from datetime import datetime, timedelta, timezone

    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    key = "job-key-003"

    job = create_durable_job(
        db_session,
        actor_id=actor_id,
        org_id=org_id,
        job_type="document_extraction",
        idempotency_key=key,
        payload={"file": "test.docx"},
    )

    # Worker 1 claims lease
    claimed_job1, _ = claim_job_lease(
        db_session,
        worker_id="worker-1",
        job_id=job.id,
        org_id=org_id,
        lease_duration_seconds=300,
    )
    assert claimed_job1.lease_owner == "worker-1"

    # Worker 2 trying to claim active lease raises 409
    with pytest.raises(HTTPException) as exc_info:
        claim_job_lease(
            db_session,
            worker_id="worker-2",
            job_id=job.id,
            org_id=org_id,
            lease_duration_seconds=300,
        )
    assert exc_info.value.status_code == 409
    assert "đang được xử lý" in exc_info.value.detail

    # Simulate lease expiry for Worker 1
    claimed_job1.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    db_session.commit()

    # Worker 2 can now safely reclaim the expired lease
    reclaimed_job, attempt2 = claim_job_lease(
        db_session,
        worker_id="worker-2",
        job_id=job.id,
        org_id=org_id,
        lease_duration_seconds=300,
    )
    assert reclaimed_job.lease_owner == "worker-2"
    assert attempt2.attempt_no == 2
    assert attempt2.worker_id == "worker-2"


def test_max_attempts_dead_letter_transition(db_session: Session):
    """Verify job transitions to dead_letter when max_attempts is reached."""
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    key = "job-key-004"

    job = create_durable_job(
        db_session,
        actor_id=actor_id,
        org_id=org_id,
        job_type="document_extraction",
        idempotency_key=key,
        payload={"file": "test.docx"},
        max_attempts=2,
    )

    # Attempt 1
    claimed1, _ = claim_job_lease(db_session, worker_id="w1", job_id=job.id, org_id=org_id)
    assert claimed1.attempt_count == 1
    # Expire attempt 1 lease
    claimed1.lease_expires_at = None
    claimed1.status = "pending"
    db_session.commit()

    # Attempt 2
    claimed2, _ = claim_job_lease(db_session, worker_id="w2", job_id=job.id, org_id=org_id)
    assert claimed2.attempt_count == 2
    # Expire attempt 2 lease
    claimed2.lease_expires_at = None
    claimed2.status = "pending"
    db_session.commit()

    # Attempt 3 exceeds max_attempts (2) -> dead_letter
    with pytest.raises(HTTPException) as exc_info:
        claim_job_lease(db_session, worker_id="w3", job_id=job.id, org_id=org_id)
    assert exc_info.value.status_code == 409
    assert "Dead Letter" in exc_info.value.detail

    # Verify status in DB is dead_letter
    db_job = db_session.query(type(job)).filter_by(id=job.id).first()
    assert db_job.status == "dead_letter"


def test_organization_scoping_isolation(db_session: Session):
    """Verify multi-tenant isolation across organization_id."""
    org1_id = uuid.uuid4()
    org2_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    key = "job-key-005"

    job_org1 = create_durable_job(
        db_session,
        actor_id=actor_id,
        org_id=org1_id,
        job_type="document_extraction",
        idempotency_key=key,
        payload={"file": "org1.docx"},
    )

    # Claim with wrong org_id raises 404
    with pytest.raises(HTTPException) as exc_info:
        claim_job_lease(
            db_session,
            worker_id="worker-1",
            job_id=job_org1.id,
            org_id=org2_id,
        )
    assert exc_info.value.status_code == 404

