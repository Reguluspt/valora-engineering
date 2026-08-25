"""S15-PR-002 Reliable Task Job and Transactional Outbox Application Services."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.excel_import.models import TaskJob, TaskJobAttempt


def create_durable_job(
    db: Session,
    *,
    actor_id: uuid.UUID,
    org_id: uuid.UUID,
    job_type: str,
    idempotency_key: str,
    payload: dict[str, Any],
    max_attempts: int = 3,
) -> TaskJob:
    """Create a transactional outbox job with idempotency key guarantee."""
    existing = (
        db.query(TaskJob)
        .filter(
            TaskJob.organization_id == org_id,
            TaskJob.idempotency_key == idempotency_key,
        )
        .first()
    )
    if existing:
        return existing

    job = TaskJob(
        id=uuid.uuid4(),
        organization_id=org_id,
        job_type=job_type,
        status="pending",
        idempotency_key=idempotency_key,
        payload=payload,
        generation_token=1,
        attempt_count=0,
        max_attempts=max_attempts,
        created_by_user_id=actor_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def claim_job_lease(
    db: Session,
    *,
    worker_id: str,
    job_id: uuid.UUID,
    org_id: uuid.UUID,
    lease_duration_seconds: int = 300,
) -> tuple[TaskJob, TaskJobAttempt]:
    """Claim a lease on a pending or expired job.
    
    Safe reclaim: If lease_expires_at < now, the job can be reclaimed by a new worker.
    """
    now = datetime.now(timezone.utc)
    job = (
        db.query(TaskJob)
        .filter(
            TaskJob.organization_id == org_id,
            TaskJob.id == job_id,
        )
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy task job.")

    if job.status not in {"pending", "claimed"}:
        raise HTTPException(status_code=409, detail="Task job đã kết thúc hoặc không ở trạng thái chờ.")

    if job.status == "claimed" and job.lease_expires_at and job.lease_expires_at > now and job.lease_owner != worker_id:
        raise HTTPException(status_code=409, detail="Task job đang được xử lý bởi worker khác.")

    if job.attempt_count >= job.max_attempts:
        job.status = "dead_letter"
        db.commit()
        raise HTTPException(status_code=409, detail="Task job đã vượt quá số lần thử tối đa (Dead Letter).")

    job.status = "claimed"
    job.lease_owner = worker_id
    job.lease_expires_at = now + timedelta(seconds=lease_duration_seconds)
    job.attempt_count += 1
    job.generation_token += 1

    attempt = TaskJobAttempt(
        id=uuid.uuid4(),
        organization_id=org_id,
        job_id=job.id,
        attempt_no=job.attempt_count,
        status="running",
        worker_id=worker_id,
        started_at=now,
    )
    db.add(attempt)
    db.commit()
    db.refresh(job)
    db.refresh(attempt)
    return job, attempt


def complete_job(
    db: Session,
    *,
    worker_id: str,
    job_id: uuid.UUID,
    org_id: uuid.UUID,
    attempt_id: uuid.UUID,
    generation_token: int,
    result_payload: dict[str, Any],
) -> TaskJob:
    """Complete a task job cleanly. Protects against stale generation overwrites."""
    now = datetime.now(timezone.utc)
    job = (
        db.query(TaskJob)
        .filter(
            TaskJob.organization_id == org_id,
            TaskJob.id == job_id,
        )
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy task job.")

    if job.generation_token != generation_token:
        raise HTTPException(status_code=409, detail="Stale generation token: Kết quả công việc cũ bị từ chối.")

    attempt = (
        db.query(TaskJobAttempt)
        .filter(
            TaskJobAttempt.id == attempt_id,
            TaskJobAttempt.job_id == job_id,
        )
        .first()
    )
    if attempt:
        attempt.status = "succeeded"
        attempt.finished_at = now

    job.status = "completed"
    job.result_payload = result_payload
    job.lease_owner = None
    job.lease_expires_at = None

    db.commit()
    db.refresh(job)
    return job
