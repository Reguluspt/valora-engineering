"""S12-PR-004: apply validated staging rows to official ProjectAssetLine with lineage."""
from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.modules.project_master_data.models import (
    AssetLineReviewStatus,
    AssetLineValidationStatus,
    AuditEvent,
    Currency,
    ImportBatchStatus,
    ImportRowValidationStatus,
    Project,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    ProjectAssetLine,
    ProjectWorkflowStatus,
    ReferenceStatus,
    Unit,
    User,
)

CONTRACT_VERSION = "s12-pr-004-v1"
COMMAND_NAME = "ApplyProjectAssetImportBatch"
SUCCESS_EVENT = "ProjectAssetImportBatchApplied"
FAILURE_EVENT = "ProjectAssetImportBatchApplyFailed"
UPLOAD_EVENT = "ProjectAssetImportBatchUploaded"
VALIDATION_SUCCESS_EVENT = "ProjectAssetImportBatchValidationSucceeded"

ERR_CONFIRM = "apply_confirmation_required"
ERR_NOT_DRAFT = "apply_project_not_draft"
ERR_STATE = "apply_state_not_allowed"
ERR_ROWS = "apply_rows_not_ready"
ERR_MAPPING = "apply_mapping_invalid"
ERR_ENGINE = "apply_engine_failed"

MSG_CONFIRM = "Bạn phải xác nhận trước khi áp dụng dữ liệu."
MSG_NOT_DRAFT = "Chỉ có thể áp dụng dữ liệu khi dự án ở trạng thái nháp."
MSG_STATE = "Lô nhập liệu chưa sẵn sàng để áp dụng."
MSG_ROWS = "Tất cả dòng phải hợp lệ trước khi áp dụng."
MSG_MAPPING = "Dữ liệu chưa thể ánh xạ vào danh sách tài sản chính thức."
MSG_ENGINE = "Không thể áp dụng dữ liệu Excel. Vui lòng thử lại."


def _status_value(status) -> str:
    return status.value if hasattr(status, "value") else str(status)


def _raise(status: int, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status,
        detail={"error_code": code, "detail": message, "message": message},
    )


def _trim(value: str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _parse_decimal(
    raw: str | None,
    *,
    max_frac: int,
    max_int_digits: int,
    default: Decimal | None,
) -> Decimal | None:
    if raw is None:
        return default
    text = str(raw).strip()
    if text == "":
        return default
    lower = text.lower()
    if lower in ("nan", "inf", "-inf", "+inf", "infinity", "-infinity", "+infinity"):
        raise ValueError("non-finite")
    try:
        dec = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid decimal") from exc
    if not dec.is_finite():
        raise ValueError("non-finite")
    if dec < 0:
        raise ValueError("negative")
    sign, digits, exp = dec.as_tuple()
    if exp < -max_frac:
        raise ValueError("scale")
    # integer digit count without scientific expansion issues
    if exp >= 0:
        int_digits = len(digits) + exp
    else:
        int_digits = max(0, len(digits) + exp)
    if int_digits > max_int_digits:
        raise ValueError("precision")
    return dec


def _resolve_unit(db: Session, raw: str | None) -> uuid.UUID | None:
    key = _trim(raw)
    if key is None:
        return None
    key_cf = key.casefold()
    active = (
        db.query(Unit)
        .filter(Unit.status == ReferenceStatus.ACTIVE)
        .all()
    )
    for attr in ("code", "display_name", "symbol"):
        matches = [
            u
            for u in active
            if getattr(u, attr) is not None
            and str(getattr(u, attr)).casefold() == key_cf
        ]
        if attr == "symbol":
            # only unique symbol
            if len(matches) == 1:
                return matches[0].id
            if len(matches) > 1:
                raise ValueError("ambiguous unit symbol")
            continue
        if len(matches) == 1:
            return matches[0].id
        if len(matches) > 1:
            raise ValueError("ambiguous unit")
        # no matches at this tier: fall through only when zero matches
    raise ValueError("unknown unit")


def _resolve_currency(db: Session, raw: str | None) -> uuid.UUID | None:
    key = _trim(raw)
    if key is None:
        return None
    key_cf = key.casefold()
    active = (
        db.query(Currency)
        .filter(Currency.status == ReferenceStatus.ACTIVE)
        .all()
    )
    for attr in ("code", "display_name"):
        matches = [
            c
            for c in active
            if getattr(c, attr) is not None
            and str(getattr(c, attr)).casefold() == key_cf
        ]
        if len(matches) == 1:
            return matches[0].id
        if len(matches) > 1:
            raise ValueError("ambiguous currency")
    # symbol forbidden: if matches only via symbol, reject
    sym = [
        c
        for c in active
        if c.symbol is not None and str(c.symbol).casefold() == key_cf
    ]
    if sym:
        raise ValueError("currency symbol forbidden")
    raise ValueError("unknown currency")


def build_apply_fingerprint(
    db: Session,
    *,
    project: Project,
    batch: ProjectAssetImportBatch,
    rows: list[ProjectAssetImportStagingRow],
) -> dict:
    def latest(event_name: str):
        return (
            db.query(AuditEvent)
            .filter(
                AuditEvent.entity_id == batch.id,
                AuditEvent.event_name == event_name,
            )
            .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
            .first()
        )

    up = latest(UPLOAD_EVENT)
    vs = latest(VALIDATION_SUCCESS_EVENT)
    ap = latest(SUCCESS_EVENT)
    return {
        "project_status": _status_value(project.status),
        "batch_status": _status_value(batch.status),
        "source_filename": batch.source_filename,
        "source_sheet_name": batch.source_sheet_name,
        "total_rows": batch.total_rows,
        "valid_rows": batch.valid_rows,
        "invalid_rows": batch.invalid_rows,
        "warning_rows": batch.warning_rows,
        "staging_row_ids": [r.id for r in rows],
        "source_row_numbers": [r.source_row_number for r in rows],
        "proposed_inputs": [
            (
                r.proposed_asset_name,
                r.proposed_description,
                r.proposed_quantity,
                r.proposed_unit,
                r.proposed_raw_price,
                r.proposed_currency,
            )
            for r in rows
        ],
        "validation": [
            (
                _status_value(r.validation_status),
                list(r.validation_errors or []),
                list(r.validation_warnings or []),
            )
            for r in rows
        ],
        "latest_upload_audit_id": str(up.id) if up else None,
        "latest_validation_success_audit_id": str(vs.id) if vs else None,
        "latest_apply_success_audit_id": str(ap.id) if ap else None,
    }


def _map_row(db: Session, row: ProjectAssetImportStagingRow) -> dict[str, Any]:
    name = _trim(row.proposed_asset_name)
    if not name or len(name) > 255:
        raise ValueError("asset_name")
    desc = _trim(row.proposed_description)
    if desc is not None and len(desc) > 5000:
        raise ValueError("description")
    qty = _parse_decimal(
        row.proposed_quantity, max_frac=4, max_int_digits=11, default=Decimal("1.0000")
    )
    assert qty is not None
    unit_id = _resolve_unit(db, row.proposed_unit)
    raw_price = _parse_decimal(
        row.proposed_raw_price, max_frac=2, max_int_digits=13, default=None
    )
    currency_id = _resolve_currency(db, row.proposed_currency)
    return {
        "asset_name": name,
        "description": desc,
        "quantity": qty,
        "unit_id": unit_id,
        "raw_price": raw_price,
        "raw_price_currency_id": currency_id,
    }


def _record_failure_audit(
    db: Session,
    *,
    actor_id: uuid.UUID,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch: ProjectAssetImportBatch,
    source_status: str,
    error_code: str,
    correlation_id: str | None,
) -> None:
    log_audit_event(
        db=db,
        event_name=FAILURE_EVENT,
        entity_type="ProjectAssetImportBatch",
        entity_id=batch.id,
        organization_id=org_id,
        actor_user_id=actor_id,
        command_name=COMMAND_NAME,
        correlation_id=correlation_id,
        payload={
            "contract_version": CONTRACT_VERSION,
            "organization_id": str(org_id),
            "project_id": str(project_id),
            "batch_id": str(batch.id),
            "source_status": source_status,
            "error_code": error_code,
        },
    )


def _recover_apply_failure(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    actor_id: uuid.UUID,
    pre_fingerprint: dict,
    source_status: str,
    error_code: str,
    correlation_id: str | None,
) -> None:
    try:
        db.expire_all()
        project = (
            db.query(Project)
            .filter(Project.organization_id == org_id, Project.id == project_id)
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
            .with_for_update()
            .first()
        )
        if not project or not batch:
            db.rollback()
            return
        rows = (
            db.query(ProjectAssetImportStagingRow)
            .filter(
                ProjectAssetImportStagingRow.import_batch_id == batch.id,
                ProjectAssetImportStagingRow.organization_id == org_id,
                ProjectAssetImportStagingRow.project_id == project_id,
            )
            .order_by(
                ProjectAssetImportStagingRow.source_row_number,
                ProjectAssetImportStagingRow.id,
            )
            .all()
        )
        current = build_apply_fingerprint(
            db, project=project, batch=batch, rows=rows
        )
        if current == pre_fingerprint:
            _record_failure_audit(
                db=db,
                actor_id=actor_id,
                org_id=org_id,
                project_id=project_id,
                batch=batch,
                source_status=source_status,
                error_code=error_code,
                correlation_id=correlation_id,
            )
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()


def apply_project_asset_import_batch(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    current_user: User,
    confirm: bool | None,
    correlation_id: str | None = None,
) -> dict:
    """Promote validated staging rows to official lines. Atomic all-or-nothing."""
    if confirm is not True:
        _raise(400, ERR_CONFIRM, MSG_CONFIRM)

    # Lock order: Project → batch → staging
    project = (
        db.query(Project)
        .filter(Project.organization_id == org_id, Project.id == project_id)
        .with_for_update()
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if _status_value(project.status) != ProjectWorkflowStatus.DRAFT.value:
        _raise(400, ERR_NOT_DRAFT, MSG_NOT_DRAFT)

    batch = (
        db.query(ProjectAssetImportBatch)
        .filter(
            ProjectAssetImportBatch.organization_id == org_id,
            ProjectAssetImportBatch.project_id == project_id,
            ProjectAssetImportBatch.id == batch_id,
        )
        .with_for_update()
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")

    if _status_value(batch.status) != ImportBatchStatus.READY_FOR_REVIEW.value:
        _raise(409, ERR_STATE, MSG_STATE)

    # Lock order: Project → batch → staging FOR UPDATE (ordered) → inserts
    rows = (
        db.query(ProjectAssetImportStagingRow)
        .filter(
            ProjectAssetImportStagingRow.import_batch_id == batch.id,
            ProjectAssetImportStagingRow.organization_id == org_id,
            ProjectAssetImportStagingRow.project_id == project_id,
        )
        .order_by(
            ProjectAssetImportStagingRow.source_row_number,
            ProjectAssetImportStagingRow.id,
        )
        .with_for_update()
        .all()
    )

    if not rows:
        _raise(409, ERR_ROWS, MSG_ROWS)

    # Counter agreement
    valid_count = sum(
        1
        for r in rows
        if _status_value(r.validation_status) == ImportRowValidationStatus.VALID.value
    )
    invalid_count = sum(
        1
        for r in rows
        if _status_value(r.validation_status) == ImportRowValidationStatus.INVALID.value
    )
    warning_count = sum(
        1
        for r in rows
        if _status_value(r.validation_status) == ImportRowValidationStatus.WARNING.value
    )
    pending_count = sum(
        1
        for r in rows
        if _status_value(r.validation_status) == ImportRowValidationStatus.PENDING.value
    )
    if (
        batch.total_rows != len(rows)
        or batch.valid_rows != valid_count
        or batch.invalid_rows != invalid_count
        or batch.warning_rows != warning_count
    ):
        _raise(409, ERR_ROWS, MSG_ROWS)

    if (
        pending_count
        or invalid_count
        or warning_count
        or valid_count != len(rows)
    ):
        _raise(409, ERR_ROWS, MSG_ROWS)

    source_status = _status_value(batch.status)
    pre_fingerprint = build_apply_fingerprint(
        db, project=project, batch=batch, rows=rows
    )
    batch_id_value = batch.id

    sp = db.begin_nested()
    savepoint_committed = False
    error_code = ERR_ENGINE
    try:
        created_lines: list[dict] = []
        for row in rows:
            try:
                mapped = _map_row(db, row)
            except ValueError:
                error_code = ERR_MAPPING
                raise

            line = ProjectAssetLine(
                project_id=project_id,
                asset_name=mapped["asset_name"],
                description=mapped["description"],
                quantity=mapped["quantity"],
                unit_id=mapped["unit_id"],
                raw_price=mapped["raw_price"],
                raw_price_currency_id=mapped["raw_price_currency_id"],
                review_status=AssetLineReviewStatus.PENDING,
                validation_status=AssetLineValidationStatus.UNVALIDATED,
                source_import_batch_id=batch.id,
                source_staging_row_id=row.id,
            )
            db.add(line)
            db.flush()
            created_lines.append(
                {
                    "line_id": line.id,
                    "staging_row_id": row.id,
                    "source_row_number": row.source_row_number,
                }
            )

        batch.status = ImportBatchStatus.APPLIED
        log_audit_event(
            db=db,
            event_name=SUCCESS_EVENT,
            entity_type="ProjectAssetImportBatch",
            entity_id=batch.id,
            organization_id=org_id,
            actor_user_id=current_user.id,
            command_name=COMMAND_NAME,
            correlation_id=correlation_id,
            payload={
                "contract_version": CONTRACT_VERSION,
                "organization_id": str(org_id),
                "project_id": str(project_id),
                "batch_id": str(batch.id),
                "source_status": source_status,
                "target_status": ImportBatchStatus.APPLIED.value,
                "total_rows": len(rows),
                "created_count": len(created_lines),
            },
        )
        db.flush()
        sp.commit()
        savepoint_committed = True
        # Response must be fully built from scalars/UUIDs before outer commit.
        # Outer commit is the final fallible success-path operation.
        response = {
            "project_id": project_id,
            "import_batch_id": batch_id_value,
            "status": ImportBatchStatus.APPLIED.value,
            "created_count": len(created_lines),
            "created_lines": created_lines,
        }
        db.commit()
        return response

    except HTTPException:
        raise
    except Exception:
        if not savepoint_committed:
            try:
                sp.rollback()
            except Exception:
                pass
        try:
            db.rollback()
        except Exception:
            pass
        _recover_apply_failure(
            db=db,
            org_id=org_id,
            project_id=project_id,
            batch_id=batch_id,
            actor_id=current_user.id,
            pre_fingerprint=pre_fingerprint,
            source_status=source_status,
            error_code=error_code,
            correlation_id=correlation_id,
        )
        if error_code == ERR_MAPPING:
            _raise(400, ERR_MAPPING, MSG_MAPPING)
        _raise(500, ERR_ENGINE, MSG_ENGINE)
