"""Tenant-safe commands for the paired dossier aggregate."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any, Sequence

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.audit import log_audit_event
from app.core.rbac import derive_effective_permissions
from app.modules.ai_governance_security.application.security_audit_service import (
    record_authorization_denial,
    record_tenant_boundary_check,
)
from app.modules.excel_import.models import (
    DossierBundle,
    DossierFileRole,
    DossierSourceFile,
)
from app.modules.project_master_data.models import (
    Customer,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    User,
    UserRole,
    UserStatus,
)

_REQUIRED_PERMISSION = "document_intelligence:job:create"
_PRIMARY_ROLES = {
    DossierFileRole.CUSTOMER_ASSET_LIST.value,
    DossierFileRole.FINAL_APPRAISAL_REPORT.value,
}
_ALLOWED_ROLES = {role.value for role in DossierFileRole}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ROLE_EXTENSIONS = {
    DossierFileRole.CUSTOMER_ASSET_LIST.value: {".xls", ".xlsx"},
    DossierFileRole.FINAL_APPRAISAL_REPORT.value: {".docx", ".pdf"},
}


@dataclass(frozen=True)
class DossierSourceSpec:
    """Verified immutable object metadata supplied by the storage boundary."""

    file_role: str
    file_name: str
    file_size_bytes: int
    checksum_sha256: str
    storage_object_key: str


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _status_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _audit_target_id(org_id: uuid.UUID, bundle_code: str) -> uuid.UUID:
    return uuid.uuid5(org_id, f"dossier-bundle:{bundle_code}")


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
            target_type="DossierBundle",
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
    raise _error(403, "permission_denied", "Tài khoản không có quyền tạo hồ sơ tài liệu.")


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


def _resolve_ownership(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    customer_id: uuid.UUID,
    project_id: uuid.UUID | None,
) -> tuple[Customer, Project | None]:
    customer = (
        db.query(Customer)
        .filter(Customer.organization_id == org_id, Customer.id == customer_id)
        .populate_existing()
        .first()
    )
    if customer is None:
        _persist_boundary_denial(
            db,
            org_id=org_id,
            actor_id=actor.id,
            resource_type="Customer",
            resource_id=customer_id,
            reason_code="customer_tenant_boundary_failed",
            detail="Không tìm thấy khách hàng.",
        )
    record_tenant_boundary_check(
        db,
        organization_id=org_id,
        actor_id=actor.id,
        resource_type="Customer",
        resource_id=customer_id,
        passed=True,
    )

    project = None
    if project_id is not None:
        project = (
            db.query(Project)
            .filter(
                Project.organization_id == org_id,
                Project.customer_id == customer_id,
                Project.id == project_id,
            )
            .populate_existing()
            .first()
        )
        if project is None:
            _persist_boundary_denial(
                db,
                org_id=org_id,
                actor_id=actor.id,
                resource_type="Project",
                resource_id=project_id,
                reason_code="project_ownership_boundary_failed",
                detail="Không tìm thấy dự án.",
            )
        record_tenant_boundary_check(
            db,
            organization_id=org_id,
            actor_id=actor.id,
            resource_type="Project",
            resource_id=project_id,
            passed=True,
        )
    return customer, project


def _validate_sources(files: Sequence[DossierSourceSpec]) -> tuple[DossierSourceSpec, ...]:
    if not files:
        raise _error(422, "dossier_sources_required", "Hồ sơ phải có tệp nguồn.")

    normalized: list[DossierSourceSpec] = []
    object_keys: set[str] = set()
    role_counts = {role: 0 for role in _PRIMARY_ROLES}
    for source in files:
        if not isinstance(source, DossierSourceSpec):
            raise _error(
                422,
                "verified_source_metadata_required",
                "Thông tin tệp phải đến từ ranh giới lưu trữ đã xác minh.",
            )
        role = source.file_role.strip()
        file_name = source.file_name.strip()
        object_key = source.storage_object_key.strip()
        checksum = source.checksum_sha256.strip()
        if role not in _ALLOWED_ROLES:
            raise _error(422, "invalid_dossier_file_role", "Vai trò tệp không hợp lệ.")
        if not file_name or PurePath(file_name).name != file_name or len(file_name) > 255:
            raise _error(422, "invalid_source_file_name", "Tên tệp nguồn không hợp lệ.")
        if source.file_size_bytes <= 0:
            raise _error(422, "invalid_source_file_size", "Kích thước tệp nguồn không hợp lệ.")
        if not _SHA256_PATTERN.fullmatch(checksum):
            raise _error(422, "invalid_source_checksum", "Mã kiểm tra tệp nguồn không hợp lệ.")
        if (
            not object_key
            or object_key.startswith(("/", "\\"))
            or any(part == ".." for part in PurePath(object_key.replace("\\", "/")).parts)
        ):
            raise _error(422, "invalid_storage_object_key", "Định danh lưu trữ không hợp lệ.")
        if object_key in object_keys:
            raise _error(409, "duplicate_storage_object", "Tệp nguồn bị lặp trong hồ sơ.")
        expected_extensions = _ROLE_EXTENSIONS.get(role)
        if expected_extensions and PurePath(file_name).suffix.lower() not in expected_extensions:
            raise _error(422, "source_type_role_mismatch", "Loại tệp không phù hợp với vai trò.")

        object_keys.add(object_key)
        if role in role_counts:
            role_counts[role] += 1
        normalized.append(
            DossierSourceSpec(
                file_role=role,
                file_name=file_name,
                file_size_bytes=source.file_size_bytes,
                checksum_sha256=checksum,
                storage_object_key=object_key,
            )
        )

    if any(count != 1 for count in role_counts.values()):
        raise _error(
            422,
            "paired_primary_sources_required",
            "Hồ sơ phải có đúng một danh sách tài sản và một báo cáo thẩm định.",
        )
    return tuple(normalized)


def _source_intent(source: DossierSourceSpec | DossierSourceFile) -> tuple[Any, ...]:
    return (
        source.file_role,
        source.file_name,
        source.file_size_bytes,
        source.checksum_sha256,
        source.storage_object_key,
    )


def _return_existing_or_conflict(
    db: Session,
    *,
    existing: DossierBundle,
    actor_id: uuid.UUID,
    customer_id: uuid.UUID,
    project_id: uuid.UUID | None,
    files: Sequence[DossierSourceSpec],
) -> tuple[DossierBundle, list[DossierSourceFile]]:
    persisted_files = (
        db.query(DossierSourceFile)
        .filter(
            DossierSourceFile.organization_id == existing.organization_id,
            DossierSourceFile.dossier_bundle_id == existing.id,
        )
        .order_by(DossierSourceFile.file_role, DossierSourceFile.storage_object_key)
        .all()
    )
    same_intent = (
        existing.created_by_user_id == actor_id
        and existing.customer_id == customer_id
        and existing.project_id == project_id
        and sorted(_source_intent(item) for item in persisted_files)
        == sorted(_source_intent(item) for item in files)
    )
    if not same_intent:
        db.rollback()
        raise _error(
            409,
            "dossier_idempotency_conflict",
            "Mã hồ sơ đã được dùng cho một nội dung khác.",
        )
    return existing, persisted_files


def create_paired_dossier_bundle(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    customer_id: uuid.UUID,
    project_id: uuid.UUID | None,
    bundle_code: str,
    files: Sequence[DossierSourceSpec],
    correlation_id: str | None = None,
) -> tuple[DossierBundle, list[DossierSourceFile]]:
    """Create one immutable, source-backed paired dossier with an atomic audit event."""
    normalized_code = bundle_code.strip()
    if not normalized_code or len(normalized_code) > 100:
        raise _error(422, "invalid_bundle_code", "Mã hồ sơ không hợp lệ.")
    if correlation_id is not None and len(correlation_id) > 128:
        raise _error(422, "invalid_correlation_id", "Mã tương quan không hợp lệ.")

    target_id = _audit_target_id(org_id, normalized_code)
    persisted_actor = _reload_actor(db, actor=actor, org_id=org_id, target_id=target_id)
    normalized_files = _validate_sources(files)
    _resolve_ownership(
        db,
        actor=persisted_actor,
        org_id=org_id,
        customer_id=customer_id,
        project_id=project_id,
    )

    existing = (
        db.query(DossierBundle)
        .filter(
            DossierBundle.organization_id == org_id,
            DossierBundle.bundle_code == normalized_code,
        )
        .populate_existing()
        .first()
    )
    if existing is not None:
        result = _return_existing_or_conflict(
            db,
            existing=existing,
            actor_id=persisted_actor.id,
            customer_id=customer_id,
            project_id=project_id,
            files=normalized_files,
        )
        db.commit()
        return result

    bundle = DossierBundle(
        organization_id=org_id,
        customer_id=customer_id,
        project_id=project_id,
        bundle_code=normalized_code,
        status="pending",
        created_by_user_id=persisted_actor.id,
    )
    db.add(bundle)
    db.flush()
    source_files = [
        DossierSourceFile(
            organization_id=org_id,
            dossier_bundle_id=bundle.id,
            file_role=source.file_role,
            file_name=source.file_name,
            file_size_bytes=source.file_size_bytes,
            checksum_sha256=source.checksum_sha256,
            storage_object_key=source.storage_object_key,
        )
        for source in normalized_files
    ]
    db.add_all(source_files)
    log_audit_event(
        db,
        event_name="DossierBundleCreated",
        entity_type="DossierBundle",
        entity_id=bundle.id,
        organization_id=org_id,
        actor_user_id=persisted_actor.id,
        command_name="CreateDossierBundle",
        correlation_id=correlation_id,
        payload={
            "customer_id": str(customer_id),
            "project_id": str(project_id) if project_id else None,
            "bundle_code": normalized_code,
            "source_roles": [source.file_role for source in normalized_files],
            "source_count": len(normalized_files),
        },
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(DossierBundle)
            .filter(
                DossierBundle.organization_id == org_id,
                DossierBundle.bundle_code == normalized_code,
            )
            .populate_existing()
            .first()
        )
        if existing is None:
            raise _error(409, "dossier_integrity_conflict", "Không thể tạo hồ sơ do xung đột dữ liệu.")
        return _return_existing_or_conflict(
            db,
            existing=existing,
            actor_id=persisted_actor.id,
            customer_id=customer_id,
            project_id=project_id,
            files=normalized_files,
        )
    db.refresh(bundle)
    for source_file in source_files:
        db.refresh(source_file)
    return bundle, source_files
