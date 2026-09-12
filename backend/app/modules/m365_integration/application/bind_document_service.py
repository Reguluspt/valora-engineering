"""Bind one canonical document revision to an immutable OneDrive metadata baseline."""

from __future__ import annotations

import hashlib
import json
import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.modules.document_workspace.models import (
    DocumentRecord,
    DocumentRevision,
    DocumentRevisionCurrentHead,
)
from app.modules.m365_integration.application.connection_service import (
    require_onedrive_actor,
)
from app.modules.m365_integration.domain.credential_vault import M365CredentialVault
from app.modules.m365_integration.domain.graph_gateway import M365GraphGateway, M365OAuthClient
from app.modules.m365_integration.domain.managed_regions import (
    DocxFingerprint,
    ManagedRegionDefinitionSet,
    ManagedRegionIntegrityError,
    fingerprint_docx,
)
from app.modules.m365_integration.models import (
    M365ManagedContentBaseline,
    M365ManagedRegionBaseline,
    M365RevisionBinding,
    OneDriveConnection,
)
from app.modules.project_master_data.models import Project, User


EVENT_M365_REVISION_BOUND = "M365_REVISION_BOUND"
EVENT_M365_BASELINE_SEALED = "M365_MANAGED_CONTENT_BASELINE_SEALED"


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _abort(db: Session, status: int, code: str, detail: str) -> None:
    db.rollback()
    raise _error(status, code, detail)


def _request_digest(
    *,
    actor_id: uuid.UUID,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    document_revision_id: uuid.UUID,
    expected_document_revision: int,
    connection_id: uuid.UUID,
    drive_item_id: str,
    managed_region_manifest_digest_sha256: str | None,
) -> str:
    payload: dict[str, object] = {
        "actor_id": str(actor_id),
        "connection_id": str(connection_id),
        "contract": (
            "m365-revision-bind-with-baseline-v2"
            if managed_region_manifest_digest_sha256 is not None
            else "m365-revision-bind-v1"
        ),
        "document_id": str(document_id),
        "document_revision_id": str(document_revision_id),
        "drive_item_id": drive_item_id,
        "expected_document_revision": expected_document_revision,
        "organization_id": str(organization_id),
        "project_id": str(project_id),
    }
    if managed_region_manifest_digest_sha256 is not None:
        payload["managed_region_manifest_digest_sha256"] = managed_region_manifest_digest_sha256
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _metadata_digest(binding: M365RevisionBinding) -> str:
    payload = {
        "c_tag": binding.c_tag,
        "drive_id": binding.drive_id,
        "drive_item_id": binding.drive_item_id,
        "e_tag": binding.e_tag,
        "graph_version_id": binding.graph_version_id,
        "last_modified_at": binding.last_modified_at.isoformat(),
        "size_bytes": binding.size_bytes,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _existing_replay(
    db: Session,
    *,
    organization_id: uuid.UUID,
    idempotency_key: str,
    request_digest: str,
) -> M365RevisionBinding | None:
    existing = (
        db.query(M365RevisionBinding)
        .filter(
            M365RevisionBinding.organization_id == organization_id,
            M365RevisionBinding.idempotency_key == idempotency_key,
        )
        .first()
    )
    if existing is None:
        return None
    if existing.request_digest_sha256 != request_digest:
        _abort(
            db,
            409,
            "idempotency_key_reused",
            "Mã lệnh đã được dùng cho dữ liệu khác.",
        )
    db.commit()
    return existing


def _connection_access_token(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    connection_id: uuid.UUID,
    oauth_client: M365OAuthClient,
    credential_vault: M365CredentialVault,
) -> tuple[OneDriveConnection, str]:
    connection = (
        db.query(OneDriveConnection)
        .filter(
            OneDriveConnection.id == connection_id,
            OneDriveConnection.organization_id == organization_id,
            OneDriveConnection.user_id == actor_id,
            OneDriveConnection.status == "active",
        )
        .first()
    )
    if connection is None:
        _abort(db, 404, "onedrive_connection_not_found", "Không tìm thấy kết nối OneDrive.")
    try:
        old_cache = credential_vault.load(
            organization_id=organization_id,
            user_id=actor_id,
            credential_id=connection.credential_id,
            purpose="token_cache",
        )
        token = oauth_client.acquire_access_token(token_cache=old_cache)
        if token.token_cache != old_cache:
            credential_vault.replace(
                organization_id=organization_id,
                user_id=actor_id,
                credential_id=connection.credential_id,
                purpose="token_cache",
                plaintext=token.token_cache,
            )
        db.commit()
        return connection, token.access_token
    except Exception as exc:
        db.rollback()
        failed = (
            db.query(OneDriveConnection)
            .filter(
                OneDriveConnection.id == connection_id,
                OneDriveConnection.organization_id == organization_id,
                OneDriveConnection.user_id == actor_id,
            )
            .first()
        )
        if failed is not None:
            failed.status = "error"
            db.commit()
        raise _error(
            502, "onedrive_token_unavailable", "Không thể làm mới quyền truy cập OneDrive."
        ) from exc


def bind_document_revision(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    document_revision_id: uuid.UUID,
    expected_document_revision: int,
    connection_id: uuid.UUID,
    drive_item_id: str,
    idempotency_key: str,
    oauth_client: M365OAuthClient,
    graph_gateway: M365GraphGateway,
    credential_vault: M365CredentialVault,
    correlation_id: str | None = None,
    definition_set: ManagedRegionDefinitionSet | None = None,
) -> M365RevisionBinding:
    """Bind immutable metadata and, when authoritative definitions exist, content proof."""
    normalized_key = idempotency_key.strip()
    normalized_item_id = drive_item_id.strip()
    if not normalized_key or len(normalized_key) > 128:
        _abort(db, 422, "invalid_idempotency_key", "Khóa idempotency không hợp lệ.")
    if not normalized_item_id or len(normalized_item_id) > 255:
        _abort(db, 422, "invalid_drive_item_id", "Định danh tệp OneDrive không hợp lệ.")
    if expected_document_revision <= 0:
        _abort(db, 422, "invalid_document_revision", "Phiên bản tài liệu không hợp lệ.")

    actor = require_onedrive_actor(db, organization_id=organization_id, user_id=actor.id)
    digest = _request_digest(
        actor_id=actor.id,
        organization_id=organization_id,
        project_id=project_id,
        document_id=document_id,
        document_revision_id=document_revision_id,
        expected_document_revision=expected_document_revision,
        connection_id=connection_id,
        drive_item_id=normalized_item_id,
        managed_region_manifest_digest_sha256=(
            definition_set.manifest_digest_sha256 if definition_set is not None else None
        ),
    )
    replay = _existing_replay(
        db,
        organization_id=organization_id,
        idempotency_key=normalized_key,
        request_digest=digest,
    )
    if replay is not None:
        return replay

    # Resolve tenant and revision authority before acquiring a token or calling Graph.
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == organization_id)
        .first()
    )
    if project is None:
        _abort(db, 404, "project_not_found", "Không tìm thấy hồ sơ.")
    document = (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.id == document_id,
            DocumentRecord.organization_id == organization_id,
            DocumentRecord.project_id == project_id,
        )
        .first()
    )
    if document is None:
        _abort(db, 404, "document_not_found", "Không tìm thấy tài liệu.")
    head = (
        db.query(DocumentRevisionCurrentHead)
        .filter(
            DocumentRevisionCurrentHead.organization_id == organization_id,
            DocumentRevisionCurrentHead.project_id == project_id,
            DocumentRevisionCurrentHead.document_id == document_id,
        )
        .first()
    )
    revision = (
        db.query(DocumentRevision)
        .filter(
            DocumentRevision.id == document_revision_id,
            DocumentRevision.organization_id == organization_id,
            DocumentRevision.project_id == project_id,
            DocumentRevision.document_id == document_id,
        )
        .first()
    )
    if revision is None or head is None:
        _abort(db, 404, "document_revision_not_found", "Không tìm thấy phiên bản tài liệu.")
    if (
        head.current_revision_id != document_revision_id
        or head.document_revision != expected_document_revision
        or revision.document_revision != expected_document_revision
    ):
        _abort(
            db,
            409,
            "document_revision_conflict",
            "Phiên bản tài liệu đã thay đổi. Vui lòng tải lại.",
        )
    expected_content_checksum = revision.content_checksum_sha256

    connection, access_token = _connection_access_token(
        db,
        organization_id=organization_id,
        actor_id=actor.id,
        connection_id=connection_id,
        oauth_client=oauth_client,
        credential_vault=credential_vault,
    )
    fingerprint: DocxFingerprint | None = None
    try:
        observed = graph_gateway.get_drive_item(
            access_token=access_token,
            drive_id=connection.drive_id,
            drive_item_id=normalized_item_id,
        )
        if definition_set is not None:
            content = graph_gateway.get_drive_item_content(
                access_token=access_token,
                drive_id=connection.drive_id,
                drive_item_id=normalized_item_id,
            )
            if hashlib.sha256(content).hexdigest() != expected_content_checksum:
                raise _error(
                    409,
                    "m365_content_checksum_mismatch",
                    "Nội dung tệp không khớp phiên bản tài liệu hiện tại.",
                )
            fingerprint = fingerprint_docx(content, definition_set)
            after = graph_gateway.get_drive_item(
                access_token=access_token,
                drive_id=connection.drive_id,
                drive_item_id=normalized_item_id,
            )
            if (
                after.drive_id != observed.drive_id
                or after.drive_item_id != observed.drive_item_id
                or after.e_tag != observed.e_tag
                or after.size_bytes != len(content)
            ):
                raise _error(
                    409,
                    "m365_content_race",
                    "Tệp OneDrive thay đổi trong lúc kiểm tra. Vui lòng thử lại.",
                )
    except HTTPException:
        db.rollback()
        raise
    except ManagedRegionIntegrityError as exc:
        db.rollback()
        raise _error(
            422,
            "managed_region_baseline_invalid",
            "Không thể xác minh cấu trúc vùng quản lý trong tài liệu.",
        ) from exc
    except Exception as exc:
        db.rollback()
        raise _error(
            502, "onedrive_item_unavailable", "Không thể đọc thông tin tệp OneDrive."
        ) from exc
    if observed.drive_id != connection.drive_id or observed.drive_item_id != normalized_item_id:
        raise _error(409, "onedrive_item_identity_mismatch", "Định danh tệp OneDrive không khớp.")

    actor = require_onedrive_actor(db, organization_id=organization_id, user_id=actor.id)
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == organization_id)
        .with_for_update()
        .first()
    )
    if project is None:
        _abort(db, 404, "project_not_found", "Không tìm thấy hồ sơ.")
    document = (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.id == document_id,
            DocumentRecord.organization_id == organization_id,
            DocumentRecord.project_id == project_id,
        )
        .with_for_update()
        .first()
    )
    if document is None:
        _abort(db, 404, "document_not_found", "Không tìm thấy tài liệu.")
    head = (
        db.query(DocumentRevisionCurrentHead)
        .filter(
            DocumentRevisionCurrentHead.organization_id == organization_id,
            DocumentRevisionCurrentHead.project_id == project_id,
            DocumentRevisionCurrentHead.document_id == document_id,
        )
        .with_for_update()
        .first()
    )
    revision = (
        db.query(DocumentRevision)
        .filter(
            DocumentRevision.id == document_revision_id,
            DocumentRevision.organization_id == organization_id,
            DocumentRevision.project_id == project_id,
            DocumentRevision.document_id == document_id,
        )
        .first()
    )
    if revision is None or head is None:
        _abort(db, 404, "document_revision_not_found", "Không tìm thấy phiên bản tài liệu.")
    if (
        head.current_revision_id != document_revision_id
        or head.document_revision != expected_document_revision
        or revision.document_revision != expected_document_revision
    ):
        _abort(
            db,
            409,
            "document_revision_conflict",
            "Phiên bản tài liệu đã thay đổi. Vui lòng tải lại.",
        )
    current_connection = (
        db.query(OneDriveConnection)
        .filter(
            OneDriveConnection.id == connection_id,
            OneDriveConnection.organization_id == organization_id,
            OneDriveConnection.user_id == actor.id,
            OneDriveConnection.status == "active",
            OneDriveConnection.drive_id == observed.drive_id,
        )
        .with_for_update()
        .first()
    )
    if current_connection is None:
        _abort(db, 404, "onedrive_connection_not_found", "Không tìm thấy kết nối OneDrive.")
    replay = _existing_replay(
        db,
        organization_id=organization_id,
        idempotency_key=normalized_key,
        request_digest=digest,
    )
    if replay is not None:
        return replay

    binding = M365RevisionBinding(
        organization_id=organization_id,
        project_id=project_id,
        document_id=document_id,
        document_revision_id=document_revision_id,
        connection_id=connection_id,
        drive_id=observed.drive_id,
        drive_item_id=observed.drive_item_id,
        graph_version_id=observed.graph_version_id,
        e_tag=observed.e_tag,
        c_tag=observed.c_tag,
        last_modified_at=observed.last_modified_at,
        size_bytes=observed.size_bytes,
        name=observed.name,
        path=observed.path,
        web_url=observed.web_url,
        idempotency_key=normalized_key,
        request_digest_sha256=digest,
        bound_by_user_id=actor.id,
    )
    db.add(binding)
    if fingerprint is not None and definition_set is not None:
        db.flush()
        baseline = M365ManagedContentBaseline(
            organization_id=organization_id,
            project_id=project_id,
            document_id=document_id,
            document_revision_id=document_revision_id,
            binding_id=binding.id,
            connection_id=connection_id,
            drive_id=observed.drive_id,
            drive_item_id=observed.drive_item_id,
            source_content_sha256=fingerprint.source_content_sha256,
            source_size_bytes=fingerprint.source_size_bytes,
            source_e_tag=observed.e_tag,
            source_c_tag=observed.c_tag,
            bind_metadata_digest_sha256=_metadata_digest(binding),
            authority_ref=definition_set.authority_ref,
            parser_contract_version=fingerprint.parser_contract_version,
            fingerprint_contract_version=fingerprint.fingerprint_contract_version,
            managed_region_manifest_digest_sha256=(
                fingerprint.managed_region_manifest_digest_sha256
            ),
            outside_managed_digest_sha256=fingerprint.outside_managed_digest_sha256,
            whole_canonical_digest_sha256=fingerprint.whole_canonical_digest_sha256,
            provenance_kind="new_binding_atomic",
            idempotency_key=normalized_key,
            request_digest_sha256=digest,
            created_by_user_id=actor.id,
        )
        db.add(baseline)
        db.flush()
        for position, region in enumerate(fingerprint.regions):
            db.add(
                M365ManagedRegionBaseline(
                    organization_id=organization_id,
                    content_baseline_id=baseline.id,
                    position=position,
                    region_key=region.region_key,
                    locator=region.locator,
                    locator_digest_sha256=hashlib.sha256(
                        region.locator.encode("utf-8")
                    ).hexdigest(),
                    semantic_type=region.semantic_type,
                    normalization_contract=region.normalization_contract,
                    normalized_value_digest_sha256=(region.normalized_value_digest_sha256),
                    structural_digest_sha256=region.structural_digest_sha256,
                )
            )
        log_audit_event(
            db,
            event_name=EVENT_M365_BASELINE_SEALED,
            entity_type="M365ManagedContentBaseline",
            entity_id=baseline.id,
            organization_id=organization_id,
            actor_user_id=actor.id,
            command_name="BindDocumentRevisionWithBaseline",
            correlation_id=correlation_id,
            payload={
                "project_id": str(project_id),
                "document_id": str(document_id),
                "document_revision_id": str(document_revision_id),
                "binding_id": str(binding.id),
                "managed_regions": [region.region_key for region in fingerprint.regions],
                "parser_contract_version": fingerprint.parser_contract_version,
                "fingerprint_contract_version": fingerprint.fingerprint_contract_version,
            },
        )
    log_audit_event(
        db,
        event_name=EVENT_M365_REVISION_BOUND,
        entity_type="M365RevisionBinding",
        entity_id=binding.id,
        organization_id=organization_id,
        actor_user_id=actor.id,
        command_name="BindDocumentRevision",
        correlation_id=correlation_id,
        payload={
            "project_id": str(project_id),
            "document_id": str(document_id),
            "document_revision_id": str(document_revision_id),
            "connection_id": str(connection_id),
            "drive_id": observed.drive_id,
            "drive_item_id": observed.drive_item_id,
            "graph_version_id": observed.graph_version_id,
            "e_tag": observed.e_tag,
        },
    )
    try:
        db.commit()
        db.refresh(binding)
        return binding
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(M365RevisionBinding)
            .filter(
                M365RevisionBinding.organization_id == organization_id,
                M365RevisionBinding.idempotency_key == normalized_key,
            )
            .first()
        )
        if raced is not None and raced.request_digest_sha256 == digest:
            return raced
        raise _error(
            409, "m365_binding_conflict", "Liên kết tài liệu đã thay đổi đồng thời."
        ) from exc
