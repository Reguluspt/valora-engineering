import uuid
from sqlalchemy.orm import Session

from app.modules.project_master_data.models import (
    User,
    Project,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    ImportBatchStatus,
    ImportRowValidationStatus,
)
from app.core.audit import log_audit_event
from app.modules.excel_import.domain import DEFAULT_LIMITS, ExcelImportLimits


def replace_staging_rows(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    staged_rows: list[dict],
    raw_cells_list: list[list[dict]],
    parsed_count: int,
    sanitized_filename: str,
    sheet_name: str,
    column_count: int,
    limits: ExcelImportLimits | None = None,
    correlation_id: str | None = None,
) -> ProjectAssetImportBatch:
    limits = limits or DEFAULT_LIMITS

    # 1. Resolve and tenant-scope
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == org_id)
        .first()
    )
    if not project:
        raise ValueError("Project not found in organization scope")

    batch = (
        db.query(ProjectAssetImportBatch)
        .filter(
            ProjectAssetImportBatch.id == batch_id,
            ProjectAssetImportBatch.organization_id == org_id,
            ProjectAssetImportBatch.project_id == project_id,
        )
        .with_for_update()
        .first()
    )
    if not batch:
        raise ValueError("Import batch not found")

    # 2. Delete old staging + insert new + update batch ALL IN ONE TX
    db.query(ProjectAssetImportStagingRow).filter(
        ProjectAssetImportStagingRow.import_batch_id == batch_id
    ).delete()

    for item in staged_rows:
        staging = ProjectAssetImportStagingRow(
            organization_id=org_id,
            project_id=project_id,
            import_batch_id=batch_id,
            source_row_number=item["source_row_number"],
            raw_values={"cells": item["raw_cells"]},
            mapped_values=item["mapped_values"],
            normalized_preview={},
            validation_status=ImportRowValidationStatus.PENDING,
            validation_errors=[],
            validation_warnings=[],
            proposed_asset_name=item["proposed_asset_name"],
            proposed_description=item["proposed_description"],
            proposed_quantity=item["proposed_quantity"],
            proposed_unit=item["proposed_unit"],
            proposed_raw_price=item["proposed_raw_price"],
            proposed_currency=item["proposed_currency"],
            proposed_appraised_unit_price=item["proposed_appraised_unit_price"],
        )
        db.add(staging)

    batch.source_filename = sanitized_filename
    batch.source_sheet_name = sheet_name
    batch.status = ImportBatchStatus.PARSED
    batch.total_rows = parsed_count
    batch.valid_rows = 0
    batch.invalid_rows = 0
    batch.warning_rows = 0

    # 3. Success audit in same transaction
    log_audit_event(
        db=db,
        event_name="ProjectAssetImportBatchUploaded",
        entity_type="ProjectAssetImportBatch",
        entity_id=batch_id,
        organization_id=org_id,
        actor_user_id=actor.id,
        command_name="ReplaceStagingRows",
        correlation_id=correlation_id,
        payload={
            "filename": sanitized_filename,
            "sheet": sheet_name,
            "row_count": parsed_count,
            "column_count": column_count,
            "limit_policy": limits.limit_version,
            "replacement_mode": "full",
        },
    )

    db.flush()

    return batch


def record_failure_audit(
    db: Session,
    *,
    org_id: uuid.UUID,
    batch_id: uuid.UUID,
    actor_id: uuid.UUID,
    sanitized_filename: str,
    requested_sheet: str | None,
    error_code: str,
    limit_category: str | None = None,
    previous_row_count: int = 0,
    correlation_id: str | None = None,
) -> None:
    batch = (
        db.query(ProjectAssetImportBatch)
        .filter(
            ProjectAssetImportBatch.id == batch_id,
            ProjectAssetImportBatch.organization_id == org_id,
        )
        .first()
    )
    if not batch:
        return

    batch.status = ImportBatchStatus.FAILED

    log_audit_event(
        db=db,
        event_name="ProjectAssetImportBatchUploadFailed",
        entity_type="ProjectAssetImportBatch",
        entity_id=batch_id,
        organization_id=org_id,
        actor_user_id=actor_id,
        command_name="ReplaceStagingRows",
        correlation_id=correlation_id,
        payload={
            "filename": sanitized_filename,
            "sheet": requested_sheet,
            "error_code": error_code,
            "limit_category": limit_category,
            "previous_rows": previous_row_count,
        },
    )

    db.flush()
