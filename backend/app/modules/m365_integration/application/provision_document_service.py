"""Adopt one verified OneDrive DOCX into canonical VALORA document lineage."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.modules.document_workspace.models import (
    DocumentRecord,
    DocumentRevision,
    DocumentRevisionCurrentHead,
)
from app.modules.m365_integration.application.bind_document_service import (
    EVENT_M365_BASELINE_SEALED,
    EVENT_M365_REVISION_BOUND,
    _connection_access_token,
    _metadata_digest,
)
from app.modules.m365_integration.application.revalidation_service import (
    _definition_set_from_template_manifest,
    _require_actor,
)
from app.modules.m365_integration.domain.credential_vault import M365CredentialVault
from app.modules.m365_integration.domain.graph_gateway import M365GraphGateway, M365OAuthClient
from app.modules.m365_integration.domain.managed_regions import (
    MAX_DOCX_BYTES,
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
from app.modules.project_master_data.models import (
    DocumentTemplate,
    DocumentTemplateStatus,
    GeneratedDocument,
    GeneratedDocumentStatus,
    OrganizationProfile,
    Project,
    RenderJob,
    RenderJobStatus,
    TemplateVersion,
    TemplateVersionStatus,
    User,
)


EVENT_M365_CANONICAL_DOCUMENT_PROVISIONED = "M365_CANONICAL_DOCUMENT_PROVISIONED"
PROJECT_UPDATE_PERMISSION = "project:update"
MAX_SNAPSHOT_BYTES = 1024 * 1024
MAX_SNAPSHOT_DEPTH = 32
MAX_SNAPSHOT_NODES = 10_000


@dataclass(frozen=True)
class ProvisionedDocument:
    document_id: uuid.UUID
    document_revision_id: uuid.UUID
    document_revision: int
    render_job_id: uuid.UUID
    generated_document_id: uuid.UUID
    binding_id: uuid.UUID
    baseline_id: uuid.UUID
    document_type: str
    title: str
    file_name: str
    web_url: str


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _abort(db: Session, status: int, code: str, detail: str) -> None:
    db.rollback()
    raise _error(status, code, detail)


def _canonical_snapshot(value: dict[str, object]) -> tuple[dict[str, object], str]:
    nodes = 0

    def visit(item: object, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_SNAPSHOT_NODES or depth > MAX_SNAPSHOT_DEPTH:
            raise ValueError("Data Snapshot is too complex.")
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ValueError("Data Snapshot keys must be strings.")
                visit(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                visit(child, depth + 1)
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError("Data Snapshot numbers must be finite.")
        elif item is not None and not isinstance(item, (str, int, float, bool)):
            raise ValueError("Data Snapshot contains an unsupported value.")

    visit(value, 0)
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(encoded) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Data Snapshot is too large.")
    normalized = json.loads(encoded)
    return normalized, hashlib.sha256(encoded).hexdigest()


def _request_digest(
    *,
    actor_id: uuid.UUID,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    template_version_id: uuid.UUID,
    connection_id: uuid.UUID,
    drive_item_id: str,
    title: str,
    data_snapshot_digest_sha256: str,
    manifest_digest_sha256: str,
) -> str:
    payload = {
        "actor_id": str(actor_id),
        "connection_id": str(connection_id),
        "contract": "m365-canonical-document-provision-v1",
        "data_snapshot_digest_sha256": data_snapshot_digest_sha256,
        "drive_item_id": drive_item_id,
        "managed_region_manifest_digest_sha256": manifest_digest_sha256,
        "organization_id": str(organization_id),
        "project_id": str(project_id),
        "template_version_id": str(template_version_id),
        "title": title,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _storage_key(document_id: uuid.UUID) -> str:
    return f"onedrive-adoption/{document_id}"


def _replay(
    db: Session,
    *,
    organization_id: uuid.UUID,
    idempotency_key: str,
    request_digest: str,
) -> ProvisionedDocument | None:
    revision = (
        db.query(DocumentRevision)
        .filter(
            DocumentRevision.organization_id == organization_id,
            DocumentRevision.idempotency_key == idempotency_key,
        )
        .first()
    )
    if revision is None:
        occupied = (
            db.query(M365RevisionBinding.id)
            .filter(
                M365RevisionBinding.organization_id == organization_id,
                M365RevisionBinding.idempotency_key == idempotency_key,
            )
            .first()
            or db.query(M365ManagedContentBaseline.id)
            .filter(
                M365ManagedContentBaseline.organization_id == organization_id,
                M365ManagedContentBaseline.idempotency_key == idempotency_key,
            )
            .first()
        )
        if occupied is not None:
            _abort(db, 409, "idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác.")
        return None
    if revision.request_digest_sha256 != request_digest:
        _abort(db, 409, "idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác.")

    document = db.get(DocumentRecord, revision.document_id)
    head = db.get(
        DocumentRevisionCurrentHead,
        (revision.organization_id, revision.project_id, revision.document_id),
    )
    binding = (
        db.query(M365RevisionBinding)
        .filter(
            M365RevisionBinding.organization_id == organization_id,
            M365RevisionBinding.document_revision_id == revision.id,
        )
        .first()
    )
    baseline = None
    if binding is not None:
        baseline = (
            db.query(M365ManagedContentBaseline)
            .filter(
                M365ManagedContentBaseline.organization_id == organization_id,
                M365ManagedContentBaseline.binding_id == binding.id,
            )
            .first()
        )
    generated = (
        db.query(GeneratedDocument)
        .filter(
            GeneratedDocument.project_id == revision.project_id,
            GeneratedDocument.storage_key == _storage_key(revision.document_id),
        )
        .first()
    )
    render_job = db.get(RenderJob, generated.render_job_id) if generated is not None else None
    if (
        document is None
        or head is None
        or head.current_revision_id != revision.id
        or binding is None
        or baseline is None
        or generated is None
        or render_job is None
    ):
        _abort(
            db,
            409,
            "provision_lineage_incomplete",
            "Lineage tài liệu hiện có không đầy đủ.",
        )
    return ProvisionedDocument(
        document_id=document.id,
        document_revision_id=revision.id,
        document_revision=revision.document_revision,
        render_job_id=render_job.id,
        generated_document_id=generated.id,
        binding_id=binding.id,
        baseline_id=baseline.id,
        document_type=document.document_type,
        title=document.title,
        file_name=binding.name,
        web_url=binding.web_url,
    )


def _load_authority(
    db: Session,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    template_version_id: uuid.UUID,
    lock: bool,
) -> tuple[Project, DocumentTemplate, TemplateVersion, ManagedRegionDefinitionSet]:
    project_query = db.query(Project).filter(
        Project.id == project_id,
        Project.organization_id == organization_id,
    )
    project = project_query.with_for_update().first() if lock else project_query.first()
    if project is None:
        _abort(db, 404, "project_not_found", "Không tìm thấy hồ sơ.")
    authority_query = (
        db.query(TemplateVersion, DocumentTemplate)
        .join(DocumentTemplate, TemplateVersion.document_template_id == DocumentTemplate.id)
        .filter(
            TemplateVersion.id == template_version_id,
            TemplateVersion.template_format == "docx",
            TemplateVersion.status == TemplateVersionStatus.ACTIVE,
            DocumentTemplate.organization_id == organization_id,
            DocumentTemplate.status == DocumentTemplateStatus.ACTIVE,
        )
    )
    authority = authority_query.with_for_update().first() if lock else authority_query.first()
    if authority is None:
        _abort(
            db,
            404,
            "managed_region_authority_not_found",
            "Không tìm thấy cấu hình vùng quản lý phù hợp.",
        )
    version, template = authority
    try:
        definitions = _definition_set_from_template_manifest(
            template_version_id=version.id,
            manifest=version.placeholder_manifest,
        )
    except ValueError as exc:
        db.rollback()
        raise _error(
            409,
            "managed_region_authority_required",
            "Tài liệu chưa có cấu hình vùng quản lý đã phê duyệt.",
        ) from exc
    return project, template, version, definitions


def provision_onedrive_document(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    template_version_id: uuid.UUID,
    connection_id: uuid.UUID,
    drive_item_id: str,
    title: str,
    data_snapshot: dict[str, object],
    idempotency_key: str,
    oauth_client: M365OAuthClient,
    graph_gateway: M365GraphGateway,
    credential_vault: M365CredentialVault,
    correlation_id: str | None = None,
) -> ProvisionedDocument:
    """Verify an existing personal-drive DOCX, then create all canonical lineage."""
    normalized_key = idempotency_key.strip()
    normalized_item_id = drive_item_id.strip()
    normalized_title = title.strip()
    if not normalized_key or len(normalized_key) > 128:
        _abort(db, 422, "invalid_idempotency_key", "Khóa idempotency không hợp lệ.")
    if not normalized_item_id or len(normalized_item_id) > 255:
        _abort(db, 422, "invalid_drive_item_id", "Định danh tệp OneDrive không hợp lệ.")
    if not normalized_title or len(normalized_title) > 255:
        _abort(db, 422, "invalid_document_title", "Tên tài liệu không hợp lệ.")
    try:
        normalized_snapshot, snapshot_digest = _canonical_snapshot(data_snapshot)
    except (TypeError, ValueError) as exc:
        db.rollback()
        raise _error(422, "invalid_data_snapshot", "Data Snapshot không hợp lệ.") from exc

    actor = _require_actor(
        db,
        organization_id=organization_id,
        actor_id=actor.id,
        permission=PROJECT_UPDATE_PERMISSION,
    )
    _, template, _, definitions = _load_authority(
        db,
        organization_id=organization_id,
        project_id=project_id,
        template_version_id=template_version_id,
        lock=False,
    )
    digest = _request_digest(
        actor_id=actor.id,
        organization_id=organization_id,
        project_id=project_id,
        template_version_id=template_version_id,
        connection_id=connection_id,
        drive_item_id=normalized_item_id,
        title=normalized_title,
        data_snapshot_digest_sha256=snapshot_digest,
        manifest_digest_sha256=definitions.manifest_digest_sha256,
    )
    replay = _replay(
        db,
        organization_id=organization_id,
        idempotency_key=normalized_key,
        request_digest=digest,
    )
    if replay is not None:
        db.rollback()
        return replay

    connection, access_token = _connection_access_token(
        db,
        organization_id=organization_id,
        actor_id=actor.id,
        connection_id=connection_id,
        oauth_client=oauth_client,
        credential_vault=credential_vault,
    )
    expected_drive_id = connection.drive_id
    try:
        observed = graph_gateway.get_drive_item(
            access_token=access_token,
            drive_id=expected_drive_id,
            drive_item_id=normalized_item_id,
        )
        if observed.size_bytes <= 0 or observed.size_bytes > MAX_DOCX_BYTES:
            raise _error(
                422,
                "managed_region_baseline_invalid",
                "Kích thước tệp DOCX nằm ngoài giới hạn cho phép.",
            )
        if not observed.name.lower().endswith(".docx"):
            raise _error(422, "managed_region_baseline_invalid", "Tệp phải có định dạng DOCX.")
        content = graph_gateway.get_drive_item_content(
            access_token=access_token,
            drive_id=expected_drive_id,
            drive_item_id=normalized_item_id,
        )
        if len(content) != observed.size_bytes:
            raise _error(409, "m365_content_race", "Tệp OneDrive thay đổi trong lúc kiểm tra.")
        content_checksum = hashlib.sha256(content).hexdigest()
        fingerprint = fingerprint_docx(content, definitions)
        after = graph_gateway.get_drive_item(
            access_token=access_token,
            drive_id=expected_drive_id,
            drive_item_id=normalized_item_id,
        )
        if (
            observed.drive_id != expected_drive_id
            or observed.drive_item_id != normalized_item_id
            or after.drive_id != observed.drive_id
            or after.drive_item_id != observed.drive_item_id
            or after.e_tag != observed.e_tag
            or after.c_tag != observed.c_tag
            or after.size_bytes != observed.size_bytes
            or after.last_modified_at != observed.last_modified_at
        ):
            raise _error(409, "m365_content_race", "Tệp OneDrive thay đổi trong lúc kiểm tra.")
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
        raise _error(502, "onedrive_item_unavailable", "Không thể đọc tệp OneDrive.") from exc

    # External I/O is complete. Re-resolve and lock every authority before inserting.
    actor_id = actor.id
    actor = _require_actor(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        permission=PROJECT_UPDATE_PERMISSION,
    )
    organization = (
        db.query(OrganizationProfile)
        .filter(OrganizationProfile.id == organization_id)
        .with_for_update()
        .first()
    )
    if organization is None:
        _abort(db, 403, "m365_revalidation_forbidden", "Không thể thực hiện thao tác này.")
    _, current_template, _, current_definitions = _load_authority(
        db,
        organization_id=organization_id,
        project_id=project_id,
        template_version_id=template_version_id,
        lock=True,
    )
    if (
        current_template.document_type != template.document_type
        or current_definitions.manifest_digest_sha256 != definitions.manifest_digest_sha256
    ):
        _abort(
            db,
            409,
            "managed_region_authority_changed",
            "Cấu hình vùng quản lý đã thay đổi. Vui lòng thử lại.",
        )
    current_connection = (
        db.query(OneDriveConnection)
        .filter(
            OneDriveConnection.id == connection_id,
            OneDriveConnection.organization_id == organization_id,
            OneDriveConnection.user_id == actor.id,
            OneDriveConnection.status == "active",
            OneDriveConnection.drive_id == expected_drive_id,
        )
        .with_for_update()
        .first()
    )
    if current_connection is None:
        _abort(db, 404, "onedrive_connection_not_found", "Không tìm thấy kết nối OneDrive.")
    replay = _replay(
        db,
        organization_id=organization_id,
        idempotency_key=normalized_key,
        request_digest=digest,
    )
    if replay is not None:
        db.rollback()
        return replay
    duplicate_item = (
        db.query(M365RevisionBinding.id)
        .filter(
            M365RevisionBinding.organization_id == organization_id,
            M365RevisionBinding.drive_id == expected_drive_id,
            M365RevisionBinding.drive_item_id == normalized_item_id,
        )
        .first()
    )
    if duplicate_item is not None:
        _abort(
            db,
            409,
            "onedrive_item_already_bound",
            "Tệp OneDrive đã được liên kết với tài liệu khác.",
        )

    document = DocumentRecord(
        organization_id=organization_id,
        project_id=project_id,
        document_type=current_template.document_type,
        title=normalized_title,
        created_by_user_id=actor.id,
    )
    db.add(document)
    db.flush()
    render_job = RenderJob(
        project_id=project_id,
        template_version_id=template_version_id,
        render_mode="onedrive_adoption",
        output_formats=["docx"],
        data_snapshot=normalized_snapshot,
        data_snapshot_hash=snapshot_digest,
        status=RenderJobStatus.COMPLETED,
        created_by=actor.id,
    )
    db.add(render_job)
    db.flush()
    generated = GeneratedDocument(
        project_id=project_id,
        render_job_id=render_job.id,
        document_type=current_template.document_type,
        output_format="docx",
        filename=observed.name,
        storage_key=_storage_key(document.id),
        checksum_sha256=content_checksum,
        file_size_bytes=len(content),
        template_version_id=template_version_id,
        data_snapshot_hash=snapshot_digest,
        status=GeneratedDocumentStatus.DRAFT,
    )
    revision = DocumentRevision(
        organization_id=organization_id,
        project_id=project_id,
        document_id=document.id,
        document_revision=1,
        data_snapshot_digest_sha256=snapshot_digest,
        content_checksum_sha256=content_checksum,
        idempotency_key=normalized_key,
        request_digest_sha256=digest,
        created_by_user_id=actor.id,
    )
    db.add_all([generated, revision])
    db.flush()
    head = DocumentRevisionCurrentHead(
        organization_id=organization_id,
        project_id=project_id,
        document_id=document.id,
        current_revision_id=revision.id,
        document_revision=1,
    )
    binding = M365RevisionBinding(
        organization_id=organization_id,
        project_id=project_id,
        document_id=document.id,
        document_revision_id=revision.id,
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
    db.add_all([head, binding])
    db.flush()
    baseline = M365ManagedContentBaseline(
        organization_id=organization_id,
        project_id=project_id,
        document_id=document.id,
        document_revision_id=revision.id,
        binding_id=binding.id,
        connection_id=connection_id,
        drive_id=observed.drive_id,
        drive_item_id=observed.drive_item_id,
        source_content_sha256=fingerprint.source_content_sha256,
        source_size_bytes=fingerprint.source_size_bytes,
        source_e_tag=observed.e_tag,
        source_c_tag=observed.c_tag,
        bind_metadata_digest_sha256=_metadata_digest(binding),
        authority_ref=current_definitions.authority_ref,
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
                locator_digest_sha256=hashlib.sha256(region.locator.encode("utf-8")).hexdigest(),
                semantic_type=region.semantic_type,
                normalization_contract=region.normalization_contract,
                normalized_value_digest_sha256=region.normalized_value_digest_sha256,
                structural_digest_sha256=region.structural_digest_sha256,
            )
        )

    common_payload = {
        "project_id": str(project_id),
        "document_id": str(document.id),
        "document_revision_id": str(revision.id),
        "binding_id": str(binding.id),
        "connection_id": str(connection_id),
        "drive_id": observed.drive_id,
        "drive_item_id": observed.drive_item_id,
    }
    log_audit_event(
        db,
        event_name=EVENT_M365_CANONICAL_DOCUMENT_PROVISIONED,
        entity_type="DocumentRecord",
        entity_id=document.id,
        organization_id=organization_id,
        actor_user_id=actor.id,
        command_name="ProvisionOneDriveDocument",
        correlation_id=correlation_id,
        payload={
            **common_payload,
            "render_job_id": str(render_job.id),
            "generated_document_id": str(generated.id),
            "template_version_id": str(template_version_id),
        },
    )
    log_audit_event(
        db,
        event_name=EVENT_M365_REVISION_BOUND,
        entity_type="M365RevisionBinding",
        entity_id=binding.id,
        organization_id=organization_id,
        actor_user_id=actor.id,
        command_name="ProvisionOneDriveDocument",
        correlation_id=correlation_id,
        payload=common_payload,
    )
    log_audit_event(
        db,
        event_name=EVENT_M365_BASELINE_SEALED,
        entity_type="M365ManagedContentBaseline",
        entity_id=baseline.id,
        organization_id=organization_id,
        actor_user_id=actor.id,
        command_name="ProvisionOneDriveDocument",
        correlation_id=correlation_id,
        payload={
            **common_payload,
            "baseline_id": str(baseline.id),
            "managed_regions": [region.region_key for region in fingerprint.regions],
            "parser_contract_version": fingerprint.parser_contract_version,
            "fingerprint_contract_version": fingerprint.fingerprint_contract_version,
        },
    )
    result = ProvisionedDocument(
        document_id=document.id,
        document_revision_id=revision.id,
        document_revision=1,
        render_job_id=render_job.id,
        generated_document_id=generated.id,
        binding_id=binding.id,
        baseline_id=baseline.id,
        document_type=document.document_type,
        title=document.title,
        file_name=binding.name,
        web_url=binding.web_url,
    )
    try:
        db.commit()
        return result
    except IntegrityError as exc:
        db.rollback()
        raced = _replay(
            db,
            organization_id=organization_id,
            idempotency_key=normalized_key,
            request_digest=digest,
        )
        if raced is not None:
            db.rollback()
            return raced
        raise _error(
            409,
            "m365_document_provision_conflict",
            "Tài liệu đã thay đổi đồng thời.",
        ) from exc
