"""Explicit persisted-validation fault, exclusively for the new disposable #206 negative fixture.

This does not claim that the real validator rejects the fixture's source values.
Never writes official lines, seals, permissions, immutable source, Intake or Result.
"""
import sys
import uuid
from app.core.config import get_settings
from app.db import SessionLocal
import app.modules.excel_import.models  # Register the fixture's complete mapping relationships.
from app.modules.project_master_data.models import (
    OrganizationProfile, Project, ProjectAssetImportBatch, ProjectAssetImportStagingRow,
    ImportRowValidationStatus, ImportBatchStatus,
)

assert get_settings().postgres_db == "valora_issue206"
with SessionLocal() as db:
    project = db.query(Project).filter_by(id=uuid.UUID(sys.argv[1])).one()
    org = db.query(OrganizationProfile).filter_by(id=project.organization_id).one()
    assert org.organization_slug.startswith("issue206-invalid")
    batch = db.query(ProjectAssetImportBatch).filter_by(id=project.current_preliminary_import_batch_id).one()
    assert batch.status == ImportBatchStatus.READY_FOR_REVIEW
    rows = db.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=batch.id).order_by(ProjectAssetImportStagingRow.source_row_number).all()
    rows[0].validation_status = ImportRowValidationStatus.INVALID
    rows[0].validation_errors = [{"field": "proposed_quantity", "message_key": "excel.validation.quantity_invalid", "message": "Số lượng không đúng định dạng số."}]
    batch.valid_rows = len(rows) - 1
    batch.invalid_rows = 1
    batch.warning_rows = 0
    db.commit()
print("disposable-validation-output-fault: installed")
