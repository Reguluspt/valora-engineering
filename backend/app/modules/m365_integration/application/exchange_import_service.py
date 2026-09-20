"""Explicit Exchange imports and authoritative Working-copy reads."""
from __future__ import annotations

import hashlib
import io
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.modules.document_workspace.application.document_storage_service import (
    create_or_recover_storage_object,
    finalize_storage_revision,
    prepare_initial_storage_intent,
    prepare_storage_intent,
    record_storage_candidate,
)
from app.modules.document_workspace.domain.document_blob_store import (
    BlobReadStatus,
    DocumentBlobStore,
)
from app.modules.document_workspace.models import (
    DocumentRevision,
    DocumentRevisionCurrentHead,
    StorageObjectBinding,
)
from app.modules.excel_import.application.import_service import upload_excel_file_orchestrator
from app.modules.excel_import.application.source_artifact_service import upload_source_artifact
from app.modules.m365_integration.application.connection_service import (
    get_connection_capabilities,
    require_onedrive_actor,
)
from app.modules.m365_integration.application.exchange_service import (
    MAX_EXCHANGE_BYTES,
    execute_exchange_create,
    prepare_exchange_create,
    provision_exchange_namespace,
)
from app.modules.m365_integration.domain.graph_gateway import M365GraphGateway
from app.modules.m365_integration.domain.managed_regions import (
    ManagedRegionDefinitionSet,
    ManagedRegionIntegrityError,
    fingerprint_docx,
)
from app.modules.m365_integration.models import M365ExchangeArtifact, OneDriveConnection
from app.modules.project_master_data.models import ProjectAssetImportBatch, User


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


@dataclass(frozen=True)
class DocxReimportResult:
    outcome: str
    revision: DocumentRevision
    binding: StorageObjectBinding
    artifact: M365ExchangeArtifact


def _verified_provider_bytes(
    *,
    graph_gateway: M365GraphGateway,
    access_token: str,
    drive_id: str,
    drive_item_id: str,
    expected_extension: str,
) -> tuple[object, bytes, str]:
    before = graph_gateway.get_drive_item(
        access_token=access_token, drive_id=drive_id, drive_item_id=drive_item_id
    )
    if (
        before.drive_id != drive_id
        or not before.name.lower().endswith(expected_extension)
        or before.size_bytes < 0
        or before.size_bytes > MAX_EXCHANGE_BYTES
    ):
        raise _error(422, "exchange_media_invalid", "Tệp Exchange không hợp lệ.")
    content = graph_gateway.get_drive_item_content(
        access_token=access_token, drive_id=drive_id, drive_item_id=drive_item_id
    )
    digest = hashlib.sha256(content).hexdigest()
    after = graph_gateway.get_drive_item(
        access_token=access_token, drive_id=drive_id, drive_item_id=drive_item_id
    )
    if (
        len(content) != before.size_bytes
        or after.drive_item_id != before.drive_item_id
        or after.drive_id != before.drive_id
        or after.e_tag != before.e_tag
        or after.size_bytes != before.size_bytes
    ):
        raise _error(409, "exchange_source_changed", "Tệp Exchange đã thay đổi khi đọc.")
    return before, content, digest


def _request_digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _require_read_capability(
    db: Session, *, organization_id: uuid.UUID, connection_id: uuid.UUID
) -> None:
    read_available, _ = get_connection_capabilities(
        db,
        organization_id=organization_id,
        connection_id=connection_id,
    )
    if not read_available:
        raise _error(409, "exchange_read_scope_required", "Cần cấp quyền đọc OneDrive.")


async def import_inbox_docx(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    connection_id: uuid.UUID,
    drive_item_id: str,
    document_type: str,
    title: str,
    definition_set: ManagedRegionDefinitionSet,
    idempotency_key: str,
    graph_gateway: M365GraphGateway,
    access_token: str,
    blob_store: DocumentBlobStore,
    storage_profile_id: str,
    container_name: str,
    retention_policy_code: str,
    retention_anchor_at: datetime,
    minimum_retain_until: datetime,
) -> tuple[DocumentRevision, StorageObjectBinding, M365ExchangeArtifact]:
    actor = require_onedrive_actor(
        db, organization_id=organization_id, user_id=actor.id
    )
    connection = db.query(OneDriveConnection).filter(
        OneDriveConnection.organization_id == organization_id,
        OneDriveConnection.id == connection_id,
        OneDriveConnection.user_id == actor.id,
        OneDriveConnection.status == "active",
    ).first()
    if connection is None:
        raise _error(404, "exchange_connection_not_found", "Không tìm thấy kết nối OneDrive.")
    _require_read_capability(
        db, organization_id=organization_id, connection_id=connection_id
    )
    provider_artifact = db.query(M365ExchangeArtifact).filter(
        M365ExchangeArtifact.organization_id == organization_id,
        M365ExchangeArtifact.connection_id == connection_id,
        M365ExchangeArtifact.drive_item_id == drive_item_id,
    ).first()
    if provider_artifact is not None and provider_artifact.project_id != project_id:
        raise _error(409, "exchange_artifact_conflict", "Tệp đã thuộc hồ sơ khác.")
    existing = provider_artifact
    if existing is not None and existing.document_revision_id is not None:
        revision = db.get(DocumentRevision, existing.document_revision_id)
        binding = db.query(StorageObjectBinding).filter(
            StorageObjectBinding.organization_id == organization_id,
            StorageObjectBinding.document_revision_id == existing.document_revision_id,
        ).first()
        if revision is not None and binding is not None:
            db.commit()
            return revision, binding, existing
    db.commit()
    metadata, content, content_sha256 = _verified_provider_bytes(
        graph_gateway=graph_gateway,
        access_token=access_token,
        drive_id=connection.drive_id,
        drive_item_id=drive_item_id,
        expected_extension=".docx",
    )
    try:
        fingerprint = fingerprint_docx(content, definition_set)
    except ManagedRegionIntegrityError as exc:
        raise _error(422, "exchange_docx_invalid", "DOCX không đạt kiểm tra an toàn.") from exc
    request_digest = _request_digest(
        {
            "organization_id": str(organization_id),
            "project_id": str(project_id),
            "connection_id": str(connection_id),
            "drive_item_id": drive_item_id,
            "e_tag": metadata.e_tag,
            "sha256": content_sha256,
            "byte_length": len(content),
            "document_type": document_type,
            "title": title,
            "manifest": definition_set.manifest_digest_sha256,
        }
    )
    intent = prepare_initial_storage_intent(
        db,
        actor=actor,
        organization_id=organization_id,
        project_id=project_id,
        document_type=document_type,
        title=title,
        expected_content_sha256=content_sha256,
        data_snapshot_digest_sha256=fingerprint.whole_canonical_digest_sha256,
        idempotency_key=idempotency_key,
        request_digest_sha256=request_digest,
        plan_digest_sha256=definition_set.manifest_digest_sha256,
        decision_digest_sha256=fingerprint.outside_managed_digest_sha256,
    )
    record_storage_candidate(
        db,
        organization_id=organization_id,
        intent_id=intent.id,
        content=content,
        provider_kind=blob_store.provider_kind,
        storage_profile_id=storage_profile_id,
        container_name=container_name,
        object_key=(
            f"{organization_id.hex}/{project_id.hex}/{intent.document_id.hex}/"
            f"{intent.id.hex}.docx"
        ),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        generator_version="onedrive-exchange-import-v1",
    )
    state = await create_or_recover_storage_object(
        db,
        organization_id=organization_id,
        intent_id=intent.id,
        content=content,
        blob_store=blob_store,
    )
    if state.current_state != "OBJECT_VERIFIED":
        raise _error(503, "exchange_storage_unavailable", "Chưa thể lưu DOCX an toàn.")
    finalized_artifact: list[M365ExchangeArtifact] = []

    def link_artifact(
        session: Session,
        revision: DocumentRevision,
        binding: StorageObjectBinding,
    ) -> None:
        del binding
        artifact = M365ExchangeArtifact(
            organization_id=organization_id,
            project_id=project_id,
            connection_id=connection_id,
            role="inbox",
            media="docx",
            state="IMPORTED",
            drive_id=connection.drive_id,
            drive_item_id=drive_item_id,
            logical_namespace="VALORA/Exchange/Inbox",
            display_name=metadata.name,
            e_tag=metadata.e_tag,
            c_tag=metadata.c_tag,
            provider_version_id=metadata.graph_version_id,
            observed_sha256=content_sha256,
            observed_byte_length=len(content),
            source_authority_type="DOCUMENT_REVISION",
            document_id=revision.document_id,
            document_revision_id=revision.id,
        )
        session.add(artifact)
        finalized_artifact.append(artifact)

    binding = finalize_storage_revision(
        db,
        organization_id=organization_id,
        intent_id=intent.id,
        retention_policy_code=retention_policy_code,
        retention_anchor_at=retention_anchor_at,
        minimum_retain_until=minimum_retain_until,
        finalization_callback=link_artifact,
    )
    revision = db.get(DocumentRevision, binding.document_revision_id)
    if revision is None:
        raise _error(409, "exchange_revision_missing", "Không thể xác minh phiên bản DOCX.")
    artifact = finalized_artifact[0] if finalized_artifact else db.query(
        M365ExchangeArtifact
    ).filter(
        M365ExchangeArtifact.organization_id == organization_id,
        M365ExchangeArtifact.connection_id == connection_id,
        M365ExchangeArtifact.drive_id == connection.drive_id,
        M365ExchangeArtifact.drive_item_id == drive_item_id,
    ).one()
    return revision, binding, artifact


async def create_docx_working_copy(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    connection_id: uuid.UUID,
    document_id: uuid.UUID,
    destination_name: str,
    idempotency_key: str,
    graph_gateway: M365GraphGateway,
    access_token: str,
    blob_store: DocumentBlobStore,
) -> M365ExchangeArtifact | None:
    actor = require_onedrive_actor(
        db, organization_id=organization_id, user_id=actor.id
    )
    head = db.query(DocumentRevisionCurrentHead).filter(
        DocumentRevisionCurrentHead.organization_id == organization_id,
        DocumentRevisionCurrentHead.project_id == project_id,
        DocumentRevisionCurrentHead.document_id == document_id,
    ).first()
    if head is None:
        raise _error(404, "document_revision_not_found", "Không tìm thấy phiên bản tài liệu.")
    binding = db.query(StorageObjectBinding).filter(
        StorageObjectBinding.organization_id == organization_id,
        StorageObjectBinding.project_id == project_id,
        StorageObjectBinding.document_id == document_id,
        StorageObjectBinding.document_revision_id == head.current_revision_id,
    ).first()
    connection = db.query(OneDriveConnection).filter(
        OneDriveConnection.organization_id == organization_id,
        OneDriveConnection.id == connection_id,
        OneDriveConnection.user_id == actor.id,
        OneDriveConnection.status == "active",
    ).first()
    if binding is None or connection is None:
        raise _error(409, "authoritative_blob_unavailable", "Blob tài liệu không khả dụng.")
    read_available, write_available = get_connection_capabilities(
        db, organization_id=organization_id, connection_id=connection_id
    )
    if not read_available or not write_available:
        raise _error(409, "exchange_reconsent_required", "Cần cấp quyền Exchange.")
    db.commit()
    read = await blob_store.read_verified(
        object_key=binding.object_key,
        expected_sha256=binding.content_sha256,
        expected_byte_length=binding.byte_length,
        max_bytes=MAX_EXCHANGE_BYTES,
    )
    if read.status != BlobReadStatus.MATCH or read.content is None:
        raise _error(503, "authoritative_blob_unavailable", "Blob tài liệu không khả dụng.")
    namespace = provision_exchange_namespace(
        graph_gateway=graph_gateway, access_token=access_token
    )
    if namespace.drive_id != connection.drive_id:
        raise _error(409, "exchange_target_escape", "Đích Exchange không hợp lệ.")
    operation = prepare_exchange_create(
        db,
        organization_id=organization_id,
        project_id=project_id,
        connection_id=connection_id,
        idempotency_key=idempotency_key,
        operation_kind="CREATE_WORKING",
        target_role="working",
        media="docx",
        drive_id=connection.drive_id,
        destination_parent_item_id=namespace.working_item_id,
        destination_name=destination_name,
        content=read.content,
    )
    return execute_exchange_create(
        db,
        organization_id=organization_id,
        operation_id=operation.id,
        content=read.content,
        graph_gateway=graph_gateway,
        access_token=access_token,
        source_authority_type="DOCUMENT_REVISION",
        document_id=document_id,
        document_revision_id=head.current_revision_id,
    )


async def create_docx_export(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    connection_id: uuid.UUID,
    document_id: uuid.UUID,
    destination_name: str,
    idempotency_key: str,
    graph_gateway: M365GraphGateway,
    access_token: str,
    blob_store: DocumentBlobStore,
) -> M365ExchangeArtifact | None:
    """Create a non-authoritative Export from the current immutable DOCX blob."""
    actor = require_onedrive_actor(
        db, organization_id=organization_id, user_id=actor.id
    )
    head = db.query(DocumentRevisionCurrentHead).filter(
        DocumentRevisionCurrentHead.organization_id == organization_id,
        DocumentRevisionCurrentHead.project_id == project_id,
        DocumentRevisionCurrentHead.document_id == document_id,
    ).first()
    if head is None:
        raise _error(404, "document_revision_not_found", "Không tìm thấy phiên bản tài liệu.")
    binding = db.query(StorageObjectBinding).filter(
        StorageObjectBinding.organization_id == organization_id,
        StorageObjectBinding.project_id == project_id,
        StorageObjectBinding.document_id == document_id,
        StorageObjectBinding.document_revision_id == head.current_revision_id,
    ).first()
    connection = db.query(OneDriveConnection).filter(
        OneDriveConnection.organization_id == organization_id,
        OneDriveConnection.id == connection_id,
        OneDriveConnection.user_id == actor.id,
        OneDriveConnection.status == "active",
    ).first()
    if binding is None or connection is None:
        raise _error(409, "authoritative_blob_unavailable", "Blob tài liệu không khả dụng.")
    read_available, write_available = get_connection_capabilities(
        db, organization_id=organization_id, connection_id=connection_id
    )
    if not read_available or not write_available:
        raise _error(409, "exchange_reconsent_required", "Cần cấp quyền Exchange.")
    db.commit()
    read = await blob_store.read_verified(
        object_key=binding.object_key,
        expected_sha256=binding.content_sha256,
        expected_byte_length=binding.byte_length,
        max_bytes=MAX_EXCHANGE_BYTES,
    )
    if read.status != BlobReadStatus.MATCH or read.content is None:
        raise _error(503, "authoritative_blob_unavailable", "Blob tài liệu không khả dụng.")
    namespace = provision_exchange_namespace(
        graph_gateway=graph_gateway, access_token=access_token
    )
    if namespace.drive_id != connection.drive_id:
        raise _error(409, "exchange_target_escape", "Đích Exchange không hợp lệ.")
    operation = prepare_exchange_create(
        db,
        organization_id=organization_id,
        project_id=project_id,
        connection_id=connection_id,
        idempotency_key=idempotency_key,
        operation_kind="CREATE_EXPORT",
        target_role="export",
        media="docx",
        drive_id=connection.drive_id,
        destination_parent_item_id=namespace.exports_item_id,
        destination_name=destination_name,
        content=read.content,
    )
    return execute_exchange_create(
        db,
        organization_id=organization_id,
        operation_id=operation.id,
        content=read.content,
        graph_gateway=graph_gateway,
        access_token=access_token,
        source_authority_type="DOCUMENT_REVISION",
        document_id=document_id,
        document_revision_id=head.current_revision_id,
    )


async def reimport_working_docx(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    definition_set: ManagedRegionDefinitionSet,
    idempotency_key: str,
    graph_gateway: M365GraphGateway,
    access_token: str,
    blob_store: DocumentBlobStore,
    storage_profile_id: str,
    container_name: str,
    retention_policy_code: str,
    retention_anchor_at: datetime,
    minimum_retain_until: datetime,
) -> DocxReimportResult:
    """Explicitly promote one verified Working DOCX into revision N+1."""
    actor = require_onedrive_actor(
        db, organization_id=organization_id, user_id=actor.id
    )
    artifact = db.query(M365ExchangeArtifact).filter(
        M365ExchangeArtifact.organization_id == organization_id,
        M365ExchangeArtifact.project_id == project_id,
        M365ExchangeArtifact.id == artifact_id,
        M365ExchangeArtifact.role == "working",
        M365ExchangeArtifact.media == "docx",
        M365ExchangeArtifact.document_id.is_not(None),
    ).first()
    if artifact is None or artifact.document_id is None:
        raise _error(404, "exchange_artifact_not_found", "Không tìm thấy bản làm việc.")
    connection = db.query(OneDriveConnection).filter(
        OneDriveConnection.organization_id == organization_id,
        OneDriveConnection.id == artifact.connection_id,
        OneDriveConnection.user_id == actor.id,
        OneDriveConnection.status == "active",
    ).first()
    if connection is None or artifact.drive_id != connection.drive_id:
        raise _error(404, "exchange_connection_not_found", "Không tìm thấy kết nối OneDrive.")
    _require_read_capability(
        db, organization_id=organization_id, connection_id=connection.id
    )
    document_id = artifact.document_id
    db.commit()
    metadata, content, content_sha256 = _verified_provider_bytes(
        graph_gateway=graph_gateway,
        access_token=access_token,
        drive_id=artifact.drive_id,
        drive_item_id=artifact.drive_item_id,
        expected_extension=".docx",
    )
    try:
        fingerprint = fingerprint_docx(content, definition_set)
    except ManagedRegionIntegrityError as exc:
        raise _error(422, "exchange_docx_invalid", "DOCX không đạt kiểm tra an toàn.") from exc
    head = db.query(DocumentRevisionCurrentHead).filter(
        DocumentRevisionCurrentHead.organization_id == organization_id,
        DocumentRevisionCurrentHead.project_id == project_id,
        DocumentRevisionCurrentHead.document_id == document_id,
    ).first()
    if head is None:
        raise _error(404, "document_revision_not_found", "Không tìm thấy phiên bản tài liệu.")
    current_binding = db.query(StorageObjectBinding).filter(
        StorageObjectBinding.organization_id == organization_id,
        StorageObjectBinding.document_revision_id == head.current_revision_id,
    ).first()
    current_revision = db.get(DocumentRevision, head.current_revision_id)
    if current_binding is None or current_revision is None:
        raise _error(409, "authoritative_blob_unavailable", "Blob tài liệu không khả dụng.")
    if (
        current_binding.content_sha256 == content_sha256
        and current_binding.byte_length == len(content)
    ):
        artifact.e_tag = metadata.e_tag
        artifact.c_tag = metadata.c_tag
        artifact.provider_version_id = metadata.graph_version_id
        artifact.observed_sha256 = content_sha256
        artifact.observed_byte_length = len(content)
        artifact.document_revision_id = current_revision.id
        artifact.state = "IMPORTED"
        artifact.observed_at = datetime.now(timezone.utc)
        db.commit()
        return DocxReimportResult("NO_CHANGE", current_revision, current_binding, artifact)
    request_digest = _request_digest(
        {
            "artifact_id": str(artifact.id),
            "document_id": str(document_id),
            "e_tag": metadata.e_tag,
            "sha256": content_sha256,
            "byte_length": len(content),
            "manifest": definition_set.manifest_digest_sha256,
        }
    )
    intent = prepare_storage_intent(
        db,
        actor=actor,
        organization_id=organization_id,
        project_id=project_id,
        document_id=document_id,
        idempotency_key=idempotency_key,
        request_digest_sha256=request_digest,
        plan_digest_sha256=definition_set.manifest_digest_sha256,
        decision_digest_sha256=fingerprint.outside_managed_digest_sha256,
    )
    record_storage_candidate(
        db,
        organization_id=organization_id,
        intent_id=intent.id,
        content=content,
        provider_kind=blob_store.provider_kind,
        storage_profile_id=storage_profile_id,
        container_name=container_name,
        object_key=(
            f"{organization_id.hex}/{project_id.hex}/{document_id.hex}/"
            f"{intent.id.hex}.docx"
        ),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        generator_version="onedrive-exchange-reimport-v1",
    )
    state = await create_or_recover_storage_object(
        db,
        organization_id=organization_id,
        intent_id=intent.id,
        content=content,
        blob_store=blob_store,
    )
    if state.current_state != "OBJECT_VERIFIED":
        raise _error(503, "exchange_storage_unavailable", "Chưa thể lưu DOCX an toàn.")

    def relink_artifact(
        session: Session,
        revision: DocumentRevision,
        binding: StorageObjectBinding,
    ) -> None:
        del session, binding
        artifact.e_tag = metadata.e_tag
        artifact.c_tag = metadata.c_tag
        artifact.provider_version_id = metadata.graph_version_id
        artifact.observed_sha256 = content_sha256
        artifact.observed_byte_length = len(content)
        artifact.document_revision_id = revision.id
        artifact.state = "IMPORTED"
        artifact.observed_at = datetime.now(timezone.utc)

    binding = finalize_storage_revision(
        db,
        organization_id=organization_id,
        intent_id=intent.id,
        retention_policy_code=retention_policy_code,
        retention_anchor_at=retention_anchor_at,
        minimum_retain_until=minimum_retain_until,
        finalization_callback=relink_artifact,
    )
    revision = db.get(DocumentRevision, binding.document_revision_id)
    if revision is None:
        raise _error(409, "exchange_revision_missing", "Không thể xác minh phiên bản DOCX.")
    return DocxReimportResult("REVISION_CREATED", revision, binding, artifact)


def import_inbox_xlsx(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    connection_id: uuid.UUID,
    batch_id: uuid.UUID,
    drive_item_id: str,
    graph_gateway: M365GraphGateway,
    access_token: str,
    request,
    reimport: bool = False,
) -> M365ExchangeArtifact:
    actor = require_onedrive_actor(
        db, organization_id=organization_id, user_id=actor.id
    )
    connection = db.query(OneDriveConnection).filter(
        OneDriveConnection.organization_id == organization_id,
        OneDriveConnection.id == connection_id,
        OneDriveConnection.user_id == actor.id,
        OneDriveConnection.status == "active",
    ).first()
    if connection is None:
        raise _error(404, "exchange_connection_not_found", "Không tìm thấy kết nối OneDrive.")
    _require_read_capability(
        db, organization_id=organization_id, connection_id=connection_id
    )
    existing = db.query(M365ExchangeArtifact).filter(
        M365ExchangeArtifact.organization_id == organization_id,
        M365ExchangeArtifact.connection_id == connection_id,
        M365ExchangeArtifact.drive_item_id == drive_item_id,
    ).first()
    if existing is not None and existing.project_id != project_id:
        raise _error(409, "exchange_artifact_conflict", "Tệp đã thuộc hồ sơ khác.")
    if existing is not None and not reimport:
        return existing
    db.commit()
    metadata, content, content_sha256 = _verified_provider_bytes(
        graph_gateway=graph_gateway,
        access_token=access_token,
        drive_id=connection.drive_id,
        drive_item_id=drive_item_id,
        expected_extension=".xlsx",
    )
    source_upload = UploadFile(filename=metadata.name, file=io.BytesIO(content))
    source = upload_source_artifact(
        db,
        org_id=organization_id,
        project_id=project_id,
        batch_id=batch_id,
        file=source_upload,
        request=request,
        current_user=actor,
    )
    batch = (
        db.query(ProjectAssetImportBatch)
        .filter(
            ProjectAssetImportBatch.organization_id == organization_id,
            ProjectAssetImportBatch.project_id == project_id,
            ProjectAssetImportBatch.id == batch_id,
        )
        .populate_existing()
        .first()
    )
    if (
        batch is None
        or source.state != "available"
        or batch.current_source_artifact_id != source.id
    ):
        raise _error(
            409,
            "exchange_excel_source_conflict",
            "Nguồn Excel mới không thắng được phiên bản hiện hành; chưa thay đổi staging.",
        )
    staging_upload = UploadFile(filename=metadata.name, file=io.BytesIO(content))
    upload_excel_file_orchestrator(
        db,
        org_id=organization_id,
        project_id=project_id,
        batch_id=batch_id,
        file=staging_upload,
        request=request,
        current_user=actor,
    )
    artifact = existing or M365ExchangeArtifact(
        organization_id=organization_id,
        project_id=project_id,
        connection_id=connection_id,
        role="inbox",
        media="xlsx",
        drive_id=connection.drive_id,
        drive_item_id=drive_item_id,
        logical_namespace="VALORA/Exchange/Inbox",
        source_authority_type="EXCEL_SOURCE_ARTIFACT",
    )
    artifact.state = "IMPORTED"
    artifact.display_name = metadata.name
    artifact.e_tag = metadata.e_tag
    artifact.c_tag = metadata.c_tag
    artifact.provider_version_id = metadata.graph_version_id
    artifact.observed_sha256 = content_sha256
    artifact.observed_byte_length = len(content)
    artifact.excel_import_batch_id = batch_id
    artifact.excel_source_artifact_id = source.id
    artifact.observed_at = datetime.now(timezone.utc)
    if existing is None:
        db.add(artifact)
    db.commit()
    return artifact
