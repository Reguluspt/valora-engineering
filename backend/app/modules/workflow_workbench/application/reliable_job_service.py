"""Reliable, tenant-safe task job and attempt state machine."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query, Session, selectinload

from app.core.audit import log_audit_event
from app.core.rbac import derive_effective_permissions
from app.modules.ai_governance_security.application.security_audit_service import (
    record_authorization_denial,
    record_tenant_boundary_check,
)
from app.modules.excel_import.models import (
    DossierBundle,
    DossierSourceFile,
    TaskJob,
    TaskJobAttempt,
    TaskJobAttemptStatus,
    TaskJobStatus,
)
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserRole,
    UserStatus,
)

_REQUIRED_PERMISSION = "document_intelligence:job:create"
_JOB_TYPES = {"document_extraction", "dossier_alignment"}
_MAX_JSON_BYTES = 262_144
_MAX_ATTEMPTS = 10
_MAX_LEASE_SECONDS = 3_600
_MAX_ERROR_MESSAGE = 2_000
_MAX_BACKOFF_SECONDS = 3_600
_CLIENT_CONTEXT_KEYS = {"actor_id", "created_by_user_id", "organization_id", "org_id"}


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _abort(db: Session, status: int, code: str, detail: str) -> None:
    db.rollback()
    raise _error(status, code, detail)


def _status_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _canonical_json(value: Any, *, field_name: str) -> tuple[Any, str]:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise _error(422, f"invalid_{field_name}", f"{field_name} không phải JSON hợp lệ.") from exc
    if len(encoded.encode("utf-8")) > _MAX_JSON_BYTES:
        raise _error(413, f"{field_name}_too_large", f"{field_name} vượt quá giới hạn cho phép.")
    return json.loads(encoded), encoded


def _audit_target_id(org_id: uuid.UUID, idempotency_key: str) -> uuid.UUID:
    return uuid.uuid5(org_id, f"task-job:{idempotency_key}")


def _persist_boundary_denial(
    db: Session,
    *,
    org_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    resource_type: str,
    resource_id: uuid.UUID,
    reason_code: str,
    detail: str,
) -> None:
    db.rollback()
    try:
        record_tenant_boundary_check(
            db,
            organization_id=org_id,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            passed=False,
            failure_reason=reason_code,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _error(
            503,
            "security_audit_unavailable",
            "Không thể ghi nhận kiểm tra bảo mật; thao tác đã bị chặn.",
        ) from exc
    raise _error(404, "resource_not_found", detail)


def _persist_authorization_denial(
    db: Session,
    *,
    org_id: uuid.UUID,
    actor_id: uuid.UUID,
    target_id: uuid.UUID,
) -> None:
    db.rollback()
    try:
        record_authorization_denial(
            db,
            organization_id=org_id,
            actor_id=actor_id,
            permission_code=_REQUIRED_PERMISSION,
            target_type="TaskJob",
            target_id=target_id,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _error(
            503,
            "security_audit_unavailable",
            "Không thể ghi nhận kiểm tra bảo mật; thao tác đã bị chặn.",
        ) from exc
    raise _error(403, "permission_denied", "Tài khoản không có quyền tạo công việc tài liệu.")


def _persist_worker_rejection(
    db: Session,
    *,
    job: TaskJob,
    worker_id: str,
    reason_code: str,
    detail: str,
) -> None:
    job_id = job.id
    org_id = job.organization_id
    db.rollback()
    try:
        log_audit_event(
            db,
            event_name="TaskJobWorkerMutationRejected",
            entity_type="TaskJob",
            entity_id=job_id,
            organization_id=org_id,
            command_name="MutateTaskJob",
            payload={"worker_id": worker_id, "reason_code": reason_code},
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _error(
            503,
            "audit_unavailable",
            "Không thể ghi nhận thao tác worker; kết quả đã bị từ chối.",
        ) from exc
    raise _error(409, reason_code, detail)


def _reload_actor(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    target_id: uuid.UUID,
) -> User:
    organization = (
        db.query(OrganizationProfile)
        .filter(OrganizationProfile.id == org_id)
        .populate_existing()
        .first()
    )
    if organization is None:
        raise _error(404, "resource_not_found", "Không tìm thấy tổ chức.")

    actor_id = getattr(actor, "id", None)
    persisted_actor = None
    if actor_id is not None:
        persisted_actor = (
            db.query(User)
            .options(
                selectinload(User.organization),
                selectinload(User.roles).selectinload(UserRole.role),
            )
            .filter(User.id == actor_id)
            .populate_existing()
            .first()
        )
    if (
        _status_value(organization.status) != OrganizationStatus.ACTIVE.value
        or persisted_actor is None
        or persisted_actor.organization_id != org_id
        or _status_value(persisted_actor.status) != UserStatus.ACTIVE.value
    ):
        _persist_boundary_denial(
            db,
            org_id=org_id,
            actor_id=(persisted_actor.id if persisted_actor is not None else None),
            resource_type="User",
            resource_id=actor_id or uuid.UUID(int=0),
            reason_code="actor_context_invalid",
            detail="Không tìm thấy tổ chức.",
        )
    if _REQUIRED_PERMISSION not in derive_effective_permissions(persisted_actor, db):
        _persist_authorization_denial(
            db,
            org_id=org_id,
            actor_id=persisted_actor.id,
            target_id=target_id,
        )
    return persisted_actor


def _parse_uuid(value: Any, *, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise _error(422, f"invalid_{field_name}", f"{field_name} không hợp lệ.") from exc


def _normalize_and_validate_target(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    job_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if _CLIENT_CONTEXT_KEYS.intersection(payload):
        raise _error(
            422,
            "client_security_context_forbidden",
            "Tenant và actor phải được lấy từ phiên làm việc tin cậy.",
        )

    bundle_id = _parse_uuid(payload.get("dossier_bundle_id"), field_name="dossier_bundle_id")
    bundle = (
        db.query(DossierBundle)
        .filter(DossierBundle.organization_id == org_id, DossierBundle.id == bundle_id)
        .populate_existing()
        .first()
    )
    if bundle is None:
        _persist_boundary_denial(
            db,
            org_id=org_id,
            actor_id=actor.id,
            resource_type="DossierBundle",
            resource_id=bundle_id,
            reason_code="dossier_tenant_boundary_failed",
            detail="Không tìm thấy hồ sơ tài liệu.",
        )
    record_tenant_boundary_check(
        db,
        organization_id=org_id,
        actor_id=actor.id,
        resource_type="DossierBundle",
        resource_id=bundle_id,
        passed=True,
    )

    normalized = dict(payload)
    normalized["dossier_bundle_id"] = str(bundle_id)
    if job_type == "document_extraction":
        source_file_id = _parse_uuid(payload.get("source_file_id"), field_name="source_file_id")
        source_file = (
            db.query(DossierSourceFile)
            .filter(
                DossierSourceFile.organization_id == org_id,
                DossierSourceFile.dossier_bundle_id == bundle_id,
                DossierSourceFile.id == source_file_id,
            )
            .populate_existing()
            .first()
        )
        if source_file is None:
            _persist_boundary_denial(
                db,
                org_id=org_id,
                actor_id=actor.id,
                resource_type="DossierSourceFile",
                resource_id=source_file_id,
                reason_code="source_file_ownership_boundary_failed",
                detail="Không tìm thấy tệp nguồn.",
            )
        record_tenant_boundary_check(
            db,
            organization_id=org_id,
            actor_id=actor.id,
            resource_type="DossierSourceFile",
            resource_id=source_file_id,
            passed=True,
        )
        normalized["source_file_id"] = str(source_file_id)
    return normalized


def _same_job_intent(
    job: TaskJob,
    *,
    actor_id: uuid.UUID,
    job_type: str,
    payload_json: str,
    max_attempts: int,
    correlation_id: str | None,
    causation_id: str | None,
) -> bool:
    _, existing_payload_json = _canonical_json(job.payload, field_name="payload")
    return (
        job.created_by_user_id == actor_id
        and job.job_type == job_type
        and existing_payload_json == payload_json
        and job.max_attempts == max_attempts
        and job.correlation_id == correlation_id
        and job.causation_id == causation_id
    )


def enqueue_durable_job(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    job_type: str,
    idempotency_key: str,
    payload: dict[str, Any],
    max_attempts: int = 3,
    correlation_id: str | None = None,
    causation_id: str | None = None,
) -> TaskJob:
    """Stage a durable job and audit event in the caller-owned transaction."""
    normalized_type = job_type.strip()
    normalized_key = idempotency_key.strip()
    if normalized_type not in _JOB_TYPES:
        raise _error(422, "unsupported_job_type", "Loại công việc không được hỗ trợ.")
    if not normalized_key or len(normalized_key) > 255:
        raise _error(422, "invalid_idempotency_key", "Khóa idempotency không hợp lệ.")
    if not isinstance(payload, dict):
        raise _error(422, "invalid_payload", "payload phải là một đối tượng JSON.")
    if not 1 <= max_attempts <= _MAX_ATTEMPTS:
        raise _error(422, "invalid_max_attempts", "Số lần thử tối đa không hợp lệ.")
    if correlation_id is not None and len(correlation_id) > 128:
        raise _error(422, "invalid_correlation_id", "Mã tương quan không hợp lệ.")
    if causation_id is not None and len(causation_id) > 128:
        raise _error(422, "invalid_causation_id", "Mã nguyên nhân không hợp lệ.")

    target_id = _audit_target_id(org_id, normalized_key)
    persisted_actor = _reload_actor(db, actor=actor, org_id=org_id, target_id=target_id)
    normalized_payload = _normalize_and_validate_target(
        db,
        actor=persisted_actor,
        org_id=org_id,
        job_type=normalized_type,
        payload=payload,
    )
    canonical_payload, payload_json = _canonical_json(normalized_payload, field_name="payload")

    existing = (
        db.query(TaskJob)
        .filter(
            TaskJob.organization_id == org_id,
            TaskJob.idempotency_key == normalized_key,
        )
        .populate_existing()
        .first()
    )
    if existing is not None:
        if not _same_job_intent(
            existing,
            actor_id=persisted_actor.id,
            job_type=normalized_type,
            payload_json=payload_json,
            max_attempts=max_attempts,
            correlation_id=correlation_id,
            causation_id=causation_id,
        ):
            raise _error(
                409,
                "job_idempotency_conflict",
                "Khóa idempotency đã được dùng cho một công việc khác.",
            )
        return existing

    job = TaskJob(
        organization_id=org_id,
        job_type=normalized_type,
        status=TaskJobStatus.PENDING.value,
        idempotency_key=normalized_key,
        payload=canonical_payload,
        generation_token=0,
        attempt_count=0,
        max_attempts=max_attempts,
        available_at=_utc_now(),
        correlation_id=correlation_id,
        causation_id=causation_id,
        created_by_user_id=persisted_actor.id,
    )
    try:
        with db.begin_nested():
            db.add(job)
            db.flush()
            log_audit_event(
                db,
                event_name="TaskJobQueued",
                entity_type="TaskJob",
                entity_id=job.id,
                organization_id=org_id,
                actor_user_id=persisted_actor.id,
                command_name="EnqueueTaskJob",
                correlation_id=correlation_id,
                payload={
                    "job_type": normalized_type,
                    "idempotency_key": normalized_key,
                    "max_attempts": max_attempts,
                    "causation_id": causation_id,
                },
            )
    except IntegrityError:
        existing = (
            db.query(TaskJob)
            .filter(
                TaskJob.organization_id == org_id,
                TaskJob.idempotency_key == normalized_key,
            )
            .populate_existing()
            .first()
        )
        if existing is None or not _same_job_intent(
            existing,
            actor_id=persisted_actor.id,
            job_type=normalized_type,
            payload_json=payload_json,
            max_attempts=max_attempts,
            correlation_id=correlation_id,
            causation_id=causation_id,
        ):
            raise _error(
                409,
                "job_idempotency_conflict",
                "Khóa idempotency đã được dùng cho một công việc khác.",
            )
        return existing
    return job


def _validate_worker(worker_id: str, lease_duration_seconds: int) -> str:
    normalized_worker = worker_id.strip()
    if not normalized_worker or len(normalized_worker) > 100:
        raise _error(422, "invalid_worker_id", "Định danh worker không hợp lệ.")
    if not 1 <= lease_duration_seconds <= _MAX_LEASE_SECONDS:
        raise _error(422, "invalid_lease_duration", "Thời hạn lease không hợp lệ.")
    return normalized_worker


def _lock_query(query: Query[Any], db: Session, *, skip_locked: bool) -> Query[Any]:
    if db.get_bind().dialect.name == "postgresql":
        return query.with_for_update(skip_locked=skip_locked)
    return query


def _current_attempt(db: Session, job: TaskJob) -> TaskJobAttempt | None:
    return (
        db.query(TaskJobAttempt)
        .filter(
            TaskJobAttempt.organization_id == job.organization_id,
            TaskJobAttempt.job_id == job.id,
            TaskJobAttempt.generation_token == job.generation_token,
        )
        .populate_existing()
        .first()
    )


def _mark_dead_letter(db: Session, job: TaskJob, *, reason_code: str, now: datetime) -> None:
    job.status = TaskJobStatus.DEAD_LETTER.value
    job.lease_owner = None
    job.lease_expires_at = None
    job.last_error_code = job.last_error_code or reason_code
    log_audit_event(
        db,
        event_name="TaskJobDeadLettered",
        entity_type="TaskJob",
        entity_id=job.id,
        organization_id=job.organization_id,
        command_name="DeadLetterTaskJob",
        correlation_id=job.correlation_id,
        payload={
            "reason_code": reason_code,
            "attempt_count": job.attempt_count,
            "generation_token": job.generation_token,
            "transitioned_at": now.isoformat(),
        },
    )


def _claim_locked_job(
    db: Session,
    *,
    job: TaskJob,
    worker_id: str,
    lease_duration_seconds: int,
    now: datetime,
    specific_claim: bool,
) -> tuple[TaskJob, TaskJobAttempt] | None:
    if job.status == TaskJobStatus.CLAIMED.value:
        lease_expires = _as_utc(job.lease_expires_at) if job.lease_expires_at else now
        attempt = _current_attempt(db, job)
        if lease_expires > now:
            if job.lease_owner == worker_id and attempt is not None and attempt.status == "running":
                db.commit()
                return job, attempt
            if specific_claim:
                _persist_worker_rejection(
                    db,
                    job=job,
                    worker_id=worker_id,
                    reason_code="active_lease_conflict",
                    detail="Công việc đang được một worker khác xử lý.",
                )
            return None
        if attempt is not None and attempt.status == TaskJobAttemptStatus.RUNNING.value:
            attempt.status = TaskJobAttemptStatus.TIMED_OUT.value
            attempt.finished_at = now
            attempt.error_code = "lease_expired"
            attempt.error_message = "Worker lease expired before completion."
        job.last_error_code = "lease_expired"
        job.last_error_message = "Worker lease expired before completion."

    if job.attempt_count >= job.max_attempts:
        _mark_dead_letter(db, job, reason_code="max_attempts_exhausted", now=now)
        db.commit()
        if specific_claim:
            raise _error(409, "job_dead_lettered", "Công việc đã hết số lần thử cho phép.")
        return None

    lease_expires_at = now + timedelta(seconds=lease_duration_seconds)
    job.status = TaskJobStatus.CLAIMED.value
    job.lease_owner = worker_id
    job.lease_expires_at = lease_expires_at
    job.attempt_count += 1
    job.generation_token += 1
    attempt = TaskJobAttempt(
        organization_id=job.organization_id,
        job_id=job.id,
        attempt_no=job.attempt_count,
        generation_token=job.generation_token,
        status=TaskJobAttemptStatus.RUNNING.value,
        worker_id=worker_id,
        lease_expires_at=lease_expires_at,
        started_at=now,
    )
    db.add(attempt)
    log_audit_event(
        db,
        event_name="TaskJobClaimed",
        entity_type="TaskJob",
        entity_id=job.id,
        organization_id=job.organization_id,
        command_name="ClaimTaskJob",
        correlation_id=job.correlation_id,
        payload={
            "worker_id": worker_id,
            "attempt_no": job.attempt_count,
            "generation_token": job.generation_token,
            "lease_expires_at": lease_expires_at.isoformat(),
        },
    )
    db.commit()
    db.refresh(job)
    db.refresh(attempt)
    return job, attempt


def claim_job_lease(
    db: Session,
    *,
    worker_id: str,
    job_id: uuid.UUID,
    org_id: uuid.UUID,
    lease_duration_seconds: int = 300,
) -> tuple[TaskJob, TaskJobAttempt]:
    """Claim one known job, fencing active owners and timing out expired attempts."""
    normalized_worker = _validate_worker(worker_id, lease_duration_seconds)
    now = _utc_now()
    query = db.query(TaskJob).filter(
        TaskJob.organization_id == org_id,
        TaskJob.id == job_id,
    )
    job = _lock_query(query, db, skip_locked=False).populate_existing().first()
    if job is None:
        _abort(db, 404, "resource_not_found", "Không tìm thấy công việc.")
    if job.status == TaskJobStatus.PENDING.value and _as_utc(job.available_at) > now:
        _abort(db, 409, "retry_not_ready", "Công việc chưa đến thời điểm thử lại.")
    if job.status not in {TaskJobStatus.PENDING.value, TaskJobStatus.CLAIMED.value}:
        _abort(db, 409, "job_not_claimable", "Công việc không còn ở trạng thái có thể nhận.")
    claimed = _claim_locked_job(
        db,
        job=job,
        worker_id=normalized_worker,
        lease_duration_seconds=lease_duration_seconds,
        now=now,
        specific_claim=True,
    )
    if claimed is None:  # pragma: no cover
        raise _error(409, "job_not_claimable", "Công việc không thể nhận.")
    return claimed


def claim_next_job(
    db: Session,
    *,
    worker_id: str,
    lease_duration_seconds: int = 300,
) -> tuple[TaskJob, TaskJobAttempt] | None:
    """Atomically claim the next due job using PostgreSQL SKIP LOCKED."""
    normalized_worker = _validate_worker(worker_id, lease_duration_seconds)
    while True:
        now = _utc_now()
        query = (
            db.query(TaskJob)
            .filter(
                or_(
                    (
                        (TaskJob.status == TaskJobStatus.PENDING.value)
                        & (TaskJob.available_at <= now)
                    ),
                    (
                        (TaskJob.status == TaskJobStatus.CLAIMED.value)
                        & (TaskJob.lease_expires_at <= now)
                    ),
                )
            )
            .order_by(TaskJob.available_at, TaskJob.created_at, TaskJob.id)
        )
        job = _lock_query(query, db, skip_locked=True).populate_existing().first()
        if job is None:
            db.rollback()
            return None
        claimed = _claim_locked_job(
            db,
            job=job,
            worker_id=normalized_worker,
            lease_duration_seconds=lease_duration_seconds,
            now=now,
            specific_claim=False,
        )
        if claimed is not None:
            return claimed


def _load_fenced_execution(
    db: Session,
    *,
    worker_id: str,
    job_id: uuid.UUID,
    org_id: uuid.UUID,
    attempt_id: uuid.UUID,
    generation_token: int,
    now: datetime,
) -> tuple[TaskJob, TaskJobAttempt]:
    query = db.query(TaskJob).filter(
        TaskJob.organization_id == org_id,
        TaskJob.id == job_id,
    )
    job = _lock_query(query, db, skip_locked=False).populate_existing().first()
    if job is None:
        _abort(db, 404, "resource_not_found", "Không tìm thấy công việc.")
    attempt = (
        db.query(TaskJobAttempt)
        .filter(
            TaskJobAttempt.organization_id == org_id,
            TaskJobAttempt.job_id == job_id,
            TaskJobAttempt.id == attempt_id,
        )
        .populate_existing()
        .first()
    )
    valid = (
        job.status == TaskJobStatus.CLAIMED.value
        and job.lease_owner == worker_id
        and job.lease_expires_at is not None
        and _as_utc(job.lease_expires_at) > now
        and job.generation_token == generation_token
        and attempt is not None
        and attempt.status == TaskJobAttemptStatus.RUNNING.value
        and attempt.worker_id == worker_id
        and attempt.generation_token == generation_token
        and attempt.attempt_no == job.attempt_count
        and _as_utc(attempt.lease_expires_at) > now
    )
    if not valid:
        _persist_worker_rejection(
            db,
            job=job,
            worker_id=worker_id,
            reason_code="stale_or_invalid_lease",
            detail="Lease hoặc generation token không còn hợp lệ.",
        )
    return job, attempt


def renew_job_lease(
    db: Session,
    *,
    worker_id: str,
    job_id: uuid.UUID,
    org_id: uuid.UUID,
    attempt_id: uuid.UUID,
    generation_token: int,
    lease_duration_seconds: int = 300,
) -> tuple[TaskJob, TaskJobAttempt]:
    """Renew the current fenced lease for a live attempt."""
    normalized_worker = _validate_worker(worker_id, lease_duration_seconds)
    now = _utc_now()
    job, attempt = _load_fenced_execution(
        db,
        worker_id=normalized_worker,
        job_id=job_id,
        org_id=org_id,
        attempt_id=attempt_id,
        generation_token=generation_token,
        now=now,
    )
    lease_expires_at = now + timedelta(seconds=lease_duration_seconds)
    job.lease_expires_at = lease_expires_at
    attempt.lease_expires_at = lease_expires_at
    log_audit_event(
        db,
        event_name="TaskJobLeaseRenewed",
        entity_type="TaskJob",
        entity_id=job.id,
        organization_id=job.organization_id,
        command_name="RenewTaskJobLease",
        correlation_id=job.correlation_id,
        payload={
            "worker_id": normalized_worker,
            "generation_token": generation_token,
            "lease_expires_at": lease_expires_at.isoformat(),
        },
    )
    db.commit()
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
    """Complete a job only when worker, attempt, generation and lease all match."""
    normalized_worker = _validate_worker(worker_id, 1)
    canonical_result, result_json = _canonical_json(result_payload, field_name="result_payload")
    now = _utc_now()

    replay = (
        db.query(TaskJob)
        .filter(TaskJob.organization_id == org_id, TaskJob.id == job_id)
        .populate_existing()
        .first()
    )
    if replay is None:
        _abort(db, 404, "resource_not_found", "Không tìm thấy công việc.")
    if replay.status == TaskJobStatus.COMPLETED.value:
        attempt = (
            db.query(TaskJobAttempt)
            .filter(
                TaskJobAttempt.organization_id == org_id,
                TaskJobAttempt.job_id == job_id,
                TaskJobAttempt.id == attempt_id,
                TaskJobAttempt.worker_id == normalized_worker,
                TaskJobAttempt.generation_token == generation_token,
                TaskJobAttempt.status == TaskJobAttemptStatus.SUCCEEDED.value,
            )
            .first()
        )
        _, persisted_result_json = _canonical_json(replay.result_payload, field_name="result_payload")
        if attempt is not None and persisted_result_json == result_json:
            db.rollback()
            return replay
        _persist_worker_rejection(
            db,
            job=replay,
            worker_id=normalized_worker,
            reason_code="completion_replay_conflict",
            detail="Kết quả hoàn thành lặp lại không khớp với lần đã ghi nhận.",
        )

    job, attempt = _load_fenced_execution(
        db,
        worker_id=normalized_worker,
        job_id=job_id,
        org_id=org_id,
        attempt_id=attempt_id,
        generation_token=generation_token,
        now=now,
    )
    attempt.status = TaskJobAttemptStatus.SUCCEEDED.value
    attempt.finished_at = now
    job.status = TaskJobStatus.COMPLETED.value
    job.result_payload = canonical_result
    job.completed_at = now
    job.lease_owner = None
    job.lease_expires_at = None
    job.last_error_code = None
    job.last_error_message = None
    log_audit_event(
        db,
        event_name="TaskJobCompleted",
        entity_type="TaskJob",
        entity_id=job.id,
        organization_id=job.organization_id,
        command_name="CompleteTaskJob",
        correlation_id=job.correlation_id,
        payload={
            "worker_id": normalized_worker,
            "attempt_no": attempt.attempt_no,
            "generation_token": generation_token,
        },
    )
    db.commit()
    db.refresh(job)
    return job


def fail_job(
    db: Session,
    *,
    worker_id: str,
    job_id: uuid.UUID,
    org_id: uuid.UUID,
    attempt_id: uuid.UUID,
    generation_token: int,
    error_code: str,
    error_message: str,
    retry_base_seconds: int = 5,
) -> TaskJob:
    """Fail the current attempt and schedule bounded retry or dead-letter transition."""
    normalized_worker = _validate_worker(worker_id, 1)
    normalized_code = error_code.strip()
    normalized_message = error_message.strip()[:_MAX_ERROR_MESSAGE]
    if not normalized_code or len(normalized_code) > 64:
        raise _error(422, "invalid_error_code", "Mã lỗi worker không hợp lệ.")
    if not normalized_message:
        raise _error(422, "invalid_error_message", "Thông tin lỗi worker không hợp lệ.")
    if not 1 <= retry_base_seconds <= _MAX_BACKOFF_SECONDS:
        raise _error(422, "invalid_retry_backoff", "Thời gian thử lại không hợp lệ.")

    now = _utc_now()
    replay_job = (
        db.query(TaskJob)
        .filter(TaskJob.organization_id == org_id, TaskJob.id == job_id)
        .populate_existing()
        .first()
    )
    if replay_job is None:
        _abort(db, 404, "resource_not_found", "Không tìm thấy công việc.")
    replay_attempt = (
        db.query(TaskJobAttempt)
        .filter(
            TaskJobAttempt.organization_id == org_id,
            TaskJobAttempt.job_id == job_id,
            TaskJobAttempt.id == attempt_id,
        )
        .populate_existing()
        .first()
    )
    if (
        replay_job.generation_token == generation_token
        and replay_job.status
        in {TaskJobStatus.PENDING.value, TaskJobStatus.DEAD_LETTER.value}
        and replay_attempt is not None
        and replay_attempt.worker_id == normalized_worker
        and replay_attempt.generation_token == generation_token
        and replay_attempt.status == TaskJobAttemptStatus.FAILED.value
    ):
        if (
            replay_attempt.error_code == normalized_code
            and replay_attempt.error_message == normalized_message
        ):
            db.rollback()
            return replay_job
        _persist_worker_rejection(
            db,
            job=replay_job,
            worker_id=normalized_worker,
            reason_code="failure_replay_conflict",
            detail="Thông tin lỗi lặp lại không khớp với lần đã ghi nhận.",
        )

    job, attempt = _load_fenced_execution(
        db,
        worker_id=normalized_worker,
        job_id=job_id,
        org_id=org_id,
        attempt_id=attempt_id,
        generation_token=generation_token,
        now=now,
    )
    attempt.status = TaskJobAttemptStatus.FAILED.value
    attempt.error_code = normalized_code
    attempt.error_message = normalized_message
    attempt.finished_at = now
    job.last_error_code = normalized_code
    job.last_error_message = normalized_message
    job.lease_owner = None
    job.lease_expires_at = None

    if job.attempt_count >= job.max_attempts:
        _mark_dead_letter(db, job, reason_code="max_attempts_exhausted", now=now)
        event_name = "TaskJobAttemptFailedAndDeadLettered"
        retry_at = None
    else:
        backoff = min(
            retry_base_seconds * (2 ** max(0, attempt.attempt_no - 1)),
            _MAX_BACKOFF_SECONDS,
        )
        retry_at = now + timedelta(seconds=backoff)
        job.status = TaskJobStatus.PENDING.value
        job.available_at = retry_at
        event_name = "TaskJobAttemptFailedAndRetryScheduled"

    log_audit_event(
        db,
        event_name=event_name,
        entity_type="TaskJob",
        entity_id=job.id,
        organization_id=job.organization_id,
        command_name="FailTaskJobAttempt",
        correlation_id=job.correlation_id,
        payload={
            "worker_id": normalized_worker,
            "attempt_no": attempt.attempt_no,
            "generation_token": generation_token,
            "error_code": normalized_code,
            "retry_at": retry_at.isoformat() if retry_at else None,
        },
    )
    db.commit()
    db.refresh(job)
    return job


def cancel_job(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    job_id: uuid.UUID,
    correlation_id: str | None = None,
) -> TaskJob:
    """Cancel a pending or claimed job and fence any in-flight worker."""
    persisted_actor = _reload_actor(db, actor=actor, org_id=org_id, target_id=job_id)
    query = db.query(TaskJob).filter(
        TaskJob.organization_id == org_id,
        TaskJob.id == job_id,
    )
    job = _lock_query(query, db, skip_locked=False).populate_existing().first()
    if job is None:
        _persist_boundary_denial(
            db,
            org_id=org_id,
            actor_id=persisted_actor.id,
            resource_type="TaskJob",
            resource_id=job_id,
            reason_code="job_tenant_boundary_failed",
            detail="Không tìm thấy công việc.",
        )
    if job.status == TaskJobStatus.CANCELLED.value:
        db.rollback()
        return job
    if job.status not in {TaskJobStatus.PENDING.value, TaskJobStatus.CLAIMED.value}:
        _abort(db, 409, "job_not_cancellable", "Công việc đã kết thúc và không thể hủy.")

    now = _utc_now()
    attempt = _current_attempt(db, job) if job.status == TaskJobStatus.CLAIMED.value else None
    if attempt is not None and attempt.status == TaskJobAttemptStatus.RUNNING.value:
        attempt.status = TaskJobAttemptStatus.CANCELLED.value
        attempt.finished_at = now
        attempt.error_code = "cancelled_by_user"
        attempt.error_message = "Cancelled by an authorized user."
    job.status = TaskJobStatus.CANCELLED.value
    job.cancelled_at = now
    job.lease_owner = None
    job.lease_expires_at = None
    log_audit_event(
        db,
        event_name="TaskJobCancelled",
        entity_type="TaskJob",
        entity_id=job.id,
        organization_id=org_id,
        actor_user_id=persisted_actor.id,
        command_name="CancelTaskJob",
        correlation_id=correlation_id or job.correlation_id,
        payload={"generation_token": job.generation_token},
    )
    db.commit()
    db.refresh(job)
    return job
