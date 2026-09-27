"""Atomic Pre-case Customer binding and current-batch switching (ADR 0046 D1-D2)."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.exc import StaleDataError

from app.core.audit import log_audit_event
from app.core.rbac import derive_effective_permissions
from app.modules.project_master_data.models import (
    Customer,
    CustomerStatus,
    OrganizationProfile,
    OrganizationStatus,
    PreliminaryProjectLifecycleCommandReceipt,
    Project,
    ProjectAssetImportBatch,
    ProjectOfficialIntakeCommit,
    User,
    UserRole,
    UserStatus,
)


PROJECT_UPDATE_PERMISSION = "project:update"
BIND_COMMAND = "BindPreliminaryProjectCustomer"
SWITCH_COMMAND = "SwitchCurrentPreliminaryImportBatch"


def _status_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _abort(db: Session, status: int, code: str, detail: str) -> None:
    db.rollback()
    raise _error(status, code, detail)


def _reload_active_actor_and_org(db: Session, *, actor: User, org_id: uuid.UUID) -> User:
    organization = (
        db.query(OrganizationProfile)
        .filter(OrganizationProfile.id == org_id)
        .populate_existing()
        .first()
    )
    actor_id = getattr(actor, "id", None)
    persisted_actor = None
    if actor_id is not None:
        persisted_actor = (
            db.query(User)
            .options(
                selectinload(User.organization),
                selectinload(User.roles).selectinload(UserRole.role),
            )
            .filter(User.id == actor_id, User.organization_id == org_id)
            .populate_existing()
            .first()
        )
    if (
        persisted_actor is None
        or organization is None
        or _status_value(persisted_actor.status) != UserStatus.ACTIVE.value
        or _status_value(organization.status) != OrganizationStatus.ACTIVE.value
        or PROJECT_UPDATE_PERMISSION not in derive_effective_permissions(persisted_actor, db)
    ):
        _abort(db, 403, "preliminary_lifecycle_forbidden", "Không thể thực hiện thao tác này.")
    return persisted_actor


def _normalized_key(db: Session, key: str) -> str:
    normalized = key.strip()
    if not normalized or len(normalized) > 128:
        _abort(db, 422, "invalid_idempotency_key", "Khóa idempotency không hợp lệ.")
    return normalized


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _lock_project(db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == org_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if project is None:
        _abort(db, 404, "project_not_found", "Không tìm thấy hồ sơ.")
    return project


def _same_request(
    receipt: PreliminaryProjectLifecycleCommandReceipt,
    *,
    command_type: str,
    actor_id: uuid.UUID,
    project_id: uuid.UUID,
    request_digest: str,
) -> bool:
    return (
        receipt.command_type == command_type
        and receipt.actor_user_id == actor_id
        and receipt.project_id == project_id
        and receipt.request_digest_sha256 == request_digest
    )


def _lookup_receipt(
    db: Session,
    *,
    org_id: uuid.UUID,
    key: str,
) -> PreliminaryProjectLifecycleCommandReceipt | None:
    return (
        db.query(PreliminaryProjectLifecycleCommandReceipt)
        .filter(
            PreliminaryProjectLifecycleCommandReceipt.organization_id == org_id,
            PreliminaryProjectLifecycleCommandReceipt.idempotency_key == key,
        )
        .populate_existing()
        .first()
    )


def _replay_or_conflict(
    db: Session,
    *,
    org_id: uuid.UUID,
    key: str,
    command_type: str,
    actor_id: uuid.UUID,
    project_id: uuid.UUID,
    request_digest: str,
) -> PreliminaryProjectLifecycleCommandReceipt | None:
    receipt = _lookup_receipt(db, org_id=org_id, key=key)
    if receipt is None:
        return None
    if not _same_request(
        receipt, command_type=command_type, actor_id=actor_id,
        project_id=project_id, request_digest=request_digest,
    ):
        _abort(db, 409, "idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác.")
    db.commit()
    db.refresh(receipt)
    return receipt


def _require_open_precase(db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID) -> None:
    committed = (
        db.query(ProjectOfficialIntakeCommit.id)
        .filter(
            ProjectOfficialIntakeCommit.organization_id == org_id,
            ProjectOfficialIntakeCommit.project_id == project_id,
        )
        .first()
    )
    if committed is not None:
        _abort(db, 409, "official_intake_already_committed", "Hồ sơ đã được chuyển chính thức.")


def _commit_change(
    db: Session,
    *,
    project: Project,
    actor: User,
    command_type: str,
    key: str,
    request_digest: str,
    expected_project_version: int,
    target_customer_id: uuid.UUID | None = None,
    previous_import_batch_id: uuid.UUID | None = None,
    target_import_batch_id: uuid.UUID | None = None,
    correlation_id: str | None = None,
) -> PreliminaryProjectLifecycleCommandReceipt:
    try:
        db.flush()
        receipt = PreliminaryProjectLifecycleCommandReceipt(
            organization_id=project.organization_id,
            project_id=project.id,
            command_type=command_type,
            idempotency_key=key,
            request_digest_sha256=request_digest,
            actor_user_id=actor.id,
            expected_project_version=expected_project_version,
            committed_project_version=project.row_version,
            target_customer_id=target_customer_id,
            previous_import_batch_id=previous_import_batch_id,
            target_import_batch_id=target_import_batch_id,
        )
        db.add(receipt)
        db.flush()
        payload = {
            "project_id": str(project.id),
            "receipt_id": str(receipt.id),
            "idempotency_key": key,
            "request_digest_sha256": request_digest,
            "project_version_before": expected_project_version,
            "project_version_after": project.row_version,
        }
        if target_customer_id is not None:
            payload["customer_id"] = str(target_customer_id)
        else:
            payload["previous_import_batch_id"] = str(previous_import_batch_id)
            payload["target_import_batch_id"] = str(target_import_batch_id)
        log_audit_event(
            db,
            event_name=(
                "PreliminaryProjectCustomerBound"
                if command_type == BIND_COMMAND else "CurrentPreliminaryImportBatchSwitched"
            ),
            entity_type="Project",
            entity_id=project.id,
            organization_id=project.organization_id,
            actor_user_id=actor.id,
            command_name=command_type,
            correlation_id=correlation_id,
            payload=payload,
        )
        db.commit()
        db.refresh(receipt)
        return receipt
    except IntegrityError as exc:
        db.rollback()
        _reload_active_actor_and_org(db, actor=actor, org_id=project.organization_id)
        raced = _replay_or_conflict(
            db, org_id=project.organization_id, key=key, command_type=command_type,
            actor_id=actor.id, project_id=project.id, request_digest=request_digest,
        )
        if raced is not None:
            return raced
        raise _error(
            409, "preliminary_lifecycle_conflict", "Hồ sơ đã thay đổi đồng thời."
        ) from exc
    except StaleDataError as exc:
        db.rollback()
        raise _error(409, "project_version_conflict", "Dữ liệu hồ sơ đã thay đổi.") from exc
    except Exception:
        db.rollback()
        raise


def bind_preliminary_project_customer(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    customer_id: uuid.UUID,
    expected_project_version: int,
    idempotency_key: str,
    correlation_id: str | None = None,
) -> PreliminaryProjectLifecycleCommandReceipt:
    """Bind one real ACTIVE Customer to an unbound Pre-case Project."""
    key = _normalized_key(db, idempotency_key)
    if expected_project_version < 1:
        _abort(db, 422, "invalid_expected_version", "Phiên bản yêu cầu không hợp lệ.")
    actor = _reload_active_actor_and_org(db, actor=actor, org_id=org_id)
    request_digest = _digest({
        "contract": "bind-preliminary-project-customer-v1",
        "actor_id": str(actor.id), "organization_id": str(org_id),
        "project_id": str(project_id), "customer_id": str(customer_id),
        "expected_project_version": expected_project_version,
    })
    project = _lock_project(db, org_id=org_id, project_id=project_id)
    replay = _replay_or_conflict(
        db, org_id=org_id, key=key, command_type=BIND_COMMAND,
        actor_id=actor.id, project_id=project_id, request_digest=request_digest,
    )
    if replay is not None:
        return replay
    if project.row_version != expected_project_version:
        _abort(db, 409, "project_version_conflict", "Dữ liệu hồ sơ đã thay đổi.")
    _require_open_precase(db, org_id=org_id, project_id=project_id)
    if project.customer_id is not None:
        _abort(db, 409, "project_already_bound", "Hồ sơ đã gắn khách hàng.")
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.organization_id == org_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if customer is None:
        _abort(db, 404, "customer_not_found", "Không tìm thấy khách hàng.")
    if _status_value(customer.status) != CustomerStatus.ACTIVE.value:
        _abort(db, 409, "customer_not_active", "Khách hàng không còn hoạt động.")
    project.customer_id = customer.id
    return _commit_change(
        db, project=project, actor=actor, command_type=BIND_COMMAND,
        key=key, request_digest=request_digest,
        expected_project_version=expected_project_version,
        target_customer_id=customer.id, correlation_id=correlation_id,
    )


def switch_current_preliminary_import_batch(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    target_import_batch_id: uuid.UUID,
    expected_current_import_batch_id: uuid.UUID | None,
    expected_project_version: int,
    idempotency_key: str,
    correlation_id: str | None = None,
) -> PreliminaryProjectLifecycleCommandReceipt:
    """Explicitly switch between established same-Project preliminary batches."""
    key = _normalized_key(db, idempotency_key)
    if expected_project_version < 1:
        _abort(db, 422, "invalid_expected_version", "Phiên bản yêu cầu không hợp lệ.")
    actor = _reload_active_actor_and_org(db, actor=actor, org_id=org_id)
    request_digest = _digest({
        "contract": "switch-current-preliminary-import-batch-v1",
        "actor_id": str(actor.id), "organization_id": str(org_id),
        "project_id": str(project_id),
        "target_import_batch_id": str(target_import_batch_id),
        "expected_current_import_batch_id": (
            str(expected_current_import_batch_id)
            if expected_current_import_batch_id is not None else None
        ),
        "expected_project_version": expected_project_version,
    })
    project = _lock_project(db, org_id=org_id, project_id=project_id)
    replay = _replay_or_conflict(
        db, org_id=org_id, key=key, command_type=SWITCH_COMMAND,
        actor_id=actor.id, project_id=project_id, request_digest=request_digest,
    )
    if replay is not None:
        return replay
    if project.row_version != expected_project_version:
        _abort(db, 409, "project_version_conflict", "Dữ liệu hồ sơ đã thay đổi.")
    _require_open_precase(db, org_id=org_id, project_id=project_id)
    if project.current_preliminary_import_batch_id is None:
        _abort(
            db, 409, "current_import_batch_unresolved",
            "Batch hiện hành chưa được xác lập; cần xử lý riêng.",
        )
    if project.current_preliminary_import_batch_id != expected_current_import_batch_id:
        _abort(db, 409, "current_import_batch_conflict", "Batch hiện hành đã thay đổi.")
    if target_import_batch_id == project.current_preliminary_import_batch_id:
        _abort(db, 409, "target_import_batch_already_current", "Batch này đã là hiện hành.")
    target = (
        db.query(ProjectAssetImportBatch)
        .filter(
            ProjectAssetImportBatch.id == target_import_batch_id,
            ProjectAssetImportBatch.organization_id == org_id,
            ProjectAssetImportBatch.project_id == project_id,
        )
        .with_for_update()
        .first()
    )
    if target is None:
        _abort(db, 404, "import_batch_not_found", "Không tìm thấy batch của hồ sơ.")
    previous_id = project.current_preliminary_import_batch_id
    project.current_preliminary_import_batch_id = target.id
    return _commit_change(
        db, project=project, actor=actor, command_type=SWITCH_COMMAND,
        key=key, request_digest=request_digest,
        expected_project_version=expected_project_version,
        previous_import_batch_id=previous_id,
        target_import_batch_id=target.id, correlation_id=correlation_id,
    )
