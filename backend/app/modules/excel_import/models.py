"""excel_import-owned persistence for Adaptive Intake source artifacts."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy import Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class ImportSourceArtifactState(str, enum.Enum):
    PENDING = "pending"
    AVAILABLE = "available"
    FAILED = "failed"
    ORPHANED = "orphaned"


class ImportSourceArtifact(Base, UUIDMixin, TimestampMixin):
    """Immutable source workbook identity + lifecycle for Adaptive Intake v2."""

    __tablename__ = "import_source_artifacts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organization_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("project_asset_import_batches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    detected_format: Mapped[str] = mapped_column(String(16), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_etag: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    adapter_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    adapter_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    adapter_metadata: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    available_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    orphaned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint("import_batch_id", "generation", name="uq_source_artifact_batch_generation"),
        UniqueConstraint("storage_object_key", name="uq_source_artifact_object_key"),
        CheckConstraint("generation > 0", name="chk_source_artifact_generation_positive"),
        CheckConstraint("file_size_bytes >= 0", name="chk_source_artifact_size_nonneg"),
        CheckConstraint(
            "length(checksum_sha256) = 64",
            name="chk_source_artifact_checksum_len",
        ),
        Index("idx_source_artifact_org", "organization_id"),
        Index("idx_source_artifact_project", "project_id"),
        Index("idx_source_artifact_batch", "import_batch_id"),
        Index("idx_source_artifact_state", "state"),
    )
