"""Read-only, exact-fixture cardinality/correspondence proof after browser acceptance."""
import json
import sys
import uuid
from app.core.config import get_settings
from app.db import SessionLocal
import app.modules.excel_import.models
from app.modules.project_master_data.models import (
    AuditEvent, Project, ProjectAssetLine, ProjectAssetReviewSeal, ProjectAssetImportBatch,
)

assert get_settings().postgres_db == "valora_issue206"
fixtures = json.load(sys.stdin)
results = {}
with SessionLocal() as db:
    db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
    for name, fixture in fixtures.items():
        project_id = uuid.UUID(fixture["project_id"])
        project = db.query(Project).filter_by(id=project_id).one()
        lines = db.query(ProjectAssetLine).filter_by(project_id=project_id).all()
        seals = db.query(ProjectAssetReviewSeal).filter_by(project_id=project_id).all()
        batch = db.query(ProjectAssetImportBatch).filter_by(id=uuid.UUID(fixture["batch_id"])).one()
        success = db.query(AuditEvent).filter_by(entity_id=batch.id, event_name="ProjectAssetImportBatchApplied").count()
        failure = db.query(AuditEvent).filter_by(entity_id=batch.id, event_name="ProjectAssetImportBatchApplyFailed").count()
        expected = 3 if name in ("normal", "lost") else 0
        assert len(lines) == expected
        assert len(seals) == (1 if expected else 0)
        assert success == (1 if expected else 0) and failure == 0
        project_status = getattr(project.status, "value", project.status)
        assert project_status == "draft"
        assert all(line.appraised_unit_price is None for line in lines)
        if expected:
            assert getattr(batch.status, "value", batch.status) == "applied"
            seal = seals[0]
            assert seal.import_batch_id == batch.id and seal.membership_version == 1
            assert len(seal.correspondence) == expected
            assert {str(line.source_staging_row_id) for line in lines} == {pair["staging_row_id"] for pair in seal.correspondence}
            assert {str(line.id) for line in lines} == {pair["line_id"] for pair in seal.correspondence}
        results[name] = {"official_lines": len(lines), "seals": len(seals), "apply_success_audits": success,
                         "apply_failure_audits": failure, "project_status": project_status}
    db.rollback()
print(json.dumps(results, sort_keys=True))
