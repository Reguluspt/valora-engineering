"""Atomic generation of an immutable PreliminaryResultArtifact from a v2 analysis snapshot."""
from __future__ import annotations

import hashlib
import io
import json
import math
import uuid
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException
from openpyxl import load_workbook
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.audit import log_audit_event
from app.core.rbac import derive_effective_permissions
from app.modules.excel_import.infrastructure.object_storage import (
    ObjectNotFound,
    ObjectStorageError,
    _read_stream_bounded,
    get_object_storage,
)
from app.modules.excel_import.models import (
    ColumnMappingDecision,
    ColumnMappingProfileUsage,
    ImportSourceArtifact,
    ImportSourceArtifactState,
    WorkbookStructureSnapshot,
)
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    PreliminaryAnalysisSnapshot,
    PreliminaryResultArtifact,
    Project,
    ProjectAssetImportBatch,
    User,
    UserRole,
    UserStatus,
)


PRELIMINARY_RESULT_GENERATE_PERMISSION = "project:preliminary_result:generate"

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
_MAX_COLUMNS = 16_384
_MAX_OBJECT_BYTES = 10 * 1024 * 1024

_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL, "https://valora.internal/pr01/preliminary-result/v1"
)


@dataclass(frozen=True)
class _GenerationContext:
    artifact_id: uuid.UUID
    normalized_key: str
    request_digest: str
    snapshot_digest: str
    customer_id: uuid.UUID
    project_version: int
    snapshot: PreliminaryAnalysisSnapshot
    artifact: ImportSourceArtifact
    batch: ProjectAssetImportBatch
    structure: WorkbookStructureSnapshot
    decision: ColumnMappingDecision
    usage: ColumnMappingProfileUsage
    candidate: dict[str, Any]
    fields: list[dict[str, Any]]
    quantity_field: dict[str, Any]
    price_col: int
    amount_col: int
    line_manifest: list[dict[str, Any]]
    output_filename: str
    storage_key: str


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


def _finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _snapshot_canonical_digest(snapshot: PreliminaryAnalysisSnapshot) -> str:
    payload = {
        "contract": "preliminary-analysis-canonical-digest-v1",
        "import_batch_id": str(snapshot.import_batch_id),
        "line_manifest_digest_sha256": snapshot.line_manifest_digest_sha256,
        "mapping_decision_digest_sha256": snapshot.mapping_decision_digest_sha256,
        "mapping_decision_id": str(snapshot.mapping_decision_id),
        "mapping_profile_usage_id": str(snapshot.mapping_profile_usage_id),
        "organization_id": str(snapshot.organization_id),
        "profile_usage_mapping_digest_sha256": snapshot.profile_usage_mapping_digest_sha256,
        "project_id": str(snapshot.project_id),
        "snapshot_id": str(snapshot.id),
        "source_artifact_generation": snapshot.source_artifact_generation,
        "source_artifact_id": str(snapshot.source_artifact_id),
        "structure_snapshot_id": str(snapshot.structure_snapshot_id),
        "version": snapshot.version,
    }
    return _sha256_hex(_canonical_json(payload))


def snapshot_canonical_digest(snapshot: PreliminaryAnalysisSnapshot) -> str:
    """Pure public wrapper returning the canonical digest for a stored PreliminaryAnalysisSnapshot."""
    return _snapshot_canonical_digest(snapshot)



def _request_digest(
    *,
    actor_id: uuid.UUID,
    project_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    snapshot_digest: str,
    expected_project_version: int,
) -> str:
    payload = {
        "actor_id": str(actor_id),
        "contract": "preliminary-result-generate-v1",
        "expected_project_version": expected_project_version,
        "preliminary_analysis_snapshot_digest_sha256": snapshot_digest,
        "preliminary_analysis_snapshot_id": str(snapshot_id),
        "project_id": str(project_id),
    }
    return _sha256_hex(_canonical_json(payload))


def _artifact_id(*, org_id: uuid.UUID, normalized_key: str, request_digest: str) -> uuid.UUID:
    return uuid.uuid5(
        _NAMESPACE,
        f"org={org_id}|key={normalized_key}|digest={request_digest}",
    )


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
        _abort(db, 403, "preliminary_result_forbidden", "Không thể thực hiện thao tác này.")
    if PRELIMINARY_RESULT_GENERATE_PERMISSION not in derive_effective_permissions(
        persisted_actor, db
    ):
        _abort(db, 403, "preliminary_result_forbidden", "Không thể thực hiện thao tác này.")
    return persisted_actor


def _validate_v2_line_manifest(line_manifest: list[dict]) -> None:
    if not line_manifest:
        raise _error(
            409,
            "preliminary_result_line_manifest_empty",
            "Danh sách dòng kết quả không được để trống.",
        )
    seen_rows: set[int] = set()
    for index, line in enumerate(line_manifest):
        if not isinstance(line, dict) or set(line.keys()) != _LINE_V2_KEYS:
            raise _error(
                409,
                "preliminary_result_line_shape_invalid",
                f"Dòng {index} không đúng định dạng v2.",
            )
        source_row_number = line.get("source_row_number")
        if (
            isinstance(source_row_number, bool)
            or not isinstance(source_row_number, int)
            or source_row_number < 1
            or source_row_number > _MAX_WORKSHEET_ROW
        ):
            raise _error(
                409,
                "preliminary_result_line_source_row_number_invalid",
                f"Dòng {index} có vị trí hàng nguồn không hợp lệ.",
            )
        if source_row_number in seen_rows:
            raise _error(
                409,
                "preliminary_result_line_source_row_number_duplicate",
                f"Dòng {index} trùng vị trí hàng nguồn.",
            )
        seen_rows.add(source_row_number)
        quantity = line.get("quantity")
        if not _finite_number(quantity) or quantity < 0:
            raise _error(
                409,
                "preliminary_result_line_quantity_invalid",
                f"Dòng {index} có số lượng không hợp lệ.",
            )


def validate_stored_v2_manifest(line_manifest: Any) -> bool:
    """Pure public validator returning True if line_manifest satisfies strict v2 rules."""
    if not isinstance(line_manifest, list) or not line_manifest:
        return False
    try:
        _validate_v2_line_manifest(line_manifest)
    except Exception:
        return False
    for line in line_manifest:
        if not isinstance(line, dict):
            return False
        if line.get("human_line_confirmed") is not True:
            return False
        if line.get("has_unresolved_blocking_line") is not False:
            return False
        identity = line.get("identity")
        if not identity or not isinstance(identity, str) or not identity.strip():
            return False
        basis = line.get("accepted_price_basis")
        if not basis or not isinstance(basis, str) or not basis.strip():
            return False
        ref_price = line.get("confirmed_reference_price")
        if not _finite_number(ref_price) or ref_price < 0:
            return False
        transport = line.get("transport_percentage")
        if not _finite_number(transport) or transport < 0 or transport > 100:
            return False
        proposed = line.get("proposed_unit_price")
        if not _finite_number(proposed) or proposed < 0:
            return False
    return True



def _resolve_candidate_and_fields(usage: ColumnMappingProfileUsage) -> tuple[dict, list]:
    mapping_snapshot = usage.mapping_snapshot
    if not isinstance(mapping_snapshot, dict):
        raise _error(
            409,
            "preliminary_result_mapping_snapshot_invalid",
            "Snapshot ánh xạ không hợp lệ.",
        )
    candidate = mapping_snapshot.get("candidate")
    if not isinstance(candidate, dict):
        raise _error(
            409,
            "preliminary_result_source_region_missing",
            "Không tìm thấy vùng nguồn trong snapshot ánh xạ.",
        )
    required_candidate_keys = {
        "sheet_name",
        "header_start_row",
        "header_end_row",
        "data_start_row",
        "min_row",
        "max_row",
        "min_column",
        "max_column",
    }
    if required_candidate_keys - set(candidate.keys()):
        raise _error(
            409,
            "preliminary_result_source_region_invalid",
            "Vùng nguồn trong snapshot ánh xạ không đầy đủ.",
        )
    fields = mapping_snapshot.get("fields")
    if not isinstance(fields, list):
        raise _error(
            409,
            "preliminary_result_mapping_fields_invalid",
            "Danh sách trường ánh xạ không hợp lệ.",
        )
    quantity_fields = [
        field for field in fields if isinstance(field, dict) and field.get("semantic_role") == "quantity"
    ]
    if len(quantity_fields) != 1:
        raise _error(
            409,
            "preliminary_result_quantity_geometry_mismatch",
            "Cần đúng một cột số lượng trong ánh xạ.",
        )
    return candidate, fields, quantity_fields[0]


def _verify_source_checksum(storage, artifact: ImportSourceArtifact) -> None:
    try:
        stream = storage.open_stream(artifact.storage_object_key)
    except ObjectNotFound as exc:
        raise _error(
            409,
            "preliminary_result_source_not_found",
            "Không tìm thấy tài liệu nguồn trong kho lưu trữ.",
        ) from exc
    except ObjectStorageError as exc:
        raise _error(
            500,
            "preliminary_result_source_read_failed",
            "Không thể đọc tài liệu nguồn.",
        ) from exc
    try:
        data = _read_stream_bounded(stream, max_bytes=_MAX_OBJECT_BYTES)
    finally:
        stream.close()
    computed = hashlib.sha256(data).hexdigest()
    if computed != artifact.checksum_sha256:
        raise _error(
            409,
            "preliminary_result_source_checksum_mismatch",
            "Mã kiểm tra tài liệu nguồn không khớp.",
        )


def _load_workbook(data: bytes) -> Any:
    try:
        return load_workbook(io.BytesIO(data), data_only=True, read_only=False)
    except Exception as exc:
        raise _error(
            409,
            "preliminary_result_workbook_structural_failure",
            "Không thể phân tích workbook nguồn.",
        ) from exc


def _check_target_geometry(
    ws,
    *,
    candidate: dict,
    price_col: int,
    amount_col: int,
    line_manifest: list[dict],
) -> None:
    header_start_row = candidate["header_start_row"]
    data_start_row = candidate["data_start_row"]
    max_row = min(candidate["max_row"], ws.max_row)

    for col in (price_col, amount_col):
        if col > _MAX_COLUMNS:
            raise _error(
                409,
                "preliminary_result_geometry_invalid",
                "Cột đích vượt quá giới hạn worksheet.",
            )

    for line in line_manifest:
        locator = line["source_row_number"]
        if not (data_start_row <= locator <= max_row):
            raise _error(
                409,
                "preliminary_result_line_locator_out_of_region",
                f"Dòng nguồn {locator} nằm ngoài vùng dữ liệu.",
            )

    # Detect merged ranges that intersect the target columns within the candidate rows.
    merged_cells = set()
    for merged_range in ws.merged_cells.ranges:
        for row in range(merged_range.min_row, merged_range.max_row + 1):
            for col in range(merged_range.min_col, merged_range.max_col + 1):
                merged_cells.add((row, col))

    for row in range(header_start_row, max_row + 1):
        for col in (price_col, amount_col):
            if (row, col) in merged_cells:
                raise _error(
                    409,
                    "preliminary_result_target_merge_conflict",
                    "Ô đích giao với vùng đã gộp.",
                )
            cell = ws.cell(row=row, column=col)
            if cell.value is not None:
                raise _error(
                    409,
                    "preliminary_result_target_not_empty",
                    "Ô đích đã có dữ liệu.",
                )


def _write_output_workbook(
    data: bytes,
    *,
    candidate: dict,
    fields: list[dict],
    quantity_field: dict,
    price_col: int,
    amount_col: int,
    line_manifest: list[dict],
) -> tuple[bytes, str]:
    wb = _load_workbook(data)
    try:
        sheet_name = candidate["sheet_name"]
        if sheet_name not in wb.sheetnames:
            raise _error(
                409,
                "preliminary_result_source_sheet_missing",
                "Sheet nguồn không tồn tại.",
            )
        ws = wb[sheet_name]

        _check_target_geometry(
            ws,
            candidate=candidate,
            price_col=price_col,
            amount_col=amount_col,
            line_manifest=line_manifest,
        )

        header_start_row = candidate["header_start_row"]
        header_end_row = candidate["header_end_row"]

        # Write vertically-merged headers.
        ws.cell(row=header_start_row, column=price_col, value="Đơn giá đề xuất")
        ws.cell(row=header_start_row, column=amount_col, value="Thành tiền")
        if header_end_row > header_start_row:
            ws.merge_cells(
                start_row=header_start_row,
                start_column=price_col,
                end_row=header_end_row,
                end_column=price_col,
            )
            ws.merge_cells(
                start_row=header_start_row,
                start_column=amount_col,
                end_row=header_end_row,
                end_column=amount_col,
            )

        # Write manifest-addressed rows with static half-up amount.
        for line in line_manifest:
            row = line["source_row_number"]
            price = Decimal(str(line["proposed_unit_price"]))
            qty = Decimal(str(line["quantity"]))
            amount = (qty * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ws.cell(row=row, column=price_col, value=price)
            ws.cell(row=row, column=amount_col, value=amount)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.read(), hashlib.sha256(output.getvalue()).hexdigest()
    finally:
        wb.close()


def _build_lineage_manifest(
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    customer_id: uuid.UUID,
    snapshot: PreliminaryAnalysisSnapshot,
    artifact: ImportSourceArtifact,
    structure: WorkbookStructureSnapshot,
    decision: ColumnMappingDecision,
    usage: ColumnMappingProfileUsage,
    candidate: dict,
    quantity_field: dict,
    price_col: int,
    amount_col: int,
    snapshot_digest: str,
    line_manifest: list[dict],
) -> dict:
    return {
        "generation_contract": "preliminary-result-generate-v1",
        "project_id": str(project_id),
        "organization_id": str(org_id),
        "customer_id": str(customer_id),
        "import_batch_id": str(snapshot.import_batch_id),
        "source_workbook": {
            "artifact_id": str(artifact.id),
            "generation": artifact.generation,
            "checksum_sha256": artifact.checksum_sha256,
            "detected_format": artifact.detected_format,
        },
        "structure_snapshot": {
            "structure_snapshot_id": str(structure.id),
            "snapshot_version": structure.snapshot_version,
            "rule_version": structure.rule_version,
            "analysis_digest_sha256": structure.analysis_digest_sha256,
        },
        "mapping": {
            "decision_id": str(decision.id),
            "decision_digest_sha256": decision.mapping_digest_sha256,
            "profile_usage_id": str(usage.id),
            "usage_mapping_digest_sha256": usage.mapping_digest_sha256,
            "template_fingerprint_sha256": usage.mapping_snapshot.get("template_fingerprint_sha256", ""),
            "mapping_contract_version": usage.mapping_contract_version,
        },
        "analysis_snapshot": {
            "id": str(snapshot.id),
            "version": snapshot.version,
            "canonical_digest_sha256": snapshot_digest,
            "line_manifest_digest_sha256": snapshot.line_manifest_digest_sha256,
            "finalized_by_user_id": str(snapshot.finalized_by_user_id),
            "finalized_at": snapshot.finalized_at.isoformat(),
        },
        "mapped_region": {
            "sheet_name": candidate["sheet_name"],
            "header_start_row": candidate["header_start_row"],
            "header_end_row": candidate["header_end_row"],
            "data_start_row": candidate["data_start_row"],
            "min_row": candidate["min_row"],
            "max_row": candidate["max_row"],
            "min_column": candidate["min_column"],
            "max_column": candidate["max_column"],
        },
        "quantity_column": {
            "source_column_index": quantity_field["source_column_index"],
            "source_column_letter": quantity_field["source_column_letter"],
        },
        "output_layout": {
            "price_column_index": price_col,
            "amount_column_index": amount_col,
            "price_header": "Đơn giá đề xuất",
            "amount_header": "Thành tiền",
            "header_merge": True,
            "amount_rule": "static_quantity_times_proposed_round_2dp_half_up",
        },
        "line_locator_count": len(line_manifest),
    }


def _t1_validate_and_lock(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    preliminary_analysis_snapshot_id: uuid.UUID,
    expected_project_version: int,
    idempotency_key: str,
) -> _GenerationContext | PreliminaryResultArtifact:
    normalized_key = idempotency_key.strip()
    if not normalized_key or len(normalized_key) > 128:
        _abort(db, 422, "invalid_idempotency_key", "Khóa idempotency không hợp lệ.")
    if expected_project_version < 1:
        _abort(db, 422, "invalid_expected_version", "Phiên bản yêu cầu không hợp lệ.")

    actor = _reload_active_actor_and_org(db, actor=actor, org_id=org_id)

    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == org_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if project is None:
        _abort(db, 404, "project_not_found", "Không tìm thấy hồ sơ.")

    snapshot = (
        db.query(PreliminaryAnalysisSnapshot)
        .filter(
            PreliminaryAnalysisSnapshot.id == preliminary_analysis_snapshot_id,
            PreliminaryAnalysisSnapshot.organization_id == org_id,
            PreliminaryAnalysisSnapshot.project_id == project_id,
        )
        .with_for_update()
        .populate_existing()
        .first()
    )
    if snapshot is None:
        _abort(db, 404, "preliminary_analysis_snapshot_not_found", "Không tìm thấy phân tích sơ bộ.")

    # Strict v2 shape gate on the stored snapshot.
    try:
        _validate_v2_line_manifest(snapshot.line_manifest)
    except HTTPException as exc:
        db.rollback()
        if exc.detail.get("error_code") == "preliminary_result_line_manifest_empty":
            raise
        raise _error(
            409,
            "preliminary_result_source_locator_missing",
            "Dữ liệu phân tích sơ bộ thiếu vị trí dòng nguồn.",
        )

    artifact = (
        db.query(ImportSourceArtifact)
        .filter(
            ImportSourceArtifact.id == snapshot.source_artifact_id,
            ImportSourceArtifact.organization_id == org_id,
            ImportSourceArtifact.project_id == project_id,
        )
        .with_for_update()
        .first()
    )
    if artifact is None:
        _abort(db, 404, "source_artifact_not_found", "Không tìm thấy tài liệu nguồn.")
    if _status_value(artifact.state) != ImportSourceArtifactState.AVAILABLE.value:
        _abort(db, 409, "source_artifact_not_available", "Tài liệu nguồn chưa sẵn sàng.")
    if artifact.detected_format != "xlsx":
        _abort(db, 409, "preliminary_result_source_format_not_xlsx", "Chỉ hỗ trợ định dạng xlsx.")

    batch = (
        db.query(ProjectAssetImportBatch)
        .filter(
            ProjectAssetImportBatch.id == snapshot.import_batch_id,
            ProjectAssetImportBatch.organization_id == org_id,
            ProjectAssetImportBatch.project_id == project_id,
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
            WorkbookStructureSnapshot.id == snapshot.structure_snapshot_id,
            WorkbookStructureSnapshot.organization_id == org_id,
            WorkbookStructureSnapshot.project_id == project_id,
            WorkbookStructureSnapshot.source_artifact_id == artifact.id,
        )
        .first()
    )
    if structure is None:
        _abort(db, 404, "structure_snapshot_not_found", "Không tìm thấy cấu trúc workbook.")

    decision = (
        db.query(ColumnMappingDecision)
        .filter(
            ColumnMappingDecision.id == snapshot.mapping_decision_id,
            ColumnMappingDecision.organization_id == org_id,
            ColumnMappingDecision.project_id == project_id,
            ColumnMappingDecision.source_artifact_id == artifact.id,
            ColumnMappingDecision.structure_snapshot_id == structure.id,
        )
        .first()
    )
    if decision is None:
        _abort(db, 404, "mapping_decision_not_found", "Không tìm thấy quyết định mapping.")
    if decision.mapping_digest_sha256 != snapshot.mapping_decision_digest_sha256:
        _abort(
            db,
            409,
            "mapping_decision_digest_mismatch",
            "Digest của quyết định mapping không khớp.",
        )

    usage = (
        db.query(ColumnMappingProfileUsage)
        .filter(
            ColumnMappingProfileUsage.id == snapshot.mapping_profile_usage_id,
            ColumnMappingProfileUsage.organization_id == org_id,
            ColumnMappingProfileUsage.project_id == project_id,
            ColumnMappingProfileUsage.import_batch_id == snapshot.import_batch_id,
            ColumnMappingProfileUsage.source_artifact_id == artifact.id,
            ColumnMappingProfileUsage.structure_snapshot_id == structure.id,
        )
        .first()
    )
    if usage is None:
        _abort(db, 404, "mapping_profile_usage_not_found", "Không tìm thấy bản ghi sử dụng mapping.")
    if usage.confirmation_decision_id != decision.id:
        _abort(
            db,
            409,
            "mapping_profile_usage_decision_mismatch",
            "Bản ghi sử dụng mapping không khớp với quyết định mapping.",
        )
    if usage.mapping_digest_sha256 != snapshot.profile_usage_mapping_digest_sha256:
        _abort(
            db,
            409,
            "mapping_profile_usage_digest_mismatch",
            "Digest của bản ghi sử dụng mapping không khớp.",
        )

    # Cross-check lineage checksums.
    if artifact.checksum_sha256 != usage.source_checksum_sha256:
        _abort(
            db,
            409,
            "preliminary_result_source_usage_checksum_mismatch",
            "Mã kiểm tra nguồn không khớp với bản ghi sử dụng mapping.",
        )
    if structure.analysis_digest_sha256 != usage.structure_digest_sha256:
        _abort(
            db,
            409,
            "preliminary_result_structure_usage_digest_mismatch",
            "Digest cấu trúc không khớp với bản ghi sử dụng mapping.",
        )

    candidate, fields, quantity_field = _resolve_candidate_and_fields(usage)

    if project.row_version != expected_project_version:
        _abort(db, 409, "project_version_conflict", "Dữ liệu hồ sơ đã thay đổi.")

    # Idempotency lookup under locks.
    existing_by_key = (
        db.query(PreliminaryResultArtifact)
        .filter(
            PreliminaryResultArtifact.organization_id == org_id,
            PreliminaryResultArtifact.idempotency_key == normalized_key,
        )
        .populate_existing()
        .first()
    )

    snapshot_digest = _snapshot_canonical_digest(snapshot)
    request_digest = _request_digest(
        actor_id=actor.id,
        project_id=project_id,
        snapshot_id=snapshot.id,
        snapshot_digest=snapshot_digest,
        expected_project_version=expected_project_version,
    )
    artifact_id = _artifact_id(
        org_id=org_id, normalized_key=normalized_key, request_digest=request_digest
    )

    if existing_by_key is not None:
        if (
            existing_by_key.id == artifact_id
            and existing_by_key.request_digest_sha256 == request_digest
            and existing_by_key.created_by_user_id == actor.id
            and existing_by_key.project_id == project_id
            and existing_by_key.source_snapshot_sha256 == snapshot_digest
        ):
            db.commit()
            db.refresh(existing_by_key)
            return existing_by_key
        _abort(
            db,
            409,
            "preliminary_result_idempotency_key_reused",
            "Mã lệnh đã được dùng cho dữ liệu khác.",
        )

    # Any project artifact (including legacy keyless) blocks generation.
    already_generated = (
        db.query(PreliminaryResultArtifact.id)
        .filter(
            PreliminaryResultArtifact.organization_id == org_id,
            PreliminaryResultArtifact.project_id == project_id,
        )
        .first()
    )
    if already_generated is not None:
        _abort(
            db,
            409,
            "preliminary_result_already_generated",
            "Hồ sơ đã có kết quả sơ bộ.",
        )

    price_col = candidate["max_column"] + 1
    amount_col = candidate["max_column"] + 2
    output_filename = f"ket-qua-so-bo-v1-{artifact_id}.xlsx"
    storage_key = f"org/{org_id}/project/{project_id}/preliminary-results/{artifact_id}.xlsx"

    # Commit read-only and release locks before object IO.
    db.commit()

    return _GenerationContext(
        artifact_id=artifact_id,
        normalized_key=normalized_key,
        request_digest=request_digest,
        snapshot_digest=snapshot_digest,
        customer_id=project.customer_id,
        project_version=project.row_version,
        snapshot=snapshot,
        artifact=artifact,
        batch=batch,
        structure=structure,
        decision=decision,
        usage=usage,
        candidate=candidate,
        fields=fields,
        quantity_field=quantity_field,
        price_col=price_col,
        amount_col=amount_col,
        line_manifest=snapshot.line_manifest,
        output_filename=output_filename,
        storage_key=storage_key,
    )


def _t1_build_and_put_object(
    ctx: _GenerationContext,
    storage,
) -> tuple[bytes, str, int]:
    # Load source bytes once for workbook transformation and re-verify checksum.
    try:
        stream = storage.open_stream(ctx.artifact.storage_object_key)
    except ObjectNotFound as exc:
        raise _error(
            409,
            "preliminary_result_source_not_found",
            "Không tìm thấy tài liệu nguồn trong kho lưu trữ.",
        ) from exc
    except ObjectStorageError as exc:
        raise _error(
            500,
            "preliminary_result_source_read_failed",
            "Không thể đọc tài liệu nguồn.",
        ) from exc
    try:
        source_data = _read_stream_bounded(stream, max_bytes=_MAX_OBJECT_BYTES)
    finally:
        stream.close()

    computed_source_checksum = hashlib.sha256(source_data).hexdigest()
    if computed_source_checksum != ctx.artifact.checksum_sha256:
        raise _error(
            409,
            "preliminary_result_source_checksum_mismatch",
            "Mã kiểm tra tài liệu nguồn không khớp.",
        )

    try:
        output_data, output_checksum = _write_output_workbook(
            source_data,
            candidate=ctx.candidate,
            fields=ctx.fields,
            quantity_field=ctx.quantity_field,
            price_col=ctx.price_col,
            amount_col=ctx.amount_col,
            line_manifest=ctx.line_manifest,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise _error(
            500,
            "preliminary_result_build_failed",
            "Không thể tạo file kết quả.",
        ) from exc

    # No-overwrite put. If the deterministic key already exists, verify size+SHA.
    existing_stat = storage.head(ctx.storage_key)
    if existing_stat is not None:
        if existing_stat.size != len(output_data):
            raise _error(
                500,
                "preliminary_result_storage_failure",
                "Kho lưu trữ chứa dữ liệu khác kích thước.",
            )
        try:
            verify_stream = storage.open_stream(ctx.storage_key)
        except ObjectStorageError as exc:
            raise _error(
                500,
                "preliminary_result_storage_failure",
                "Không thể xác minh dữ liệu trong kho lưu trữ.",
            ) from exc
        try:
            existing_data = _read_stream_bounded(verify_stream, max_bytes=_MAX_OBJECT_BYTES)
        finally:
            verify_stream.close()
        if hashlib.sha256(existing_data).hexdigest() != output_checksum:
            raise _error(
                500,
                "preliminary_result_storage_failure",
                "Kho lưu trữ chứa dữ liệu khác mã kiểm tra.",
            )
        return output_data, output_checksum, len(output_data)

    try:
        output_stream = io.BytesIO(output_data)
        storage.put_stream(
            ctx.storage_key,
            output_stream,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            expected_size=len(output_data),
        )
    except ObjectStorageError as exc:
        raise _error(
            500,
            "preliminary_result_storage_failed",
            "Không thể lưu file kết quả.",
        ) from exc

    return output_data, output_checksum, len(output_data)


def _t2_insert_artifact(
    db: Session,
    *,
    ctx: _GenerationContext,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    output_checksum: str,
    output_size: int,
    correlation_id: str | None,
) -> PreliminaryResultArtifact:
    actor = _reload_active_actor_and_org(db, actor=actor, org_id=org_id)

    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == org_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if project is None:
        _abort(db, 404, "project_not_found", "Không tìm thấy hồ sơ.")

    snapshot = (
        db.query(PreliminaryAnalysisSnapshot)
        .filter(
            PreliminaryAnalysisSnapshot.id == ctx.snapshot.id,
            PreliminaryAnalysisSnapshot.organization_id == org_id,
            PreliminaryAnalysisSnapshot.project_id == project_id,
        )
        .with_for_update()
        .populate_existing()
        .first()
    )
    if snapshot is None:
        _abort(db, 404, "preliminary_analysis_snapshot_not_found", "Không tìm thấy phân tích sơ bộ.")

    # Recheck invariants.
    if project.row_version != ctx.project_version:
        _abort(db, 409, "project_version_conflict", "Dữ liệu hồ sơ đã thay đổi.")

    recomputed = _snapshot_canonical_digest(snapshot)
    if recomputed != ctx.snapshot_digest:
        _abort(
            db,
            409,
            "preliminary_result_snapshot_digest_changed",
            "Dữ liệu phân tích sơ bộ đã thay đổi.",
        )

    existing_by_key = (
        db.query(PreliminaryResultArtifact)
        .filter(
            PreliminaryResultArtifact.organization_id == org_id,
            PreliminaryResultArtifact.idempotency_key == ctx.normalized_key,
        )
        .populate_existing()
        .first()
    )
    if existing_by_key is not None:
        if (
            existing_by_key.id == ctx.artifact_id
            and existing_by_key.request_digest_sha256 == ctx.request_digest
            and existing_by_key.created_by_user_id == actor.id
            and existing_by_key.project_id == project_id
            and existing_by_key.source_snapshot_sha256 == ctx.snapshot_digest
        ):
            db.commit()
            db.refresh(existing_by_key)
            return existing_by_key
        _abort(
            db,
            409,
            "preliminary_result_idempotency_key_reused",
            "Mã lệnh đã được dùng cho dữ liệu khác.",
        )

    already_generated = (
        db.query(PreliminaryResultArtifact.id)
        .filter(
            PreliminaryResultArtifact.organization_id == org_id,
            PreliminaryResultArtifact.project_id == project_id,
        )
        .first()
    )
    if already_generated is not None:
        _abort(
            db,
            409,
            "preliminary_result_already_generated",
            "Hồ sơ đã có kết quả sơ bộ.",
        )

    lineage_manifest = _build_lineage_manifest(
        org_id=org_id,
        project_id=project_id,
        customer_id=ctx.customer_id,
        snapshot=snapshot,
        artifact=ctx.artifact,
        structure=ctx.structure,
        decision=ctx.decision,
        usage=ctx.usage,
        candidate=ctx.candidate,
        quantity_field=ctx.quantity_field,
        price_col=ctx.price_col,
        amount_col=ctx.amount_col,
        snapshot_digest=ctx.snapshot_digest,
        line_manifest=ctx.line_manifest,
    )

    artifact = PreliminaryResultArtifact(
        id=ctx.artifact_id,
        organization_id=org_id,
        customer_id=ctx.customer_id,
        project_id=project_id,
        version=1,
        original_filename=ctx.output_filename,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=output_size,
        content_checksum_sha256=output_checksum,
        storage_object_key=ctx.storage_key,
        source_snapshot_sha256=ctx.snapshot_digest,
        idempotency_key=ctx.normalized_key,
        request_digest_sha256=ctx.request_digest,
        lineage_manifest=lineage_manifest,
        created_by_user_id=actor.id,
    )
    db.add(artifact)
    try:
        db.flush()
        log_audit_event(
            db,
            event_name="PreliminaryResultArtifactGenerated",
            entity_type="PreliminaryResultArtifact",
            entity_id=artifact.id,
            organization_id=org_id,
            actor_user_id=actor.id,
            command_name="GeneratePreliminaryResultArtifact",
            correlation_id=correlation_id,
            payload={
                "project_id": str(project_id),
                "preliminary_analysis_snapshot_id": str(snapshot.id),
                "preliminary_analysis_snapshot_version": snapshot.version,
                "source_snapshot_sha256": ctx.snapshot_digest,
                "content_checksum_sha256": output_checksum,
                "file_size_bytes": output_size,
                "version": 1,
                "project_version_before": ctx.project_version,
            },
        )
        db.commit()
        db.refresh(artifact)
        return artifact
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(PreliminaryResultArtifact)
            .filter(
                PreliminaryResultArtifact.organization_id == org_id,
                PreliminaryResultArtifact.idempotency_key == ctx.normalized_key,
            )
            .populate_existing()
            .first()
        )
        if raced is not None and (
            raced.id == ctx.artifact_id
            and raced.request_digest_sha256 == ctx.request_digest
            and raced.created_by_user_id == actor.id
            and raced.project_id == project_id
            and raced.source_snapshot_sha256 == ctx.snapshot_digest
        ):
            return raced
        if raced is not None:
            raise _error(
                409,
                "preliminary_result_idempotency_key_reused",
                "Mã lệnh đã được dùng cho dữ liệu khác.",
            ) from exc
        raced_project = (
            db.query(PreliminaryResultArtifact.id)
            .filter(
                PreliminaryResultArtifact.organization_id == org_id,
                PreliminaryResultArtifact.project_id == project_id,
            )
            .first()
        )
        if raced_project is not None:
            raise _error(
                409,
                "preliminary_result_already_generated",
                "Hồ sơ đã có kết quả sơ bộ.",
            ) from exc
        raise _error(
            409,
            "preliminary_result_conflict",
            "Hồ sơ đã thay đổi đồng thời.",
        ) from exc
    except Exception:
        db.rollback()
        raise


def generate_preliminary_result_artifact(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    preliminary_analysis_snapshot_id: uuid.UUID,
    expected_project_version: int,
    idempotency_key: str,
    confirmed: bool,
    correlation_id: str | None = None,
) -> PreliminaryResultArtifact:
    """Generate the one-per-project preliminary-result artifact and atomic success audit."""
    if confirmed is not True:
        _abort(db, 400, "preliminary_result_confirmation_required", "Cần xác nhận thao tác.")

    t1_result = _t1_validate_and_lock(
        db,
        actor=actor,
        org_id=org_id,
        project_id=project_id,
        preliminary_analysis_snapshot_id=preliminary_analysis_snapshot_id,
        expected_project_version=expected_project_version,
        idempotency_key=idempotency_key,
    )
    if isinstance(t1_result, PreliminaryResultArtifact):
        return t1_result

    storage = get_object_storage()
    try:
        output_data, output_checksum, output_size = _t1_build_and_put_object(
            t1_result, storage
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise _error(
            500,
            "preliminary_result_build_failed",
            "Không thể tạo file kết quả.",
        ) from exc

    try:
        return _t2_insert_artifact(
            db,
            ctx=t1_result,
            actor=actor,
            org_id=org_id,
            project_id=project_id,
            output_checksum=output_checksum,
            output_size=output_size,
            correlation_id=correlation_id,
        )
    except Exception:
        # Best-effort idempotent cleanup of our own deterministic key on DB failure.
        try:
            storage.delete(t1_result.storage_key)
        except Exception:
            pass
        raise
