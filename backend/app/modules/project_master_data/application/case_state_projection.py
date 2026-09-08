"""Offline read-only projection service for the PR-01 Global Case State foundation.

Architecture: ADR 0036, ADR 0037, ADR 0038.
Scope: Provider-only implementation for the four PR-01 prefix stages. Stages 5-16
remain explicitly unavailable. The read path uses one supplied SQLAlchemy Session
without FOR UPDATE, writes, commits, rollbacks, or audit events.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload

from app.contracts.uiux_v23 import CANONICAL_CASE_STAGES
from app.core.rbac import derive_effective_permissions
from app.modules.excel_import.models import (
    ColumnMappingDecision,
    ColumnMappingDecisionKind,
    ColumnMappingDecisionOutcome,
    ColumnMappingProfileUsage,
    ImportSourceArtifact,
    ImportSourceArtifactState,
    WorkbookStructureSnapshot,
)
from app.modules.project_master_data.application.official_intake_service import (
    get_official_intake_open_blockers,
    get_official_intake_open_warnings,
)
from app.modules.project_master_data.application.preliminary_result_service import (
    _build_lineage_manifest,
    snapshot_canonical_digest,
    validate_stored_v2_manifest,
)
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    PreliminaryAnalysisSnapshot,
    PreliminaryResultArtifact,
    Project,
    ProjectAssetImportBatch,
    ProjectOfficialIntakeCommit,
    User,
    UserRole,
    UserStatus,
    ValidationIssue,
)


PROJECT_READ_PERMISSION = "project:read"

SEMANTIC_ROUTE_KEYS: dict[str, str] = {
    "PRELIMINARY_REQUEST": "preliminary_request_pending",
    "PRELIMINARY_ANALYSIS": "preliminary_analysis_pending",
    "PRELIMINARY_READY": "preliminary_ready_pending",
    "OFFICIAL_INTAKE": "official_intake_pending",
}

STAGE_VIETNAMESE_LABELS: dict[str, str] = {
    "PRELIMINARY_REQUEST": "Tạo yêu cầu sơ bộ",
    "PRELIMINARY_ANALYSIS": "Phân tích danh mục",
    "PRELIMINARY_READY": "Tạo file kết quả sơ bộ",
    "OFFICIAL_INTAKE": "Chuyển sang thẩm định chính thức",
}


class ProjectionError(Exception):
    """Typed safe projection computation error."""


class ProjectionIntegrityError(ProjectionError):
    """Integrity failure during projection computation (dangling pointer or duplicate rows)."""


@dataclass(frozen=True)
class InternalNextAction:
    """Internal typed next-action descriptor."""

    kind: str  # "BLOCKER" | "PENDING" | "UNAVAILABLE" | "NO_AUTHORIZED_DOWNSTREAM_ACTION"
    stage: str | None
    semantic_route_key: str | None
    validation_issue_id: str | None = None


@dataclass(frozen=True)
class StageCapability:
    """Versioned static capability metadata for a canonical stage."""

    stage: str
    available: bool
    provider_key: str | None = None
    version: str = "pr01-prefix-v1"


CAPABILITY_REGISTRY_VERSION = "pr01-prefix-v1"

STATIC_STAGE_CAPABILITIES: tuple[StageCapability, ...] = (
    StageCapability("PRELIMINARY_REQUEST", available=True, provider_key="preliminary_request_v1"),
    StageCapability("PRELIMINARY_ANALYSIS", available=True, provider_key="preliminary_analysis_v1"),
    StageCapability("PRELIMINARY_READY", available=True, provider_key="preliminary_ready_v1"),
    StageCapability("OFFICIAL_INTAKE", available=True, provider_key="official_intake_commit_v1"),
    *(StageCapability(stage, available=False, provider_key=None) for stage in CANONICAL_CASE_STAGES[4:]),
)


@dataclass(frozen=True)
class StageProjection:
    """Projected state for a single canonical stage."""

    stage: str
    result: str  # COMPLETE | INCOMPLETE | BLOCKED | NOT_AVAILABLE
    provider_key: str | None = None
    fact_token: str | None = None


@dataclass(frozen=True)
class ProviderResult:
    """Internal result emitted by an authoritative raw provider."""

    stage: str
    result: str  # COMPLETE | INCOMPLETE | NOT_AVAILABLE
    fact_token: str
    provider_key: str
    authoritative_entity: Any = None


@dataclass(frozen=True)
class CaseStateProjection:
    """Global Case State projection result."""

    case_version: str
    current_stage: str
    next_action: InternalNextAction | None
    stages: list[StageProjection]
    blockers: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    stale: list[dict[str, Any]]
    facts: list[str]
    capabilities: tuple[StageCapability, ...]


def _canonical_json(payload: Any) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().lower()


def _format_utc_timestamp(dt: datetime.datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
        dt = dt.astimezone(datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _status_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _reload_active_actor_and_org(
    db: Session, *, actor: User, org_id: uuid.UUID
) -> User:
    organization = (
        db.query(OrganizationProfile)
        .filter(OrganizationProfile.id == org_id)
        .populate_existing()
        .first()
    )
    actor_id = getattr(actor, "id", None)
    persisted_actor = None
    if actor_id is not None:
        persisted_actor = (
            db.query(User)
            .options(
                selectinload(User.organization),
                selectinload(User.roles).selectinload(UserRole.role),
            )
            .filter(User.id == actor_id, User.organization_id == org_id)
            .populate_existing()
            .first()
        )
    if (
        persisted_actor is None
        or organization is None
        or _status_value(persisted_actor.status) != UserStatus.ACTIVE.value
        or _status_value(organization.status) != OrganizationStatus.ACTIVE.value
    ):
        raise HTTPException(
            status_code=403,
            detail={"error_code": "case_state_forbidden", "detail": "Không có quyền truy cập."},
        )
    if PROJECT_READ_PERMISSION not in derive_effective_permissions(
        persisted_actor, db
    ):
        raise HTTPException(
            status_code=403,
            detail={"error_code": "case_state_forbidden", "detail": "Không có quyền truy cập."},
        )
    return persisted_actor


def evaluate_preliminary_request_provider(
    db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID
) -> ProviderResult:
    """Raw provider for PRELIMINARY_REQUEST."""
    batches = (
        db.query(ProjectAssetImportBatch)
        .filter(
            ProjectAssetImportBatch.organization_id == org_id,
            ProjectAssetImportBatch.project_id == project_id,
        )
        .all()
    )

    if len(batches) == 0:
        return ProviderResult(
            stage="PRELIMINARY_REQUEST",
            result="INCOMPLETE",
            fact_token="preliminary_request_v1:null:absent-v1:absent",
            provider_key="preliminary_request_v1",
            authoritative_entity=None,
        )

    if len(batches) == 1:
        batch = batches[0]
        if batch.current_source_artifact_id is None:
            return ProviderResult(
                stage="PRELIMINARY_REQUEST",
                result="INCOMPLETE",
                fact_token="preliminary_request_v1:null:absent-v1:absent",
                provider_key="preliminary_request_v1",
                authoritative_entity=batch,
            )

        artifact = (
            db.query(ImportSourceArtifact)
            .filter(
                ImportSourceArtifact.id == batch.current_source_artifact_id,
                ImportSourceArtifact.organization_id == org_id,
                ImportSourceArtifact.project_id == project_id,
            )
            .first()
        )
        if artifact is None or artifact.import_batch_id != batch.id:
            raise ProjectionIntegrityError(
                "Dangling or cross-lineage artifact pointer in import batch."
            )

        ts = artifact.available_at if artifact.available_at is not None else artifact.created_at
        state_val = _status_value(artifact.state).lower()

        payload = {
            "artifact_checksum_sha256": str(artifact.checksum_sha256).lower(),
            "artifact_generation": int(artifact.generation),
            "artifact_id": str(artifact.id).lower(),
            "artifact_state": state_val,
            "authoritative_timestamp": _format_utc_timestamp(ts),
            "import_batch_id": str(batch.id).lower(),
            "schema": "preliminary-request-authoritative-version-v1",
        }
        av1_sha = _sha256_hex(_canonical_json(payload))

        if state_val == ImportSourceArtifactState.AVAILABLE.value:
            raw_result = "COMPLETE"
            state_tag = "complete"
        else:
            raw_result = "INCOMPLETE"
            state_tag = "incomplete"

        fact_token = f"preliminary_request_v1:{str(artifact.id).lower()}:av1-{av1_sha}:{state_tag}"
        return ProviderResult(
            stage="PRELIMINARY_REQUEST",
            result=raw_result,
            fact_token=fact_token,
            provider_key="preliminary_request_v1",
            authoritative_entity=artifact,
        )

    # >= 2 batches: multiplicity produces ambiguity payload and NOT_AVAILABLE
    batch_ids = sorted(str(b.id).lower() for b in batches)
    amb_payload = {
        "batch_count": len(batches),
        "batch_ids": batch_ids,
        "schema": "preliminary-request-ambiguity-v1",
    }
    amb_sha = _sha256_hex(_canonical_json(amb_payload))
    return ProviderResult(
        stage="PRELIMINARY_REQUEST",
        result="NOT_AVAILABLE",
        fact_token=f"preliminary_request_v1:null:amb1-{amb_sha}:not_available",
        provider_key="preliminary_request_v1",
        authoritative_entity=None,
    )


def evaluate_preliminary_analysis_provider(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    req_provider_result: ProviderResult | None = None,
) -> ProviderResult:
    """Raw provider for PRELIMINARY_ANALYSIS."""
    snapshots = (
        db.query(PreliminaryAnalysisSnapshot)
        .filter(
            PreliminaryAnalysisSnapshot.organization_id == org_id,
            PreliminaryAnalysisSnapshot.project_id == project_id,
        )
        .all()
    )

    if len(snapshots) == 0:
        return ProviderResult(
            stage="PRELIMINARY_ANALYSIS",
            result="INCOMPLETE",
            fact_token="preliminary_analysis_v1:null:absent-v1:absent",
            provider_key="preliminary_analysis_v1",
            authoritative_entity=None,
        )

    if len(snapshots) == 1:
        snapshot = snapshots[0]
        canonical_digest = snapshot_canonical_digest(snapshot)
        finalized_ts = _format_utc_timestamp(snapshot.finalized_at)

        payload = {
            "canonical_snapshot_digest": canonical_digest,
            "finalized_at": finalized_ts,
            "schema": "preliminary-analysis-provider-authoritative-version-v1",
            "snapshot_id": str(snapshot.id).lower(),
            "snapshot_version": int(snapshot.version),
        }
        av1_sha = _sha256_hex(_canonical_json(payload))

        # Evaluate lineage and validity for completeness
        is_complete = False
        batches = (
            db.query(ProjectAssetImportBatch)
            .filter(
                ProjectAssetImportBatch.organization_id == org_id,
                ProjectAssetImportBatch.project_id == project_id,
            )
            .all()
        )
        if (
            len(batches) == 1
            and batches[0].id == snapshot.import_batch_id
            and batches[0].current_source_artifact_id == snapshot.source_artifact_id
        ):
            source_artifact = (
                db.query(ImportSourceArtifact)
                .filter(
                    ImportSourceArtifact.id == snapshot.source_artifact_id,
                    ImportSourceArtifact.organization_id == org_id,
                    ImportSourceArtifact.project_id == project_id,
                )
                .first()
            )
            if (
                source_artifact is not None
                and source_artifact.import_batch_id == batches[0].id
                and source_artifact.generation == snapshot.source_artifact_generation
                and _status_value(source_artifact.state).lower() == ImportSourceArtifactState.AVAILABLE.value
            ):
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
                if (
                    structure is not None
                    and structure.import_batch_id == batches[0].id
                    and structure.source_artifact_id == source_artifact.id
                    and structure.source_checksum_sha256 == source_artifact.checksum_sha256
                    and decision is not None
                    and decision.customer_id == snapshot.customer_id
                    and decision.project_id == project_id
                    and decision.import_batch_id == batches[0].id
                    and decision.source_artifact_id == source_artifact.id
                    and decision.structure_snapshot_id == structure.id
                    and decision.decision_kind == ColumnMappingDecisionKind.CONFIRMATION.value
                    and decision.outcome in (ColumnMappingDecisionOutcome.ACCEPTED.value, ColumnMappingDecisionOutcome.CORRECTED.value)
                    and decision.mapping_digest_sha256 == snapshot.mapping_decision_digest_sha256
                    and usage is not None
                    and usage.customer_id == snapshot.customer_id
                    and usage.project_id == project_id
                    and usage.import_batch_id == batches[0].id
                    and usage.source_artifact_id == source_artifact.id
                    and usage.structure_snapshot_id == structure.id
                    and usage.confirmation_decision_id == decision.id
                    and usage.mapping_digest_sha256 == snapshot.profile_usage_mapping_digest_sha256
                    and usage.source_checksum_sha256 == source_artifact.checksum_sha256
                    and usage.structure_digest_sha256 == structure.analysis_digest_sha256
                    and _sha256_hex(_canonical_json(snapshot.line_manifest)) == snapshot.line_manifest_digest_sha256
                    and validate_stored_v2_manifest(snapshot.line_manifest)
                ):
                    is_complete = True

        raw_result = "COMPLETE" if is_complete else "INCOMPLETE"
        state_tag = "complete" if is_complete else "incomplete"
        fact_token = f"preliminary_analysis_v1:{str(snapshot.id).lower()}:av1-{av1_sha}:{state_tag}"
        return ProviderResult(
            stage="PRELIMINARY_ANALYSIS",
            result=raw_result,
            fact_token=fact_token,
            provider_key="preliminary_analysis_v1",
            authoritative_entity=snapshot,
        )

    # >= 2 snapshots: multiplicity produces ambiguity payload and NOT_AVAILABLE
    identities = sorted(f"{str(s.id).lower()}@{s.version}" for s in snapshots)
    amb_payload = {
        "count": len(snapshots),
        "identities": identities,
        "schema": "preliminary-analysis-ambiguity-v1",
    }
    amb_sha = _sha256_hex(_canonical_json(amb_payload))
    return ProviderResult(
        stage="PRELIMINARY_ANALYSIS",
        result="NOT_AVAILABLE",
        fact_token=f"preliminary_analysis_v1:null:amb1-{amb_sha}:not_available",
        provider_key="preliminary_analysis_v1",
        authoritative_entity=None,
    )


def _extract_candidate_and_quantity(
    usage: ColumnMappingProfileUsage,
) -> tuple[dict, dict] | None:
    mapping_snapshot = usage.mapping_snapshot
    if not isinstance(mapping_snapshot, dict):
        return None
    candidate = mapping_snapshot.get("candidate")
    if not isinstance(candidate, dict):
        return None
    required_candidate_keys = {
        "sheet_name",
        "header_start_row",
        "header_end_row",
        "data_start_row",
        "min_row",
        "max_row",
        "min_column",
        "max_column",
    }
    if required_candidate_keys - set(candidate.keys()):
        return None
    if not isinstance(candidate.get("max_column"), int) or isinstance(candidate.get("max_column"), bool):
        return None
    fields = mapping_snapshot.get("fields")
    if not isinstance(fields, list):
        return None
    quantity_fields = [
        f for f in fields if isinstance(f, dict) and f.get("semantic_role") == "quantity"
    ]
    if len(quantity_fields) != 1:
        return None
    q_field = quantity_fields[0]
    if "source_column_index" not in q_field or "source_column_letter" not in q_field:
        return None
    if not isinstance(q_field["source_column_index"], int) or isinstance(q_field["source_column_index"], bool):
        return None
    return candidate, q_field


def evaluate_preliminary_ready_provider(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    analysis_provider_result: ProviderResult | None = None,
) -> ProviderResult:
    """Raw provider for PRELIMINARY_READY."""
    artifacts = (
        db.query(PreliminaryResultArtifact)
        .filter(
            PreliminaryResultArtifact.organization_id == org_id,
            PreliminaryResultArtifact.project_id == project_id,
        )
        .all()
    )

    if len(artifacts) == 0:
        return ProviderResult(
            stage="PRELIMINARY_READY",
            result="INCOMPLETE",
            fact_token="preliminary_ready_v1:null:absent-v1:absent",
            provider_key="preliminary_ready_v1",
            authoritative_entity=None,
        )

    if len(artifacts) == 1:
        artifact = artifacts[0]
        manifest = artifact.lineage_manifest if isinstance(artifact.lineage_manifest, dict) else {}
        canonical_lineage_digest = _sha256_hex(_canonical_json(manifest))
        analysis_snap_info = manifest.get("analysis_snapshot") if isinstance(manifest.get("analysis_snapshot"), dict) else {}
        analysis_snapshot_id = analysis_snap_info.get("id")
        created_ts = _format_utc_timestamp(artifact.created_at)

        payload = {
            "analysis_snapshot_id": str(analysis_snapshot_id).lower() if analysis_snapshot_id else None,
            "artifact_id": str(artifact.id).lower(),
            "canonical_lineage_manifest_digest": canonical_lineage_digest,
            "content_checksum_sha256": str(artifact.content_checksum_sha256).lower(),
            "created_at": created_ts,
            "schema": "preliminary-ready-provider-authoritative-version-v1",
            "source_snapshot_sha256": str(artifact.source_snapshot_sha256).lower(),
            "version": int(artifact.version),
        }
        av1_sha = _sha256_hex(_canonical_json(payload))

        is_complete = False
        if (
            analysis_provider_result is not None
            and analysis_provider_result.result == "COMPLETE"
            and analysis_provider_result.authoritative_entity is not None
        ):
            snapshot: PreliminaryAnalysisSnapshot = analysis_provider_result.authoritative_entity
            expected_snapshot_digest = snapshot_canonical_digest(snapshot)
            if (
                isinstance(manifest, dict)
                and bool(manifest)
                and artifact.source_snapshot_sha256 == expected_snapshot_digest
            ):
                source_artifact = (
                    db.query(ImportSourceArtifact)
                    .filter(
                        ImportSourceArtifact.id == snapshot.source_artifact_id,
                        ImportSourceArtifact.organization_id == org_id,
                        ImportSourceArtifact.project_id == project_id,
                    )
                    .first()
                )
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
                if (
                    source_artifact is not None
                    and structure is not None
                    and decision is not None
                    and usage is not None
                ):
                    candidate_and_qty = _extract_candidate_and_quantity(usage)
                    if candidate_and_qty is not None:
                        candidate, quantity_field = candidate_and_qty
                        price_col = candidate["max_column"] + 1
                        amount_col = candidate["max_column"] + 2
                        line_manifest = (
                            snapshot.line_manifest
                            if isinstance(snapshot.line_manifest, list)
                            else []
                        )
                        try:
                            expected_manifest = _build_lineage_manifest(
                                org_id=org_id,
                                project_id=project_id,
                                customer_id=snapshot.customer_id,
                                snapshot=snapshot,
                                artifact=source_artifact,
                                structure=structure,
                                decision=decision,
                                usage=usage,
                                candidate=candidate,
                                quantity_field=quantity_field,
                                price_col=price_col,
                                amount_col=amount_col,
                                snapshot_digest=expected_snapshot_digest,
                                line_manifest=line_manifest,
                            )
                            if _canonical_json(manifest) == _canonical_json(expected_manifest):
                                is_complete = True
                        except Exception:
                            is_complete = False

        raw_result = "COMPLETE" if is_complete else "INCOMPLETE"
        state_tag = "complete" if is_complete else "incomplete"
        fact_token = f"preliminary_ready_v1:{str(artifact.id).lower()}:av1-{av1_sha}:{state_tag}"
        return ProviderResult(
            stage="PRELIMINARY_READY",
            result=raw_result,
            fact_token=fact_token,
            provider_key="preliminary_ready_v1",
            authoritative_entity=artifact,
        )

    # >= 2 artifacts: multiplicity produces ambiguity payload and NOT_AVAILABLE
    identities = sorted(f"{str(a.id).lower()}@{a.version}" for a in artifacts)
    amb_payload = {
        "count": len(artifacts),
        "identities": identities,
        "schema": "preliminary-ready-ambiguity-v1",
    }
    amb_sha = _sha256_hex(_canonical_json(amb_payload))
    return ProviderResult(
        stage="PRELIMINARY_READY",
        result="NOT_AVAILABLE",
        fact_token=f"preliminary_ready_v1:null:amb1-{amb_sha}:not_available",
        provider_key="preliminary_ready_v1",
        authoritative_entity=None,
    )


def evaluate_official_intake_provider(
    db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID
) -> ProviderResult:
    """Raw provider for OFFICIAL_INTAKE."""
    commits = (
        db.query(ProjectOfficialIntakeCommit)
        .filter(
            ProjectOfficialIntakeCommit.organization_id == org_id,
            ProjectOfficialIntakeCommit.project_id == project_id,
        )
        .all()
    )

    if len(commits) == 0:
        return ProviderResult(
            stage="OFFICIAL_INTAKE",
            result="INCOMPLETE",
            fact_token="official_intake_commit_v1:null:absent-v1:absent",
            provider_key="official_intake_commit_v1",
            authoritative_entity=None,
        )

    if len(commits) == 1:
        commit = commits[0]
        committed_ts = _format_utc_timestamp(commit.committed_at)
        payload = {
            "artifact_checksum": str(commit.preliminary_result_sha256).lower(),
            "artifact_id": str(commit.preliminary_result_artifact_id).lower(),
            "artifact_version": int(commit.preliminary_result_version),
            "committed_at": committed_ts,
            "schema": "official-intake-authoritative-version-v1",
            "source_snapshot_sha256": str(commit.source_snapshot_sha256).lower(),
        }
        av1_sha = _sha256_hex(_canonical_json(payload))
        return ProviderResult(
            stage="OFFICIAL_INTAKE",
            result="COMPLETE",
            fact_token=f"official_intake_commit_v1:{str(commit.id).lower()}:av1-{av1_sha}:complete",
            provider_key="official_intake_commit_v1",
            authoritative_entity=commit,
        )

    # Multiple commit rows is an integrity violation, not ambiguity
    raise ProjectionIntegrityError(
        "Multiple ProjectOfficialIntakeCommit rows found for project."
    )


def compute_case_version(
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    facts: list[str],
) -> tuple[str, list[str]]:
    """Compute deterministic case_version token from sorted facts."""
    sorted_facts = sorted(facts)
    envelope = {
        "contract": "global-case-state-v1",
        "facts": sorted_facts,
        "organization_id": str(org_id).lower(),
        "project_id": str(project_id).lower(),
    }
    encoded = _canonical_json(envelope)
    token = _sha256_hex(encoded)
    return token, sorted_facts


def determine_current_stage(
    stage_results: list[StageProjection],
) -> str:
    """Determine current stage from the leading COMPLETE PR-01 prefix."""
    leading_complete = 0
    for stage_proj in stage_results[:4]:
        if stage_proj.result == "COMPLETE":
            leading_complete += 1
        else:
            break

    if leading_complete == 0:
        return "PRELIMINARY_REQUEST"
    if leading_complete == 1:
        return "PRELIMINARY_ANALYSIS"
    if leading_complete == 2:
        return "PRELIMINARY_READY"
    return "OFFICIAL_INTAKE"


def determine_internal_next_action(
    stage_results: list[StageProjection],
    *,
    blockers: list[ValidationIssue],
) -> InternalNextAction | None:
    """Determine one internal next action using the PR-01 precedence contract."""
    if blockers:
        lowest_id = str(blockers[0].id)
        return InternalNextAction(
            kind="BLOCKER",
            stage="OFFICIAL_INTAKE",
            semantic_route_key=None,
            validation_issue_id=lowest_id,
        )

    prefix_results = stage_results[:4]
    if all(stage.result == "COMPLETE" for stage in prefix_results):
        return InternalNextAction(
            kind="NO_AUTHORIZED_DOWNSTREAM_ACTION",
            stage=None,
            semantic_route_key=None,
            validation_issue_id=None,
        )

    for stage_projection in prefix_results:
        if stage_projection.result == "INCOMPLETE":
            return InternalNextAction(
                kind="PENDING",
                stage=stage_projection.stage,
                semantic_route_key=SEMANTIC_ROUTE_KEYS.get(stage_projection.stage),
                validation_issue_id=None,
            )
        if stage_projection.result == "NOT_AVAILABLE":
            return InternalNextAction(
                kind="UNAVAILABLE",
                stage=stage_projection.stage,
                semantic_route_key=None,
                validation_issue_id=None,
            )

    return InternalNextAction(
        kind="NO_AUTHORIZED_DOWNSTREAM_ACTION",
        stage=None,
        semantic_route_key=None,
        validation_issue_id=None,
    )


def get_case_state_projection(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
) -> CaseStateProjection:
    """Compute Global Case State for one tenant-scoped Project in one read transaction."""
    _reload_active_actor_and_org(db, actor=actor, org_id=org_id)

    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == org_id)
        .populate_existing()
        .first()
    )
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "project_not_found", "detail": "Không tìm thấy hồ sơ."},
        )

    try:
        request_result = evaluate_preliminary_request_provider(
            db, org_id=org_id, project_id=project_id
        )
        analysis_result = evaluate_preliminary_analysis_provider(
            db,
            org_id=org_id,
            project_id=project_id,
            req_provider_result=request_result,
        )
        ready_result = evaluate_preliminary_ready_provider(
            db,
            org_id=org_id,
            project_id=project_id,
            analysis_provider_result=analysis_result,
        )
        official_result = evaluate_official_intake_provider(
            db, org_id=org_id, project_id=project_id
        )
        blockers = get_official_intake_open_blockers(
            db, org_id=org_id, project_id=project_id
        )
        warnings = get_official_intake_open_warnings(
            db, org_id=org_id, project_id=project_id
        )
    except (ProjectionError, HTTPException):
        raise
    except Exception as exc:
        raise ProjectionError(
            "Unexpected provider failure during projection calculation."
        ) from exc

    stage_projections: list[StageProjection] = [
        StageProjection(
            stage="PRELIMINARY_REQUEST",
            result=request_result.result,
            provider_key=request_result.provider_key,
            fact_token=request_result.fact_token,
        ),
        StageProjection(
            stage="PRELIMINARY_ANALYSIS",
            result=analysis_result.result,
            provider_key=analysis_result.provider_key,
            fact_token=analysis_result.fact_token,
        ),
        StageProjection(
            stage="PRELIMINARY_READY",
            result=ready_result.result,
            provider_key=ready_result.provider_key,
            fact_token=ready_result.fact_token,
        ),
    ]

    projected_official_result = official_result.result
    if official_result.result != "COMPLETE" and blockers:
        projected_official_result = "BLOCKED"
    stage_projections.append(
        StageProjection(
            stage="OFFICIAL_INTAKE",
            result=projected_official_result,
            provider_key=official_result.provider_key,
            fact_token=official_result.fact_token,
        )
    )

    stage_projections.extend(
        StageProjection(
            stage=stage,
            result="NOT_AVAILABLE",
            provider_key=None,
            fact_token=None,
        )
        for stage in CANONICAL_CASE_STAGES[4:]
    )

    facts: list[str] = [
        request_result.fact_token,
        analysis_result.fact_token,
        ready_result.fact_token,
        official_result.fact_token,
    ]
    facts.extend(
        f"validation_issue_blocker_v1:{str(issue.id).lower()}:rv{issue.row_version}:open"
        for issue in blockers
    )
    facts.extend(
        f"validation_issue_warning_v1:{str(issue.id).lower()}:rv{issue.row_version}:open"
        for issue in warnings
    )

    case_version, sorted_facts = compute_case_version(
        org_id=org_id, project_id=project_id, facts=facts
    )
    current_stage = determine_current_stage(stage_projections)
    next_action = determine_internal_next_action(stage_projections, blockers=blockers)

    blocker_dicts = [
        {
            "id": str(issue.id),
            "target_type": issue.target_type,
            "target_id": str(issue.target_id),
            "severity": _status_value(issue.severity),
            "status": _status_value(issue.status),
            "row_version": issue.row_version,
        }
        for issue in blockers
    ]
    warning_dicts = [
        {
            "id": str(issue.id),
            "target_type": issue.target_type,
            "target_id": str(issue.target_id),
            "severity": _status_value(issue.severity),
            "status": _status_value(issue.status),
            "row_version": issue.row_version,
        }
        for issue in warnings
    ]

    return CaseStateProjection(
        case_version=case_version,
        current_stage=current_stage,
        next_action=next_action,
        stages=stage_projections,
        blockers=blocker_dicts,
        warnings=warning_dicts,
        stale=[],
        facts=sorted_facts,
        capabilities=STATIC_STAGE_CAPABILITIES,
    )
