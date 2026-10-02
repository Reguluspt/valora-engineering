"""Real preliminary lifecycle fixtures for the guarded Asset Review entry."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.modules.excel_import.application.column_mapping_service import (
    confirm_column_mapping,
    materialize_confirmed_mapping_to_staging,
)
from app.modules.excel_import.application.mapping_authority import authority_slot
from app.modules.excel_import.infrastructure.object_storage import FakeObjectStorage
from app.modules.project_master_data.application.official_intake_service import (
    commit_project_official_intake,
)
from app.modules.project_master_data.application.preliminary_analysis_service import (
    finalize_preliminary_analysis,
)
from app.modules.project_master_data.application.preliminary_result_service import (
    generate_preliminary_result_artifact,
)
from app.modules.project_master_data.models import (
    ProjectAssetImportStagingRow, ReferenceStatus, Role, Unit, UserRole,
)
from tests.test_s13_pr_004_column_mapping import _propose, _seed


def seed_guarded_entry(db: Session, storage=None) -> dict:
    """Commit mapping, analysis, result, and Intake facts while retaining staging rows."""
    if storage is None:
        storage = FakeObjectStorage()
    seeded = _seed(db, storage=storage)
    org, user, project, batch = (
        seeded["org"], seeded["user"], seeded["project"], seeded["batch"]
    )
    role = Role(
        code=f"g2-asset-review-{uuid.uuid4().hex[:8]}",
        display_name="Guarded Asset Review fixture",
        permissions=[
            "project:read",
            "workbench:edit",
            "project:preliminary_analysis:finalize",
            "project:preliminary_result:generate",
            "project:official_intake:commit",
        ],
    )
    db.add(role)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))
    db.commit()

    proposal = _propose(db, seeded).decision
    slot = authority_slot(db, org_id=org.id, project_id=project.id)
    decision = confirm_column_mapping(
        db,
        actor=user,
        org_id=org.id,
        project_id=project.id,
        batch_id=batch.id,
        proposal_decision_id=proposal.id,
        mapping_snapshot=proposal.mapping_snapshot,
        memory_scope="none",
        command_id=uuid.uuid4(),
        expected_selection_revision=slot.selection_revision if slot is not None else 0,
    )
    slot = authority_slot(db, org_id=org.id, project_id=project.id)
    assert slot is not None
    usage = materialize_confirmed_mapping_to_staging(
        db,
        actor=user,
        org_id=org.id,
        project_id=project.id,
        batch_id=batch.id,
        confirmation_decision_id=decision.id,
        command_id=uuid.uuid4(),
        expected_selection_revision=slot.selection_revision,
        storage=storage,
    )
    rows = (
        db.query(ProjectAssetImportStagingRow)
        .filter_by(organization_id=org.id, project_id=project.id, import_batch_id=batch.id)
        .order_by(ProjectAssetImportStagingRow.source_row_number)
        .all()
    )
    unit_name = rows[0].proposed_unit
    if db.query(Unit).filter_by(display_name=unit_name, status=ReferenceStatus.ACTIVE).first() is None:
        db.add(Unit(code="testunit", display_name=unit_name, status=ReferenceStatus.ACTIVE))
        db.commit()
    line_manifest = [
        {
            "identity": row.proposed_asset_name,
            "accepted_price_basis": "Human confirmed fixture reference price",
            "confirmed_reference_price": 100.0,
            "transport_percentage": 0.0,
            "proposed_unit_price": 100.0,
            "human_line_confirmed": True,
            "has_unresolved_blocking_line": False,
            "source_row_number": row.source_row_number,
            "quantity": float(row.proposed_quantity),
        }
        for row in rows
    ]
    analysis = finalize_preliminary_analysis(
        db,
        actor=user,
        org_id=org.id,
        project_id=project.id,
        expected_project_version=project.row_version,
        import_batch_id=batch.id,
        source_artifact_id=seeded["artifact"].id,
        structure_snapshot_id=seeded["snapshot"].id,
        mapping_decision_id=decision.id,
        mapping_profile_usage_id=usage.id,
        mapping_decision_digest_sha256=decision.mapping_digest_sha256,
        profile_usage_mapping_digest_sha256=usage.mapping_digest_sha256,
        line_manifest=line_manifest,
        idempotency_key=f"g2-analysis-{uuid.uuid4()}",
        confirmed=True,
    )
    with patch(
        "app.modules.project_master_data.application.preliminary_result_service.get_object_storage",
        return_value=storage,
    ):
        result = generate_preliminary_result_artifact(
            db,
            actor=user,
            org_id=org.id,
            project_id=project.id,
            preliminary_analysis_snapshot_id=analysis.id,
            expected_project_version=project.row_version,
            idempotency_key=f"g2-result-{uuid.uuid4()}",
            confirmed=True,
        )
    intake = commit_project_official_intake(
        db,
        actor=user,
        org_id=org.id,
        project_id=project.id,
        preliminary_result_artifact_id=result.id,
        expected_project_version=project.row_version,
        expected_preliminary_result_version=result.version,
        idempotency_key=f"g2-intake-{uuid.uuid4()}",
        confirmed=True,
    )
    return {
        "org": org,
        "user": user,
        "customer": seeded["customer"],
        "role": role,
        "project": project,
        "batch": batch,
        "source": seeded["artifact"],
        "structure": seeded["snapshot"],
        "decision": decision,
        "usage": usage,
        "analysis": analysis,
        "result": result,
        "intake": intake,
        "staging_rows": rows,
        "storage": storage,
    }
