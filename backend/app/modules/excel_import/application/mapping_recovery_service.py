"""Tenant-scoped recovery projection of explicit Column Mapping authority."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.excel_import.application.column_mapping_service import (
    _reload_active_actor_and_org, _verify_decision_snapshot,
)
from app.modules.excel_import.application.mapping_authority import authority_slot
from app.modules.excel_import.application.workbook_structure_service import _verify_snapshot_page
from app.modules.excel_import.models import (
    ColumnMappingDecision, ColumnMappingProfileUsage, ImportSourceArtifact,
    ImportSourceArtifactState,
    WorkbookStructureSnapshot,
)
from app.modules.project_master_data.models import (
    Project, ProjectAssetImportBatch, ProjectOfficialIntakeCommit, User,
)


def get_mapping_recovery_state(
    db: Session, *, actor: User, org_id: uuid.UUID,
    project_id: uuid.UUID, batch_id: uuid.UUID,
) -> dict:
    _reload_active_actor_and_org(db, actor=actor, org_id=org_id)
    project = db.query(Project).filter(
        Project.organization_id == org_id, Project.id == project_id,
    ).first()
    batch = db.query(ProjectAssetImportBatch).filter(
        ProjectAssetImportBatch.organization_id == org_id,
        ProjectAssetImportBatch.project_id == project_id,
        ProjectAssetImportBatch.id == batch_id,
    ).first()
    if project is None or batch is None:
        raise HTTPException(status_code=404, detail="Import batch not found")
    current_batch_id = project.current_preliminary_import_batch_id
    current_source_id = batch.current_source_artifact_id if current_batch_id == batch_id else None
    closed = db.query(ProjectOfficialIntakeCommit.id).filter(
        ProjectOfficialIntakeCommit.organization_id == org_id,
        ProjectOfficialIntakeCommit.project_id == project_id,
    ).first() is not None
    slot = authority_slot(db, org_id=org_id, project_id=project_id)
    result = {
        "project_id": project_id, "batch_id": batch_id,
        "current_batch_id": current_batch_id,
        "current_source_artifact_id": current_source_id,
        "selection_revision": slot.selection_revision if slot else 0,
        "status": "no_selection", "official_intake_closed": closed,
        "selected_confirmation_decision_id": None,
        "selected_structure_snapshot_id": None,
        "selected_source_artifact_id": None,
        "selected_candidate": None, "mapping_snapshot": None,
        "mapping_digest_sha256": None, "memory_scope": None, "profile_id": None,
        "selected_command_id": None, "selected_outcome": None,
        "selected_usage_id": None,
        "current_staging_usage_id": None,
        "materialized_asset_row_count": None,
        "materialized_mapping_digest_sha256": None,
        "recent_proposals": [],
    }
    if current_batch_id != batch_id:
        result["status"] = "stale_lineage"
        return result
    # Ordering bounds the UI history only. It never chooses authority.
    proposals = db.query(ColumnMappingDecision).filter(
        ColumnMappingDecision.organization_id == org_id,
        ColumnMappingDecision.project_id == project_id,
        ColumnMappingDecision.import_batch_id == batch_id,
        ColumnMappingDecision.source_artifact_id == current_source_id,
        ColumnMappingDecision.decision_kind == "proposal",
    ).order_by(ColumnMappingDecision.created_at.desc(), ColumnMappingDecision.id.desc()).limit(25).all()
    result["recent_proposals"] = [
        {
            "proposal_decision_id": proposal.id,
            "source_artifact_id": proposal.source_artifact_id,
            "structure_snapshot_id": proposal.structure_snapshot_id,
            "command_id": proposal.command_id,
            "terminal_outcomes": [
                {"decision_id": terminal.id, "command_id": terminal.command_id,
                 "outcome": terminal.outcome}
                for terminal in db.query(ColumnMappingDecision).filter(
                    ColumnMappingDecision.organization_id == org_id,
                    ColumnMappingDecision.project_id == project_id,
                    ColumnMappingDecision.proposal_decision_id == proposal.id,
                    ColumnMappingDecision.decision_kind.in_(("confirmation", "rejection")),
                ).order_by(ColumnMappingDecision.created_at.desc(), ColumnMappingDecision.id.desc()).limit(8).all()
            ],
        }
        for proposal in proposals
    ]
    if slot is None or slot.confirmation_decision_id is None:
        historical_decision = db.query(ColumnMappingDecision.id).filter(
            ColumnMappingDecision.organization_id == org_id,
            ColumnMappingDecision.project_id == project_id,
            ColumnMappingDecision.import_batch_id == batch_id,
            ColumnMappingDecision.source_artifact_id == current_source_id,
            ColumnMappingDecision.decision_kind == "confirmation",
        ).first()
        historical_usage = db.query(ColumnMappingProfileUsage.id).filter(
            ColumnMappingProfileUsage.organization_id == org_id,
            ColumnMappingProfileUsage.project_id == project_id,
            ColumnMappingProfileUsage.import_batch_id == batch_id,
            ColumnMappingProfileUsage.source_artifact_id == current_source_id,
        ).first()
        if historical_decision is not None or historical_usage is not None:
            result["status"] = "unresolved_legacy_history"
        return result
    result["selected_confirmation_decision_id"] = slot.confirmation_decision_id
    result["selected_structure_snapshot_id"] = slot.structure_snapshot_id
    result["selected_source_artifact_id"] = slot.source_artifact_id
    if slot.import_batch_id != batch_id or slot.source_artifact_id != current_source_id:
        result["status"] = "stale_lineage"
        return result
    decision = db.query(ColumnMappingDecision).filter(
        ColumnMappingDecision.organization_id == org_id,
        ColumnMappingDecision.project_id == project_id,
        ColumnMappingDecision.import_batch_id == batch_id,
        ColumnMappingDecision.source_artifact_id == slot.source_artifact_id,
        ColumnMappingDecision.structure_snapshot_id == slot.structure_snapshot_id,
        ColumnMappingDecision.id == slot.confirmation_decision_id,
        ColumnMappingDecision.decision_kind == "confirmation",
        ColumnMappingDecision.outcome.in_(("accepted", "corrected")),
        ColumnMappingDecision.proposal_source_kind == "human",
    ).first()
    source = db.query(ImportSourceArtifact).filter(
        ImportSourceArtifact.organization_id == org_id,
        ImportSourceArtifact.project_id == project_id,
        ImportSourceArtifact.import_batch_id == batch_id,
        ImportSourceArtifact.id == current_source_id,
    ).first()
    structure = db.query(WorkbookStructureSnapshot).filter(
        WorkbookStructureSnapshot.organization_id == org_id,
        WorkbookStructureSnapshot.project_id == project_id,
        WorkbookStructureSnapshot.import_batch_id == batch_id,
        WorkbookStructureSnapshot.source_artifact_id == current_source_id,
        WorkbookStructureSnapshot.id == slot.structure_snapshot_id,
    ).first()
    if decision is None or source is None or structure is None or (
        source.state != ImportSourceArtifactState.AVAILABLE.value
    ) or (
        structure.source_checksum_sha256 != source.checksum_sha256
    ):
        result["status"] = "stale_lineage"
        return result
    sealed = decision.mapping_snapshot if isinstance(decision.mapping_snapshot, dict) else {}
    source_seal = sealed.get("source") if isinstance(sealed.get("source"), dict) else {}
    structure_seal = sealed.get("structure") if isinstance(sealed.get("structure"), dict) else {}
    if (
        source_seal.get("source_artifact_id") != str(source.id)
        or source_seal.get("generation") != source.generation
        or source_seal.get("checksum_sha256") != source.checksum_sha256
        or structure_seal.get("structure_snapshot_id") != str(structure.id)
        or structure_seal.get("snapshot_version") != structure.snapshot_version
        or structure_seal.get("rule_version") != structure.rule_version
        or structure_seal.get("analysis_digest_sha256") != structure.analysis_digest_sha256
    ):
        result["status"] = "stale_lineage"
        return result
    try:
        _verify_snapshot_page(db, [structure], source)
        _verify_decision_snapshot(decision)
    except HTTPException:
        result["status"] = "stale_lineage"
        return result
    result.update({
        "selected_candidate": decision.mapping_snapshot.get("candidate"),
        "mapping_snapshot": decision.mapping_snapshot,
        "mapping_digest_sha256": decision.mapping_digest_sha256,
        "memory_scope": decision.memory_scope, "profile_id": decision.profile_id,
        "selected_command_id": decision.command_id, "selected_outcome": decision.outcome,
    })
    if slot.selected_usage_id is None:
        result["current_staging_usage_id"] = slot.current_staging_usage_id
        occupied = db.query(ColumnMappingProfileUsage.id).filter(
            ColumnMappingProfileUsage.organization_id == org_id,
            ColumnMappingProfileUsage.project_id == project_id,
            ColumnMappingProfileUsage.import_batch_id == batch_id,
            ColumnMappingProfileUsage.source_artifact_id == current_source_id,
            ColumnMappingProfileUsage.structure_snapshot_id == slot.structure_snapshot_id,
        ).first()
        result["status"] = "selected_recovery_required" if occupied else "selected_unmaterialized"
        return result
    usage = db.query(ColumnMappingProfileUsage).filter(
        ColumnMappingProfileUsage.organization_id == org_id,
        ColumnMappingProfileUsage.project_id == project_id,
        ColumnMappingProfileUsage.import_batch_id == batch_id,
        ColumnMappingProfileUsage.source_artifact_id == current_source_id,
        ColumnMappingProfileUsage.structure_snapshot_id == slot.structure_snapshot_id,
        ColumnMappingProfileUsage.id == slot.selected_usage_id,
    ).first()
    if (
        usage is None or slot.current_staging_usage_id != slot.selected_usage_id
        or usage.confirmation_decision_id != decision.id
        or usage.mapping_digest_sha256 != decision.mapping_digest_sha256
        or usage.source_checksum_sha256 != source.checksum_sha256
        or usage.structure_digest_sha256 != structure.analysis_digest_sha256
    ):
        result["status"] = "stale_lineage"
        return result
    result["status"] = "materialized"
    result["selected_usage_id"] = slot.selected_usage_id
    result["current_staging_usage_id"] = slot.current_staging_usage_id
    result["materialized_asset_row_count"] = usage.materialized_asset_row_count
    result["materialized_mapping_digest_sha256"] = usage.mapping_digest_sha256
    return result
