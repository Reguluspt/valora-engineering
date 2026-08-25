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
