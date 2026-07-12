import uuid
from fastapi import UploadFile, Request, HTTPException
from sqlalchemy.orm import Session

from app.modules.project_master_data.models import (
    ProjectAssetImportBatch, ProjectAssetImportStagingRow, ImportBatchStatus
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
    batch = db.query(ProjectAssetImportBatch).filter(
        ProjectAssetImportBatch.organization_id == org_id,
        ProjectAssetImportBatch.project_id == project_id,
        ProjectAssetImportBatch.id == batch_id
    ).with_for_update().first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")

    previous_count = (
        db.query(ProjectAssetImportStagingRow)
        .filter(ProjectAssetImportStagingRow.import_batch_id == batch_id)
        .count()
    )

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
        if not savepoint_committed:
            sp.rollback()
        else:
            db.rollback()

        try:
            db.refresh(batch)
        except Exception:
            pass

        if getattr(batch, "status", None) != ImportBatchStatus.PARSED:
            record_failure_audit(
                db=db,
                org_id=org_id,
                batch_id=batch_id,
                actor_id=current_user.id,
                sanitized_filename=sanitized,
                requested_sheet=getattr(batch, "source_sheet_name", None),
                error_code=pe.error_code,
                limit_category=pe.limit_category,
                previous_row_count=previous_count,
                correlation_id=correlation_id,
            )
            db.commit()
        raise HTTPException(status_code=pe.status, detail=pe.detail)

    except Exception:
        if not savepoint_committed:
            sp.rollback()
        else:
            db.rollback()

        try:
            db.refresh(batch)
        except Exception:
            pass

        if getattr(batch, "status", None) != ImportBatchStatus.PARSED:
            record_failure_audit(
                db=db,
                org_id=org_id,
                batch_id=batch_id,
                actor_id=current_user.id,
                sanitized_filename=sanitized,
                requested_sheet=getattr(batch, "source_sheet_name", None),
                error_code="unexpected_error",
                limit_category=None,
                previous_row_count=previous_count,
                correlation_id=correlation_id,
            )
            db.commit()
        raise HTTPException(status_code=500, detail="Lỗi hệ thống khi xử lý tệp Excel.")
