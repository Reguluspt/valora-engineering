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
