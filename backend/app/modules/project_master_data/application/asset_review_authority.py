"""One authority envelope for snapshot reads and Project-serialized mutation CAS."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.modules.excel_import.application.mapping_authority import authority_slot
from app.modules.excel_import.models import ColumnMappingProfileUsage, ColumnMappingDecision, WorkbookStructureSnapshot
from app.modules.project_master_data.models import (
    AuditEvent, Project, ProjectAssetImportStagingRow, ProjectAssetLine,
    ProjectAssetReviewSeal, ValidationIssue,
    PreliminaryResultArtifact,
)

CONTRACT_VERSION = "s12-post-intake-guarded-apply-v2"
CASE_CONTRACT = "global-case-state-v3-asset-review-line-decision-v1"
REGISTERED_INPUTS = ("proposed_asset_name", "proposed_description", "proposed_quantity",
                     "proposed_unit", "proposed_raw_price", "proposed_currency")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def materialized_inputs(rows) -> list[dict]:
    return [{"id": str(r.id), "organization_id": str(r.organization_id),
             "project_id": str(r.project_id), "batch_id": str(r.import_batch_id),
             "source_row_number": r.source_row_number,
             "inputs": {key: getattr(r, key) for key in REGISTERED_INPUTS},
             "raw_values": r.raw_values, "mapped_values": r.mapped_values}
            for r in sorted(rows, key=lambda r: (r.source_row_number, str(r.id)))]


def membership_digest(correspondence: list[dict]) -> str:
    return canonical_digest(correspondence)


def compute_case_version(*, org_id, project_id, facts):
    ordered = sorted(facts)
    return canonical_digest({"contract": CASE_CONTRACT, "facts": ordered,
        "organization_id": str(org_id).lower(), "project_id": str(project_id).lower()}), ordered


@dataclass
class AuthoritySnapshot:
    project: Any
    prefix: list
    batch: Any
    source: Any
    analysis: Any
    result: Any
    intake: Any
    slot: Any
    usage: Any
    rows: list
    lines: list
    issues: list
    seal: Any
    lineage_current: bool
    seal_current: bool
    stale: list[str]
    entry_manifest: dict
    case_version: str
    facts: list[str]
    line_proofs: dict = field(default_factory=dict)
    references: dict = field(default_factory=dict)


def lock_project(db, *, org_id, project_id):
    project = (db.query(Project).filter(Project.id == project_id,
               Project.organization_id == org_id).populate_existing().with_for_update().first())
    if project is None:
        raise HTTPException(404, detail="Project not found")
    return project


def require_mutation_actor(db, *, actor, org_id, permission="workbench:edit"):
    from sqlalchemy.orm import selectinload
    from app.core.rbac import derive_effective_permissions
    from app.modules.project_master_data.models import User, UserRole, OrganizationProfile
    persisted = db.query(User).options(selectinload(User.roles).selectinload(UserRole.role)).filter(
        User.id == actor.id, User.organization_id == org_id).populate_existing().first()
    organization = db.query(OrganizationProfile).filter(OrganizationProfile.id == org_id).populate_existing().first()
    if (not persisted or not organization
            or str(getattr(persisted.status, "value", persisted.status)) != "active"
            or str(getattr(organization.status, "value", organization.status)) != "active"
            or permission not in derive_effective_permissions(persisted, db)):
        raise HTTPException(403, detail="Permission required")
    return persisted


def resolve_authority(db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID,
                      locked: bool = False) -> AuthoritySnapshot:
    # Imports are local so prefix providers can consume this same resolver.
    from app.modules.project_master_data.application.case_state_projection import (
        ProjectionIntegrityError, evaluate_preliminary_request_provider,
        evaluate_preliminary_analysis_provider, evaluate_preliminary_ready_provider,
        evaluate_official_intake_provider,
    )
    if not locked and db.get_bind().dialect.name == "postgresql":
        if db.connection().get_isolation_level() not in ("REPEATABLE READ", "SERIALIZABLE"):
            raise ProjectionIntegrityError("Case State requires a caller-owned consistent snapshot")
    with db.no_autoflush:
        project = (db.query(Project).filter(Project.id == project_id,
                   Project.organization_id == org_id).populate_existing().first())
        if project is None:
            raise HTTPException(404, detail="Project not found")
        request = evaluate_preliminary_request_provider(db, org_id=org_id, project_id=project_id)
        analysis_provider = evaluate_preliminary_analysis_provider(db, org_id=org_id,
            project_id=project_id, req_provider_result=request)
        result_provider = evaluate_preliminary_ready_provider(db, org_id=org_id,
            project_id=project_id, analysis_provider_result=analysis_provider)
        intake_provider = evaluate_official_intake_provider(db, org_id=org_id, project_id=project_id)
        prefix = [request, analysis_provider, result_provider, intake_provider]
        intake = intake_provider.authoritative_entity
        result = result_provider.authoritative_entity
        analysis = analysis_provider.authoritative_entity
        current_result, current_analysis = result, analysis
        if intake:
            result = db.query(PreliminaryResultArtifact).filter(
                PreliminaryResultArtifact.id == intake.preliminary_result_artifact_id,
                PreliminaryResultArtifact.organization_id == org_id,
                PreliminaryResultArtifact.project_id == project_id).populate_existing().first()
            if result is None:
                raise ProjectionIntegrityError("Intake Result is outside Project scope")
            from app.modules.project_master_data.application.preliminary_result_currentness import (
                _validated_analysis, CurrentResultCorruption,
            )
            try:
                analysis = _validated_analysis(db, result=result, manifest=result.lineage_manifest,
                    org_id=org_id, project_id=project_id)
            except CurrentResultCorruption as exc:
                raise ProjectionIntegrityError("Committed Result analysis integrity failed") from exc
        from app.modules.project_master_data.application.preliminary_analysis_currentness import (
            current_batch, current_source, CurrentBatchUnresolved,
        )
        try:
            batch = current_batch(db, org_id=org_id, project_id=project_id)
            source = current_source(db, org_id=org_id, project_id=project_id, batch=batch) if batch else None
        except CurrentBatchUnresolved:
            batch = source = None
        if locked and batch is not None:
            from app.modules.project_master_data.models import ProjectAssetImportBatch
            batch = db.query(ProjectAssetImportBatch).filter_by(
                id=batch.id, organization_id=org_id, project_id=project_id
            ).populate_existing().with_for_update().one()
        slot = authority_slot(db, org_id=org_id, project_id=project_id)
        usage = None
        if slot and slot.current_staging_usage_id:
            usage = db.query(ColumnMappingProfileUsage).filter(
                ColumnMappingProfileUsage.id == slot.current_staging_usage_id,
                ColumnMappingProfileUsage.organization_id == org_id,
                ColumnMappingProfileUsage.project_id == project_id).populate_existing().first()
            if usage is None:
                raise ProjectionIntegrityError("Current staging usage is outside Project scope")
        decision = structure = None
        if usage:
            decision = db.query(ColumnMappingDecision).filter(ColumnMappingDecision.id == usage.confirmation_decision_id,
                ColumnMappingDecision.organization_id == org_id, ColumnMappingDecision.project_id == project_id).populate_existing().first()
            structure = db.query(WorkbookStructureSnapshot).filter(WorkbookStructureSnapshot.id == usage.structure_snapshot_id,
                WorkbookStructureSnapshot.organization_id == org_id, WorkbookStructureSnapshot.project_id == project_id).populate_existing().first()
            if not decision or not structure:
                raise ProjectionIntegrityError("Selected materialization has cross-scoped lineage")
        rows_query = db.query(ProjectAssetImportStagingRow).filter(
            ProjectAssetImportStagingRow.organization_id == org_id,
            ProjectAssetImportStagingRow.project_id == project_id,
            ProjectAssetImportStagingRow.import_batch_id == (batch.id if batch else None)
        ).order_by(ProjectAssetImportStagingRow.source_row_number, ProjectAssetImportStagingRow.id).populate_existing()
        lines_query = db.query(ProjectAssetLine).filter(ProjectAssetLine.project_id == project_id).order_by(
            ProjectAssetLine.id).populate_existing()
        if locked:
            rows_query = rows_query.with_for_update()
            lines_query = lines_query.with_for_update()
        rows, lines = rows_query.all(), lines_query.all()
        from app.modules.project_master_data.application.asset_line_proofs import (
            load_references, resolve_line_proofs,
        )
        references = load_references(db, lines, locked=locked)
        line_ids = [line.id for line in lines]
        issues = db.query(ValidationIssue).filter(
            or_(and_(ValidationIssue.target_type.in_(("project", "Project")),
                     ValidationIssue.target_id == project_id),
                and_(ValidationIssue.target_type.in_(("project_asset_line", "ProjectAssetLine")),
                     ValidationIssue.target_id.in_(line_ids)))
        ).order_by(ValidationIssue.id).populate_existing().all()
        seals = db.query(ProjectAssetReviewSeal).filter(ProjectAssetReviewSeal.organization_id == org_id,
            ProjectAssetReviewSeal.project_id == project_id).populate_existing().all()
        if len(seals) > 1:
            raise ProjectionIntegrityError("Duplicate initial authoritative set")
        seal = seals[0] if seals else None
        inputs_digest = canonical_digest(materialized_inputs(rows))
        stale = []
        lineage_current = bool(intake and result and analysis and batch and source and usage and slot)
        if lineage_current:
            lineage_current = bool(
                current_result and current_analysis
                and current_result.id == result.id and current_analysis.id == analysis.id
                and intake.preliminary_result_artifact_id == result.id
                and intake.preliminary_result_version == result.version
                and intake.preliminary_result_sha256 == result.content_checksum_sha256
                and intake.source_snapshot_sha256 == result.source_snapshot_sha256
                and slot.selected_usage_id == usage.id
                and slot.current_staging_usage_id == usage.id
                and slot.confirmation_decision_id == usage.confirmation_decision_id
                and analysis.mapping_profile_usage_id == usage.id
                and usage.import_batch_id == batch.id and usage.source_artifact_id == source.id
                and inputs_digest == usage.materialized_input_sha256)
        if intake and not lineage_current:
            stale.append("lineage_mismatch")
        if analysis and (len(rows) != len(analysis.line_manifest)
                or {r.source_row_number for r in rows} != {r["source_row_number"] for r in analysis.line_manifest}
                or len({r.source_row_number for r in rows}) != len(rows)):
            lineage_current = False
            stale.append("selection_mismatch")
        manifest = {
            "intake_id": str(intake.id) if intake else None,
            "result_id": str(result.id) if result else None,
            "result_sha256": result.content_checksum_sha256 if result else None,
            "result_manifest_sha256": canonical_digest(result.lineage_manifest) if result else None,
            "source_snapshot_sha256": result.source_snapshot_sha256 if result else None,
            "analysis_id": str(analysis.id) if analysis else None,
            "analysis_digest_sha256": analysis.line_manifest_digest_sha256 if analysis else None,
            "result_version": result.version if result else None,
            "intake_version": intake.preliminary_result_version if intake else None,
            "batch_id": str(batch.id) if batch else None,
            "source_id": str(source.id) if source else None,
            "usage_id": str(usage.id) if usage else None,
            "mapping_id": str(usage.confirmation_decision_id) if usage else None,
            "structure_id": str(usage.structure_snapshot_id) if usage else None,
            "materialized_input_sha256": inputs_digest,
        }
        expected_correspondence = [{"staging_row_id": str(r.id), "source_row_number": r.source_row_number,
            "line_id": str(next((line.id for line in lines if line.source_staging_row_id == r.id), ""))}
            for r in rows]
        seal_current = bool(seal and lineage_current and seal.lineage_manifest == manifest
            and seal.official_intake_commit_id == intake.id and seal.preliminary_result_artifact_id == result.id
            and seal.import_batch_id == batch.id and seal.source_artifact_id == source.id
            and seal.structure_snapshot_id == usage.structure_snapshot_id
            and seal.mapping_decision_id == usage.confirmation_decision_id and seal.staging_usage_id == usage.id
            and seal.entry_lineage_sha256 == canonical_digest(manifest)
            and seal.correspondence == expected_correspondence
            and len(lines) == len(rows) and len(rows) > 0
            and all(line.source_import_batch_id == batch.id for line in lines)
            and seal.authoritative_set_sha256 == membership_digest(expected_correspondence)
            and seal.membership_version == 1 and seal.contract_version == CONTRACT_VERSION)
        if intake and batch and str(getattr(batch.status, "value", batch.status)) == "applied" and not seal_current:
            stale.append("seal_mismatch")
        line_proofs, proof_facts = resolve_line_proofs(db, org_id=org_id,
            project_id=project_id, lines=lines, references=references,
            seal=seal, seal_current=seal_current)
        generation = []
        if batch:
            generation = [str(a.id) for a in db.query(AuditEvent).filter(
                AuditEvent.organization_id == org_id, AuditEvent.entity_id == batch.id,
                AuditEvent.event_name.in_(("ProjectAssetImportBatchValidationSucceeded",
                                          "ProjectAssetImportBatchApplied")))
                .order_by(AuditEvent.id).all()]
        added = {
            "project": {"row_version": project.row_version, "status": str(getattr(project.status, "value", project.status)),
                        "current_batch": str(project.current_preliminary_import_batch_id) if project.current_preliminary_import_batch_id else None},
            "entry": manifest,
            "current_selection": {"revision": slot.selection_revision,
                "confirmation": str(slot.confirmation_decision_id) if slot.confirmation_decision_id else None,
                "selected_usage": str(slot.selected_usage_id) if slot.selected_usage_id else None,
                "current_usage": str(slot.current_staging_usage_id) if slot.current_staging_usage_id else None} if slot else None,
            "usage": {"id": str(usage.id), "mapping_digest": usage.mapping_digest_sha256,
                "mapping_snapshot": canonical_digest(usage.mapping_snapshot),
                "input_sha256": usage.materialized_input_sha256, "source_checksum": usage.source_checksum_sha256,
                "structure_digest": usage.structure_digest_sha256, "row_count": usage.materialized_asset_row_count} if usage else None,
            "mapping": {"id": str(decision.id), "digest": decision.mapping_digest_sha256,
                "snapshot_digest": canonical_digest(decision.mapping_snapshot), "outcome": decision.outcome} if decision else None,
            "structure": {"id": str(structure.id), "digest": structure.analysis_digest_sha256,
                "source_checksum": structure.source_checksum_sha256} if structure else None,
            "batch": {"id": str(batch.id), "status": str(getattr(batch.status,"value",batch.status)),
                "counters": [batch.total_rows, batch.valid_rows, batch.invalid_rows, batch.warning_rows],
                "generation": generation} if batch else None,
            "rows": [{"id": str(r.id), "inputs_sha256": canonical_digest(materialized_inputs([r])),
                "validation_status": str(getattr(r.validation_status,"value",r.validation_status)),
                "errors": r.validation_errors, "warnings": r.validation_warnings} for r in rows],
            "lines": [{"id": str(line.id), "row_version": line.row_version,
                "review_status": str(getattr(line.review_status,"value",line.review_status)),
                "validation_status": str(getattr(line.validation_status,"value",line.validation_status)),
                "batch_id": str(line.source_import_batch_id) if line.source_import_batch_id else None,
                "row_id": str(line.source_staging_row_id) if line.source_staging_row_id else None} for line in lines],
            "seal": {"id": str(seal.id), "membership_version": seal.membership_version,
                "entry": seal.entry_lineage_sha256, "set": seal.authoritative_set_sha256,
                "correspondence": seal.correspondence, "manifest": canonical_digest(seal.lineage_manifest),
                "binding": [str(getattr(seal, field)) for field in ("official_intake_commit_id", "preliminary_result_artifact_id",
                    "import_batch_id", "source_artifact_id", "structure_snapshot_id", "mapping_decision_id", "staging_usage_id")],
                "contract": seal.contract_version} if seal else None,
            "issues": [{"id": str(i.id), "row_version": i.row_version, "target_type": i.target_type,
                "target_id": str(i.target_id), "severity": str(getattr(i.severity,"value",i.severity)),
                "status": str(getattr(i.status,"value",i.status))} for i in issues],
            "conflicts": sorted(set(stale)),
            "line_decision_authority": proof_facts,
        }
        facts = sorted([p.fact_token for p in prefix] + ["asset_review_authority_v1:" + canonical_digest(added)])
        case_version, facts = compute_case_version(org_id=org_id, project_id=project_id, facts=facts)
        return AuthoritySnapshot(project, prefix, batch, source, analysis, result, intake, slot,
            usage, rows, lines, issues, seal, lineage_current, seal_current,
            sorted(set(stale)), manifest, case_version, facts, line_proofs, references)
