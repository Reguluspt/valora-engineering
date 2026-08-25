"""excel_import-owned persistence for Adaptive Intake source artifacts."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
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


class ColumnMappingScopeType(str, enum.Enum):
    CUSTOMER = "customer"
    ORGANIZATION_TEMPLATE = "organization_template"


class ColumnMappingProfileStatus(str, enum.Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class ColumnMappingDecisionKind(str, enum.Enum):
    PROPOSAL = "proposal"
    CONFIRMATION = "confirmation"
    REJECTION = "rejection"


class ColumnMappingDecisionOutcome(str, enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    CORRECTED = "corrected"
    REJECTED = "rejected"


class ColumnMappingMemoryScope(str, enum.Enum):
    NONE = "none"
    CUSTOMER = "customer"


class ColumnMappingProposalSourceKind(str, enum.Enum):
    HUMAN = "human"
    DETERMINISTIC_RULE = "deterministic_rule"
    AI_TASK = "ai_task"


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
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_source_artifact_creator_tenant",
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
        UniqueConstraint(
            "organization_id",
            "project_id",
            "import_batch_id",
            "source_artifact_id",
            "id",
            name="uq_workbook_structure_tenant_source_id",
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
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_workbook_structure_creator_tenant",
            ondelete="RESTRICT",
        ),
        Index("idx_workbook_structure_org", "organization_id"),
        Index("idx_workbook_structure_project", "project_id"),
        Index("idx_workbook_structure_batch", "import_batch_id"),
        Index("idx_workbook_structure_artifact", "source_artifact_id"),
        Index("idx_workbook_structure_disposition", "disposition"),
    )


class ColumnMappingProfile(Base, UUIDMixin):
    """Immutable versioned reusable mapping memory (active can only be superseded)."""

    __tablename__ = "column_mapping_profiles"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=True
    )
    source_customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    source_project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_import_batch_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    profile_family_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    template_fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprint_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("import_source_artifacts.id", ondelete="RESTRICT"), nullable=False
    )
    structure_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workbook_structure_snapshots.id", ondelete="RESTRICT"), nullable=False
    )
    sheet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    header_start_row: Mapped[int] = mapped_column(Integer, nullable=False)
    header_end_row: Mapped[int] = mapped_column(Integer, nullable=False)
    data_start_row: Mapped[int] = mapped_column(Integer, nullable=False)
    min_column: Mapped[int] = mapped_column(Integer, nullable=False)
    max_column: Mapped[int] = mapped_column(Integer, nullable=False)
    supersedes_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("column_mapping_profiles.id", ondelete="RESTRICT"), nullable=True
    )
    confirmed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_mapping_profile_org_id"),
        UniqueConstraint(
            "profile_family_id", "profile_version", name="uq_mapping_profile_family_version"
        ),
        CheckConstraint("profile_version > 0", name="chk_mapping_profile_version_positive"),
        CheckConstraint(
            "scope_type IN ('customer', 'organization_template')",
            name="chk_mapping_profile_scope",
        ),
        CheckConstraint(
            "status IN ('candidate', 'active', 'superseded', 'rejected')",
            name="chk_mapping_profile_status",
        ),
        CheckConstraint(
            "header_start_row > 0 AND header_end_row >= header_start_row "
            "AND data_start_row > header_end_row",
            name="chk_mapping_profile_row_bounds",
        ),
        CheckConstraint(
            "min_column > 0 AND max_column >= min_column",
            name="chk_mapping_profile_column_bounds",
        ),
        CheckConstraint(
            "length(template_fingerprint_sha256) = 64 "
            "AND template_fingerprint_sha256 = lower(template_fingerprint_sha256)",
            name="chk_mapping_profile_fingerprint",
        ),
        CheckConstraint(
            "length(mapping_digest_sha256) = 64 "
            "AND mapping_digest_sha256 = lower(mapping_digest_sha256)",
            name="chk_mapping_profile_digest",
        ),
        CheckConstraint(
            "(scope_type = 'customer' AND customer_id IS NOT NULL "
            "AND customer_id = source_customer_id AND approved_by_user_id IS NULL "
            "AND approved_at IS NULL) OR "
            "(scope_type = 'organization_template' AND customer_id IS NULL "
            "AND approved_by_user_id IS NOT NULL AND approved_at IS NOT NULL)",
            name="chk_mapping_profile_scope_fields",
        ),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_mapping_profile_customer_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_mapping_profile_source_customer_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_customer_id", "source_project_id"],
            ["projects.organization_id", "projects.customer_id", "projects.id"],
            name="fk_mapping_profile_source_project_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_project_id", "source_import_batch_id"],
            [
                "project_asset_import_batches.organization_id",
                "project_asset_import_batches.project_id",
                "project_asset_import_batches.id",
            ],
            name="fk_mapping_profile_source_batch_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            [
                "organization_id",
                "source_project_id",
                "source_import_batch_id",
                "source_artifact_id",
            ],
            [
                "import_source_artifacts.organization_id",
                "import_source_artifacts.project_id",
                "import_source_artifacts.import_batch_id",
                "import_source_artifacts.id",
            ],
            name="fk_mapping_profile_source_artifact_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            [
                "organization_id",
                "source_project_id",
                "source_import_batch_id",
                "source_artifact_id",
                "structure_snapshot_id",
            ],
            [
                "workbook_structure_snapshots.organization_id",
                "workbook_structure_snapshots.project_id",
                "workbook_structure_snapshots.import_batch_id",
                "workbook_structure_snapshots.source_artifact_id",
                "workbook_structure_snapshots.id",
            ],
            name="fk_mapping_profile_structure_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "supersedes_profile_id"],
            ["column_mapping_profiles.organization_id", "column_mapping_profiles.id"],
            name="fk_mapping_profile_supersedes_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "confirmed_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_mapping_profile_confirmer_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "approved_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_mapping_profile_approver_tenant",
            ondelete="RESTRICT",
        ),
        Index("idx_mapping_profile_org", "organization_id"),
        Index("idx_mapping_profile_customer", "organization_id", "customer_id"),
        Index("idx_mapping_profile_family", "profile_family_id"),
        Index("idx_mapping_profile_snapshot", "structure_snapshot_id"),
        Index(
            "uq_mapping_profile_active_customer",
            "organization_id",
            "customer_id",
            "template_fingerprint_sha256",
            unique=True,
            postgresql_where=text("status = 'active' AND scope_type = 'customer'"),
            sqlite_where=text("status = 'active' AND scope_type = 'customer'"),
        ),
        Index(
            "uq_mapping_profile_active_org_template",
            "organization_id",
            "template_fingerprint_sha256",
            unique=True,
            postgresql_where=text(
                "status = 'active' AND scope_type = 'organization_template'"
            ),
            sqlite_where=text(
                "status = 'active' AND scope_type = 'organization_template'"
            ),
        ),
    )


class ColumnMappingField(Base, UUIDMixin):
    """One immutable semantic role assignment per profile/source position."""

    __tablename__ = "column_mapping_fields"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_column_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_column_letter: Mapped[str] = mapped_column(String(16), nullable=False)
    original_header: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_header: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    semantic_role: Mapped[str] = mapped_column(String(64), nullable=False)
    required_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    proposal_source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    proposal_source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    proposal_confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "profile_id"],
            ["column_mapping_profiles.organization_id", "column_mapping_profiles.id"],
            name="fk_mapping_field_profile_tenant",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("profile_id", "source_column_index", name="uq_mapping_field_position"),
        CheckConstraint("source_column_index > 0", name="chk_mapping_field_index_positive"),
        CheckConstraint(
            "semantic_role IN ('row_number', 'raw_asset_name', 'raw_description', 'unit', "
            "'quantity', 'customer_unit_price', 'customer_amount', 'reference_value', "
            "'appraiser_proposed_price', 'evidence_note', 'ignore')",
            name="chk_mapping_field_role",
        ),
        CheckConstraint(
            "proposal_source_kind IN ('human', 'deterministic_rule', 'ai_task')",
            name="chk_mapping_field_source_kind",
        ),
        CheckConstraint(
            "proposal_confidence IS NULL OR "
            "(proposal_confidence >= 0 AND proposal_confidence <= 1)",
            name="chk_mapping_field_confidence",
        ),
        Index("idx_mapping_field_org", "organization_id"),
        Index("idx_mapping_field_profile", "profile_id"),
    )


class ColumnMappingDecision(Base, UUIDMixin):
    """Append-only proposal, confirmation, or rejection business truth."""

    __tablename__ = "column_mapping_decisions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    import_batch_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("import_source_artifacts.id", ondelete="RESTRICT"), nullable=False
    )
    structure_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workbook_structure_snapshots.id", ondelete="RESTRICT"), nullable=False
    )
    decision_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    memory_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    proposal_decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("column_mapping_decisions.id", ondelete="RESTRICT"), nullable=True
    )
    profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("column_mapping_profiles.id", ondelete="RESTRICT"), nullable=True
    )
    supersedes_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("column_mapping_profiles.id", ondelete="RESTRICT"), nullable=True
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    command_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    proposal_source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    proposal_source_version: Mapped[str] = mapped_column(String(64), nullable=False)
    proposal_source_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mapping_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    template_fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_snapshot: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    mapping_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    before_summary: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
    after_summary: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
    reason_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reason_text: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "customer_id",
            "project_id",
            "import_batch_id",
            "source_artifact_id",
            "structure_snapshot_id",
            "id",
            name="uq_mapping_decision_tenant_lineage_id",
        ),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_mapping_decision_customer_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "customer_id", "project_id"],
            ["projects.organization_id", "projects.customer_id", "projects.id"],
            name="fk_mapping_decision_project_customer_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id"],
            [
                "project_asset_import_batches.organization_id",
                "project_asset_import_batches.project_id",
                "project_asset_import_batches.id",
            ],
            name="fk_mapping_decision_batch_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id", "source_artifact_id"],
            [
                "import_source_artifacts.organization_id",
                "import_source_artifacts.project_id",
                "import_source_artifacts.import_batch_id",
                "import_source_artifacts.id",
            ],
            name="fk_mapping_decision_artifact_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            [
                "organization_id",
                "project_id",
                "import_batch_id",
                "source_artifact_id",
                "structure_snapshot_id",
            ],
            [
                "workbook_structure_snapshots.organization_id",
                "workbook_structure_snapshots.project_id",
                "workbook_structure_snapshots.import_batch_id",
                "workbook_structure_snapshots.source_artifact_id",
                "workbook_structure_snapshots.id",
            ],
            name="fk_mapping_decision_structure_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            [
                "organization_id",
                "customer_id",
                "project_id",
                "import_batch_id",
                "source_artifact_id",
                "structure_snapshot_id",
                "proposal_decision_id",
            ],
            [
                "column_mapping_decisions.organization_id",
                "column_mapping_decisions.customer_id",
                "column_mapping_decisions.project_id",
                "column_mapping_decisions.import_batch_id",
                "column_mapping_decisions.source_artifact_id",
                "column_mapping_decisions.structure_snapshot_id",
                "column_mapping_decisions.id",
            ],
            name="fk_mapping_decision_proposal_lineage",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "profile_id"],
            ["column_mapping_profiles.organization_id", "column_mapping_profiles.id"],
            name="fk_mapping_decision_profile_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "supersedes_profile_id"],
            ["column_mapping_profiles.organization_id", "column_mapping_profiles.id"],
            name="fk_mapping_decision_supersedes_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "actor_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_mapping_decision_actor_tenant",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "organization_id", "command_id", name="uq_mapping_decision_command"
        ),
        CheckConstraint(
            "decision_kind IN ('proposal', 'confirmation', 'rejection')",
            name="chk_mapping_decision_kind",
        ),
        CheckConstraint(
            "outcome IN ('proposed', 'accepted', 'corrected', 'rejected')",
            name="chk_mapping_decision_outcome",
        ),
        CheckConstraint(
            "memory_scope IN ('none', 'customer')",
            name="chk_mapping_decision_memory_scope",
        ),
        CheckConstraint(
            "proposal_source_kind IN ('human', 'deterministic_rule', 'ai_task')",
            name="chk_mapping_decision_source_kind",
        ),
        CheckConstraint(
            "(decision_kind = 'proposal' AND outcome = 'proposed' "
            "AND proposal_decision_id IS NULL AND memory_scope = 'none' "
            "AND profile_id IS NULL AND supersedes_profile_id IS NULL) OR "
            "(decision_kind = 'confirmation' AND outcome IN ('accepted', 'corrected') "
            "AND proposal_decision_id IS NOT NULL AND proposal_source_kind = 'human') OR "
            "(decision_kind = 'rejection' AND outcome = 'rejected' "
            "AND proposal_decision_id IS NOT NULL AND memory_scope = 'none' "
            "AND profile_id IS NULL AND supersedes_profile_id IS NULL "
            "AND proposal_source_kind = 'human')",
            name="chk_mapping_decision_shape",
        ),
        CheckConstraint(
            "length(template_fingerprint_sha256) = 64 "
            "AND template_fingerprint_sha256 = lower(template_fingerprint_sha256)",
            name="chk_mapping_decision_fingerprint",
        ),
        CheckConstraint(
            "length(mapping_digest_sha256) = 64 "
            "AND mapping_digest_sha256 = lower(mapping_digest_sha256)",
            name="chk_mapping_decision_digest",
        ),
        Index("idx_mapping_decision_org", "organization_id"),
        Index("idx_mapping_decision_batch", "import_batch_id"),
        Index("idx_mapping_decision_proposal", "proposal_decision_id"),
        Index("idx_mapping_decision_profile", "profile_id"),
    )


class ColumnMappingProfileUsage(Base, UUIDMixin):
    """Append-only exact confirmed mapping used for one source generation."""

    __tablename__ = "column_mapping_profile_usages"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    import_batch_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("import_source_artifacts.id", ondelete="RESTRICT"), nullable=False
    )
    structure_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workbook_structure_snapshots.id", ondelete="RESTRICT"), nullable=False
    )
    confirmation_decision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("column_mapping_decisions.id", ondelete="RESTRICT"), nullable=False
    )
    profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("column_mapping_profiles.id", ondelete="RESTRICT"), nullable=True
    )
    profile_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    command_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    materialization_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    template_fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_snapshot: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    mapping_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    structure_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    materialized_asset_row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_mapping_usage_customer_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "customer_id", "project_id"],
            ["projects.organization_id", "projects.customer_id", "projects.id"],
            name="fk_mapping_usage_project_customer_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id"],
            [
                "project_asset_import_batches.organization_id",
                "project_asset_import_batches.project_id",
                "project_asset_import_batches.id",
            ],
            name="fk_mapping_usage_batch_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id", "source_artifact_id"],
            [
                "import_source_artifacts.organization_id",
                "import_source_artifacts.project_id",
                "import_source_artifacts.import_batch_id",
                "import_source_artifacts.id",
            ],
            name="fk_mapping_usage_artifact_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            [
                "organization_id",
                "project_id",
                "import_batch_id",
                "source_artifact_id",
                "structure_snapshot_id",
            ],
            [
                "workbook_structure_snapshots.organization_id",
                "workbook_structure_snapshots.project_id",
                "workbook_structure_snapshots.import_batch_id",
                "workbook_structure_snapshots.source_artifact_id",
                "workbook_structure_snapshots.id",
            ],
            name="fk_mapping_usage_structure_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            [
                "organization_id",
                "customer_id",
                "project_id",
                "import_batch_id",
                "source_artifact_id",
                "structure_snapshot_id",
                "confirmation_decision_id",
            ],
            [
                "column_mapping_decisions.organization_id",
                "column_mapping_decisions.customer_id",
                "column_mapping_decisions.project_id",
                "column_mapping_decisions.import_batch_id",
                "column_mapping_decisions.source_artifact_id",
                "column_mapping_decisions.structure_snapshot_id",
                "column_mapping_decisions.id",
            ],
            name="fk_mapping_usage_confirmation_lineage",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "profile_id"],
            ["column_mapping_profiles.organization_id", "column_mapping_profiles.id"],
            name="fk_mapping_usage_profile_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_mapping_usage_creator_tenant",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "organization_id",
            "project_id",
            "import_batch_id",
            "source_artifact_id",
            "structure_snapshot_id",
            name="uq_mapping_usage_generation",
        ),
        UniqueConstraint("organization_id", "command_id", name="uq_mapping_usage_command"),
        CheckConstraint(
            "(profile_id IS NULL AND profile_version IS NULL) OR "
            "(profile_id IS NOT NULL AND profile_version IS NOT NULL AND profile_version > 0)",
            name="chk_mapping_usage_profile_version",
        ),
        CheckConstraint(
            "materialized_asset_row_count >= 0",
            name="chk_mapping_usage_row_count",
        ),
        CheckConstraint(
            "length(template_fingerprint_sha256) = 64 "
            "AND template_fingerprint_sha256 = lower(template_fingerprint_sha256)",
            name="chk_mapping_usage_fingerprint",
        ),
        CheckConstraint(
            "length(mapping_digest_sha256) = 64 "
            "AND mapping_digest_sha256 = lower(mapping_digest_sha256)",
            name="chk_mapping_usage_digest",
        ),
        CheckConstraint(
            "length(source_checksum_sha256) = 64 "
            "AND source_checksum_sha256 = lower(source_checksum_sha256)",
            name="chk_mapping_usage_source_checksum",
        ),
        CheckConstraint(
            "length(structure_digest_sha256) = 64 "
            "AND structure_digest_sha256 = lower(structure_digest_sha256)",
            name="chk_mapping_usage_structure_digest",
        ),
        Index("idx_mapping_usage_org", "organization_id"),
        Index("idx_mapping_usage_batch", "import_batch_id"),
        Index("idx_mapping_usage_decision", "confirmation_decision_id"),
        Index("idx_mapping_usage_profile", "profile_id"),
    )


class RawAssetObservation(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "raw_asset_observations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    import_batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_asset_import_batches.id", ondelete="RESTRICT"), nullable=False
    )
    source_artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("import_source_artifacts.id", ondelete="RESTRICT"), nullable=False
    )
    structure_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workbook_structure_snapshots.id", ondelete="RESTRICT"), nullable=False
    )
    staging_row_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("project_asset_import_staging_rows.id", ondelete="SET NULL"), nullable=True
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_asset_name: Mapped[str] = mapped_column(Text, nullable=False)
    raw_unit: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_quantity: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    raw_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    evidence_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    section_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("idx_raw_obs_org", "organization_id"),
        Index("idx_raw_obs_customer", "customer_id"),
        Index("idx_raw_obs_batch", "import_batch_id"),
        Index("idx_raw_obs_artifact", "source_artifact_id"),
    )


class ContextualAssetAliasStatus(str, enum.Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class ContextualAssetAlias(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "contextual_asset_aliases"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=True
    )
    alias_name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_alias_name: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, nullable=True
    )
    asset_variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    source_decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        Index("idx_ctx_alias_org", "organization_id"),
        Index("idx_ctx_alias_customer", "customer_id"),
        Index("idx_ctx_alias_normalized", "organization_id", "customer_id", "normalized_alias_name"),
    )


class AssetIdentityDecision(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "asset_identity_decisions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    raw_observation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("raw_asset_observations.id", ondelete="RESTRICT"), nullable=False
    )
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False)  # accepted, corrected, rejected, deferred
    chosen_canonical_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    chosen_asset_variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    chosen_alias_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    command_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)

    __table_args__ = (
        Index("idx_identity_dec_org", "organization_id"),
        Index("idx_identity_dec_obs", "raw_observation_id"),
        Index("idx_identity_dec_project", "project_id"),
        UniqueConstraint("organization_id", "command_id", name="uq_asset_identity_decision_command"),
    )


class LearningFeedbackEvent(Base, TimestampMixin, UUIDMixin):
    __tablename__ = "learning_feedback_events"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organization_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=True
    )
    source_decision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("asset_identity_decisions.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # positive_match, negative_match
    raw_wording: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # CanonicalAsset, AssetVariant, ContextualAlias
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    feedback_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_feedback_org", "organization_id"),
        Index("idx_feedback_decision", "source_decision_id"),
    )


