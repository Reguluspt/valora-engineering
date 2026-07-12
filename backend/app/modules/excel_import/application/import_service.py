import uuid
from fastapi import UploadFile, Request, HTTPException
from sqlalchemy.orm import Session

from app.modules.project_master_data.models import (
    ProjectAssetImportBatch, ProjectAssetImportStagingRow
)
from app.modules.excel_import.application.parse_workbook import (
    parse_workbook_lazy, ParseError, sanitize_filename, get_request_size, enforce_request_limit
)
from app.modules.excel_import.application.replace_staging_rows import (
    replace_staging_rows, record_failure_audit
)
from app.modules.excel_import.domain import DEFAULT_LIMITS

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
    # 1. Acquire pessimistic write lock
    batch = db.query(ProjectAssetImportBatch).filter(
        ProjectAssetImportBatch.organization_id == org_id,
        ProjectAssetImportBatch.project_id == project_id,
        ProjectAssetImportBatch.id == batch_id
    ).with_for_update().first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")

    # 2. Capture pre-operation fingerprint
    pre_fingerprint = {
        "status": batch.status,
        "source_filename": batch.source_filename,
        "source_sheet_name": batch.source_sheet_name,
        "total_rows": batch.total_rows,
    }

    previous_count = (
        db.query(ProjectAssetImportStagingRow)
        .filter(ProjectAssetImportStagingRow.import_batch_id == batch_id)
        .count()
    )

    sanitized = sanitize_filename(file.filename or "import.xlsx")

    sp = db.begin_nested()
    savepoint_committed = False
    post_fingerprint: dict | None = None
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
        # Capture post-savepoint fingerprint so the commit_failure recovery
        # path can detect concurrent writes that occurred after our savepoint
        # was released but before the outer commit succeeded.
        post_fingerprint = {
            "status": batch.status,
            "source_filename": batch.source_filename,
            "source_sheet_name": batch.source_sheet_name,
            "total_rows": batch.total_rows,
        }
        db.commit()
        return batch

    except ParseError as pe:
        # ParseError always happens before savepoint release; lock is still held.
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
                limit_category=pe.limit_category
            )
        raise HTTPException(status_code=pe.status, detail=pe.detail)

    except Exception:
        if not savepoint_committed:
            # Failure before savepoint release; lock is still held.
            sp.rollback()
            err_code = "unexpected_error"
            try:
                record_failure_audit(
                    db=db,
                    org_id=org_id,
                    batch_id=batch_id,
                    actor_id=current_user.id,
                    sanitized_filename=sanitized,
                    requested_sheet=pre_fingerprint["source_sheet_name"],
                    error_code=err_code,
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
                    error_code=err_code,
                    limit_category=None
                )
        else:
            # Savepoint was committed but outer commit failed. Lock is released.
            # Rollback outer transaction; do NOT call direct failure audit.
            db.rollback()
            err_code = "commit_failure"
            # Use the post-savepoint fingerprint as the concurrency guard: if
            # another session updated the batch during the rollback window the
            # fingerprint will differ and the recovery will safely abort.
            _recover_commit_failure(
                db=db,
                org_id=org_id,
                batch_id=batch_id,
                actor_id=current_user.id,
                sanitized_filename=sanitized,
                pre_fingerprint=post_fingerprint or pre_fingerprint,
                previous_count=previous_count,
                correlation_id=correlation_id,
                error_code=err_code,
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
    skip_fingerprint_guard: bool = False,
) -> None:
    """Attempt a best-effort failure audit after a commit error.

    When skip_fingerprint_guard is True the concurrency guard is bypassed.
    This is appropriate for the commit_failure path where the savepoint has
    already been released and the batch row already reflects the new state,
    so the pre-fingerprint no longer matches the current DB row.
    """
    try:
        db.expire_all()
        locked = db.query(ProjectAssetImportBatch).filter(
            ProjectAssetImportBatch.organization_id == org_id,
            ProjectAssetImportBatch.id == batch_id
        ).with_for_update().first()
        if locked:
            fingerprint_ok = skip_fingerprint_guard or {
                "status": locked.status,
                "source_filename": locked.source_filename,
                "source_sheet_name": locked.source_sheet_name,
                "total_rows": locked.total_rows,
            } == pre_fingerprint
            if fingerprint_ok:
                record_failure_audit(
                    db=db,
                    org_id=org_id,
                    batch_id=batch_id,
                    actor_id=actor_id,
                    sanitized_filename=sanitized_filename,
                    requested_sheet=(
                        locked.source_sheet_name
                        if skip_fingerprint_guard
                        else pre_fingerprint["source_sheet_name"]
                    ),
                    error_code=error_code,
                    limit_category=limit_category,
                    previous_row_count=previous_count,
                    correlation_id=correlation_id
                )
                db.commit()
            else:
                db.rollback()
    except Exception:
        db.rollback()

