"""Tenant-safe sealed baseline and OneDrive Personal revalidation services."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

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
from app.modules.m365_integration.domain.credential_vault import M365CredentialVault
from app.modules.m365_integration.domain.graph_gateway import (
    GraphDriveItem,
    M365GraphGateway,
    M365OAuthClient,
)
from app.modules.m365_integration.domain.managed_regions import (
    DocxFingerprint,
    FINGERPRINT_CONTRACT_VERSION,
    ManagedRegionDefinition,
    ManagedRegionDefinitionSet,
    ManagedRegionIntegrityError,
    PARSER_CONTRACT_VERSION,
    fingerprint_docx,
)
from app.modules.m365_integration.models import (
    M365ManagedContentBaseline,
    M365ManagedRegionBaseline,
    M365RevalidationObservation,
    M365RevisionBinding,
    OneDriveConnection,
)
from app.modules.project_master_data.models import (
    DocumentTemplate,
    DocumentTemplateStatus,
    GeneratedDocument,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    TemplateVersion,
    TemplateVersionStatus,
    User,
    UserRole,
    UserStatus,
)


PROJECT_READ_PERMISSION = "project:read"
PROJECT_UPDATE_PERMISSION = "project:update"
EVENT_BASELINE_SEALED = "M365_MANAGED_CONTENT_BASELINE_SEALED"
EVENT_REVALIDATION_COMPLETED = "M365_REVALIDATION_COMPLETED"
VALID_TRIGGERS = {"explicit_refresh", "freshness_required_action", "reconnect"}
MANAGED_REGION_MANIFEST_CONTRACT = "valora-managed-regions-v1"


@dataclass(frozen=True)
class _Scope:
    actor_id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    document_id: uuid.UUID
    document_revision_id: uuid.UUID
    document_revision: int
    document_data_snapshot_digest_sha256: str
    document_content_checksum_sha256: str
    binding_id: uuid.UUID
    connection_id: uuid.UUID
    connection_user_id: uuid.UUID
    credential_id: uuid.UUID
    drive_id: str
    drive_item_id: str
    binding_name: str
    binding_path: str | None
    binding_web_url: str
    binding_e_tag: str
    binding_c_tag: str | None
    baseline_id: uuid.UUID | None


@dataclass(frozen=True)
class RevalidationReadiness:
    document_id: uuid.UUID
    document_revision_id: uuid.UUID
    document_revision: int
    binding_id: uuid.UUID
    drive_id: str
    drive_item_id: str
    file_name: str
    file_path: str | None
    web_url: str
    baseline_eligible: bool
    recovery_code: str | None
    classification: str | None
    completed_at: datetime | None
    affected_region_keys: tuple[str, ...]
    is_fresh: bool
    is_safe_for_freshness_required_action: bool
    stale_reason: str | None
    blocking_reason: str | None
    next_action: str | None
    retryable: bool


@dataclass(frozen=True)
class _ObservationResult:
    classification: str
    reason_category: str | None
    retryable: bool
    metadata: GraphDriveItem | None = None
    fingerprint: DocxFingerprint | None = None
    affected_region_keys: tuple[str, ...] = ()
    affected_region_digests: tuple[dict[str, str], ...] = ()


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _abort(db: Session, status: int, code: str, detail: str) -> None:
    db.rollback()
    raise _error(status, code, detail)


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _definition_set_from_template_manifest(
    *,
    template_version_id: uuid.UUID,
    manifest: object,
) -> ManagedRegionDefinitionSet:
    """Parse only the explicit versioned Managed Region authority shape."""
    if not isinstance(manifest, dict) or manifest.get("managed_regions_contract") != (
        MANAGED_REGION_MANIFEST_CONTRACT
    ):
        raise ValueError("Managed Region manifest contract is unavailable.")
    raw_regions = manifest.get("managed_regions")
    if not isinstance(raw_regions, list) or not 1 <= len(raw_regions) <= 256:
        raise ValueError("Managed Region manifest is unavailable.")
    expected_keys = {
        "region_key",
        "locator",
        "semantic_type",
        "normalization_contract",
    }
    definitions: list[ManagedRegionDefinition] = []
    for raw_region in raw_regions:
        if not isinstance(raw_region, dict) or set(raw_region) != expected_keys:
            raise ValueError("Managed Region manifest entry is invalid.")
        if not all(isinstance(raw_region[key], str) for key in expected_keys):
            raise ValueError("Managed Region manifest entry is invalid.")
        definitions.append(
            ManagedRegionDefinition(
                region_key=raw_region["region_key"],
                locator=raw_region["locator"],
                semantic_type=raw_region["semantic_type"],
                normalization_contract=raw_region["normalization_contract"],
            )
        )
    return ManagedRegionDefinitionSet(
        authority_ref=(
            f"template-version:{template_version_id}:{MANAGED_REGION_MANIFEST_CONTRACT}"
        ),
        definitions=tuple(definitions),
    )


def _require_actor(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    permission: str,
) -> User:
    actor = (
        db.query(User)
        .options(
            selectinload(User.organization),
            selectinload(User.roles).selectinload(UserRole.role),
        )
        .filter(User.id == actor_id, User.organization_id == organization_id)
        .populate_existing()
        .first()
    )
    organization = db.get(OrganizationProfile, organization_id)
    if (
        actor is None
        or organization is None
        or str(getattr(actor.status, "value", actor.status)) != UserStatus.ACTIVE.value
        or str(getattr(organization.status, "value", organization.status))
        != OrganizationStatus.ACTIVE.value
        or permission not in derive_effective_permissions(actor, db)
    ):
        _abort(db, 403, "m365_revalidation_forbidden", "Không thể thực hiện thao tác này.")
    return actor


def _load_scope(
    db: Session,
    *,
    actor_id: uuid.UUID,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    expected_document_revision_id: uuid.UUID | None,
    expected_document_revision: int | None,
    permission: str,
    require_baseline: bool,
    binding_id: uuid.UUID | None = None,
    lock: bool = False,
) -> _Scope:
    actor = _require_actor(
        db,
        organization_id=organization_id,
        actor_id=actor_id,
        permission=permission,
    )
    project_query = db.query(Project).filter(
        Project.id == project_id,
        Project.organization_id == organization_id,
    )
    project = project_query.with_for_update().first() if lock else project_query.first()
    if project is None:
        _abort(db, 404, "project_not_found", "Không tìm thấy hồ sơ.")
    document_query = db.query(DocumentRecord).filter(
        DocumentRecord.id == document_id,
        DocumentRecord.organization_id == organization_id,
        DocumentRecord.project_id == project_id,
    )
    document = document_query.with_for_update().first() if lock else document_query.first()
    if document is None:
        _abort(db, 404, "document_not_found", "Không tìm thấy tài liệu.")
    head_query = db.query(DocumentRevisionCurrentHead).filter(
        DocumentRevisionCurrentHead.organization_id == organization_id,
        DocumentRevisionCurrentHead.project_id == project_id,
        DocumentRevisionCurrentHead.document_id == document_id,
    )
    head = head_query.with_for_update().first() if lock else head_query.first()
    if head is None:
        _abort(db, 404, "document_revision_not_found", "Không tìm thấy phiên bản tài liệu.")
    if expected_document_revision_id is not None and head.current_revision_id != (
        expected_document_revision_id
    ):
        _abort(
            db,
            409,
            "document_revision_conflict",
            "Phiên bản tài liệu đã thay đổi. Vui lòng tải lại.",
        )
    if expected_document_revision is not None and head.document_revision != (
        expected_document_revision
    ):
        _abort(
            db,
            409,
            "document_revision_conflict",
            "Phiên bản tài liệu đã thay đổi. Vui lòng tải lại.",
        )
    revision = (
        db.query(DocumentRevision)
        .filter(
            DocumentRevision.id == head.current_revision_id,
            DocumentRevision.organization_id == organization_id,
            DocumentRevision.project_id == project_id,
            DocumentRevision.document_id == document_id,
        )
        .first()
    )
    if revision is None:
        _abort(db, 404, "document_revision_not_found", "Không tìm thấy phiên bản tài liệu.")
    binding_query = db.query(M365RevisionBinding).filter(
        M365RevisionBinding.organization_id == organization_id,
        M365RevisionBinding.project_id == project_id,
        M365RevisionBinding.document_id == document_id,
        M365RevisionBinding.document_revision_id == revision.id,
    )
    if binding_id is not None:
        binding_query = binding_query.filter(M365RevisionBinding.id == binding_id)
    binding = binding_query.with_for_update().first() if lock else binding_query.first()
    if binding is None:
        _abort(db, 404, "m365_binding_not_found", "Không tìm thấy liên kết OneDrive.")
    connection_query = db.query(OneDriveConnection).filter(
        OneDriveConnection.id == binding.connection_id,
        OneDriveConnection.organization_id == organization_id,
        OneDriveConnection.user_id == actor.id,
        OneDriveConnection.status == "active",
        OneDriveConnection.drive_id == binding.drive_id,
    )
    connection = connection_query.with_for_update().first() if lock else connection_query.first()
    if connection is None:
        _abort(
            db,
            404,
            "onedrive_connection_not_found",
            "Không tìm thấy kết nối OneDrive.",
        )
    baseline_query = db.query(M365ManagedContentBaseline).filter(
        M365ManagedContentBaseline.organization_id == organization_id,
        M365ManagedContentBaseline.binding_id == binding.id,
        M365ManagedContentBaseline.document_revision_id == revision.id,
    )
    baseline = baseline_query.with_for_update().first() if lock else baseline_query.first()
    if require_baseline and baseline is None:
        _abort(
            db,
            409,
            "revalidation_baseline_required",
            "Tài liệu chưa có mốc so sánh hợp lệ. Vui lòng thiết lập lại liên kết.",
        )
    return _Scope(
        actor_id=actor.id,
        organization_id=organization_id,
        project_id=project_id,
        document_id=document_id,
        document_revision_id=revision.id,
        document_revision=revision.document_revision,
        document_data_snapshot_digest_sha256=revision.data_snapshot_digest_sha256,
        document_content_checksum_sha256=revision.content_checksum_sha256,
        binding_id=binding.id,
        connection_id=connection.id,
        connection_user_id=connection.user_id,
        credential_id=connection.credential_id,
        drive_id=binding.drive_id,
        drive_item_id=binding.drive_item_id,
        binding_name=binding.name,
        binding_path=binding.path,
        binding_web_url=binding.web_url,
        binding_e_tag=binding.e_tag,
        binding_c_tag=binding.c_tag,
        baseline_id=baseline.id if baseline is not None else None,
    )


def _acquire_access_token(
    db: Session,
    *,
    scope: _Scope,
    oauth_client: M365OAuthClient,
    credential_vault: M365CredentialVault,
) -> str:
    old_cache = credential_vault.load(
        organization_id=scope.organization_id,
        user_id=scope.connection_user_id,
        credential_id=scope.credential_id,
        purpose="token_cache",
    )
    token = oauth_client.acquire_access_token(token_cache=old_cache)
    if token.token_cache != old_cache:
        credential_vault.replace(
            organization_id=scope.organization_id,
            user_id=scope.connection_user_id,
            credential_id=scope.credential_id,
            purpose="token_cache",
            plaintext=token.token_cache,
        )
    db.commit()
    return token.access_token


def _baseline_request_digest(
    scope: _Scope,
    definition_set: ManagedRegionDefinitionSet,
) -> str:
    return _digest(
        {
            "actor_id": str(scope.actor_id),
            "binding_id": str(scope.binding_id),
            "contract": "m365-content-baseline-seal-v1",
            "document_revision_id": str(scope.document_revision_id),
            "manifest_digest": definition_set.manifest_digest_sha256,
            "organization_id": str(scope.organization_id),
            "project_id": str(scope.project_id),
        }
    )


def _bind_metadata_digest(binding: M365RevisionBinding) -> str:
    return _digest(
        {
            "c_tag": binding.c_tag,
            "drive_id": binding.drive_id,
            "drive_item_id": binding.drive_item_id,
            "e_tag": binding.e_tag,
            "graph_version_id": binding.graph_version_id,
            "last_modified_at": binding.last_modified_at.isoformat(),
            "size_bytes": binding.size_bytes,
        }
    )


def resolve_managed_region_definition_set(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    expected_document_revision_id: uuid.UUID,
    expected_document_revision: int,
    binding_id: uuid.UUID,
    generated_document_id: uuid.UUID,
) -> ManagedRegionDefinitionSet:
    """Resolve active template authority without accepting client-authored region facts."""
    scope = _load_scope(
        db,
        actor_id=actor.id,
        organization_id=organization_id,
        project_id=project_id,
        document_id=document_id,
        expected_document_revision_id=expected_document_revision_id,
        expected_document_revision=expected_document_revision,
        permission=PROJECT_UPDATE_PERMISSION,
        require_baseline=False,
        binding_id=binding_id,
    )
    authority = (
        db.query(GeneratedDocument, TemplateVersion, DocumentTemplate)
        .join(TemplateVersion, GeneratedDocument.template_version_id == TemplateVersion.id)
        .join(
            DocumentTemplate,
            TemplateVersion.document_template_id == DocumentTemplate.id,
        )
        .filter(
            GeneratedDocument.id == generated_document_id,
            GeneratedDocument.project_id == scope.project_id,
            GeneratedDocument.output_format == "docx",
            GeneratedDocument.document_type == DocumentTemplate.document_type,
            DocumentTemplate.organization_id == scope.organization_id,
        )
        .first()
    )
    if authority is None:
        _abort(
            db,
            404,
            "managed_region_authority_not_found",
            "Không tìm thấy cấu hình vùng quản lý phù hợp.",
        )
    generated, template_version, template = authority
    document = db.get(DocumentRecord, scope.document_id)
    if (
        document is None
        or template.document_type != document.document_type
        or generated.data_snapshot_hash
        != scope.document_data_snapshot_digest_sha256
        or str(getattr(template.status, "value", template.status))
        != DocumentTemplateStatus.ACTIVE.value
        or str(getattr(template_version.status, "value", template_version.status))
        != TemplateVersionStatus.ACTIVE.value
    ):
        _abort(
            db,
            409,
            "managed_region_authority_required",
            "Tài liệu chưa có cấu hình vùng quản lý đã phê duyệt.",
        )
    try:
        return _definition_set_from_template_manifest(
            template_version_id=template_version.id,
            manifest=template_version.placeholder_manifest,
        )
    except ValueError as exc:
        db.rollback()
        raise _error(
            409,
            "managed_region_authority_required",
            "Tài liệu chưa có cấu hình vùng quản lý đã phê duyệt.",
        ) from exc


def seal_existing_binding_baseline(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    expected_document_revision_id: uuid.UUID,
    expected_document_revision: int,
    binding_id: uuid.UUID,
    definition_set: ManagedRegionDefinitionSet,
    idempotency_key: str,
    oauth_client: M365OAuthClient,
    graph_gateway: M365GraphGateway,
    credential_vault: M365CredentialVault,
    correlation_id: str | None = None,
) -> M365ManagedContentBaseline:
    """Seal a PR-05 binding only when current bytes prove the immutable revision."""
    normalized_key = idempotency_key.strip()
    if not normalized_key or len(normalized_key) > 128:
        _abort(db, 422, "invalid_idempotency_key", "Khóa idempotency không hợp lệ.")
    scope = _load_scope(
        db,
        actor_id=actor.id,
        organization_id=organization_id,
        project_id=project_id,
        document_id=document_id,
        expected_document_revision_id=expected_document_revision_id,
        expected_document_revision=expected_document_revision,
        permission=PROJECT_UPDATE_PERMISSION,
        require_baseline=False,
        binding_id=binding_id,
    )
    digest = _baseline_request_digest(scope, definition_set)
    existing = (
        db.query(M365ManagedContentBaseline)
        .filter(
            M365ManagedContentBaseline.organization_id == organization_id,
            M365ManagedContentBaseline.idempotency_key == normalized_key,
        )
        .first()
    )
    if existing is not None:
        if existing.request_digest_sha256 != digest:
            _abort(db, 409, "idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác.")
        db.commit()
        return existing
    if scope.baseline_id is not None:
        _abort(
            db,
            409,
            "m365_content_baseline_exists",
            "Tài liệu đã có mốc so sánh nội dung.",
        )

    try:
        access_token = _acquire_access_token(
            db,
            scope=scope,
            oauth_client=oauth_client,
            credential_vault=credential_vault,
        )
        before = graph_gateway.get_drive_item(
            access_token=access_token,
            drive_id=scope.drive_id,
            drive_item_id=scope.drive_item_id,
        )
        if (
            before.drive_id != scope.drive_id
            or before.drive_item_id != scope.drive_item_id
            or before.e_tag != scope.binding_e_tag
            or (
                before.c_tag is not None
                and scope.binding_c_tag is not None
                and before.c_tag != scope.binding_c_tag
            )
        ):
            raise _error(
                409,
                "revalidation_baseline_required",
                "Tệp đã thay đổi từ khi liên kết. Không thể tạo mốc so sánh lịch sử.",
            )
        content = graph_gateway.get_drive_item_content(
            access_token=access_token,
            drive_id=scope.drive_id,
            drive_item_id=scope.drive_item_id,
        )
        if hashlib.sha256(content).hexdigest() != scope.document_content_checksum_sha256:
            raise _error(
                409,
                "revalidation_baseline_required",
                "Nội dung tệp không khớp phiên bản tài liệu đã liên kết.",
            )
        fingerprint = fingerprint_docx(content, definition_set)
        after = graph_gateway.get_drive_item(
            access_token=access_token,
            drive_id=scope.drive_id,
            drive_item_id=scope.drive_item_id,
        )
        if (
            after.drive_id != before.drive_id
            or after.drive_item_id != before.drive_item_id
            or after.e_tag != before.e_tag
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
            502,
            "onedrive_item_unavailable",
            "Không thể đọc nội dung tệp OneDrive.",
        ) from exc

    db.rollback()
    locked = _load_scope(
        db,
        actor_id=scope.actor_id,
        organization_id=scope.organization_id,
        project_id=scope.project_id,
        document_id=scope.document_id,
        expected_document_revision_id=scope.document_revision_id,
        expected_document_revision=scope.document_revision,
        permission=PROJECT_UPDATE_PERMISSION,
        require_baseline=False,
        binding_id=scope.binding_id,
        lock=True,
    )
    if locked != scope:
        _abort(
            db,
            409,
            "m365_revalidation_lineage_conflict",
            "Liên kết tài liệu đã thay đổi. Vui lòng tải lại.",
        )
    existing = (
        db.query(M365ManagedContentBaseline)
        .filter(
            M365ManagedContentBaseline.organization_id == organization_id,
            M365ManagedContentBaseline.idempotency_key == normalized_key,
        )
        .first()
    )
    if existing is not None:
        if existing.request_digest_sha256 != digest:
            _abort(db, 409, "idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác.")
        db.commit()
        return existing
    binding = db.get(M365RevisionBinding, scope.binding_id)
    assert binding is not None
    baseline = M365ManagedContentBaseline(
        organization_id=scope.organization_id,
        project_id=scope.project_id,
        document_id=scope.document_id,
        document_revision_id=scope.document_revision_id,
        binding_id=scope.binding_id,
        connection_id=scope.connection_id,
        drive_id=scope.drive_id,
        drive_item_id=scope.drive_item_id,
        source_content_sha256=fingerprint.source_content_sha256,
        source_size_bytes=fingerprint.source_size_bytes,
        source_e_tag=before.e_tag,
        source_c_tag=before.c_tag,
        bind_metadata_digest_sha256=_bind_metadata_digest(binding),
        authority_ref=definition_set.authority_ref,
        parser_contract_version=fingerprint.parser_contract_version,
        fingerprint_contract_version=fingerprint.fingerprint_contract_version,
        managed_region_manifest_digest_sha256=(fingerprint.managed_region_manifest_digest_sha256),
        outside_managed_digest_sha256=fingerprint.outside_managed_digest_sha256,
        whole_canonical_digest_sha256=fingerprint.whole_canonical_digest_sha256,
        provenance_kind="existing_binding_verified",
        idempotency_key=normalized_key,
        request_digest_sha256=digest,
        created_by_user_id=scope.actor_id,
    )
    db.add(baseline)
    db.flush()
    for position, region in enumerate(fingerprint.regions):
        db.add(
            M365ManagedRegionBaseline(
                organization_id=scope.organization_id,
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
    log_audit_event(
        db,
        event_name=EVENT_BASELINE_SEALED,
        entity_type="M365ManagedContentBaseline",
        entity_id=baseline.id,
        organization_id=scope.organization_id,
        actor_user_id=scope.actor_id,
        command_name="SealExistingM365BindingBaseline",
        correlation_id=correlation_id,
        payload={
            "project_id": str(scope.project_id),
            "document_id": str(scope.document_id),
            "document_revision_id": str(scope.document_revision_id),
            "binding_id": str(scope.binding_id),
            "managed_regions": [region.region_key for region in fingerprint.regions],
            "parser_contract_version": fingerprint.parser_contract_version,
            "fingerprint_contract_version": fingerprint.fingerprint_contract_version,
        },
    )
    try:
        db.commit()
        db.refresh(baseline)
        return baseline
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(M365ManagedContentBaseline)
            .filter(
                M365ManagedContentBaseline.organization_id == organization_id,
                M365ManagedContentBaseline.idempotency_key == normalized_key,
            )
            .first()
        )
        if raced is not None and raced.request_digest_sha256 == digest:
            return raced
        raise _error(
            409,
            "m365_content_baseline_conflict",
            "Mốc so sánh nội dung đã thay đổi đồng thời.",
        ) from exc


def _definition_set_from_baseline(
    db: Session,
    baseline: M365ManagedContentBaseline,
) -> tuple[ManagedRegionDefinitionSet, dict[str, M365ManagedRegionBaseline]]:
    if (
        baseline.parser_contract_version != PARSER_CONTRACT_VERSION
        or baseline.fingerprint_contract_version != FINGERPRINT_CONTRACT_VERSION
    ):
        raise ManagedRegionIntegrityError("Managed Region parser contract is unsupported.")
    rows = (
        db.query(M365ManagedRegionBaseline)
        .filter(
            M365ManagedRegionBaseline.organization_id == baseline.organization_id,
            M365ManagedRegionBaseline.content_baseline_id == baseline.id,
        )
        .order_by(M365ManagedRegionBaseline.position, M365ManagedRegionBaseline.region_key)
        .all()
    )
    definitions = tuple(
        ManagedRegionDefinition(
            region_key=row.region_key,
            locator=row.locator,
            semantic_type=row.semantic_type,
            normalization_contract=row.normalization_contract,
        )
        for row in rows
    )
    definition_set = ManagedRegionDefinitionSet(
        authority_ref=baseline.authority_ref,
        definitions=definitions,
    )
    if definition_set.manifest_digest_sha256 != baseline.managed_region_manifest_digest_sha256:
        raise ManagedRegionIntegrityError("Managed Region manifest digest is inconsistent.")
    return definition_set, {row.region_key: row for row in rows}


def _provider_error_result(exc: Exception) -> _ObservationResult:
    category = getattr(exc, "category", "provider_unavailable")
    retryable = bool(getattr(exc, "retryable", True))
    if category in {"not_found", "identity_mismatch", "not_a_file"}:
        return _ObservationResult(
            classification="file_replaced_or_moved",
            reason_category=category,
            retryable=retryable,
        )
    return _ObservationResult(
        classification="access_unavailable",
        reason_category=category,
        retryable=retryable,
    )


def _observe(
    db: Session,
    *,
    scope: _Scope,
    oauth_client: M365OAuthClient,
    graph_gateway: M365GraphGateway,
    credential_vault: M365CredentialVault,
) -> _ObservationResult:
    try:
        access_token = _acquire_access_token(
            db,
            scope=scope,
            oauth_client=oauth_client,
            credential_vault=credential_vault,
        )
        metadata = graph_gateway.get_drive_item(
            access_token=access_token,
            drive_id=scope.drive_id,
            drive_item_id=scope.drive_item_id,
        )
    except Exception as exc:
        db.rollback()
        return _provider_error_result(exc)
    if metadata.drive_id != scope.drive_id or metadata.drive_item_id != scope.drive_item_id:
        return _ObservationResult(
            classification="file_replaced_or_moved",
            reason_category="identity_mismatch",
            retryable=False,
            metadata=metadata,
        )

    baseline = db.get(M365ManagedContentBaseline, scope.baseline_id)
    assert baseline is not None
    tags_agree = metadata.e_tag == baseline.source_e_tag and (
        metadata.c_tag is None
        or baseline.source_c_tag is None
        or metadata.c_tag == baseline.source_c_tag
    )
    if tags_agree:
        return _ObservationResult(
            classification="no_change",
            reason_category=None,
            retryable=False,
            metadata=metadata,
        )

    try:
        definition_set, baseline_regions = _definition_set_from_baseline(db, baseline)
        content = graph_gateway.get_drive_item_content(
            access_token=access_token,
            drive_id=scope.drive_id,
            drive_item_id=scope.drive_item_id,
        )
        after = graph_gateway.get_drive_item(
            access_token=access_token,
            drive_id=scope.drive_id,
            drive_item_id=scope.drive_item_id,
        )
        if (
            after.drive_id != metadata.drive_id
            or after.drive_item_id != metadata.drive_item_id
            or after.e_tag != metadata.e_tag
            or after.size_bytes != len(content)
        ):
            return _ObservationResult(
                classification="access_unavailable",
                reason_category="metadata_content_race",
                retryable=True,
                metadata=after,
            )
        fingerprint = fingerprint_docx(content, definition_set)
    except ManagedRegionIntegrityError:
        return _ObservationResult(
            classification="access_unavailable",
            reason_category="content_integrity_unavailable",
            retryable=False,
            metadata=metadata,
        )
    except Exception as exc:
        return _provider_error_result(exc)

    affected: list[str] = []
    affected_digests: list[dict[str, str]] = []
    for region in fingerprint.regions:
        old = baseline_regions[region.region_key]
        if (
            old.normalized_value_digest_sha256 != region.normalized_value_digest_sha256
            or old.structural_digest_sha256 != region.structural_digest_sha256
        ):
            affected.append(region.region_key)
            affected_digests.append(
                {
                    "region": region.region_key,
                    "old_value_digest": old.normalized_value_digest_sha256,
                    "new_value_digest": region.normalized_value_digest_sha256,
                    "old_structure_digest": old.structural_digest_sha256,
                    "new_structure_digest": region.structural_digest_sha256,
                }
            )
    if affected:
        classification = "external_change_in_managed"
    elif fingerprint.outside_managed_digest_sha256 != (baseline.outside_managed_digest_sha256):
        classification = "external_change_outside_managed"
    else:
        classification = "no_change"
    return _ObservationResult(
        classification=classification,
        reason_category=None,
        retryable=False,
        metadata=after,
        fingerprint=fingerprint,
        affected_region_keys=tuple(affected),
        affected_region_digests=tuple(affected_digests),
    )


def _revalidation_request_digest(scope: _Scope, trigger: str) -> str:
    return _digest(
        {
            "actor_id": str(scope.actor_id),
            "baseline_id": str(scope.baseline_id),
            "binding_id": str(scope.binding_id),
            "contract": "m365-revalidation-v1",
            "document_revision_id": str(scope.document_revision_id),
            "organization_id": str(scope.organization_id),
            "project_id": str(scope.project_id),
            "trigger": trigger,
        }
    )


def _existing_observation(
    db: Session,
    *,
    organization_id: uuid.UUID,
    idempotency_key: str,
    request_digest: str,
) -> M365RevalidationObservation | None:
    observation = (
        db.query(M365RevalidationObservation)
        .filter(
            M365RevalidationObservation.organization_id == organization_id,
            M365RevalidationObservation.idempotency_key == idempotency_key,
        )
        .first()
    )
    if observation is None:
        return None
    if observation.request_digest_sha256 != request_digest:
        _abort(db, 409, "idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác.")
    db.commit()
    return observation


def revalidate_document(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    expected_document_revision_id: uuid.UUID,
    expected_document_revision: int,
    trigger: str,
    idempotency_key: str,
    oauth_client: M365OAuthClient,
    graph_gateway: M365GraphGateway,
    credential_vault: M365CredentialVault,
    correlation_id: str | None = None,
) -> M365RevalidationObservation:
    """Observe the exact current binding and append one terminal five-way result."""
    normalized_key = idempotency_key.strip()
    if not normalized_key or len(normalized_key) > 128:
        _abort(db, 422, "invalid_idempotency_key", "Khóa idempotency không hợp lệ.")
    if trigger not in VALID_TRIGGERS:
        _abort(db, 422, "invalid_revalidation_trigger", "Lý do kiểm tra không hợp lệ.")
    started_at = datetime.now(timezone.utc)
    scope = _load_scope(
        db,
        actor_id=actor.id,
        organization_id=organization_id,
        project_id=project_id,
        document_id=document_id,
        expected_document_revision_id=expected_document_revision_id,
        expected_document_revision=expected_document_revision,
        permission=PROJECT_READ_PERMISSION,
        require_baseline=True,
    )
    digest = _revalidation_request_digest(scope, trigger)
    replay = _existing_observation(
        db,
        organization_id=organization_id,
        idempotency_key=normalized_key,
        request_digest=digest,
    )
    if replay is not None:
        return replay

    result = _observe(
        db,
        scope=scope,
        oauth_client=oauth_client,
        graph_gateway=graph_gateway,
        credential_vault=credential_vault,
    )
    db.rollback()
    locked = _load_scope(
        db,
        actor_id=scope.actor_id,
        organization_id=scope.organization_id,
        project_id=scope.project_id,
        document_id=scope.document_id,
        expected_document_revision_id=scope.document_revision_id,
        expected_document_revision=scope.document_revision,
        permission=PROJECT_READ_PERMISSION,
        require_baseline=True,
        binding_id=scope.binding_id,
        lock=True,
    )
    if locked != scope:
        _abort(
            db,
            409,
            "m365_revalidation_lineage_conflict",
            "Liên kết tài liệu đã thay đổi. Vui lòng tải lại.",
        )
    replay = _existing_observation(
        db,
        organization_id=organization_id,
        idempotency_key=normalized_key,
        request_digest=digest,
    )
    if replay is not None:
        return replay

    metadata = result.metadata
    fingerprint = result.fingerprint
    observation = M365RevalidationObservation(
        organization_id=scope.organization_id,
        project_id=scope.project_id,
        document_id=scope.document_id,
        document_revision_id=scope.document_revision_id,
        binding_id=scope.binding_id,
        content_baseline_id=scope.baseline_id,
        connection_id=scope.connection_id,
        trigger=trigger,
        classification=result.classification,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        observed_drive_id=metadata.drive_id if metadata else None,
        observed_drive_item_id=metadata.drive_item_id if metadata else None,
        observed_graph_version_id=metadata.graph_version_id if metadata else None,
        observed_e_tag=metadata.e_tag if metadata else None,
        observed_c_tag=metadata.c_tag if metadata else None,
        observed_last_modified_at=metadata.last_modified_at if metadata else None,
        observed_size_bytes=metadata.size_bytes if metadata else None,
        observed_name=metadata.name if metadata else None,
        observed_path=metadata.path if metadata else None,
        observed_web_url=metadata.web_url if metadata else None,
        observed_content_sha256=(fingerprint.source_content_sha256 if fingerprint else None),
        observed_whole_canonical_digest_sha256=(
            fingerprint.whole_canonical_digest_sha256 if fingerprint else None
        ),
        observed_outside_managed_digest_sha256=(
            fingerprint.outside_managed_digest_sha256 if fingerprint else None
        ),
        parser_contract_version=(fingerprint.parser_contract_version if fingerprint else None),
        fingerprint_contract_version=(
            fingerprint.fingerprint_contract_version if fingerprint else None
        ),
        affected_region_keys=list(result.affected_region_keys),
        affected_region_digests=list(result.affected_region_digests),
        reason_category=result.reason_category,
        retryable=result.retryable,
        idempotency_key=normalized_key,
        request_digest_sha256=digest,
        actor_user_id=scope.actor_id,
        correlation_id=correlation_id,
    )
    try:
        db.add(observation)
        db.flush()
        log_audit_event(
            db,
            event_name=EVENT_REVALIDATION_COMPLETED,
            entity_type="M365RevalidationObservation",
            entity_id=observation.id,
            organization_id=scope.organization_id,
            actor_user_id=scope.actor_id,
            command_name="RevalidateM365Document",
            correlation_id=correlation_id,
            payload={
                "project_id": str(scope.project_id),
                "document_id": str(scope.document_id),
                "document_revision_id": str(scope.document_revision_id),
                "binding_id": str(scope.binding_id),
                "classification": result.classification,
                "managed_regions": list(result.affected_region_keys),
                "reason_category": result.reason_category,
                "retryable": result.retryable,
                "trigger": trigger,
            },
        )
        db.commit()
        db.refresh(observation)
        return observation
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(M365RevalidationObservation)
            .filter(
                M365RevalidationObservation.organization_id == organization_id,
                M365RevalidationObservation.idempotency_key == normalized_key,
            )
            .first()
        )
        if raced is not None and raced.request_digest_sha256 == digest:
            return raced
        raise _error(
            409,
            "m365_revalidation_conflict",
            "Kết quả kiểm tra đã thay đổi đồng thời.",
        ) from exc


def get_revalidation_readiness(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    document_id: uuid.UUID,
) -> RevalidationReadiness:
    """Compute current readiness from exact current revision/binding/baseline lineage."""
    scope = _load_scope(
        db,
        actor_id=actor.id,
        organization_id=organization_id,
        project_id=project_id,
        document_id=document_id,
        expected_document_revision_id=None,
        expected_document_revision=None,
        permission=PROJECT_READ_PERMISSION,
        require_baseline=False,
    )
    if scope.baseline_id is None:
        return RevalidationReadiness(
            document_id=scope.document_id,
            document_revision_id=scope.document_revision_id,
            document_revision=scope.document_revision,
            binding_id=scope.binding_id,
            drive_id=scope.drive_id,
            drive_item_id=scope.drive_item_id,
            file_name=scope.binding_name,
            file_path=scope.binding_path,
            web_url=scope.binding_web_url,
            baseline_eligible=False,
            recovery_code="baseline_required",
            classification=None,
            completed_at=None,
            affected_region_keys=(),
            is_fresh=False,
            is_safe_for_freshness_required_action=False,
            stale_reason="baseline_required",
            blocking_reason="baseline_required",
            next_action="reconnect_or_rebind",
            retryable=False,
        )
    latest = (
        db.query(M365RevalidationObservation)
        .filter(
            M365RevalidationObservation.organization_id == scope.organization_id,
            M365RevalidationObservation.project_id == scope.project_id,
            M365RevalidationObservation.document_id == scope.document_id,
            M365RevalidationObservation.document_revision_id == scope.document_revision_id,
            M365RevalidationObservation.binding_id == scope.binding_id,
            M365RevalidationObservation.content_baseline_id == scope.baseline_id,
        )
        .order_by(
            M365RevalidationObservation.completed_at.desc(),
            M365RevalidationObservation.id.desc(),
        )
        .first()
    )
    if latest is None:
        return RevalidationReadiness(
            document_id=scope.document_id,
            document_revision_id=scope.document_revision_id,
            document_revision=scope.document_revision,
            binding_id=scope.binding_id,
            drive_id=scope.drive_id,
            drive_item_id=scope.drive_item_id,
            file_name=scope.binding_name,
            file_path=scope.binding_path,
            web_url=scope.binding_web_url,
            baseline_eligible=True,
            recovery_code="revalidation_required",
            classification=None,
            completed_at=None,
            affected_region_keys=(),
            is_fresh=False,
            is_safe_for_freshness_required_action=False,
            stale_reason="revalidation_required",
            blocking_reason=None,
            next_action="check_changes",
            retryable=True,
        )
    safe = latest.classification in {"no_change", "external_change_outside_managed"}
    blocking = (
        "binding_untrusted"
        if latest.classification == "file_replaced_or_moved"
        else "managed_change_review_required"
        if latest.classification == "external_change_in_managed"
        else "access_unavailable"
        if latest.classification == "access_unavailable"
        else None
    )
    next_action = (
        "review_managed_changes"
        if latest.classification == "external_change_in_managed"
        else "reconnect_or_rebind"
        if latest.classification == "file_replaced_or_moved"
        else "retry_revalidation"
        if latest.classification == "access_unavailable"
        else None
    )
    return RevalidationReadiness(
        document_id=scope.document_id,
        document_revision_id=scope.document_revision_id,
        document_revision=scope.document_revision,
        binding_id=scope.binding_id,
        drive_id=scope.drive_id,
        drive_item_id=scope.drive_item_id,
        file_name=latest.observed_name or scope.binding_name,
        file_path=(
            latest.observed_path if latest.observed_path is not None else scope.binding_path
        ),
        web_url=latest.observed_web_url or scope.binding_web_url,
        baseline_eligible=True,
        recovery_code=blocking,
        classification=latest.classification,
        completed_at=latest.completed_at,
        affected_region_keys=tuple(latest.affected_region_keys),
        is_fresh=safe,
        is_safe_for_freshness_required_action=safe,
        stale_reason=(
            "access_unavailable"
            if latest.classification == "access_unavailable"
            else "binding_untrusted"
            if latest.classification == "file_replaced_or_moved"
            else None
        ),
        blocking_reason=blocking,
        next_action=next_action,
        retryable=latest.retryable,
    )
