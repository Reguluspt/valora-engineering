"""Public API schemas for ImportSourceArtifact (no storage key leakage)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from app.modules.excel_import.domain.column_mapping import (
    ColumnMappingContractError,
    validate_mapping_snapshot,
)


class ImportSourceArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    import_batch_id: uuid.UUID
    generation: int
    original_filename: str
    detected_format: str
    content_type: str
    file_size_bytes: int
    checksum_sha256: str
    state: str
    adapter_name: Optional[str] = None
    adapter_version: Optional[str] = None
    adapter_metadata: dict[str, Any] = Field(default_factory=dict)
    created_by_user_id: uuid.UUID
    created_at: datetime
    available_at: Optional[datetime] = None


class SourceArtifactReconcileResponse(BaseModel):
    scanned: int
    marked_orphan: int
    deleted_objects: int
    marked_failed: int = 0
    errors: int = 0


class WorkbookStructureSnapshotResponse(BaseModel):
    """Public, digest-bound structure evidence; no storage object key."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    import_batch_id: uuid.UUID
    source_artifact_id: uuid.UUID
    snapshot_version: int
    source_checksum_sha256: str
    rule_version: str
    adapter_name: str
    adapter_version: str
    disposition: str
    candidate_count: int
    structure_payload: dict[str, Any]
    analysis_digest_sha256: str
    created_by_user_id: uuid.UUID
    created_at: datetime


class MappingProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_artifact_id: uuid.UUID
    structure_snapshot_id: uuid.UUID
    candidate_index: StrictInt = Field(..., ge=0)
    command_id: uuid.UUID


class MappingConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_decision_id: uuid.UUID
    mapping_snapshot: dict[str, Any]
    memory_scope: Literal["none", "customer"]
    supersedes_profile_id: uuid.UUID | None = None
    command_id: uuid.UUID

    @field_validator("mapping_snapshot")
    @classmethod
    def _valid_mapping_snapshot(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            validate_mapping_snapshot(value)
        except ColumnMappingContractError as exc:
            raise ValueError(exc.detail) from exc
        return value


class MappingRejectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_decision_id: uuid.UUID
    command_id: uuid.UUID
    reason_code: str | None = Field(None, max_length=64)
    reason_text: str | None = Field(None, max_length=1000)


class MappingMaterializationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_decision_id: uuid.UUID
    command_id: uuid.UUID


class MappingProposalResponse(BaseModel):
    decision_id: uuid.UUID
    source_artifact_id: uuid.UUID
    structure_snapshot_id: uuid.UUID
    mapping_snapshot: dict[str, Any]
    mapping_digest_sha256: str
    review_required: bool
    review_reasons: list[str]
    exact_profile_id: uuid.UUID | None
    similar_profile_ids: list[uuid.UUID]
    organization_template_id: uuid.UUID | None


class MappingDecisionResponse(BaseModel):
    decision_id: uuid.UUID
    proposal_decision_id: uuid.UUID
    outcome: str
    mapping_digest_sha256: str
    memory_scope: str
    profile_id: uuid.UUID | None
    source_artifact_id: uuid.UUID
    structure_snapshot_id: uuid.UUID


class MappingMaterializationResponse(BaseModel):
    usage_id: uuid.UUID
    confirmation_decision_id: uuid.UUID
    mapping_digest_sha256: str
    materialized_asset_row_count: int
    source_artifact_id: uuid.UUID
    structure_snapshot_id: uuid.UUID
