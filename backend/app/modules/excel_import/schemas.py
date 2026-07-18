"""Public API schemas for ImportSourceArtifact (no storage key leakage)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


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
