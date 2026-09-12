"""Atomic human-confirmed finalization of a PreliminaryAnalysisSnapshot fact."""
from __future__ import annotations

import hashlib
import json
import math
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.audit import log_audit_event
from app.core.rbac import derive_effective_permissions
from app.modules.excel_import.models import (
    ColumnMappingDecision,
    ColumnMappingDecisionKind,
    ColumnMappingDecisionOutcome,
    ColumnMappingProfileUsage,
    ColumnMappingProposalSourceKind,
    ImportSourceArtifact,
    ImportSourceArtifactState,
    WorkbookStructureSnapshot,
)
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    PreliminaryAnalysisSnapshot,
    Project,
    ProjectAssetImportBatch,
    User,
    UserRole,
    UserStatus,
)


PRELIMINARY_ANALYSIS_FINALIZE_PERMISSION = "project:preliminary_analysis:finalize"

_LINE_V2_KEYS = frozenset(
    {
        "identity",
        "accepted_price_basis",
        "confirmed_reference_price",
        "transport_percentage",
        "proposed_unit_price",
        "human_line_confirmed",
        "has_unresolved_blocking_line",
        "source_row_number",
        "quantity",
    }
)
_MAX_WORKSHEET_ROW = 1_048_576


def _status_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _abort(db: Session, status: int, code: str, detail: str) -> None:
    db.rollback()
    raise _error(status, code, detail)


def _canonical_json(payload: dict | list) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _strict_bool_true(value: Any, field_label: str) -> None:
    if value is not True:
        raise _error(
            409,
            "preliminary_analysis_line_confirmation_missing",
            f"{field_label} chưa được xác nhận thủ công.",
        )


def _strict_bool_false(value: Any, field_label: str) -> None:
    if value is not False:
        raise _error(
            409,
            "preliminary_analysis_line_blocking",
            f"{field_label} còn vấn đề bắt buộc chưa xử lý.",
        )


def _finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _request_digest(
    *,
    actor_id: uuid.UUID,
    project_id: uuid.UUID,
    source_artifact_id: uuid.UUID,
    structure_snapshot_id: uuid.UUID,
    mapping_decision_id: uuid.UUID,
    mapping_profile_usage_id: uuid.UUID,
    mapping_decision_digest_sha256: str,
    profile_usage_mapping_digest_sha256: str,
    line_manifest_digest_sha256: str,
    expected_project_version: int,
) -> str:
    payload = {
        "actor_id": str(actor_id),
        "contract": "preliminary-analysis-finalize-v2",
        "expected_project_version": expected_project_version,
        "line_manifest_digest_sha256": line_manifest_digest_sha256,
        "mapping_decision_digest_sha256": mapping_decision_digest_sha256,
        "mapping_decision_id": str(mapping_decision_id),
        "mapping_profile_usage_digest_sha256": profile_usage_mapping_digest_sha256,
        "mapping_profile_usage_id": str(mapping_profile_usage_id),
        "project_id": str(project_id),
        "source_artifact_id": str(source_artifact_id),
        "structure_snapshot_id": str(structure_snapshot_id),
    }
    return _sha256_hex(_canonical_json(payload))


def _reload_active_actor_and_org(
    db: Session, *, actor: User, org_id: uuid.UUID
) -> User:
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
    ):
        _abort(db, 403, "preliminary_analysis_forbidden", "Không thể thực hiện thao tác này.")
    if PRELIMINARY_ANALYSIS_FINALIZE_PERMISSION not in derive_effective_permissions(
        persisted_actor, db
    ):
        _abort(db, 403, "preliminary_analysis_forbidden", "Không thể thực hiện thao tác này.")
    return persisted_actor


def _same_request(
    snapshot: PreliminaryAnalysisSnapshot,
    *,
    actor_id: uuid.UUID,
    project_id: uuid.UUID,
    source_artifact_id: uuid.UUID,
    mapping_decision_id: uuid.UUID,
    mapping_profile_usage_id: uuid.UUID,
    request_digest: str,
) -> bool:
    return (
        snapshot.finalized_by_user_id == actor_id
        and snapshot.project_id == project_id
        and snapshot.source_artifact_id == source_artifact_id
        and snapshot.mapping_decision_id == mapping_decision_id
        and snapshot.mapping_profile_usage_id == mapping_profile_usage_id
        and snapshot.request_digest_sha256 == request_digest
    )


def _is_v1_shaped(line_manifest: list[dict]) -> bool:
    """v1-shaped manifests lack the mandatory v2 locator/quantity fields."""
    if not line_manifest:
        return False
    return any(
        not isinstance(line, dict)
        or _LINE_V2_KEYS - set(line.keys())
        or (set(line.keys()) - _LINE_V2_KEYS)
        for line in line_manifest
    )


def _validate_line_conditions(line_manifest: list[dict]) -> None:
    if not line_manifest:
        raise _error(
            409,
            "preliminary_analysis_line_manifest_empty",
            "Danh sách dòng phân tích không được để trống.",
        )
    seen_rows: set[int] = set()
    for index, line in enumerate(line_manifest):
        if not isinstance(line, dict):
            raise _error(
                409,
                "preliminary_analysis_line_invalid",
                f"Dòng {index} không đúng định dạng.",
            )
        if set(line.keys()) != _LINE_V2_KEYS:
            raise _error(
                409,
                "preliminary_analysis_contract_superseded",
                "Dữ liệu dòng không đúng phiên bản v2.",
            )
        identity = line.get("identity")
        if not identity or not isinstance(identity, str) or not identity.strip():
            raise _error(
                409,
                "preliminary_analysis_line_identity_missing",
                f"Dòng {index} thiếu thông tin định danh.",
            )
        basis = line.get("accepted_price_basis")
        if not basis or not isinstance(basis, str) or not basis.strip():
            raise _error(
                409,
                "preliminary_analysis_line_price_basis_missing",
                f"Dòng {index} thiếu cơ sở giá được chấp nhận.",
            )
        ref_price = line.get("confirmed_reference_price")
        if not _finite_number(ref_price) or ref_price < 0:
            raise _error(
                409,
                "preliminary_analysis_line_reference_price_invalid",
                f"Dòng {index} có giá tham khảo không hợp lệ.",
            )
        transport = line.get("transport_percentage")
        if not _finite_number(transport) or transport < 0 or transport > 100:
            raise _error(
                409,
                "preliminary_analysis_line_transport_invalid",
                f"Dòng {index} có tỷ lệ vận chuyển không hợp lệ.",
            )
        proposed = line.get("proposed_unit_price")
        if not _finite_number(proposed) or proposed < 0:
            raise _error(
                409,
                "preliminary_analysis_line_proposed_price_invalid",
                f"Dòng {index} có đơn giá đề xuất không hợp lệ.",
            )
        _strict_bool_true(line.get("human_line_confirmed"), f"Dòng {index}")
        _strict_bool_false(line.get("has_unresolved_blocking_line"), f"Dòng {index}")
        source_row_number = line.get("source_row_number")
        if (
            isinstance(source_row_number, bool)
            or not isinstance(source_row_number, int)
            or source_row_number < 1
            or source_row_number > _MAX_WORKSHEET_ROW
        ):
            raise _error(
                409,
                "preliminary_analysis_line_source_row_number_invalid",
                f"Dòng {index} có vị trí hàng nguồn không hợp lệ.",
            )
        if source_row_number in seen_rows:
            raise _error(
                409,
                "preliminary_analysis_line_source_row_number_duplicate",
                f"Dòng {index} trùng vị trí hàng nguồn.",
            )
        seen_rows.add(source_row_number)
        quantity = line.get("quantity")
        if not _finite_number(quantity) or quantity < 0:
            raise _error(
                409,
                "preliminary_analysis_line_quantity_invalid",
                f"Dòng {index} có số lượng không hợp lệ.",
            )


def finalize_preliminary_analysis(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    expected_project_version: int,
    import_batch_id: uuid.UUID,
    source_artifact_id: uuid.UUID,
    structure_snapshot_id: uuid.UUID,
    mapping_decision_id: uuid.UUID,
    mapping_profile_usage_id: uuid.UUID,
    mapping_decision_digest_sha256: str,
    profile_usage_mapping_digest_sha256: str,
    line_manifest: list[dict],
    idempotency_key: str,
    confirmed: bool,
    correlation_id: str | None = None,
) -> PreliminaryAnalysisSnapshot:
    """Create the one-per-project preliminary-analysis fact and atomic success audit."""
    if confirmed is not True:
        _abort(db, 400, "preliminary_analysis_confirmation_required", "Cần xác nhận thao tác.")
    normalized_key = idempotency_key.strip()
    if not normalized_key or len(normalized_key) > 128:
        _abort(db, 422, "invalid_idempotency_key", "Khóa idempotency không hợp lệ.")
    if expected_project_version < 1:
        _abort(db, 422, "invalid_expected_version", "Phiên bản yêu cầu không hợp lệ.")

    # Branch A shape gate: v1-shaped requests are superseded before any DB lookup.
    if _is_v1_shaped(line_manifest):
        _abort(
            db,
            409,
            "preliminary_analysis_contract_superseded",
            "Dữ liệu phân tích sơ bộ đã được thay thế bởi phiên bản v2.",
        )

    try:
        _validate_line_conditions(line_manifest)
    except HTTPException:
        db.rollback()
        raise

    actor = _reload_active_actor_and_org(db, actor=actor, org_id=org_id)

    line_manifest_digest_sha256 = _sha256_hex(_canonical_json(line_manifest))
    request_digest = _request_digest(
        actor_id=actor.id,
        project_id=project_id,
        source_artifact_id=source_artifact_id,
        structure_snapshot_id=structure_snapshot_id,
        mapping_decision_id=mapping_decision_id,
        mapping_profile_usage_id=mapping_profile_usage_id,
        mapping_decision_digest_sha256=mapping_decision_digest_sha256,
        profile_usage_mapping_digest_sha256=profile_usage_mapping_digest_sha256,
        line_manifest_digest_sha256=line_manifest_digest_sha256,
        expected_project_version=expected_project_version,
    )

    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == org_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if project is None:
        _abort(db, 404, "project_not_found", "Không tìm thấy hồ sơ.")

    artifact = (
        db.query(ImportSourceArtifact)
        .filter(
            ImportSourceArtifact.id == source_artifact_id,
            ImportSourceArtifact.organization_id == org_id,
            ImportSourceArtifact.project_id == project.id,
        )
        .with_for_update()
        .first()
    )
    if artifact is None:
        _abort(db, 404, "source_artifact_not_found", "Không tìm thấy tài liệu nguồn.")
    if _status_value(artifact.state) != ImportSourceArtifactState.AVAILABLE.value:
        _abort(
            db,
            409,
            "source_artifact_not_available",
            "Tài liệu nguồn chưa sẵn sàng.",
        )

    batch = (
        db.query(ProjectAssetImportBatch)
        .filter(
            ProjectAssetImportBatch.id == import_batch_id,
            ProjectAssetImportBatch.organization_id == org_id,
            ProjectAssetImportBatch.project_id == project.id,
        )
        .first()
    )
    if batch is None:
        _abort(db, 404, "import_batch_not_found", "Không tìm thấy đợt nhập liệu.")
    if batch.current_source_artifact_id != artifact.id:
        _abort(
            db,
            409,
            "source_artifact_not_current",
            "Tài liệu nguồn không phải thế hệ hiện tại của đợt nhập liệu.",
        )

    structure = (
        db.query(WorkbookStructureSnapshot)
        .filter(
            WorkbookStructureSnapshot.id == structure_snapshot_id,
            WorkbookStructureSnapshot.organization_id == org_id,
            WorkbookStructureSnapshot.project_id == project.id,
            WorkbookStructureSnapshot.source_artifact_id == artifact.id,
        )
        .first()
    )
    if structure is None:
        _abort(
            db,
            404,
            "structure_snapshot_not_found",
            "Không tìm thấy cấu trúc workbook.",
        )

    decision = (
        db.query(ColumnMappingDecision)
        .filter(
            ColumnMappingDecision.id == mapping_decision_id,
            ColumnMappingDecision.organization_id == org_id,
            ColumnMappingDecision.project_id == project.id,
            ColumnMappingDecision.source_artifact_id == artifact.id,
            ColumnMappingDecision.structure_snapshot_id == structure.id,
        )
        .first()
    )
    if decision is None:
        _abort(db, 404, "mapping_decision_not_found", "Không tìm thấy quyết định mapping.")
    if (
        _status_value(decision.decision_kind) != ColumnMappingDecisionKind.CONFIRMATION.value
        or _status_value(decision.outcome) not in {
            ColumnMappingDecisionOutcome.ACCEPTED.value,
            ColumnMappingDecisionOutcome.CORRECTED.value,
        }
        or _status_value(decision.proposal_source_kind) != ColumnMappingProposalSourceKind.HUMAN.value
    ):
        _abort(
            db,
            409,
            "mapping_decision_not_human_confirmed",
            "Quyết định mapping chưa được xác nhận thủ công.",
        )
    if decision.mapping_digest_sha256 != mapping_decision_digest_sha256:
        _abort(
            db,
            409,
            "mapping_decision_digest_mismatch",
            "Digest của quyết định mapping không khớp.",
        )

    usage = (
        db.query(ColumnMappingProfileUsage)
        .filter(
            ColumnMappingProfileUsage.organization_id == org_id,
            ColumnMappingProfileUsage.project_id == project.id,
            ColumnMappingProfileUsage.import_batch_id == import_batch_id,
            ColumnMappingProfileUsage.source_artifact_id == artifact.id,
            ColumnMappingProfileUsage.structure_snapshot_id == structure.id,
        )
        .first()
    )
    if usage is None:
        _abort(
            db,
            404,
            "mapping_profile_usage_not_found",
            "Không tìm thấy bản ghi sử dụng mapping.",
        )
    if usage.id != mapping_profile_usage_id:
        _abort(
            db,
            409,
            "mapping_profile_usage_mismatch",
            "Bản ghi sử dụng mapping không khớp.",
        )
    if usage.confirmation_decision_id != decision.id:
        _abort(
            db,
            409,
            "mapping_profile_usage_decision_mismatch",
            "Bản ghi sử dụng mapping không liên kết với quyết định đã chọn.",
        )
    if usage.mapping_digest_sha256 != profile_usage_mapping_digest_sha256:
        _abort(
            db,
            409,
            "mapping_profile_usage_digest_mismatch",
            "Digest của bản ghi sử dụng mapping không khớp.",
        )

    existing = (
        db.query(PreliminaryAnalysisSnapshot)
        .filter(
            PreliminaryAnalysisSnapshot.organization_id == org_id,
            PreliminaryAnalysisSnapshot.idempotency_key == normalized_key,
        )
        .populate_existing()
        .first()
    )
    if existing is not None:
        if not _same_request(
            existing,
            actor_id=actor.id,
            project_id=project_id,
            source_artifact_id=source_artifact_id,
            mapping_decision_id=mapping_decision_id,
            mapping_profile_usage_id=mapping_profile_usage_id,
            request_digest=request_digest,
        ):
            _abort(db, 409, "preliminary_analysis_idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác.")
        db.commit()
        db.refresh(existing)
        return existing

    if project.row_version != expected_project_version:
        _abort(db, 409, "project_version_conflict", "Dữ liệu hồ sơ đã thay đổi.")

    already_finalized = (
        db.query(PreliminaryAnalysisSnapshot.id)
        .filter(
            PreliminaryAnalysisSnapshot.organization_id == org_id,
            PreliminaryAnalysisSnapshot.project_id == project.id,
        )
        .first()
    )
    if already_finalized is not None:
        _abort(
            db,
            409,
            "preliminary_analysis_already_finalized",
            "Hồ sơ đã được phân tích sơ bộ.",
        )

    snapshot = PreliminaryAnalysisSnapshot(
        organization_id=org_id,
        customer_id=project.customer_id,
        project_id=project.id,
        version=1,
        import_batch_id=import_batch_id,
        source_artifact_id=artifact.id,
        structure_snapshot_id=structure.id,
        mapping_decision_id=decision.id,
        mapping_profile_usage_id=usage.id,
        source_artifact_generation=artifact.generation,
        mapping_decision_digest_sha256=decision.mapping_digest_sha256,
        profile_usage_mapping_digest_sha256=usage.mapping_digest_sha256,
        line_manifest=line_manifest,
        line_manifest_digest_sha256=line_manifest_digest_sha256,
        finalized_by_user_id=actor.id,
        idempotency_key=normalized_key,
        request_digest_sha256=request_digest,
    )
    db.add(snapshot)
    try:
        db.flush()
        log_audit_event(
            db,
            event_name="PreliminaryAnalysisSnapshotFinalized",
            entity_type="PreliminaryAnalysisSnapshot",
            entity_id=snapshot.id,
            organization_id=org_id,
            actor_user_id=actor.id,
            command_name="FinalizePreliminaryAnalysisSnapshot",
            correlation_id=correlation_id,
            payload={
                "project_id": str(project.id),
                "source_artifact_id": str(artifact.id),
                "source_artifact_generation": artifact.generation,
                "structure_snapshot_id": str(structure.id),
                "mapping_decision_id": str(decision.id),
                "mapping_profile_usage_id": str(usage.id),
                "line_manifest_digest_sha256": line_manifest_digest_sha256,
                "project_version_before": project.row_version,
            },
        )
        db.commit()
        db.refresh(snapshot)
        return snapshot
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(PreliminaryAnalysisSnapshot)
            .filter(
                PreliminaryAnalysisSnapshot.organization_id == org_id,
                PreliminaryAnalysisSnapshot.idempotency_key == normalized_key,
            )
            .populate_existing()
            .first()
        )
        if raced is not None and _same_request(
            raced,
            actor_id=actor.id,
            project_id=project_id,
            source_artifact_id=source_artifact_id,
            mapping_decision_id=mapping_decision_id,
            mapping_profile_usage_id=mapping_profile_usage_id,
            request_digest=request_digest,
        ):
            return raced
        if raced is not None:
            raise _error(
                409,
                "preliminary_analysis_idempotency_key_reused",
                "Mã lệnh đã được dùng cho dữ liệu khác.",
            ) from exc
        raced_project = (
            db.query(PreliminaryAnalysisSnapshot.id)
            .filter(
                PreliminaryAnalysisSnapshot.organization_id == org_id,
                PreliminaryAnalysisSnapshot.project_id == project_id,
            )
            .first()
        )
        if raced_project is not None:
            raise _error(
                409,
                "preliminary_analysis_already_finalized",
                "Hồ sơ đã được phân tích sơ bộ.",
            ) from exc
        raise _error(
            409,
            "preliminary_analysis_conflict",
            "Hồ sơ đã thay đổi đồng thời.",
        ) from exc
    except Exception:
        db.rollback()
        raise
