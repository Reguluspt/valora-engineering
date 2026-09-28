"""Read-only selection of the highest valid Result for the current Analysis."""

from __future__ import annotations

import re
import uuid

from sqlalchemy.orm import Session

from app.modules.excel_import.models import (
    ColumnMappingDecision,
    ColumnMappingProfileUsage,
    ImportSourceArtifact,
    WorkbookStructureSnapshot,
)
from app.modules.project_master_data.application.preliminary_result_service import (
    _build_lineage_manifest,
    _canonical_json,
    _resolve_candidate_and_fields,
    _sha256_hex,
    snapshot_canonical_digest,
    validate_stored_v2_manifest,
)
from app.modules.project_master_data.models import (
    PreliminaryAnalysisSnapshot,
    PreliminaryResultArtifact,
)


class CurrentResultCorruption(Exception):
    """Stored Result evidence cannot be classified as valid current or history."""


def _lineage_entity(db: Session, model, *, id: uuid.UUID, org_id: uuid.UUID, project_id: uuid.UUID):
    entity = db.query(model).filter(
        model.id == id,
        model.organization_id == org_id,
        model.project_id == project_id,
    ).first()
    if entity is None:
        raise CurrentResultCorruption("Result lineage reference is missing or cross-scoped.")
    return entity


def _validated_analysis(
    db: Session, *, result: PreliminaryResultArtifact, manifest: dict,
    org_id: uuid.UUID, project_id: uuid.UUID,
) -> PreliminaryAnalysisSnapshot:
    if manifest.get("organization_id") != str(org_id) or manifest.get("project_id") != str(project_id):
        raise CurrentResultCorruption("Result manifest scope disagrees with its fact.")
    expected_customer = str(result.customer_id) if result.customer_id is not None else None
    if manifest.get("customer_id") != expected_customer:
        raise CurrentResultCorruption("Result Customer snapshot disagrees with its manifest.")
    info = manifest.get("analysis_snapshot")
    if not isinstance(info, dict):
        raise CurrentResultCorruption("Result analysis reference is malformed.")
    try:
        analysis_id = uuid.UUID(info["id"])
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise CurrentResultCorruption("Result analysis ID is malformed.") from exc
    analysis = _lineage_entity(
        db, PreliminaryAnalysisSnapshot, id=analysis_id,
        org_id=org_id, project_id=project_id,
    )
    digest = snapshot_canonical_digest(analysis)
    if (
        info.get("version") != analysis.version
        or info.get("canonical_digest_sha256") != digest
        or result.source_snapshot_sha256 != digest
        or not validate_stored_v2_manifest(analysis.line_manifest)
        or _sha256_hex(_canonical_json(analysis.line_manifest))
        != analysis.line_manifest_digest_sha256
    ):
        raise CurrentResultCorruption("Result analysis version or digest is invalid.")
    return analysis


def _validate_manifest(
    db: Session, *, result: PreliminaryResultArtifact,
    manifest: dict, analysis: PreliminaryAnalysisSnapshot,
    org_id: uuid.UUID, project_id: uuid.UUID,
) -> None:
    if (
        not isinstance(result.content_checksum_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", result.content_checksum_sha256) is None
        or result.file_size_bytes < 0
        or not result.storage_object_key
    ):
        raise CurrentResultCorruption("Result file identity is invalid.")
    source = _lineage_entity(
        db, ImportSourceArtifact, id=analysis.source_artifact_id,
        org_id=org_id, project_id=project_id,
    )
    structure = _lineage_entity(
        db, WorkbookStructureSnapshot, id=analysis.structure_snapshot_id,
        org_id=org_id, project_id=project_id,
    )
    decision = _lineage_entity(
        db, ColumnMappingDecision, id=analysis.mapping_decision_id,
        org_id=org_id, project_id=project_id,
    )
    usage = _lineage_entity(
        db, ColumnMappingProfileUsage, id=analysis.mapping_profile_usage_id,
        org_id=org_id, project_id=project_id,
    )
    if (
        source.import_batch_id != analysis.import_batch_id
        or source.generation != analysis.source_artifact_generation
        or structure.import_batch_id != analysis.import_batch_id
        or structure.source_artifact_id != source.id
        or structure.source_checksum_sha256 != source.checksum_sha256
        or decision.import_batch_id != analysis.import_batch_id
        or decision.source_artifact_id != source.id
        or decision.structure_snapshot_id != structure.id
        or decision.mapping_digest_sha256 != analysis.mapping_decision_digest_sha256
        or usage.import_batch_id != analysis.import_batch_id
        or usage.source_artifact_id != source.id
        or usage.structure_snapshot_id != structure.id
        or usage.confirmation_decision_id != decision.id
        or usage.mapping_digest_sha256 != analysis.profile_usage_mapping_digest_sha256
        or usage.source_checksum_sha256 != source.checksum_sha256
        or usage.structure_digest_sha256 != structure.analysis_digest_sha256
    ):
        raise CurrentResultCorruption("Result source or mapping lineage is invalid.")
    try:
        candidate, _, quantity_field = _resolve_candidate_and_fields(usage)
        max_column = candidate["max_column"]
        if isinstance(max_column, bool) or not isinstance(max_column, int):
            raise ValueError("Invalid output column")
        expected = _build_lineage_manifest(
            org_id=org_id, project_id=project_id, customer_id=result.customer_id,
            snapshot=analysis, artifact=source, structure=structure,
            decision=decision, usage=usage, candidate=candidate,
            quantity_field=quantity_field, price_col=max_column + 1,
            amount_col=max_column + 2,
            snapshot_digest=snapshot_canonical_digest(analysis),
            line_manifest=analysis.line_manifest,
        )
    except Exception as exc:
        raise CurrentResultCorruption("Result manifest inputs are invalid.") from exc
    if _canonical_json(manifest) != _canonical_json(expected):
        raise CurrentResultCorruption("Result manifest does not match stored lineage.")


def select_current_result(
    db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID,
    current_analysis: PreliminaryAnalysisSnapshot | None,
) -> PreliminaryResultArtifact | None:
    """Return highest valid matching version; valid older Analysis Results are history."""
    results = db.query(PreliminaryResultArtifact).filter(
        PreliminaryResultArtifact.organization_id == org_id,
        PreliminaryResultArtifact.project_id == project_id,
    ).all()
    versions = [result.version for result in results]
    if len(versions) != len(set(versions)):
        raise CurrentResultCorruption("Conflicting Result claims at the same version.")
    matching: list[PreliminaryResultArtifact] = []
    for result in results:
        manifest = result.lineage_manifest
        if not isinstance(manifest, dict) or not manifest:
            raise CurrentResultCorruption("Result manifest is missing or malformed.")
        analysis = _validated_analysis(
            db, result=result, manifest=manifest, org_id=org_id, project_id=project_id,
        )
        if current_analysis is not None and analysis.id == current_analysis.id:
            _validate_manifest(
                db, result=result, manifest=manifest, analysis=analysis,
                org_id=org_id, project_id=project_id,
            )
            matching.append(result)
    return max(matching, key=lambda result: result.version) if matching else None
