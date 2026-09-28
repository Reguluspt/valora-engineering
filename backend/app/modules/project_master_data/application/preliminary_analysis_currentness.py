"""Read-only selection of the current preliminary batch and analysis snapshot."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Callable, Any

from sqlalchemy.orm import Session

from app.modules.excel_import.models import (
    ColumnMappingDecision,
    ColumnMappingDecisionKind,
    ColumnMappingDecisionOutcome,
    ColumnMappingProfileUsage,
    ColumnMappingProposalSourceKind,
    ImportSourceArtifact,
    ImportSourceArtifactState,
    WorkbookStructureSnapshot,
)
from app.modules.project_master_data.models import (
    PreliminaryAnalysisSnapshot,
    Project,
    ProjectAssetImportBatch,
)


class CurrentnessIntegrityError(Exception):
    """Current authority contains an impossible or corrupt lineage."""


class CurrentAnalysisCorruption(CurrentnessIntegrityError):
    """A stored current-lineage snapshot is invalid."""


class CurrentBatchUnresolved(CurrentnessIntegrityError):
    """Retained batches exist but no verified current-batch pointer exists."""

    def __init__(self, batch_ids: list[uuid.UUID]) -> None:
        self.batch_ids = tuple(sorted(str(batch_id).lower() for batch_id in batch_ids))
        super().__init__("Project has retained batches without current-batch authority.")


def current_batch(
    db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID
) -> ProjectAssetImportBatch | None:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == org_id)
        .first()
    )
    if project is None:
        raise CurrentnessIntegrityError("Project missing during currentness evaluation.")
    if project.current_preliminary_import_batch_id is None:
        retained_ids = (
            db.query(ProjectAssetImportBatch.id)
            .filter(
                ProjectAssetImportBatch.organization_id == org_id,
                ProjectAssetImportBatch.project_id == project_id,
            )
            .all()
        )
        if retained_ids:
            raise CurrentBatchUnresolved([row[0] for row in retained_ids])
        return None
    batch = (
        db.query(ProjectAssetImportBatch)
        .filter(
            ProjectAssetImportBatch.id == project.current_preliminary_import_batch_id,
            ProjectAssetImportBatch.organization_id == org_id,
            ProjectAssetImportBatch.project_id == project_id,
        )
        .first()
    )
    if batch is None:
        raise CurrentnessIntegrityError("Dangling or cross-lineage Project batch pointer.")
    return batch


def current_source(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    batch: ProjectAssetImportBatch,
) -> ImportSourceArtifact | None:
    if batch.current_source_artifact_id is None:
        return None
    source = (
        db.query(ImportSourceArtifact)
        .filter(
            ImportSourceArtifact.id == batch.current_source_artifact_id,
            ImportSourceArtifact.organization_id == org_id,
            ImportSourceArtifact.project_id == project_id,
        )
        .first()
    )
    if source is None or source.import_batch_id != batch.id:
        raise CurrentnessIntegrityError("Dangling or cross-lineage current source pointer.")
    return source


def select_current_analysis(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    valid_manifest: Callable[[Any], bool],
) -> PreliminaryAnalysisSnapshot | None:
    """Return highest valid lineage match; historical snapshots do not compete."""
    batch = current_batch(db, org_id=org_id, project_id=project_id)
    if batch is None:
        return None
    source = current_source(db, org_id=org_id, project_id=project_id, batch=batch)
    if (
        source is None
        or str(getattr(source.state, "value", source.state))
        != ImportSourceArtifactState.AVAILABLE.value
    ):
        return None
    snapshots = (
        db.query(PreliminaryAnalysisSnapshot)
        .filter(
            PreliminaryAnalysisSnapshot.organization_id == org_id,
            PreliminaryAnalysisSnapshot.project_id == project_id,
            PreliminaryAnalysisSnapshot.import_batch_id == batch.id,
            PreliminaryAnalysisSnapshot.source_artifact_id == source.id,
        )
        .order_by(PreliminaryAnalysisSnapshot.version.desc())
        .all()
    )
    versions = [snapshot.version for snapshot in snapshots]
    if len(versions) != len(set(versions)):
        raise CurrentAnalysisCorruption("Conflicting analysis authority at the same version.")
    corrupt = False
    for snapshot in snapshots:
        if snapshot.source_artifact_generation != source.generation:
            continue
        structure = (
            db.query(WorkbookStructureSnapshot)
            .filter(
                WorkbookStructureSnapshot.id == snapshot.structure_snapshot_id,
                WorkbookStructureSnapshot.organization_id == org_id,
                WorkbookStructureSnapshot.project_id == project_id,
            )
            .first()
        )
        decision = (
            db.query(ColumnMappingDecision)
            .filter(
                ColumnMappingDecision.id == snapshot.mapping_decision_id,
                ColumnMappingDecision.organization_id == org_id,
                ColumnMappingDecision.project_id == project_id,
            )
            .first()
        )
        usage = (
            db.query(ColumnMappingProfileUsage)
            .filter(
                ColumnMappingProfileUsage.id == snapshot.mapping_profile_usage_id,
                ColumnMappingProfileUsage.organization_id == org_id,
                ColumnMappingProfileUsage.project_id == project_id,
            )
            .first()
        )
        manifest = snapshot.line_manifest
        digest_matches = (
            isinstance(manifest, list)
            and hashlib.sha256(
                json.dumps(
                    manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
            == snapshot.line_manifest_digest_sha256
        )
        if (
            structure is not None
            and structure.import_batch_id == batch.id
            and structure.source_artifact_id == source.id
            and structure.source_checksum_sha256 == source.checksum_sha256
            and decision is not None
            and decision.import_batch_id == batch.id
            and decision.source_artifact_id == source.id
            and decision.structure_snapshot_id == structure.id
            and str(getattr(decision.decision_kind, "value", decision.decision_kind))
            == ColumnMappingDecisionKind.CONFIRMATION.value
            and str(getattr(decision.outcome, "value", decision.outcome))
            in {
                ColumnMappingDecisionOutcome.ACCEPTED.value,
                ColumnMappingDecisionOutcome.CORRECTED.value,
            }
            and str(getattr(decision.proposal_source_kind, "value", decision.proposal_source_kind))
            == ColumnMappingProposalSourceKind.HUMAN.value
            and decision.mapping_digest_sha256 == snapshot.mapping_decision_digest_sha256
            and usage is not None
            and usage.import_batch_id == batch.id
            and usage.source_artifact_id == source.id
            and usage.structure_snapshot_id == structure.id
            and usage.confirmation_decision_id == decision.id
            and usage.mapping_digest_sha256 == snapshot.profile_usage_mapping_digest_sha256
            and usage.source_checksum_sha256 == source.checksum_sha256
            and usage.structure_digest_sha256 == structure.analysis_digest_sha256
            and digest_matches
            and valid_manifest(manifest)
        ):
            return snapshot
        corrupt = True
    if corrupt:
        raise CurrentAnalysisCorruption("No valid snapshot for corrupt current analysis lineage.")
    return None
