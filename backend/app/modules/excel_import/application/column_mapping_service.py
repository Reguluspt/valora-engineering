"""S13-PR-004 application services for confirmed Column Mapping Memory."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Iterator, Mapping, Sequence

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.excel_import.application.adapters import detect_format_and_adapter
from app.modules.excel_import.application.workbook_structure_service import (
    ArtifactFingerprint,
    _materialize_verified_source,
    _verify_snapshot_page,
)
from app.modules.excel_import.domain.column_mapping import (
    FINGERPRINT_CONTRACT_VERSION,
    MAPPING_CONTRACT_VERSION,
    MATERIALIZATION_CONTRACT_VERSION,
    SUPPORTED_STRUCTURE_RULE_VERSION,
    ColumnMappingContractError,
    MappingField,
    MappingSuggestion,
    SemanticRole,
    build_mapping_snapshot,
    build_template_fingerprint,
    candidate_geometry,
    canonical_json_bytes,
    column_letter,
    mapping_digest,
    mapping_summary,
    normalize_header,
    profile_mapping_digest,
    project_asset_row,
    similar_template_remap,
    suggest_mapping,
    validate_mapping_snapshot,
)
from app.modules.excel_import.domain.source_artifact import DEFAULT_SOURCE_LIMITS
from app.modules.excel_import.domain.workbook_adapter import AdapterError
from app.modules.excel_import.domain.workbook_structure import (
    RowClass,
    canonical_payload_digest,
    replay_frozen_candidate_rows,
)
from app.modules.excel_import.infrastructure.object_storage import (
    ObjectStoragePort,
    get_object_storage,
)
from app.modules.excel_import.models import (
    ColumnMappingDecision,
    ColumnMappingField,
    ColumnMappingProfile,
    ColumnMappingProfileUsage,
    ImportSourceArtifact,
    WorkbookStructureSnapshot,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    ImportBatchStatus,
    ImportRowValidationStatus,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    User,
    UserStatus,
)

_SPOOL_CHUNK_ROWS = 250
_AUDIT_ENTITY = "ColumnMappingDecision"


@dataclass(frozen=True)
class MappingContext:
    project: Project
    batch: ProjectAssetImportBatch
    artifact: ImportSourceArtifact
    snapshot: WorkbookStructureSnapshot
    candidate_index: int
    candidate: dict[str, Any]
    template_fingerprint_sha256: str


@dataclass(frozen=True)
class VerifiedProfile:
    profile: ColumnMappingProfile
    fields: tuple[MappingField, ...]
    candidate: dict[str, Any]


@dataclass(frozen=True)
class ProfileRetrievalResult:
    exact_customer_profile: VerifiedProfile | None
    similar_customer_profiles: tuple[VerifiedProfile, ...]
    organization_template: VerifiedProfile | None


@dataclass(frozen=True)
class MappingProposalResult:
    decision: ColumnMappingDecision
    review_required: bool
    review_reasons: tuple[str, ...]
    exact_profile_id: uuid.UUID | None
    similar_profile_ids: tuple[uuid.UUID, ...]
    organization_template_id: uuid.UUID | None


@dataclass(frozen=True)
class StructureSeal:
    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    import_batch_id: uuid.UUID
    source_artifact_id: uuid.UUID
    snapshot_version: int
    source_checksum_sha256: str
    rule_version: str
    adapter_name: str
    adapter_version: str
    disposition: str
    candidate_count: int
    analysis_digest_sha256: str
    payload_digest_sha256: str

    @classmethod
    def freeze(cls, snapshot: WorkbookStructureSnapshot) -> StructureSeal:
        return cls(
            id=snapshot.id,
            organization_id=snapshot.organization_id,
            project_id=snapshot.project_id,
            import_batch_id=snapshot.import_batch_id,
            source_artifact_id=snapshot.source_artifact_id,
            snapshot_version=snapshot.snapshot_version,
            source_checksum_sha256=snapshot.source_checksum_sha256,
            rule_version=snapshot.rule_version,
            adapter_name=snapshot.adapter_name,
            adapter_version=snapshot.adapter_version,
            disposition=_status_value(snapshot.disposition),
            candidate_count=snapshot.candidate_count,
            analysis_digest_sha256=snapshot.analysis_digest_sha256,
            payload_digest_sha256=canonical_payload_digest(snapshot.structure_payload),
        )


@dataclass(frozen=True)
class ConfirmationSeal:
    id: uuid.UUID
    organization_id: uuid.UUID
    customer_id: uuid.UUID
    project_id: uuid.UUID
    import_batch_id: uuid.UUID
    source_artifact_id: uuid.UUID
    structure_snapshot_id: uuid.UUID
    profile_id: uuid.UUID | None
    actor_user_id: uuid.UUID
    outcome: str
    template_fingerprint_sha256: str
    mapping_digest_sha256: str
    mapping_snapshot_json: bytes

    @classmethod
    def freeze(cls, decision: ColumnMappingDecision) -> ConfirmationSeal:
        return cls(
            id=decision.id,
            organization_id=decision.organization_id,
            customer_id=decision.customer_id,
            project_id=decision.project_id,
            import_batch_id=decision.import_batch_id,
            source_artifact_id=decision.source_artifact_id,
            structure_snapshot_id=decision.structure_snapshot_id,
            profile_id=decision.profile_id,
            actor_user_id=decision.actor_user_id,
            outcome=_status_value(decision.outcome),
            template_fingerprint_sha256=decision.template_fingerprint_sha256,
            mapping_digest_sha256=decision.mapping_digest_sha256,
            mapping_snapshot_json=canonical_json_bytes(decision.mapping_snapshot),
        )

    def mapping_snapshot(self) -> dict[str, Any]:
        value = json.loads(self.mapping_snapshot_json)
        if not isinstance(value, dict):
            raise ValueError("invalid frozen mapping snapshot")
        return value


@dataclass(frozen=True)
class FrozenMaterialization:
    source: ArtifactFingerprint
    structure: StructureSeal
    confirmation: ConfirmationSeal
    customer_id: uuid.UUID
    batch_source_artifact_id: uuid.UUID | None
    batch_status: str
    candidate_json: bytes
    fields: tuple[MappingField, ...]

    def candidate(self) -> dict[str, Any]:
        value = json.loads(self.candidate_json)
        if not isinstance(value, dict):
            raise ValueError("invalid frozen candidate")
        return value


def _status_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _contract_error(exc: ColumnMappingContractError) -> HTTPException:
    status = 409 if exc.error_code in {
        "mapping_candidate_invalid",
        "mapping_role_invalid",
        "mapping_role_cardinality_invalid",
        "unsupported_structure_rule_version",
    } else 500
    return _error(status, exc.error_code, exc.detail)


def _assert_actor(actor: User, org_id: uuid.UUID) -> None:
    if (
        actor is None
        or actor.id is None
        or actor.organization_id != org_id
        or _status_value(actor.status) != UserStatus.ACTIVE.value
    ):
        raise HTTPException(status_code=404, detail="Project not found")


def _reload_active_actor_and_org(
    db: Session, *, actor: User, org_id: uuid.UUID
) -> User:
    actor_id = getattr(actor, "id", None)
    organization = (
        db.query(OrganizationProfile)
        .filter(
            OrganizationProfile.id == org_id,
            OrganizationProfile.status == OrganizationStatus.ACTIVE.value,
        )
        .populate_existing()
        .first()
    )
    persisted_actor = (
        db.query(User)
        .filter(
            User.id == actor_id,
            User.organization_id == org_id,
            User.status == UserStatus.ACTIVE.value,
        )
        .populate_existing()
        .first()
    )
    if organization is None or persisted_actor is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return persisted_actor


def _candidate_at(snapshot: WorkbookStructureSnapshot, candidate_index: int) -> dict[str, Any]:
    if isinstance(candidate_index, bool) or not isinstance(candidate_index, int) or candidate_index < 0:
        raise _error(409, "mapping_candidate_invalid", "Vùng bảng được chọn không hợp lệ.")
    payload = snapshot.structure_payload
    candidates = payload.get("candidates") if isinstance(payload, dict) else None
    if not isinstance(candidates, list) or candidate_index >= len(candidates):
        raise _error(409, "mapping_candidate_invalid", "Vùng bảng được chọn không còn hợp lệ.")
    candidate = candidates[candidate_index]
    if not isinstance(candidate, dict):
        raise _error(500, "mapping_structure_integrity_failure", "Bằng chứng cấu trúc không toàn vẹn.")
    try:
        candidate_geometry(candidate)
    except ColumnMappingContractError as exc:
        raise _error(500, "mapping_structure_integrity_failure", exc.detail) from exc
    return candidate


def _resolve_context(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    artifact_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    candidate_index: int,
    allow_applied: bool = False,
) -> MappingContext:
    _assert_actor(actor, org_id)
    project = (
        db.query(Project)
        .filter(Project.organization_id == org_id, Project.id == project_id)
        .populate_existing()
        .first()
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    batch = (
        db.query(ProjectAssetImportBatch)
        .filter(
            ProjectAssetImportBatch.organization_id == org_id,
            ProjectAssetImportBatch.project_id == project_id,
            ProjectAssetImportBatch.id == batch_id,
        )
        .populate_existing()
        .first()
    )
    if batch is None:
        raise HTTPException(status_code=404, detail="Import batch not found")
    artifact = (
        db.query(ImportSourceArtifact)
        .filter(
            ImportSourceArtifact.organization_id == org_id,
            ImportSourceArtifact.project_id == project_id,
            ImportSourceArtifact.import_batch_id == batch_id,
            ImportSourceArtifact.id == artifact_id,
        )
        .populate_existing()
        .first()
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Source artifact not found")
    if batch.current_source_artifact_id != artifact.id:
        raise _error(
            409,
            "mapping_source_not_current",
            "Tệp nguồn không còn là thế hệ hiện tại của lô nhập liệu.",
        )
    if _status_value(artifact.state) != "available":
        raise _error(409, "mapping_source_not_available", "Tệp nguồn chưa sẵn sàng để ánh xạ.")
    if not allow_applied and _status_value(batch.status) == ImportBatchStatus.APPLIED.value:
        raise _error(
            409, "mapping_batch_already_applied", "Lô nhập liệu đã được áp dụng trước đó."
        )
    snapshot = (
        db.query(WorkbookStructureSnapshot)
        .filter(
            WorkbookStructureSnapshot.organization_id == org_id,
            WorkbookStructureSnapshot.project_id == project_id,
            WorkbookStructureSnapshot.import_batch_id == batch_id,
            WorkbookStructureSnapshot.source_artifact_id == artifact_id,
            WorkbookStructureSnapshot.id == snapshot_id,
        )
        .populate_existing()
        .first()
    )
    if snapshot is None:
        raise _error(404, "mapping_structure_not_found", "Không tìm thấy snapshot cấu trúc.")
    try:
        _verify_snapshot_page(db, [snapshot], artifact)
    except HTTPException as exc:
        raise _error(
            500,
            "mapping_structure_integrity_failure",
            "Bằng chứng cấu trúc không còn toàn vẹn.",
        ) from exc
    if snapshot.rule_version != SUPPORTED_STRUCTURE_RULE_VERSION:
        raise _error(
            409,
            "unsupported_structure_rule_version",
            "Snapshot cần được phân tích lại bằng quy tắc cấu trúc hiện hành.",
        )
    candidate = _candidate_at(snapshot, candidate_index)
    try:
        fingerprint = build_template_fingerprint(candidate, rule_version=snapshot.rule_version)
    except ColumnMappingContractError as exc:
        raise _contract_error(exc) from exc
    return MappingContext(project, batch, artifact, snapshot, candidate_index, candidate, fingerprint)


def _mapping_fields_from_rows(rows: Sequence[ColumnMappingField]) -> tuple[MappingField, ...]:
    output: list[MappingField] = []
    for row in sorted(rows, key=lambda item: item.source_column_index):
        try:
            role = SemanticRole(_status_value(row.semantic_role))
        except ValueError as exc:
            raise _error(
                500, "mapping_profile_integrity_failure", "Hồ sơ ánh xạ chứa vai trò không hợp lệ."
            ) from exc
        if row.normalized_header != normalize_header(row.original_header):
            raise _error(
                500,
                "mapping_profile_integrity_failure",
                "Bằng chứng tiêu đề trong hồ sơ ánh xạ không toàn vẹn.",
            )
        output.append(
            MappingField(
                row.source_column_index,
                row.source_column_letter,
                row.original_header,
                role,
            )
        )
    return tuple(output)


def _profile_candidate(profile: ColumnMappingProfile, fields: Sequence[MappingField]) -> dict[str, Any]:
    return {
        "sheet_name": profile.sheet_name,
        "header_start_row": profile.header_start_row,
        "header_end_row": profile.header_end_row,
        "data_start_row": profile.data_start_row,
        "candidate_table_bounds": {
            "min_row": profile.header_start_row,
            "max_row": profile.data_start_row,
            "min_column": profile.min_column,
            "max_column": profile.max_column,
        },
        "header_labels": [field.original_header for field in fields],
    }


def _verify_profile(db: Session, profile: ColumnMappingProfile) -> VerifiedProfile:
    scope = _status_value(profile.scope_type)
    if (
        (scope == "customer" and (
            profile.customer_id is None
            or profile.customer_id != profile.source_customer_id
            or profile.approved_by_user_id is not None
            or profile.approved_at is not None
        ))
        or (scope == "organization_template" and (
            profile.customer_id is not None
            or profile.approved_by_user_id is None
            or profile.approved_at is None
        ))
        or scope not in {"customer", "organization_template"}
    ):
        raise _error(
            500, "mapping_profile_integrity_failure", "Phạm vi hồ sơ ánh xạ không hợp lệ."
        )
    rows = (
        db.query(ColumnMappingField)
        .filter(
            ColumnMappingField.organization_id == profile.organization_id,
            ColumnMappingField.profile_id == profile.id,
        )
        .order_by(ColumnMappingField.source_column_index, ColumnMappingField.id)
        .populate_existing()
        .all()
    )
    fields = _mapping_fields_from_rows(rows)
    candidate = _profile_candidate(profile, fields)
    try:
        digest = profile_mapping_digest(candidate, fields)
        fingerprint = build_template_fingerprint(
            candidate, rule_version=SUPPORTED_STRUCTURE_RULE_VERSION
        )
    except ColumnMappingContractError as exc:
        raise _error(500, "mapping_profile_integrity_failure", exc.detail) from exc
    if (
        digest != profile.mapping_digest_sha256
        or fingerprint != profile.template_fingerprint_sha256
        or profile.mapping_contract_version != MAPPING_CONTRACT_VERSION
        or profile.fingerprint_contract_version != FINGERPRINT_CONTRACT_VERSION
    ):
        raise _error(
            500, "mapping_profile_integrity_failure", "Hồ sơ ánh xạ không còn toàn vẹn."
        )
    artifact = (
        db.query(ImportSourceArtifact)
        .filter(
            ImportSourceArtifact.id == profile.source_artifact_id,
            ImportSourceArtifact.organization_id == profile.organization_id,
            ImportSourceArtifact.project_id == profile.source_project_id,
            ImportSourceArtifact.import_batch_id == profile.source_import_batch_id,
        )
        .populate_existing()
        .first()
    )
    snapshot = (
        db.query(WorkbookStructureSnapshot)
        .filter(
            WorkbookStructureSnapshot.id == profile.structure_snapshot_id,
            WorkbookStructureSnapshot.organization_id == profile.organization_id,
            WorkbookStructureSnapshot.project_id == profile.source_project_id,
            WorkbookStructureSnapshot.import_batch_id == profile.source_import_batch_id,
            WorkbookStructureSnapshot.source_artifact_id == profile.source_artifact_id,
        )
        .populate_existing()
        .first()
    )
    source_project = (
        db.query(Project)
        .filter(
            Project.id == profile.source_project_id,
            Project.organization_id == profile.organization_id,
            Project.customer_id == profile.source_customer_id,
        )
        .populate_existing()
        .first()
    )
    source_batch = (
        db.query(ProjectAssetImportBatch)
        .filter(
            ProjectAssetImportBatch.organization_id == profile.organization_id,
            ProjectAssetImportBatch.project_id == profile.source_project_id,
            ProjectAssetImportBatch.id == profile.source_import_batch_id,
        )
        .populate_existing()
        .first()
    )
    confirmer = (
        db.query(User)
        .filter(
            User.id == profile.confirmed_by_user_id,
            User.organization_id == profile.organization_id,
        )
        .first()
    )
    approver = None
    if profile.approved_by_user_id is not None:
        approver = (
            db.query(User)
            .filter(
                User.id == profile.approved_by_user_id,
                User.organization_id == profile.organization_id,
            )
            .first()
        )
    if (
        artifact is None
        or snapshot is None
        or source_project is None
        or source_batch is None
        or source_project.customer_id != profile.source_customer_id
        or confirmer is None
        or (scope == "organization_template" and approver is None)
    ):
        raise _error(
            500, "mapping_profile_integrity_failure", "Lineage của hồ sơ ánh xạ không hợp lệ."
        )
    try:
        _verify_snapshot_page(db, [snapshot], artifact)
    except HTTPException as exc:
        raise _error(
            500, "mapping_profile_integrity_failure", "Snapshot nguồn của hồ sơ không toàn vẹn."
        ) from exc
    return VerifiedProfile(profile, fields, candidate)


def retrieve_mapping_profiles(
    db: Session, *, context: MappingContext
) -> ProfileRetrievalResult:
    base = db.query(ColumnMappingProfile).filter(
        ColumnMappingProfile.organization_id == context.project.organization_id,
        ColumnMappingProfile.status == "active",
    )
    exact_rows = (
        base.filter(
            ColumnMappingProfile.scope_type == "customer",
            ColumnMappingProfile.customer_id == context.project.customer_id,
            ColumnMappingProfile.template_fingerprint_sha256
            == context.template_fingerprint_sha256,
        )
        .populate_existing()
        .all()
    )
    if len(exact_rows) > 1:
        raise _error(409, "mapping_profile_conflict", "Có nhiều hồ sơ ánh xạ đang hoạt động.")
    exact = _verify_profile(db, exact_rows[0]) if exact_rows else None

    similar: list[VerifiedProfile] = []
    current_geometry = candidate_geometry(context.candidate)
    candidates = (
        base.filter(
            ColumnMappingProfile.scope_type == "customer",
            ColumnMappingProfile.customer_id == context.project.customer_id,
            ColumnMappingProfile.template_fingerprint_sha256
            != context.template_fingerprint_sha256,
        )
        .order_by(
            ColumnMappingProfile.confirmed_at.desc(), ColumnMappingProfile.id.asc()
        )
        .populate_existing()
        .all()
    )
    for row in candidates:
        verified = _verify_profile(db, row)
        result = similar_template_remap(
            current_headers=current_geometry["header_labels"],
            current_min_column=current_geometry["min_column"],
            current_header_height=(
                current_geometry["header_end_row"] - current_geometry["header_start_row"] + 1
            ),
            profile_fields=verified.fields,
            profile_headers=[field.original_header for field in verified.fields],
            profile_header_height=(row.header_end_row - row.header_start_row + 1),
        )
        if result.qualifies:
            similar.append(verified)

    template_rows = (
        base.filter(
            ColumnMappingProfile.scope_type == "organization_template",
            ColumnMappingProfile.customer_id.is_(None),
            ColumnMappingProfile.template_fingerprint_sha256
            == context.template_fingerprint_sha256,
        )
        .populate_existing()
        .all()
    )
    if len(template_rows) > 1:
        raise _error(409, "mapping_profile_conflict", "Có nhiều mẫu tổ chức đang hoạt động.")
    organization_template = None
    if template_rows:
        template = template_rows[0]
        if template.approved_by_user_id is None or template.approved_at is None:
            raise _error(
                500,
                "mapping_profile_integrity_failure",
                "Mẫu tổ chức chưa có bằng chứng phê duyệt hợp lệ.",
            )
        organization_template = _verify_profile(db, template)
    return ProfileRetrievalResult(exact, tuple(similar), organization_template)


def _current_snapshot(
    context: MappingContext, fields: Iterable[MappingField | Mapping[str, Any]]
) -> dict[str, Any]:
    try:
        return build_mapping_snapshot(
            source_artifact_id=str(context.artifact.id),
            source_generation=context.artifact.generation,
            source_checksum_sha256=context.artifact.checksum_sha256,
            structure_snapshot_id=str(context.snapshot.id),
            snapshot_version=context.snapshot.snapshot_version,
            structure_rule_version=context.snapshot.rule_version,
            structure_digest_sha256=context.snapshot.analysis_digest_sha256,
            candidate_index=context.candidate_index,
            candidate=context.candidate,
            fields=fields,
        )
    except ColumnMappingContractError as exc:
        raise _contract_error(exc) from exc


def _prefill_fields(context: MappingContext, verified: VerifiedProfile) -> tuple[MappingField, ...]:
    geometry = candidate_geometry(context.candidate)
    if len(verified.fields) != len(geometry["header_labels"]):
        raise _error(
            500, "mapping_profile_integrity_failure", "Số lượng cột của hồ sơ không còn hợp lệ."
        )
    return tuple(
        MappingField(
            geometry["min_column"] + offset,
            verified.fields[offset].source_column_letter,
            geometry["header_labels"][offset],
            verified.fields[offset].semantic_role,
        )
        for offset in range(len(verified.fields))
    )


def _audit(
    db: Session,
    *,
    actor: User,
    event_name: str,
    command_name: str,
    entity_type: str,
    entity_id: uuid.UUID,
    org_id: uuid.UUID,
    correlation_id: str | None,
    payload: dict[str, Any],
) -> None:
    db.add(
        AuditEvent(
            organization_id=org_id,
            actor_user_id=actor.id,
            event_name=event_name,
            entity_type=entity_type,
            entity_id=entity_id,
            command_name=command_name,
            correlation_id=correlation_id,
            payload=payload,
        )
    )


def _proposal_result_from_existing(decision: ColumnMappingDecision) -> MappingProposalResult:
    summary = decision.before_summary if isinstance(decision.before_summary, dict) else {}
    try:
        similar_ids = tuple(uuid.UUID(value) for value in summary.get("similar_profile_ids", []))
        exact_id = uuid.UUID(summary["exact_profile_id"]) if summary.get("exact_profile_id") else None
        template_id = (
            uuid.UUID(summary["organization_template_id"])
            if summary.get("organization_template_id")
            else None
        )
    except (ValueError, TypeError) as exc:
        raise _error(
            500, "mapping_structure_integrity_failure", "Bằng chứng đề xuất không toàn vẹn."
        ) from exc
    return MappingProposalResult(
        decision,
        True,
        tuple(summary.get("review_reasons", ["human_confirmation_required"])),
        exact_id,
        similar_ids,
        template_id,
    )


def propose_column_mapping(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    artifact_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    candidate_index: int,
    command_id: uuid.UUID,
    correlation_id: str | None = None,
) -> MappingProposalResult:
    actor = _reload_active_actor_and_org(db, actor=actor, org_id=org_id)
    existing = (
        db.query(ColumnMappingDecision)
        .filter(
            ColumnMappingDecision.organization_id == org_id,
            ColumnMappingDecision.command_id == command_id,
        )
        .populate_existing()
        .first()
    )
    if existing is not None:
        candidate = existing.mapping_snapshot.get("candidate", {})
        if (
            _status_value(existing.decision_kind) != "proposal"
            or existing.actor_user_id != actor.id
            or existing.project_id != project_id
            or existing.import_batch_id != batch_id
            or existing.source_artifact_id != artifact_id
            or existing.structure_snapshot_id != snapshot_id
            or candidate.get("candidate_index") != candidate_index
        ):
            raise _error(409, "idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác.")
        return _proposal_result_from_existing(existing)

    context = _resolve_context(
        db,
        actor=actor,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=artifact_id,
        snapshot_id=snapshot_id,
        candidate_index=candidate_index,
    )
    retrieval = retrieve_mapping_profiles(db, context=context)
    exact_id = retrieval.exact_customer_profile.profile.id if retrieval.exact_customer_profile else None
    template_id = retrieval.organization_template.profile.id if retrieval.organization_template else None
    review_reasons: list[str] = ["human_confirmation_required"]
    source_ref: str | None = None
    if retrieval.exact_customer_profile is not None:
        fields = _prefill_fields(context, retrieval.exact_customer_profile)
        source_ref = str(exact_id)
        review_reasons.append("exact_customer_profile_prefill")
    elif retrieval.similar_customer_profiles:
        # Similar mappings are review provenance, never an automatically selected profile.
        closest = retrieval.similar_customer_profiles[0]
        geometry = candidate_geometry(context.candidate)
        remap = similar_template_remap(
            current_headers=geometry["header_labels"],
            current_min_column=geometry["min_column"],
            current_header_height=(geometry["header_end_row"] - geometry["header_start_row"] + 1),
            profile_fields=closest.fields,
            profile_headers=[field.original_header for field in closest.fields],
            profile_header_height=(
                closest.profile.header_end_row - closest.profile.header_start_row + 1
            ),
        )
        fields = remap.fields
        review_reasons.extend(("similar_customer_profiles_for_review", "profile_not_selected"))
    elif retrieval.organization_template is not None:
        fields = _prefill_fields(context, retrieval.organization_template)
        source_ref = str(template_id)
        review_reasons.append("approved_organization_template_prefill")
    else:
        suggestion: MappingSuggestion = suggest_mapping(context.candidate)
        fields = suggestion.fields
        review_reasons.extend(suggestion.reasons)
    snapshot = _current_snapshot(context, fields)
    digest = mapping_digest(snapshot)
    summary = mapping_summary(snapshot)
    before_summary = {
        "exact_profile_id": str(exact_id) if exact_id else None,
        "similar_profile_ids": [
            str(item.profile.id) for item in retrieval.similar_customer_profiles
        ],
        "organization_template_id": str(template_id) if template_id else None,
        "review_reasons": list(dict.fromkeys(review_reasons)),
    }
    decision = ColumnMappingDecision(
        organization_id=org_id,
        customer_id=context.project.customer_id,
        project_id=project_id,
        import_batch_id=batch_id,
        source_artifact_id=artifact_id,
        structure_snapshot_id=snapshot_id,
        decision_kind="proposal",
        outcome="proposed",
        memory_scope="none",
        proposal_decision_id=None,
        profile_id=None,
        supersedes_profile_id=None,
        actor_user_id=actor.id,
        command_id=command_id,
        correlation_id=correlation_id,
        proposal_source_kind="deterministic_rule",
        proposal_source_version=MAPPING_CONTRACT_VERSION,
        proposal_source_ref=source_ref,
        mapping_contract_version=MAPPING_CONTRACT_VERSION,
        template_fingerprint_sha256=context.template_fingerprint_sha256,
        mapping_snapshot=snapshot,
        mapping_digest_sha256=digest,
        before_summary=before_summary,
        after_summary=summary,
        reason_code=None,
        reason_text=None,
    )
    db.add(decision)
    _audit(
        db,
        actor=actor,
        event_name="ColumnMappingProposed",
        command_name="ProposeColumnMapping",
        entity_type=_AUDIT_ENTITY,
        entity_id=decision.id,
        org_id=org_id,
        correlation_id=correlation_id,
        payload={
            "organization_id": str(org_id),
            "project_id": str(project_id),
            "batch_id": str(batch_id),
            "source_artifact_id": str(artifact_id),
            "structure_snapshot_id": str(snapshot_id),
            "decision_id": str(decision.id),
            "mapping_contract_version": MAPPING_CONTRACT_VERSION,
            "rule_version": context.snapshot.rule_version,
            "source_generation": context.artifact.generation,
            "template_fingerprint_sha256": context.template_fingerprint_sha256,
            "mapping_digest_sha256": digest,
            "outcome": "proposed",
            "role_counts": summary["role_counts"],
        },
    )
    try:
        db.commit()
        db.refresh(decision)
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(ColumnMappingDecision)
            .filter(
                ColumnMappingDecision.organization_id == org_id,
                ColumnMappingDecision.command_id == command_id,
            )
            .populate_existing()
            .first()
        )
        if raced is not None:
            candidate = raced.mapping_snapshot.get("candidate", {})
            if (
                _status_value(raced.decision_kind) == "proposal"
                and raced.actor_user_id == actor.id
                and raced.project_id == project_id
                and raced.import_batch_id == batch_id
                and raced.source_artifact_id == artifact_id
                and raced.structure_snapshot_id == snapshot_id
                and candidate.get("candidate_index") == candidate_index
            ):
                return _proposal_result_from_existing(raced)
        raise _error(409, "idempotency_key_reused", "Mã lệnh đã được dùng trước đó.") from exc
    return MappingProposalResult(
        decision,
        True,
        tuple(before_summary["review_reasons"]),
        exact_id,
        tuple(item.profile.id for item in retrieval.similar_customer_profiles),
        template_id,
    )


def _verify_decision_snapshot(decision: ColumnMappingDecision) -> tuple[MappingField, ...]:
    try:
        fields = validate_mapping_snapshot(decision.mapping_snapshot)
        digest = mapping_digest(decision.mapping_snapshot)
    except ColumnMappingContractError as exc:
        raise _error(
            500, "mapping_structure_integrity_failure", "Snapshot quyết định không toàn vẹn."
        ) from exc
    if digest != decision.mapping_digest_sha256:
        raise _error(
            500, "mapping_structure_integrity_failure", "Mã kiểm tra quyết định không khớp."
        )
    return fields


def _proposal_for_command(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    proposal_decision_id: uuid.UUID,
) -> ColumnMappingDecision:
    proposal = (
        db.query(ColumnMappingDecision)
        .filter(
            ColumnMappingDecision.organization_id == org_id,
            ColumnMappingDecision.project_id == project_id,
            ColumnMappingDecision.import_batch_id == batch_id,
            ColumnMappingDecision.id == proposal_decision_id,
            ColumnMappingDecision.decision_kind == "proposal",
            ColumnMappingDecision.outcome == "proposed",
        )
        .populate_existing()
        .first()
    )
    if proposal is None:
        raise _error(409, "mapping_proposal_not_current", "Đề xuất ánh xạ không còn hợp lệ.")
    _verify_decision_snapshot(proposal)
    return proposal


def _canonical_snapshot_from_roles(
    snapshot: Mapping[str, Any], context: MappingContext
) -> tuple[dict[str, Any], tuple[MappingField, ...]]:
    """Bind caller-selected roles to server-verified source, structure, and candidate evidence."""
    try:
        caller_fields = validate_mapping_snapshot(snapshot)
        geometry = candidate_geometry(context.candidate)
    except ColumnMappingContractError as exc:
        raise _contract_error(exc) from exc
    trusted_fields = tuple(
        MappingField(
            source_column_index=geometry["min_column"] + offset,
            source_column_letter=column_letter(geometry["min_column"] + offset),
            original_header=geometry["header_labels"][offset],
            semantic_role=caller_fields[offset].semantic_role,
        )
        for offset in range(len(geometry["header_labels"]))
    )
    canonical = _current_snapshot(context, trusted_fields)
    caller_source = snapshot.get("source")
    caller_structure = snapshot.get("structure")
    caller_candidate = snapshot.get("candidate")
    if (
        snapshot.get("contract_version") != canonical["contract_version"]
        or caller_source != canonical["source"]
        or caller_structure != canonical["structure"]
        or snapshot.get("template_fingerprint_sha256")
        != canonical["template_fingerprint_sha256"]
        or caller_candidate != canonical["candidate"]
        or len(caller_fields) != len(trusted_fields)
        or any(
            caller.source_column_index != trusted.source_column_index
            or caller.source_column_letter != trusted.source_column_letter
            or caller.original_header != trusted.original_header
            for caller, trusted in zip(caller_fields, trusted_fields, strict=True)
        )
    ):
        raise _error(
            409,
            "mapping_proposal_not_current",
            "Snapshot ánh xạ không khớp bằng chứng candidate đã niêm phong.",
        )
    return canonical, trusted_fields


def _assert_snapshot_matches_context(
    snapshot: Mapping[str, Any], context: MappingContext
) -> tuple[dict[str, Any], tuple[MappingField, ...]]:
    canonical, fields = _canonical_snapshot_from_roles(snapshot, context)
    if canonical_json_bytes(canonical) != canonical_json_bytes(dict(snapshot)):
        raise _error(
            409,
            "mapping_proposal_not_current",
            "Snapshot ánh xạ không còn khớp nguồn hiện tại.",
        )
    return canonical, fields


def _new_profile(
    db: Session,
    *,
    context: MappingContext,
    actor: User,
    fields: Sequence[MappingField],
    supersedes: ColumnMappingProfile | None,
) -> ColumnMappingProfile:
    geometry = candidate_geometry(context.candidate)
    profile_id = uuid.uuid4()
    profile = ColumnMappingProfile(
        id=profile_id,
        organization_id=context.project.organization_id,
        customer_id=context.project.customer_id,
        source_customer_id=context.project.customer_id,
        scope_type="customer",
        profile_family_id=(supersedes.profile_family_id if supersedes else profile_id),
        profile_version=(supersedes.profile_version + 1 if supersedes else 1),
        status="active",
        template_fingerprint_sha256=context.template_fingerprint_sha256,
        fingerprint_contract_version=FINGERPRINT_CONTRACT_VERSION,
        mapping_contract_version=MAPPING_CONTRACT_VERSION,
        mapping_digest_sha256=profile_mapping_digest(context.candidate, fields),
        source_project_id=context.project.id,
        source_import_batch_id=context.batch.id,
        source_artifact_id=context.artifact.id,
        structure_snapshot_id=context.snapshot.id,
        sheet_name=geometry["sheet_name"],
        header_start_row=geometry["header_start_row"],
        header_end_row=geometry["header_end_row"],
        data_start_row=geometry["data_start_row"],
        min_column=geometry["min_column"],
        max_column=geometry["max_column"],
        supersedes_profile_id=(supersedes.id if supersedes else None),
        confirmed_by_user_id=actor.id,
        confirmed_at=datetime.now(timezone.utc),
        approved_by_user_id=None,
        approved_at=None,
    )
    db.add(profile)
    db.flush([profile])
    for field in fields:
        db.add(
            ColumnMappingField(
                organization_id=context.project.organization_id,
                profile_id=profile.id,
                source_column_index=field.source_column_index,
                source_column_letter=field.source_column_letter,
                original_header=field.original_header,
                normalized_header=normalize_header(field.original_header),
                semantic_role=field.semantic_role.value,
                required_flag=field.semantic_role is SemanticRole.RAW_ASSET_NAME,
                proposal_source_kind="human",
                proposal_source_version=MAPPING_CONTRACT_VERSION,
                proposal_confidence=None,
            )
        )
    return profile


def confirm_column_mapping(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    proposal_decision_id: uuid.UUID,
    mapping_snapshot: Mapping[str, Any],
    memory_scope: str = "none",
    supersedes_profile_id: uuid.UUID | None = None,
    command_id: uuid.UUID,
    correlation_id: str | None = None,
) -> ColumnMappingDecision:
    actor = _reload_active_actor_and_org(db, actor=actor, org_id=org_id)
    if memory_scope not in {"none", "customer"}:
        raise _error(409, "mapping_role_invalid", "Phạm vi ghi nhớ ánh xạ không hợp lệ.")
    proposal = _proposal_for_command(
        db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        proposal_decision_id=proposal_decision_id,
    )
    proposal_candidate = proposal.mapping_snapshot["candidate"]["candidate_index"]
    context = _resolve_context(
        db,
        actor=actor,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=proposal.source_artifact_id,
        snapshot_id=proposal.structure_snapshot_id,
        candidate_index=proposal_candidate,
    )
    if proposal.customer_id != context.project.customer_id:
        raise _error(409, "mapping_proposal_not_current", "Khách hàng của dự án đã thay đổi.")
    canonical_snapshot, fields = _canonical_snapshot_from_roles(mapping_snapshot, context)
    final_digest = mapping_digest(canonical_snapshot)
    existing = (
        db.query(ColumnMappingDecision)
        .filter(
            ColumnMappingDecision.organization_id == org_id,
            ColumnMappingDecision.command_id == command_id,
        )
        .populate_existing()
        .first()
    )
    if existing is not None:
        if (
            _status_value(existing.decision_kind) != "confirmation"
            or existing.actor_user_id != actor.id
            or existing.project_id != project_id
            or existing.import_batch_id != batch_id
            or existing.proposal_decision_id != proposal_decision_id
            or existing.mapping_digest_sha256 != final_digest
            or _status_value(existing.memory_scope) != memory_scope
            or existing.supersedes_profile_id != supersedes_profile_id
        ):
            raise _error(409, "idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác.")
        return existing

    # Frozen lock order: Project -> batch -> optional profile/family.
    project = (
        db.query(Project)
        .filter(Project.organization_id == org_id, Project.id == project_id)
        .populate_existing()
        .with_for_update()
        .first()
    )
    batch = (
        db.query(ProjectAssetImportBatch)
        .filter(
            ProjectAssetImportBatch.organization_id == org_id,
            ProjectAssetImportBatch.project_id == project_id,
            ProjectAssetImportBatch.id == batch_id,
        )
        .populate_existing()
        .with_for_update()
        .first()
    )
    if project is None or batch is None:
        raise HTTPException(status_code=404, detail="Import batch not found")
    if project.customer_id != proposal.customer_id:
        raise _error(409, "mapping_proposal_not_current", "Khách hàng của dự án đã thay đổi.")
    if _status_value(batch.status) == ImportBatchStatus.APPLIED.value:
        raise _error(409, "mapping_batch_already_applied", "Lô nhập liệu đã được áp dụng.")
    if batch.current_source_artifact_id != proposal.source_artifact_id:
        raise _error(409, "mapping_source_not_current", "Tệp nguồn không còn là thế hệ hiện tại.")

    profile: ColumnMappingProfile | None = None
    supersedes: ColumnMappingProfile | None = None
    semantic_digest = profile_mapping_digest(context.candidate, fields)
    if memory_scope == "customer":
        active_exact = (
            db.query(ColumnMappingProfile)
            .filter(
                ColumnMappingProfile.organization_id == org_id,
                ColumnMappingProfile.customer_id == project.customer_id,
                ColumnMappingProfile.scope_type == "customer",
                ColumnMappingProfile.status == "active",
                ColumnMappingProfile.template_fingerprint_sha256
                == context.template_fingerprint_sha256,
            )
            .order_by(ColumnMappingProfile.id)
            .populate_existing()
            .with_for_update()
            .all()
        )
        if len(active_exact) > 1:
            raise _error(409, "mapping_profile_conflict", "Có nhiều hồ sơ ánh xạ đang hoạt động.")
        active = active_exact[0] if active_exact else None
        try:
            proposal_similar_ids = {
                uuid.UUID(value)
                for value in (proposal.before_summary or {}).get("similar_profile_ids", [])
            }
        except (TypeError, ValueError, AttributeError) as exc:
            raise _error(
                500,
                "mapping_structure_integrity_failure",
                "Bằng chứng hồ sơ tương tự trong đề xuất không toàn vẹn.",
            ) from exc
        current_retrieval = retrieve_mapping_profiles(db, context=context)
        verified_similar_ids = {
            item.profile.id for item in current_retrieval.similar_customer_profiles
        }
        authorized_similar_ids = proposal_similar_ids & verified_similar_ids
        if active is not None and active.mapping_digest_sha256 == semantic_digest:
            if supersedes_profile_id is not None:
                raise _error(
                    409,
                    "mapping_profile_stale",
                    "Ánh xạ không thay đổi nên không được chỉ định hồ sơ thay thế.",
                )
            _verify_profile(db, active)
            profile = active
        else:
            if active is not None and supersedes_profile_id != active.id:
                raise _error(
                    409,
                    "mapping_profile_stale",
                    "Ánh xạ thay đổi phải nêu đúng hồ sơ hiện hành cần thay thế.",
                )
            if (
                active is None
                and supersedes_profile_id is not None
                and supersedes_profile_id not in authorized_similar_ids
            ):
                raise _error(
                    409,
                    "mapping_profile_stale",
                    "Hồ sơ cần thay thế không thuộc provenance đã xác thực của đề xuất.",
                )
            cited_id = supersedes_profile_id
            if cited_id is not None:
                supersedes = (
                    db.query(ColumnMappingProfile)
                    .filter(
                        ColumnMappingProfile.organization_id == org_id,
                        ColumnMappingProfile.customer_id == project.customer_id,
                        ColumnMappingProfile.scope_type == "customer",
                        ColumnMappingProfile.id == cited_id,
                    )
                    .populate_existing()
                    .with_for_update()
                    .first()
                )
                if supersedes is None or _status_value(supersedes.status) != "active":
                    raise _error(409, "mapping_profile_stale", "Hồ sơ cần thay thế không còn hiện hành.")
                _verify_profile(db, supersedes)
            savepoint = db.begin_nested()
            try:
                if supersedes is not None:
                    # Release the partial-unique active slot before inserting
                    # the next immutable profile version.
                    supersedes.status = "superseded"
                    db.flush([supersedes])
                profile = _new_profile(
                    db, context=context, actor=actor, fields=fields, supersedes=supersedes
                )
                # Persist fields before the confirmation references the profile.
                db.flush()
                savepoint.commit()
            except IntegrityError as exc:
                savepoint.rollback()
                raced_active = (
                    db.query(ColumnMappingProfile)
                    .filter(
                        ColumnMappingProfile.organization_id == org_id,
                        ColumnMappingProfile.customer_id == project.customer_id,
                        ColumnMappingProfile.scope_type == "customer",
                        ColumnMappingProfile.status == "active",
                    )
                    .first()
                )
                if (
                    raced_active is not None
                    and raced_active.template_fingerprint_sha256 == context.template_fingerprint_sha256
                    and raced_active.mapping_digest_sha256 == semantic_digest
                ):
                    profile = raced_active
                else:
                    raise _error(
                        409,
                        "mapping_profile_conflict",
                        "Hồ sơ ánh xạ đã thay đổi đồng thời.",
                    ) from exc

    outcome = "accepted" if final_digest == proposal.mapping_digest_sha256 else "corrected"
    decision = ColumnMappingDecision(
        organization_id=org_id,
        customer_id=project.customer_id,
        project_id=project_id,
        import_batch_id=batch_id,
        source_artifact_id=proposal.source_artifact_id,
        structure_snapshot_id=proposal.structure_snapshot_id,
        decision_kind="confirmation",
        outcome=outcome,
        memory_scope=memory_scope,
        proposal_decision_id=proposal.id,
        profile_id=(profile.id if profile else None),
        supersedes_profile_id=(supersedes.id if supersedes else None),
        actor_user_id=actor.id,
        command_id=command_id,
        correlation_id=correlation_id,
        proposal_source_kind="human",
        proposal_source_version=MAPPING_CONTRACT_VERSION,
        proposal_source_ref=str(proposal.id),
        mapping_contract_version=MAPPING_CONTRACT_VERSION,
        template_fingerprint_sha256=context.template_fingerprint_sha256,
        mapping_snapshot=canonical_snapshot,
        mapping_digest_sha256=final_digest,
        before_summary=mapping_summary(proposal.mapping_snapshot),
        after_summary=mapping_summary(canonical_snapshot),
        reason_code=None,
        reason_text=None,
    )
    db.add(decision)
    _audit(
        db,
        actor=actor,
        event_name="ColumnMappingConfirmed",
        command_name="ConfirmColumnMapping",
        entity_type=_AUDIT_ENTITY,
        entity_id=decision.id,
        org_id=org_id,
        correlation_id=correlation_id,
        payload={
            "organization_id": str(org_id),
            "project_id": str(project_id),
            "batch_id": str(batch_id),
            "source_artifact_id": str(proposal.source_artifact_id),
            "structure_snapshot_id": str(proposal.structure_snapshot_id),
            "decision_id": str(decision.id),
            "profile_id": str(profile.id) if profile else None,
            "profile_version": profile.profile_version if profile else None,
            "mapping_contract_version": MAPPING_CONTRACT_VERSION,
            "template_fingerprint_sha256": context.template_fingerprint_sha256,
            "mapping_digest_sha256": final_digest,
            "source_generation": context.artifact.generation,
            "outcome": outcome,
            "role_counts": decision.after_summary["role_counts"],
        },
    )
    try:
        db.commit()
        db.refresh(decision)
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(ColumnMappingDecision)
            .filter(
                ColumnMappingDecision.organization_id == org_id,
                ColumnMappingDecision.command_id == command_id,
            )
            .populate_existing()
            .first()
        )
        if raced is not None:
            if (
                _status_value(raced.decision_kind) == "confirmation"
                and raced.actor_user_id == actor.id
                and raced.project_id == project_id
                and raced.import_batch_id == batch_id
                and raced.proposal_decision_id == proposal_decision_id
                and raced.mapping_digest_sha256 == final_digest
                and _status_value(raced.memory_scope) == memory_scope
                and raced.supersedes_profile_id == supersedes_profile_id
            ):
                return raced
            raise _error(
                409, "idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác."
            ) from exc
        raise _error(409, "mapping_profile_conflict", "Hồ sơ ánh xạ đã thay đổi đồng thời.") from exc
    return decision


def reject_column_mapping(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    proposal_decision_id: uuid.UUID,
    command_id: uuid.UUID,
    reason_code: str | None = None,
    reason_text: str | None = None,
    correlation_id: str | None = None,
) -> ColumnMappingDecision:
    actor = _reload_active_actor_and_org(db, actor=actor, org_id=org_id)
    existing = (
        db.query(ColumnMappingDecision)
        .filter(
            ColumnMappingDecision.organization_id == org_id,
            ColumnMappingDecision.command_id == command_id,
        )
        .populate_existing()
        .first()
    )
    if existing is not None:
        if (
            _status_value(existing.decision_kind) != "rejection"
            or existing.actor_user_id != actor.id
            or existing.project_id != project_id
            or existing.import_batch_id != batch_id
            or existing.proposal_decision_id != proposal_decision_id
            or existing.reason_code != reason_code
            or existing.reason_text != reason_text
        ):
            raise _error(409, "idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác.")
        return existing
    proposal = _proposal_for_command(
        db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        proposal_decision_id=proposal_decision_id,
    )
    candidate_index = proposal.mapping_snapshot["candidate"]["candidate_index"]
    context = _resolve_context(
        db,
        actor=actor,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=proposal.source_artifact_id,
        snapshot_id=proposal.structure_snapshot_id,
        candidate_index=candidate_index,
    )
    if proposal.customer_id != context.project.customer_id:
        raise _error(409, "mapping_proposal_not_current", "Khách hàng của dự án đã thay đổi.")
    decision = ColumnMappingDecision(
        organization_id=org_id,
        customer_id=context.project.customer_id,
        project_id=project_id,
        import_batch_id=batch_id,
        source_artifact_id=proposal.source_artifact_id,
        structure_snapshot_id=proposal.structure_snapshot_id,
        decision_kind="rejection",
        outcome="rejected",
        memory_scope="none",
        proposal_decision_id=proposal.id,
        profile_id=None,
        supersedes_profile_id=None,
        actor_user_id=actor.id,
        command_id=command_id,
        correlation_id=correlation_id,
        proposal_source_kind="human",
        proposal_source_version=MAPPING_CONTRACT_VERSION,
        proposal_source_ref=str(proposal.id),
        mapping_contract_version=MAPPING_CONTRACT_VERSION,
        template_fingerprint_sha256=proposal.template_fingerprint_sha256,
        mapping_snapshot=proposal.mapping_snapshot,
        mapping_digest_sha256=proposal.mapping_digest_sha256,
        before_summary=mapping_summary(proposal.mapping_snapshot),
        after_summary={
            "mapping_digest_sha256": proposal.mapping_digest_sha256,
            "outcome": "rejected",
        },
        reason_code=reason_code,
        reason_text=reason_text,
    )
    db.add(decision)
    _audit(
        db,
        actor=actor,
        event_name="ColumnMappingRejected",
        command_name="RejectColumnMapping",
        entity_type=_AUDIT_ENTITY,
        entity_id=decision.id,
        org_id=org_id,
        correlation_id=correlation_id,
        payload={
            "organization_id": str(org_id),
            "project_id": str(project_id),
            "batch_id": str(batch_id),
            "source_artifact_id": str(proposal.source_artifact_id),
            "structure_snapshot_id": str(proposal.structure_snapshot_id),
            "decision_id": str(decision.id),
            "mapping_contract_version": MAPPING_CONTRACT_VERSION,
            "template_fingerprint_sha256": proposal.template_fingerprint_sha256,
            "mapping_digest_sha256": proposal.mapping_digest_sha256,
            "source_generation": context.artifact.generation,
            "outcome": "rejected",
        },
    )
    try:
        db.commit()
        db.refresh(decision)
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(ColumnMappingDecision)
            .filter(
                ColumnMappingDecision.organization_id == org_id,
                ColumnMappingDecision.command_id == command_id,
            )
            .populate_existing()
            .first()
        )
        if raced is not None and (
            _status_value(raced.decision_kind) == "rejection"
            and raced.actor_user_id == actor.id
            and raced.project_id == project_id
            and raced.import_batch_id == batch_id
            and raced.proposal_decision_id == proposal_decision_id
            and raced.reason_code == reason_code
            and raced.reason_text == reason_text
        ):
            return raced
        raise _error(409, "idempotency_key_reused", "Mã lệnh đã được dùng trước đó.") from exc
    return decision


def _write_spool(rows: Iterable[dict[str, Any]]) -> tuple[str, int, str]:
    fd, path = tempfile.mkstemp(prefix="valora-mapping-", suffix=".jsonl")
    os.close(fd)
    digest = hashlib.sha256()
    count = 0
    try:
        with open(path, "wb") as output:
            for row in rows:
                encoded = canonical_json_bytes(row) + b"\n"
                output.write(encoded)
                digest.update(encoded)
                count += 1
        return path, count, digest.hexdigest()
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


def _read_spool(path: str, *, expected_digest: str) -> Iterator[dict[str, Any]]:
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for line in source:
            digest.update(line)
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("invalid mapping spool row")
            yield value
    if digest.hexdigest() != expected_digest:
        raise ValueError("mapping spool digest mismatch")


def _materialization_rows(
    *, path: str, frozen: FrozenMaterialization
) -> Iterator[dict[str, Any]]:
    adapter = None
    try:
        detected_format, adapter = detect_format_and_adapter(
            path, frozen.source.original_filename, limits=DEFAULT_SOURCE_LIMITS
        )
        if detected_format.value != frozen.source.detected_format:
            raise _error(409, "mapping_materialization_stale", "Định dạng tệp nguồn đã thay đổi.")
        adapter.inspect(path)
        candidate = frozen.candidate()
        bounds = candidate.get("candidate_table_bounds", {})
        rows = adapter.iter_rows(path, candidate["sheet_name"])
        for sliced, classification in replay_frozen_candidate_rows(
            rows,
            data_start_row=candidate["data_start_row"],
            max_row=bounds["max_row"],
            min_column=bounds["min_column"],
            max_column=bounds["max_column"],
        ):
            if classification.row_class is RowClass.ASSET:
                yield project_asset_row(sliced, frozen.fields)
    finally:
        if adapter is not None:
            adapter.close()


def _usage_matches(
    usage: ColumnMappingProfileUsage,
    confirmation: ConfirmationSeal,
    *,
    actor_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    command_id: uuid.UUID,
) -> bool:
    return (
        usage.confirmation_decision_id == confirmation.id
        and usage.mapping_digest_sha256 == confirmation.mapping_digest_sha256
        and usage.command_id == command_id
        and usage.created_by_user_id == actor_id
        and usage.customer_id == confirmation.customer_id
        and usage.project_id == project_id
        and usage.import_batch_id == batch_id
        and usage.source_artifact_id == confirmation.source_artifact_id
        and usage.structure_snapshot_id == confirmation.structure_snapshot_id
    )


def _ensure_outer_write_transaction(db: Session) -> None:
    """Keep a released SQLite savepoint subordinate to the outer unit of work."""
    connection = db.connection()
    if connection.dialect.name != "sqlite":
        return
    driver_connection = getattr(connection.connection, "driver_connection", None)
    if driver_connection is not None and not driver_connection.in_transaction:
        connection.exec_driver_sql("BEGIN")


def materialize_confirmed_mapping_to_staging(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    confirmation_decision_id: uuid.UUID,
    command_id: uuid.UUID,
    correlation_id: str | None = None,
    storage: ObjectStoragePort | None = None,
) -> ColumnMappingProfileUsage:
    actor = _reload_active_actor_and_org(db, actor=actor, org_id=org_id)
    actor_id = actor.id
    confirmation = (
        db.query(ColumnMappingDecision)
        .filter(
            ColumnMappingDecision.organization_id == org_id,
            ColumnMappingDecision.project_id == project_id,
            ColumnMappingDecision.import_batch_id == batch_id,
            ColumnMappingDecision.id == confirmation_decision_id,
            ColumnMappingDecision.decision_kind == "confirmation",
            ColumnMappingDecision.outcome.in_(("accepted", "corrected")),
        )
        .populate_existing()
        .first()
    )
    if confirmation is None:
        raise _error(
            409, "mapping_confirmation_required", "Cần xác nhận ánh xạ hợp lệ trước khi tạo staging."
        )
    _verify_decision_snapshot(confirmation)
    candidate_index = confirmation.mapping_snapshot["candidate"]["candidate_index"]
    context = _resolve_context(
        db,
        actor=actor,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=confirmation.source_artifact_id,
        snapshot_id=confirmation.structure_snapshot_id,
        candidate_index=candidate_index,
    )
    _, fields = _assert_snapshot_matches_context(confirmation.mapping_snapshot, context)
    if confirmation.customer_id != context.project.customer_id:
        raise _error(409, "mapping_confirmation_required", "Xác nhận ánh xạ không hợp lệ.")
    frozen = FrozenMaterialization(
        source=ArtifactFingerprint.freeze(context.artifact),
        structure=StructureSeal.freeze(context.snapshot),
        confirmation=ConfirmationSeal.freeze(confirmation),
        customer_id=context.project.customer_id,
        batch_source_artifact_id=context.batch.current_source_artifact_id,
        batch_status=_status_value(context.batch.status),
        candidate_json=canonical_json_bytes(context.candidate),
        fields=fields,
    )
    command_usage = (
        db.query(ColumnMappingProfileUsage)
        .filter(
            ColumnMappingProfileUsage.organization_id == org_id,
            ColumnMappingProfileUsage.command_id == command_id,
        )
        .populate_existing()
        .first()
    )
    if command_usage is not None:
        if _usage_matches(
            command_usage,
            frozen.confirmation,
            actor_id=actor_id,
            project_id=project_id,
            batch_id=batch_id,
            command_id=command_id,
        ):
            return command_usage
        raise _error(409, "idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác.")
    existing = (
        db.query(ColumnMappingProfileUsage)
        .filter(
            ColumnMappingProfileUsage.organization_id == org_id,
            ColumnMappingProfileUsage.project_id == project_id,
            ColumnMappingProfileUsage.import_batch_id == batch_id,
            ColumnMappingProfileUsage.source_artifact_id == frozen.source.id,
            ColumnMappingProfileUsage.structure_snapshot_id == frozen.structure.id,
        )
        .populate_existing()
        .first()
    )
    if existing is not None:
        raise _error(409, "mapping_usage_conflict", "Thế hệ nguồn này đã được tạo staging trước đó.")

    storage = storage or get_object_storage()
    spool_path: str | None = None
    try:
        try:
            with _materialize_verified_source(frozen.source, storage) as source_path:
                try:
                    spool_path, row_count, spool_digest = _write_spool(
                        _materialization_rows(path=source_path, frozen=frozen)
                    )
                except AdapterError as exc:
                    raise _error(exc.status, "mapping_materialization_stale", exc.detail) from exc
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            code = detail.get("error_code")
            if isinstance(code, str) and code.startswith("mapping_"):
                raise
            if code in {"source_object_missing", "source_object_unavailable", "source_stream_close_failed"}:
                raise _error(
                    409,
                    "mapping_source_not_available",
                    "Không thể đọc tệp nguồn đã xác nhận.",
                ) from exc
            raise _error(
                409,
                "mapping_materialization_stale",
                "Bằng chứng tệp nguồn không còn khớp dữ liệu đã xác nhận.",
            ) from exc

        project = (
            db.query(Project)
            .filter(Project.organization_id == org_id, Project.id == project_id)
            .populate_existing()
            .with_for_update()
            .first()
        )
        batch = (
            db.query(ProjectAssetImportBatch)
            .filter(
                ProjectAssetImportBatch.organization_id == org_id,
                ProjectAssetImportBatch.project_id == project_id,
                ProjectAssetImportBatch.id == batch_id,
            )
            .populate_existing()
            .with_for_update()
            .first()
        )
        locked_artifact = (
            db.query(ImportSourceArtifact)
            .filter(
                ImportSourceArtifact.organization_id == org_id,
                ImportSourceArtifact.project_id == project_id,
                ImportSourceArtifact.import_batch_id == batch_id,
                ImportSourceArtifact.id == frozen.source.id,
            )
            .populate_existing()
            .with_for_update()
            .first()
        )
        locked_confirmation = (
            db.query(ColumnMappingDecision)
            .filter(
                ColumnMappingDecision.organization_id == org_id,
                ColumnMappingDecision.customer_id == frozen.customer_id,
                ColumnMappingDecision.project_id == project_id,
                ColumnMappingDecision.import_batch_id == batch_id,
                ColumnMappingDecision.id == frozen.confirmation.id,
            )
            .populate_existing()
            .with_for_update()
            .first()
        )
        existing_after_lock = (
            db.query(ColumnMappingProfileUsage)
            .filter(
                ColumnMappingProfileUsage.organization_id == org_id,
                ColumnMappingProfileUsage.project_id == project_id,
                ColumnMappingProfileUsage.import_batch_id == batch_id,
                ColumnMappingProfileUsage.source_artifact_id == frozen.source.id,
                ColumnMappingProfileUsage.structure_snapshot_id == frozen.structure.id,
            )
            .populate_existing()
            .with_for_update()
            .first()
        )
        if existing_after_lock is not None:
            if _usage_matches(
                existing_after_lock,
                frozen.confirmation,
                actor_id=actor_id,
                project_id=project_id,
                batch_id=batch_id,
                command_id=command_id,
            ):
                return existing_after_lock
            raise _error(409, "mapping_usage_conflict", "Thế hệ nguồn đã có staging.")
        if batch is not None and _status_value(batch.status) == ImportBatchStatus.APPLIED.value:
            raise _error(409, "mapping_batch_already_applied", "Lô nhập liệu đã được áp dụng.")
        if (
            project is None
            or batch is None
            or locked_artifact is None
            or locked_confirmation is None
            or project.customer_id != frozen.customer_id
            or batch.current_source_artifact_id != frozen.batch_source_artifact_id
            or batch.current_source_artifact_id != frozen.source.id
            or _status_value(batch.status) != frozen.batch_status
            or ArtifactFingerprint.freeze(locked_artifact) != frozen.source
            or ConfirmationSeal.freeze(locked_confirmation) != frozen.confirmation
        ):
            raise _error(409, "mapping_materialization_stale", "Nguồn ánh xạ đã thay đổi.")
        locked_snapshot = (
            db.query(WorkbookStructureSnapshot)
            .filter(
                WorkbookStructureSnapshot.organization_id == org_id,
                WorkbookStructureSnapshot.project_id == project_id,
                WorkbookStructureSnapshot.import_batch_id == batch_id,
                WorkbookStructureSnapshot.source_artifact_id == frozen.source.id,
                WorkbookStructureSnapshot.id == frozen.structure.id,
            )
            .populate_existing()
            .with_for_update()
            .first()
        )
        if locked_snapshot is None or StructureSeal.freeze(locked_snapshot) != frozen.structure:
            raise _error(409, "mapping_materialization_stale", "Snapshot cấu trúc đã thay đổi.")
        try:
            _verify_snapshot_page(db, [locked_snapshot], locked_artifact)
        except HTTPException as exc:
            raise _error(
                500, "mapping_structure_integrity_failure", "Snapshot cấu trúc không toàn vẹn."
            ) from exc
        _ensure_outer_write_transaction(db)
        savepoint = db.begin_nested()
        try:
            db.query(ProjectAssetImportStagingRow).filter(
                ProjectAssetImportStagingRow.organization_id == org_id,
                ProjectAssetImportStagingRow.project_id == project_id,
                ProjectAssetImportStagingRow.import_batch_id == batch_id,
            ).delete(synchronize_session=False)
            assert spool_path is not None
            pending = 0
            for row in _read_spool(spool_path, expected_digest=spool_digest):
                db.add(
                    ProjectAssetImportStagingRow(
                        organization_id=org_id,
                        project_id=project_id,
                        import_batch_id=batch_id,
                        source_row_number=row["source_row_number"],
                        raw_values=row["raw_values"],
                        mapped_values=row["mapped_values"],
                        normalized_preview={},
                        validation_status=ImportRowValidationStatus.PENDING,
                        validation_errors=[],
                        validation_warnings=[],
                        proposed_asset_name=row["proposed_asset_name"],
                        proposed_description=row["proposed_description"],
                        proposed_quantity=row["proposed_quantity"],
                        proposed_unit=row["proposed_unit"],
                        proposed_raw_price=row["proposed_raw_price"],
                        proposed_currency=None,
                        proposed_appraised_unit_price=row[
                            "proposed_appraised_unit_price"
                        ],
                        proposed_review_status=None,
                        proposed_validation_status=None,
                    )
                )
                pending += 1
                if pending >= _SPOOL_CHUNK_ROWS:
                    db.flush()
                    pending = 0
            db.flush()
            profile = None
            if frozen.confirmation.profile_id is not None:
                profile = (
                    db.query(ColumnMappingProfile)
                    .filter(
                        ColumnMappingProfile.organization_id == org_id,
                        ColumnMappingProfile.customer_id == frozen.customer_id,
                        ColumnMappingProfile.id == frozen.confirmation.profile_id,
                    )
                    .populate_existing()
                    .with_for_update()
                    .first()
                )
                if profile is None:
                    raise _error(
                        500, "mapping_profile_integrity_failure", "Hồ sơ ánh xạ không tồn tại."
                    )
            usage = ColumnMappingProfileUsage(
                organization_id=org_id,
                customer_id=frozen.customer_id,
                project_id=project_id,
                import_batch_id=batch_id,
                source_artifact_id=frozen.source.id,
                structure_snapshot_id=frozen.structure.id,
                confirmation_decision_id=frozen.confirmation.id,
                profile_id=(profile.id if profile else None),
                profile_version=(profile.profile_version if profile else None),
                command_id=command_id,
                materialization_contract_version=MATERIALIZATION_CONTRACT_VERSION,
                mapping_contract_version=MAPPING_CONTRACT_VERSION,
                template_fingerprint_sha256=frozen.confirmation.template_fingerprint_sha256,
                mapping_snapshot=frozen.confirmation.mapping_snapshot(),
                mapping_digest_sha256=frozen.confirmation.mapping_digest_sha256,
                source_checksum_sha256=frozen.source.checksum_sha256,
                structure_digest_sha256=frozen.structure.analysis_digest_sha256,
                materialized_asset_row_count=row_count,
                created_by_user_id=actor_id,
            )
            db.add(usage)
            batch.source_filename = frozen.source.original_filename
            batch.source_sheet_name = frozen.confirmation.mapping_snapshot()["candidate"][
                "sheet_name"
            ]
            batch.status = ImportBatchStatus.PARSED
            batch.total_rows = row_count
            batch.valid_rows = 0
            batch.invalid_rows = 0
            batch.warning_rows = 0
            _audit(
                db,
                actor=actor,
                event_name="ConfirmedMappingMaterialized",
                command_name="MaterializeConfirmedMappingToStaging",
                entity_type="ColumnMappingProfileUsage",
                entity_id=usage.id,
                org_id=org_id,
                correlation_id=correlation_id,
                payload={
                    "organization_id": str(org_id),
                    "project_id": str(project_id),
                    "batch_id": str(batch_id),
                    "source_artifact_id": str(frozen.source.id),
                    "structure_snapshot_id": str(frozen.structure.id),
                    "decision_id": str(frozen.confirmation.id),
                    "profile_id": str(profile.id) if profile else None,
                    "usage_id": str(usage.id),
                    "mapping_contract_version": MAPPING_CONTRACT_VERSION,
                    "materialization_contract_version": MATERIALIZATION_CONTRACT_VERSION,
                    "template_fingerprint_sha256": (
                        frozen.confirmation.template_fingerprint_sha256
                    ),
                    "mapping_digest_sha256": frozen.confirmation.mapping_digest_sha256,
                    "source_generation": frozen.source.generation,
                    "materialized_asset_row_count": row_count,
                },
            )
            db.flush()
            savepoint.commit()
            db.commit()
            db.refresh(usage)
            return usage
        except Exception:
            try:
                savepoint.rollback()
            except Exception:
                pass
            db.rollback()
            raise
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(ColumnMappingProfileUsage)
            .filter(
                ColumnMappingProfileUsage.organization_id == org_id,
                ColumnMappingProfileUsage.command_id == command_id,
            )
            .populate_existing()
            .first()
        )
        if raced is not None:
            if _usage_matches(
                raced,
                frozen.confirmation,
                actor_id=actor_id,
                project_id=project_id,
                batch_id=batch_id,
                command_id=command_id,
            ):
                return raced
            raise _error(
                409, "idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác."
            ) from exc
        raise _error(409, "mapping_usage_conflict", "Thế hệ nguồn đã được xử lý đồng thời.") from exc
    finally:
        if spool_path is not None:
            try:
                os.unlink(spool_path)
            except OSError:
                pass
