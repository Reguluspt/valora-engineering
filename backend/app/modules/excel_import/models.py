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
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy import Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDMixin, utc_now


class ImportSourceArtifactState(str, enum.Enum):
    PENDING = "pending"
    AVAILABLE = "available"
    FAILED = "failed"
    ORPHANED = "orphaned"


class WorkbookStructureDisposition(str, enum.Enum):
    PROPOSED = "proposed"
    REVIEW_REQUIRED = "review_required"


class ImportSourceArtifact(Base, UUIDMixin, TimestampMixin):
    """Immutable source workbook identity + lifecycle for Adaptive Intake v2."""

    __tablename__ = "import_source_artifacts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organization_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="RESTRICT"),
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
    adapter_metadata: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
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
        # Enables composite FK: batch (id, current_source_artifact_id) → (import_batch_id, id)
        UniqueConstraint("import_batch_id", "id", name="uq_source_artifact_batch_id"),
        # Enables fail-closed tenant-scoped WorkbookStructureSnapshot linkage.
        UniqueConstraint(
            "organization_id",
            "project_id",
            "import_batch_id",
            "id",
            name="uq_source_artifact_tenant_scope_id",
        ),
        CheckConstraint("generation > 0", name="chk_source_artifact_generation_positive"),
        CheckConstraint("file_size_bytes >= 0", name="chk_source_artifact_size_nonneg"),
        CheckConstraint(
            "length(checksum_sha256) = 64",
            name="chk_source_artifact_checksum_len",
        ),
        CheckConstraint(
            "checksum_sha256 = lower(checksum_sha256)",
            name="chk_source_artifact_checksum_lower",
        ),
        CheckConstraint(
            "state IN ('pending', 'available', 'failed', 'orphaned')",
            name="chk_source_artifact_state",
        ),
        CheckConstraint(
            "detected_format IN ('xls', 'xlsx')",
            name="chk_source_artifact_format",
        ),
        ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id"],
            [
                "project_asset_import_batches.organization_id",
                "project_asset_import_batches.project_id",
                "project_asset_import_batches.id",
            ],
            name="fk_source_artifact_batch_tenant",
            ondelete="RESTRICT",
        ),
        Index("idx_source_artifact_org", "organization_id"),
        Index("idx_source_artifact_project", "project_id"),
        Index("idx_source_artifact_batch", "import_batch_id"),
        Index("idx_source_artifact_state", "state"),
    )


class WorkbookStructureSnapshot(Base, UUIDMixin):
    """Append-only, digest-bound structure discovery evidence."""

    __tablename__ = "workbook_structure_snapshots"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    import_batch_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_artifact_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    snapshot_version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    adapter_name: Mapped[str] = mapped_column(String(64), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(64), nullable=False)
    disposition: Mapped[str] = mapped_column(String(32), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    structure_payload: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    analysis_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "source_artifact_id",
            "snapshot_version",
            name="uq_workbook_structure_artifact_version",
        ),
        CheckConstraint(
            "snapshot_version > 0",
            name="chk_workbook_structure_version_positive",
        ),
        CheckConstraint(
            "candidate_count >= 0",
            name="chk_workbook_structure_candidate_count_nonneg",
        ),
        CheckConstraint(
            "length(source_checksum_sha256) = 64",
            name="chk_workbook_structure_source_checksum_len",
        ),
        CheckConstraint(
            "source_checksum_sha256 = lower(source_checksum_sha256)",
            name="chk_workbook_structure_source_checksum_lower",
        ),
        CheckConstraint(
            "disposition IN ('proposed', 'review_required')",
            name="chk_workbook_structure_disposition",
        ),
        CheckConstraint(
            "length(analysis_digest_sha256) = 64",
            name="chk_workbook_structure_digest_len",
        ),
        CheckConstraint(
            "analysis_digest_sha256 = lower(analysis_digest_sha256)",
            name="chk_workbook_structure_digest_lower",
        ),
        ForeignKeyConstraint(
            [
                "organization_id",
                "project_id",
                "import_batch_id",
                "source_artifact_id",
            ],
            [
                "import_source_artifacts.organization_id",
                "import_source_artifacts.project_id",
                "import_source_artifacts.import_batch_id",
                "import_source_artifacts.id",
            ],
            name="fk_workbook_structure_source_tenant",
            ondelete="RESTRICT",
        ),
        Index("idx_workbook_structure_org", "organization_id"),
        Index("idx_workbook_structure_project", "project_id"),
        Index("idx_workbook_structure_batch", "import_batch_id"),
        Index("idx_workbook_structure_artifact", "source_artifact_id"),
        Index("idx_workbook_structure_disposition", "disposition"),
    )
