import uuid
from fastapi import UploadFile, Request, HTTPException
from sqlalchemy.orm import Session

from app.modules.project_master_data.models import (
    Project,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    AuditEvent,
)
from app.modules.excel_import.application.parse_workbook import (
    parse_workbook_lazy, ParseError, sanitize_filename, get_request_size, enforce_request_limit
)
from app.modules.excel_import.application.replace_staging_rows import (
    replace_staging_rows, record_failure_audit
)
from app.modules.excel_import.domain import DEFAULT_LIMITS


def _build_pre_fingerprint(db: Session, batch: ProjectAssetImportBatch) -> dict:
    staging_ids = [
        r.id for r in db.query(ProjectAssetImportStagingRow)
        .filter(ProjectAssetImportStagingRow.import_batch_id == batch.id)
        .order_by(ProjectAssetImportStagingRow.id)
        .all()
    ]
    latest_success_audit = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_id == batch.id,
            AuditEvent.event_name == "ProjectAssetImportBatchUploaded"
        )
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    return {
        "status": batch.status,
        "source_filename": batch.source_filename,
        "source_sheet_name": batch.source_sheet_name,
        "total_rows": batch.total_rows,
        "staging_row_ids": staging_ids,
        "latest_success_audit_id": str(latest_success_audit.id) if latest_success_audit else None,
    }


def upload_excel_file_orchestrator(
    db: Session,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    file: UploadFile,
    request: Request | None,
    current_user,
    correlation_id: str | None = None
) -> ProjectAssetImportBatch:
    # Lock order (ADR 0029 / Apply-compatible): Project → batch → staging mutation
    project = (
        db.query(Project)
        .filter(Project.organization_id == org_id, Project.id == project_id)
        .with_for_update()
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    batch = db.query(ProjectAssetImportBatch).filter(
        ProjectAssetImportBatch.organization_id == org_id,
        ProjectAssetImportBatch.project_id == project_id,
        ProjectAssetImportBatch.id == batch_id
    ).with_for_update().first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")

    status_val = batch.status.value if hasattr(batch.status, "value") else str(batch.status)
    if status_val == "applied":
        raise HTTPException(
            status_code=409,
            detail="Lô nhập liệu đã được áp dụng và không thể tải lên lại.",
        )

    pre_fingerprint = _build_pre_fingerprint(db, batch)
    previous_count = len(pre_fingerprint["staging_row_ids"])
    sanitized = sanitize_filename(file.filename or "import.xlsx")

    sp = db.begin_nested()
    savepoint_committed = False
    try:
        request_size = get_request_size(request)
        enforce_request_limit(request_size, DEFAULT_LIMITS)

        lazy = parse_workbook_lazy(
            file=file,
            source_sheet_name=batch.source_sheet_name,
        )
        batch = replace_staging_rows(
            db=db,
            actor=current_user,
            org_id=org_id,
            project_id=project_id,
            batch_id=batch_id,
            lazy_rows=lazy,
            parsed_count=None,
            sanitized_filename=sanitized,
            sheet_name=lazy.resolved_sheet,
            column_count=lazy.column_count,
            correlation_id=correlation_id,
        )
        sp.commit()
        savepoint_committed = True
        db.commit()
        return batch

    except ParseError as pe:
        sp.rollback()
        try:
            record_failure_audit(
                db=db,
                org_id=org_id,
                batch_id=batch_id,
                actor_id=current_user.id,
                sanitized_filename=sanitized,
                requested_sheet=pre_fingerprint["source_sheet_name"],
                error_code=pe.error_code,
                limit_category=pe.limit_category,
                previous_row_count=previous_count,
                correlation_id=correlation_id,
            )
            db.commit()
        except Exception:
            db.rollback()
            _recover_commit_failure(
                db=db,
                org_id=org_id,
                batch_id=batch_id,
                actor_id=current_user.id,
                sanitized_filename=sanitized,
                pre_fingerprint=pre_fingerprint,
                previous_count=previous_count,
                correlation_id=correlation_id,
                error_code=pe.error_code,
                limit_category=pe.limit_category,
            )
        raise HTTPException(status_code=pe.status, detail=pe.detail)

    except Exception:
        if not savepoint_committed:
            sp.rollback()
            try:
                record_failure_audit(
                    db=db,
                    org_id=org_id,
                    batch_id=batch_id,
                    actor_id=current_user.id,
                    sanitized_filename=sanitized,
                    requested_sheet=pre_fingerprint["source_sheet_name"],
                    error_code="unexpected_error",
                    limit_category=None,
                    previous_row_count=previous_count,
                    correlation_id=correlation_id,
                )
                db.commit()
            except Exception:
                db.rollback()
                _recover_commit_failure(
                    db=db,
                    org_id=org_id,
                    batch_id=batch_id,
                    actor_id=current_user.id,
                    sanitized_filename=sanitized,
                    pre_fingerprint=pre_fingerprint,
                    previous_count=previous_count,
                    correlation_id=correlation_id,
                    error_code="unexpected_error",
                    limit_category=None,
                )
        else:
            db.rollback()
            _recover_commit_failure(
                db=db,
                org_id=org_id,
                batch_id=batch_id,
                actor_id=current_user.id,
                sanitized_filename=sanitized,
                pre_fingerprint=pre_fingerprint,
                previous_count=previous_count,
                correlation_id=correlation_id,
                error_code="commit_failure",
                limit_category=None,
            )
        raise HTTPException(status_code=500, detail="Lỗi hệ thống khi xử lý tệp Excel.")


def _recover_commit_failure(
    db: Session,
    org_id: uuid.UUID,
    batch_id: uuid.UUID,
    actor_id: uuid.UUID,
    sanitized_filename: str,
    pre_fingerprint: dict,
    previous_count: int,
    correlation_id: str | None,
    error_code: str,
    limit_category: str | None,
) -> None:
    try:
        db.expire_all()
        locked = db.query(ProjectAssetImportBatch).filter(
            ProjectAssetImportBatch.organization_id == org_id,
            ProjectAssetImportBatch.id == batch_id
        ).with_for_update().first()
        if locked:
            current = _build_pre_fingerprint(db, locked)
            if current == pre_fingerprint:
                record_failure_audit(
                    db=db,
                    org_id=org_id,
                    batch_id=batch_id,
                    actor_id=actor_id,
                    sanitized_filename=sanitized_filename,
                    requested_sheet=pre_fingerprint["source_sheet_name"],
                    error_code=error_code,
                    limit_category=limit_category,
                    previous_row_count=previous_count,
                    correlation_id=correlation_id,
                )
                db.commit()
            else:
                db.rollback()
    except Exception:
        db.rollback()
