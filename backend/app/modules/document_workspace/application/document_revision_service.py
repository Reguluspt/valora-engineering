"""Tenant-safe creation of a canonical document and its first immutable revision."""
from __future__ import annotations

import hashlib
import json
import re
import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.audit import log_audit_event
from app.core.rbac import derive_effective_permissions
from app.modules.document_workspace.models import (
    DocumentRecord,
    DocumentRevision,
    DocumentRevisionCurrentHead,
)
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    Project,
    User,
    UserRole,
    UserStatus,
)


DOCUMENT_CREATE_PERMISSION = "project:update"
EVENT_DOCUMENT_REVISION_CREATED = "DOCUMENT_REVISION_CREATED"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _abort(db: Session, status: int, code: str, detail: str) -> None:
    db.rollback()
    raise _error(status, code, detail)


def _reload_actor(db: Session, *, actor: User, organization_id: uuid.UUID) -> User:
    persisted = (
        db.query(User)
        .options(
            selectinload(User.organization),
            selectinload(User.roles).selectinload(UserRole.role),
        )
        .filter(User.id == actor.id, User.organization_id == organization_id)
        .populate_existing()
        .first()
    )
    organization = db.get(OrganizationProfile, organization_id)
    if (
        persisted is None
        or organization is None
        or str(getattr(persisted.status, "value", persisted.status)) != UserStatus.ACTIVE.value
        or str(getattr(organization.status, "value", organization.status))
        != OrganizationStatus.ACTIVE.value
        or DOCUMENT_CREATE_PERMISSION not in derive_effective_permissions(persisted, db)
    ):
        _abort(db, 403, "document_forbidden", "Không thể thực hiện thao tác này.")
    return persisted


def _request_digest(
    *,
    actor_id: uuid.UUID,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    document_type: str,
    title: str,
    data_snapshot_digest_sha256: str,
    content_checksum_sha256: str,
) -> str:
    payload = {
        "actor_id": str(actor_id),
        "content_checksum_sha256": content_checksum_sha256,
        "contract": "document-first-revision-v1",
        "data_snapshot_digest_sha256": data_snapshot_digest_sha256,
        "document_type": document_type,
        "organization_id": str(organization_id),
        "project_id": str(project_id),
        "title": title,
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def create_document_with_first_revision(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    document_type: str,
    title: str,
    data_snapshot_digest_sha256: str,
    content_checksum_sha256: str,
    idempotency_key: str,
    correlation_id: str | None = None,
) -> DocumentRevision:
    """Create one DocumentRecord, revision 1 and current head atomically."""
    normalized_key = idempotency_key.strip()
    normalized_type = document_type.strip()
    normalized_title = title.strip()
    if not normalized_key or len(normalized_key) > 128:
        _abort(db, 422, "invalid_idempotency_key", "Khóa idempotency không hợp lệ.")
    if not normalized_type or len(normalized_type) > 64:
        _abort(db, 422, "invalid_document_type", "Loại tài liệu không hợp lệ.")
    if not normalized_title or len(normalized_title) > 255:
        _abort(db, 422, "invalid_document_title", "Tên tài liệu không hợp lệ.")
    if not _SHA256_RE.fullmatch(data_snapshot_digest_sha256):
        _abort(db, 422, "invalid_snapshot_digest", "Mã Data Snapshot không hợp lệ.")
    if not _SHA256_RE.fullmatch(content_checksum_sha256):
        _abort(db, 422, "invalid_content_checksum", "Mã kiểm tra tài liệu không hợp lệ.")

    actor = _reload_actor(db, actor=actor, organization_id=organization_id)
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == organization_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if project is None:
        _abort(db, 404, "project_not_found", "Không tìm thấy hồ sơ.")

    digest = _request_digest(
        actor_id=actor.id,
        organization_id=organization_id,
        project_id=project_id,
        document_type=normalized_type,
        title=normalized_title,
        data_snapshot_digest_sha256=data_snapshot_digest_sha256,
        content_checksum_sha256=content_checksum_sha256,
    )
    existing = (
        db.query(DocumentRevision)
        .filter(
            DocumentRevision.organization_id == organization_id,
            DocumentRevision.idempotency_key == normalized_key,
        )
        .first()
    )
    if existing is not None:
        if existing.request_digest_sha256 != digest:
            _abort(
                db,
                409,
                "idempotency_key_reused",
                "Mã lệnh đã được dùng cho dữ liệu khác.",
            )
        db.commit()
        return existing

    try:
        document = DocumentRecord(
            organization_id=organization_id,
            project_id=project_id,
            document_type=normalized_type,
            title=normalized_title,
            created_by_user_id=actor.id,
        )
        db.add(document)
        db.flush()
        revision = DocumentRevision(
            organization_id=organization_id,
            project_id=project_id,
            document_id=document.id,
            document_revision=1,
            data_snapshot_digest_sha256=data_snapshot_digest_sha256,
            content_checksum_sha256=content_checksum_sha256,
            idempotency_key=normalized_key,
            request_digest_sha256=digest,
            created_by_user_id=actor.id,
        )
        db.add(revision)
        db.flush()
        db.add(
            DocumentRevisionCurrentHead(
                organization_id=organization_id,
                project_id=project_id,
                document_id=document.id,
                current_revision_id=revision.id,
                document_revision=1,
            )
        )
        log_audit_event(
            db,
            event_name=EVENT_DOCUMENT_REVISION_CREATED,
            entity_type="DocumentRevision",
            entity_id=revision.id,
            organization_id=organization_id,
            actor_user_id=actor.id,
            command_name="CreateDocumentWithFirstRevision",
            correlation_id=correlation_id,
            payload={
                "project_id": str(project_id),
                "document_id": str(document.id),
                "document_revision": 1,
                "document_type": normalized_type,
            },
        )
        db.commit()
        db.refresh(revision)
        return revision
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(DocumentRevision)
            .filter(
                DocumentRevision.organization_id == organization_id,
                DocumentRevision.idempotency_key == normalized_key,
            )
            .first()
        )
        if raced is not None and raced.request_digest_sha256 == digest:
            return raced
        raise _error(
            409, "document_revision_conflict", "Tài liệu đã thay đổi đồng thời."
        ) from exc
