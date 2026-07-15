"""S12-PR-003 application service: validate import staging rows under batch lock."""
from __future__ import annotations

import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.modules.excel_import.domain.validation_rules import RULE_SET_VERSION, evaluate_row
from app.modules.project_master_data.models import (
    AuditEvent,
    ImportBatchStatus,
    ImportRowValidationStatus,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    User,
)

DISALLOWED_CLIENT_DETAIL = "Lô nhập liệu chưa ở trạng thái có thể kiểm tra."
ENGINE_FAILURE_CLIENT_DETAIL = "Không thể kiểm tra dữ liệu Excel. Vui lòng thử lại."

SUCCESS_EVENT = "ProjectAssetImportBatchValidationSucceeded"
FAILURE_EVENT = "ProjectAssetImportBatchValidationFailed"
COMMAND_NAME = "ValidateProjectAssetImportBatch"


def _status_value(status) -> str:
    return status.value if hasattr(status, "value") else str(status)


def _is_allowed_source(status) -> bool:
    return _status_value(status) in {
        ImportBatchStatus.PARSED.value,
        ImportBatchStatus.VALIDATION_FAILED.value,
        ImportBatchStatus.READY_FOR_REVIEW.value,
    }


def build_validation_fingerprint(db: Session, batch: ProjectAssetImportBatch) -> dict:
    """Generation fingerprint for validation concurrency / stale-failure guard."""
    rows = (
        db.query(ProjectAssetImportStagingRow)
        .filter(ProjectAssetImportStagingRow.import_batch_id == batch.id)
        .order_by(ProjectAssetImportStagingRow.id)
        .all()
    )
    latest_success = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_id == batch.id,
            AuditEvent.event_name == SUCCESS_EVENT,
        )
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    return {
        "status": _status_value(batch.status),
        "source_filename": batch.source_filename,
        "source_sheet_name": batch.source_sheet_name,
        "total_rows": batch.total_rows,
        "valid_rows": batch.valid_rows,
        "invalid_rows": batch.invalid_rows,
        "warning_rows": batch.warning_rows,
        "staging_row_ids": [r.id for r in rows],
        # Null-aware typed pairs: do not str() collapse None vs "None" or empty vs null.
        "validation_inputs": [
            (r.proposed_asset_name, r.proposed_quantity) for r in rows
        ],
        "latest_validation_success_audit_id": (
            str(latest_success.id) if latest_success else None
        ),
    }


def _apply_validation_to_rows(
    rows: list[ProjectAssetImportStagingRow],
) -> tuple[int, int, int]:
    valid = 0
    invalid = 0
    for row in rows:
        status, errors, warnings = evaluate_row(
            row.proposed_asset_name, row.proposed_quantity
        )
        if status == "valid":
            row.validation_status = ImportRowValidationStatus.VALID
            valid += 1
        else:
            row.validation_status = ImportRowValidationStatus.INVALID
            invalid += 1
        row.validation_errors = errors
        row.validation_warnings = warnings
    return valid, invalid, 0


def _record_success_audit(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch: ProjectAssetImportBatch,
    source_status: str,
    correlation_id: str | None,
) -> None:
    log_audit_event(
        db=db,
        event_name=SUCCESS_EVENT,
        entity_type="ProjectAssetImportBatch",
        entity_id=batch.id,
        organization_id=org_id,
        actor_user_id=actor.id,
        command_name=COMMAND_NAME,
        correlation_id=correlation_id,
        payload={
            "rule_set_version": RULE_SET_VERSION,
            "organization_id": str(org_id),
            "project_id": str(project_id),
            "batch_id": str(batch.id),
            "source_status": source_status,
            "total_rows": batch.total_rows,
            "valid_rows": batch.valid_rows,
            "invalid_rows": batch.invalid_rows,
            "warning_rows": batch.warning_rows,
        },
    )


def _record_failure_audit(
    db: Session,
    *,
    actor_id: uuid.UUID,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch: ProjectAssetImportBatch,
    source_status: str,
    correlation_id: str | None,
) -> None:
    batch.status = ImportBatchStatus.VALIDATION_FAILED
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
            "rule_set_version": RULE_SET_VERSION,
            "organization_id": str(org_id),
            "project_id": str(project_id),
            "batch_id": str(batch.id),
            "source_status": source_status,
            "error_code": "validation_engine_failed",
        },
    )
    db.flush()


def _recover_validation_failure(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    actor_id: uuid.UUID,
    pre_fingerprint: dict,
    source_status: str,
    correlation_id: str | None,
) -> None:
    try:
        db.expire_all()
        locked = (
            db.query(ProjectAssetImportBatch)
            .filter(
                ProjectAssetImportBatch.organization_id == org_id,
                ProjectAssetImportBatch.project_id == project_id,
                ProjectAssetImportBatch.id == batch_id,
            )
            .with_for_update()
            .first()
        )
        if not locked:
            db.rollback()
            return
        current = build_validation_fingerprint(db, locked)
        if current == pre_fingerprint:
            _record_failure_audit(
                db=db,
                actor_id=actor_id,
                org_id=org_id,
                project_id=project_id,
                batch=locked,
                source_status=source_status,
                correlation_id=correlation_id,
            )
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()


def validate_project_asset_import_batch(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    current_user: User,
    correlation_id: str | None = None,
) -> ProjectAssetImportBatch:
    """Validate all staging rows for a batch. Staging-only; never touches ProjectAssetLine."""
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

    if _status_value(batch.status) == ImportBatchStatus.APPLIED.value:
        raise HTTPException(
            status_code=409,
            detail="Lô nhập liệu đã được áp dụng và không ở trạng thái có thể kiểm tra.",
        )

    if not _is_allowed_source(batch.status):
        raise HTTPException(status_code=409, detail=DISALLOWED_CLIENT_DETAIL)

    source_status = _status_value(batch.status)
    pre_fingerprint = build_validation_fingerprint(db, batch)

    sp = db.begin_nested()
    savepoint_committed = False
    try:
        rows = (
            db.query(ProjectAssetImportStagingRow)
            .filter(
                ProjectAssetImportStagingRow.import_batch_id == batch.id,
                ProjectAssetImportStagingRow.organization_id == org_id,
                ProjectAssetImportStagingRow.project_id == project_id,
            )
            .order_by(ProjectAssetImportStagingRow.id)
            .all()
        )
        valid_rows, invalid_rows, warning_rows = _apply_validation_to_rows(rows)
        batch.total_rows = len(rows)
        batch.valid_rows = valid_rows
        batch.invalid_rows = invalid_rows
        batch.warning_rows = warning_rows
        batch.status = ImportBatchStatus.READY_FOR_REVIEW

        _record_success_audit(
            db=db,
            actor=current_user,
            org_id=org_id,
            project_id=project_id,
            batch=batch,
            source_status=source_status,
            correlation_id=correlation_id,
        )
        db.flush()
        sp.commit()
        savepoint_committed = True
        db.commit()
        db.refresh(batch)
        return batch

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
        # Failure audit only if generation fingerprint still matches (no stale overwrite).
        _recover_validation_failure(
            db=db,
            org_id=org_id,
            project_id=project_id,
            batch_id=batch_id,
            actor_id=current_user.id,
            pre_fingerprint=pre_fingerprint,
            source_status=source_status,
            correlation_id=correlation_id,
        )
        raise HTTPException(status_code=500, detail=ENGINE_FAILURE_CLIENT_DETAIL)
