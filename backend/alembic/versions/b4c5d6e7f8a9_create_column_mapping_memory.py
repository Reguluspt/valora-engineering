"""create column mapping memory

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-07-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def _jsonb() -> postgresql.JSONB:
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_s13_pr004_user_tenant_id", "users", ["organization_id", "id"]
    )
    op.create_unique_constraint(
        "uq_s13_pr004_customer_tenant_id", "customers", ["organization_id", "id"]
    )
    op.create_unique_constraint(
        "uq_s13_pr004_project_tenant_customer_id",
        "projects",
        ["organization_id", "customer_id", "id"],
    )
    op.create_unique_constraint(
        "uq_workbook_structure_tenant_source_id",
        "workbook_structure_snapshots",
        ["organization_id", "project_id", "import_batch_id", "source_artifact_id", "id"],
    )
    op.create_foreign_key(
        "fk_source_artifact_creator_tenant",
        "import_source_artifacts",
        "users",
        ["organization_id", "created_by_user_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_workbook_structure_creator_tenant",
        "workbook_structure_snapshots",
        "users",
        ["organization_id", "created_by_user_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "column_mapping_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("source_customer_id", sa.UUID(), nullable=False),
        sa.Column("source_project_id", sa.UUID(), nullable=False),
        sa.Column("source_import_batch_id", sa.UUID(), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("profile_family_id", sa.UUID(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("template_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("fingerprint_contract_version", sa.String(length=64), nullable=False),
        sa.Column("mapping_contract_version", sa.String(length=64), nullable=False),
        sa.Column("mapping_digest_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_artifact_id", sa.UUID(), nullable=False),
        sa.Column("structure_snapshot_id", sa.UUID(), nullable=False),
        sa.Column("sheet_name", sa.String(length=255), nullable=False),
        sa.Column("header_start_row", sa.Integer(), nullable=False),
        sa.Column("header_end_row", sa.Integer(), nullable=False),
        sa.Column("data_start_row", sa.Integer(), nullable=False),
        sa.Column("min_column", sa.Integer(), nullable=False),
        sa.Column("max_column", sa.Integer(), nullable=False),
        sa.Column("supersedes_profile_id", sa.UUID(), nullable=True),
        sa.Column("confirmed_by_user_id", sa.UUID(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by_user_id", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint("profile_version > 0", name="chk_mapping_profile_version_positive"),
        sa.CheckConstraint(
            "scope_type IN ('customer', 'organization_template')",
            name="chk_mapping_profile_scope",
        ),
        sa.CheckConstraint(
            "status IN ('candidate', 'active', 'superseded', 'rejected')",
            name="chk_mapping_profile_status",
        ),
        sa.CheckConstraint(
            "header_start_row > 0 AND header_end_row >= header_start_row "
            "AND data_start_row > header_end_row",
            name="chk_mapping_profile_row_bounds",
        ),
        sa.CheckConstraint(
            "min_column > 0 AND max_column >= min_column",
            name="chk_mapping_profile_column_bounds",
        ),
        sa.CheckConstraint(
            "length(template_fingerprint_sha256) = 64 "
            "AND template_fingerprint_sha256 = lower(template_fingerprint_sha256)",
            name="chk_mapping_profile_fingerprint",
        ),
        sa.CheckConstraint(
            "length(mapping_digest_sha256) = 64 "
            "AND mapping_digest_sha256 = lower(mapping_digest_sha256)",
            name="chk_mapping_profile_digest",
        ),
        sa.CheckConstraint(
            "(scope_type = 'customer' AND customer_id IS NOT NULL "
            "AND customer_id = source_customer_id AND approved_by_user_id IS NULL "
            "AND approved_at IS NULL) OR "
            "(scope_type = 'organization_template' AND customer_id IS NULL "
            "AND approved_by_user_id IS NOT NULL AND approved_at IS NOT NULL)",
            name="chk_mapping_profile_scope_fields",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["source_customer_id"], ["customers.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["source_artifact_id"], ["import_source_artifacts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["structure_snapshot_id"],
            ["workbook_structure_snapshots.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_profile_id"], ["column_mapping_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_mapping_profile_customer_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_mapping_profile_source_customer_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_customer_id", "source_project_id"],
            ["projects.organization_id", "projects.customer_id", "projects.id"],
            name="fk_mapping_profile_source_project_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "source_project_id", "source_import_batch_id"],
            [
                "project_asset_import_batches.organization_id",
                "project_asset_import_batches.project_id",
                "project_asset_import_batches.id",
            ],
            name="fk_mapping_profile_source_batch_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
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
        sa.ForeignKeyConstraint(
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
        sa.ForeignKeyConstraint(
            ["organization_id", "supersedes_profile_id"],
            ["column_mapping_profiles.organization_id", "column_mapping_profiles.id"],
            name="fk_mapping_profile_supersedes_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "confirmed_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_mapping_profile_confirmer_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "approved_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_mapping_profile_approver_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_mapping_profile_org_id"),
        sa.UniqueConstraint(
            "profile_family_id", "profile_version", name="uq_mapping_profile_family_version"
        ),
    )
    op.create_index("idx_mapping_profile_org", "column_mapping_profiles", ["organization_id"])
    op.create_index(
        "idx_mapping_profile_customer",
        "column_mapping_profiles",
        ["organization_id", "customer_id"],
    )
    op.create_index(
        "idx_mapping_profile_family", "column_mapping_profiles", ["profile_family_id"]
    )
    op.create_index(
        "idx_mapping_profile_snapshot", "column_mapping_profiles", ["structure_snapshot_id"]
    )
    op.create_index(
        "uq_mapping_profile_active_customer",
        "column_mapping_profiles",
        ["organization_id", "customer_id", "template_fingerprint_sha256"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND scope_type = 'customer'"),
    )
    op.create_index(
        "uq_mapping_profile_active_org_template",
        "column_mapping_profiles",
        ["organization_id", "template_fingerprint_sha256"],
        unique=True,
        postgresql_where=sa.text(
            "status = 'active' AND scope_type = 'organization_template'"
        ),
    )

    op.create_table(
        "column_mapping_fields",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("source_column_index", sa.Integer(), nullable=False),
        sa.Column("source_column_letter", sa.String(length=16), nullable=False),
        sa.Column("original_header", sa.Text(), nullable=True),
        sa.Column("normalized_header", sa.Text(), nullable=True),
        sa.Column("semantic_role", sa.String(length=64), nullable=False),
        sa.Column("required_flag", sa.Boolean(), nullable=False),
        sa.Column("proposal_source_kind", sa.String(length=32), nullable=False),
        sa.Column("proposal_source_version", sa.String(length=64), nullable=False),
        sa.Column("proposal_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint("source_column_index > 0", name="chk_mapping_field_index_positive"),
        sa.CheckConstraint(
            "semantic_role IN ('row_number', 'raw_asset_name', 'raw_description', 'unit', "
            "'quantity', 'customer_unit_price', 'customer_amount', 'reference_value', "
            "'appraiser_proposed_price', 'evidence_note', 'ignore')",
            name="chk_mapping_field_role",
        ),
        sa.CheckConstraint(
            "proposal_source_kind IN ('human', 'deterministic_rule', 'ai_task')",
            name="chk_mapping_field_source_kind",
        ),
        sa.CheckConstraint(
            "proposal_confidence IS NULL OR "
            "(proposal_confidence >= 0 AND proposal_confidence <= 1)",
            name="chk_mapping_field_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "profile_id"],
            ["column_mapping_profiles.organization_id", "column_mapping_profiles.id"],
            name="fk_mapping_field_profile_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "source_column_index", name="uq_mapping_field_position"),
    )
    op.create_index("idx_mapping_field_org", "column_mapping_fields", ["organization_id"])
    op.create_index("idx_mapping_field_profile", "column_mapping_fields", ["profile_id"])

    op.create_table(
        "column_mapping_decisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("import_batch_id", sa.UUID(), nullable=False),
        sa.Column("source_artifact_id", sa.UUID(), nullable=False),
        sa.Column("structure_snapshot_id", sa.UUID(), nullable=False),
        sa.Column("decision_kind", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("memory_scope", sa.String(length=32), nullable=False),
        sa.Column("proposal_decision_id", sa.UUID(), nullable=True),
        sa.Column("profile_id", sa.UUID(), nullable=True),
        sa.Column("supersedes_profile_id", sa.UUID(), nullable=True),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("command_id", sa.UUID(), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("proposal_source_kind", sa.String(length=32), nullable=False),
        sa.Column("proposal_source_version", sa.String(length=64), nullable=False),
        sa.Column("proposal_source_ref", sa.String(length=255), nullable=True),
        sa.Column("mapping_contract_version", sa.String(length=64), nullable=False),
        sa.Column("template_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("mapping_snapshot", _jsonb(), nullable=False),
        sa.Column("mapping_digest_sha256", sa.String(length=64), nullable=False),
        sa.Column("before_summary", _jsonb(), nullable=False),
        sa.Column("after_summary", _jsonb(), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("reason_text", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "decision_kind IN ('proposal', 'confirmation', 'rejection')",
            name="chk_mapping_decision_kind",
        ),
        sa.CheckConstraint(
            "outcome IN ('proposed', 'accepted', 'corrected', 'rejected')",
            name="chk_mapping_decision_outcome",
        ),
        sa.CheckConstraint(
            "memory_scope IN ('none', 'customer')",
            name="chk_mapping_decision_memory_scope",
        ),
        sa.CheckConstraint(
            "proposal_source_kind IN ('human', 'deterministic_rule', 'ai_task')",
            name="chk_mapping_decision_source_kind",
        ),
        sa.CheckConstraint(
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
        sa.CheckConstraint(
            "length(template_fingerprint_sha256) = 64 "
            "AND template_fingerprint_sha256 = lower(template_fingerprint_sha256)",
            name="chk_mapping_decision_fingerprint",
        ),
        sa.CheckConstraint(
            "length(mapping_digest_sha256) = 64 "
            "AND mapping_digest_sha256 = lower(mapping_digest_sha256)",
            name="chk_mapping_decision_digest",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id"],
            [
                "project_asset_import_batches.organization_id",
                "project_asset_import_batches.project_id",
                "project_asset_import_batches.id",
            ],
            name="fk_mapping_decision_batch_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_artifact_id"], ["import_source_artifacts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["structure_snapshot_id"],
            ["workbook_structure_snapshots.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["proposal_decision_id"], ["column_mapping_decisions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["column_mapping_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_profile_id"], ["column_mapping_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_mapping_decision_customer_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id", "project_id"],
            ["projects.organization_id", "projects.customer_id", "projects.id"],
            name="fk_mapping_decision_project_customer_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
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
        sa.ForeignKeyConstraint(
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
        sa.ForeignKeyConstraint(
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
        sa.ForeignKeyConstraint(
            ["organization_id", "profile_id"],
            ["column_mapping_profiles.organization_id", "column_mapping_profiles.id"],
            name="fk_mapping_decision_profile_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "supersedes_profile_id"],
            ["column_mapping_profiles.organization_id", "column_mapping_profiles.id"],
            name="fk_mapping_decision_supersedes_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "actor_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_mapping_decision_actor_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "command_id", name="uq_mapping_decision_command"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "customer_id",
            "project_id",
            "import_batch_id",
            "source_artifact_id",
            "structure_snapshot_id",
            "id",
            name="uq_mapping_decision_tenant_lineage_id",
        ),
    )
    op.create_index("idx_mapping_decision_org", "column_mapping_decisions", ["organization_id"])
    op.create_index("idx_mapping_decision_batch", "column_mapping_decisions", ["import_batch_id"])
    op.create_index(
        "idx_mapping_decision_proposal", "column_mapping_decisions", ["proposal_decision_id"]
    )
    op.create_index("idx_mapping_decision_profile", "column_mapping_decisions", ["profile_id"])

    op.create_table(
        "column_mapping_profile_usages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("import_batch_id", sa.UUID(), nullable=False),
        sa.Column("source_artifact_id", sa.UUID(), nullable=False),
        sa.Column("structure_snapshot_id", sa.UUID(), nullable=False),
        sa.Column("confirmation_decision_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=True),
        sa.Column("command_id", sa.UUID(), nullable=False),
        sa.Column("materialization_contract_version", sa.String(length=64), nullable=False),
        sa.Column("mapping_contract_version", sa.String(length=64), nullable=False),
        sa.Column("template_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("mapping_snapshot", _jsonb(), nullable=False),
        sa.Column("mapping_digest_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("structure_digest_sha256", sa.String(length=64), nullable=False),
        sa.Column("materialized_asset_row_count", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "(profile_id IS NULL AND profile_version IS NULL) OR "
            "(profile_id IS NOT NULL AND profile_version IS NOT NULL AND profile_version > 0)",
            name="chk_mapping_usage_profile_version",
        ),
        sa.CheckConstraint(
            "materialized_asset_row_count >= 0", name="chk_mapping_usage_row_count"
        ),
        sa.CheckConstraint(
            "length(template_fingerprint_sha256) = 64 "
            "AND template_fingerprint_sha256 = lower(template_fingerprint_sha256)",
            name="chk_mapping_usage_fingerprint",
        ),
        sa.CheckConstraint(
            "length(mapping_digest_sha256) = 64 "
            "AND mapping_digest_sha256 = lower(mapping_digest_sha256)",
            name="chk_mapping_usage_digest",
        ),
        sa.CheckConstraint(
            "length(source_checksum_sha256) = 64 "
            "AND source_checksum_sha256 = lower(source_checksum_sha256)",
            name="chk_mapping_usage_source_checksum",
        ),
        sa.CheckConstraint(
            "length(structure_digest_sha256) = 64 "
            "AND structure_digest_sha256 = lower(structure_digest_sha256)",
            name="chk_mapping_usage_structure_digest",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id"],
            [
                "project_asset_import_batches.organization_id",
                "project_asset_import_batches.project_id",
                "project_asset_import_batches.id",
            ],
            name="fk_mapping_usage_batch_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_artifact_id"], ["import_source_artifacts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["structure_snapshot_id"],
            ["workbook_structure_snapshots.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["confirmation_decision_id"],
            ["column_mapping_decisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["column_mapping_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_mapping_usage_customer_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id", "project_id"],
            ["projects.organization_id", "projects.customer_id", "projects.id"],
            name="fk_mapping_usage_project_customer_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
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
        sa.ForeignKeyConstraint(
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
        sa.ForeignKeyConstraint(
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
        sa.ForeignKeyConstraint(
            ["organization_id", "profile_id"],
            ["column_mapping_profiles.organization_id", "column_mapping_profiles.id"],
            name="fk_mapping_usage_profile_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_mapping_usage_creator_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "project_id",
            "import_batch_id",
            "source_artifact_id",
            "structure_snapshot_id",
            name="uq_mapping_usage_generation",
        ),
        sa.UniqueConstraint("organization_id", "command_id", name="uq_mapping_usage_command"),
    )
    op.create_index("idx_mapping_usage_org", "column_mapping_profile_usages", ["organization_id"])
    op.create_index(
        "idx_mapping_usage_batch", "column_mapping_profile_usages", ["import_batch_id"]
    )
    op.create_index(
        "idx_mapping_usage_decision",
        "column_mapping_profile_usages",
        ["confirmation_decision_id"],
    )
    op.create_index(
        "idx_mapping_usage_profile", "column_mapping_profile_usages", ["profile_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_mapping_usage_profile", table_name="column_mapping_profile_usages")
    op.drop_index("idx_mapping_usage_decision", table_name="column_mapping_profile_usages")
    op.drop_index("idx_mapping_usage_batch", table_name="column_mapping_profile_usages")
    op.drop_index("idx_mapping_usage_org", table_name="column_mapping_profile_usages")
    op.drop_table("column_mapping_profile_usages")

    op.drop_index("idx_mapping_decision_profile", table_name="column_mapping_decisions")
    op.drop_index("idx_mapping_decision_proposal", table_name="column_mapping_decisions")
    op.drop_index("idx_mapping_decision_batch", table_name="column_mapping_decisions")
    op.drop_index("idx_mapping_decision_org", table_name="column_mapping_decisions")
    op.drop_table("column_mapping_decisions")

    op.drop_index("idx_mapping_field_profile", table_name="column_mapping_fields")
    op.drop_index("idx_mapping_field_org", table_name="column_mapping_fields")
    op.drop_table("column_mapping_fields")

    op.drop_index(
        "uq_mapping_profile_active_org_template", table_name="column_mapping_profiles"
    )
    op.drop_index("uq_mapping_profile_active_customer", table_name="column_mapping_profiles")
    op.drop_index("idx_mapping_profile_snapshot", table_name="column_mapping_profiles")
    op.drop_index("idx_mapping_profile_family", table_name="column_mapping_profiles")
    op.drop_index("idx_mapping_profile_customer", table_name="column_mapping_profiles")
    op.drop_index("idx_mapping_profile_org", table_name="column_mapping_profiles")
    op.drop_table("column_mapping_profiles")

    op.drop_constraint(
        "fk_workbook_structure_creator_tenant",
        "workbook_structure_snapshots",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_source_artifact_creator_tenant",
        "import_source_artifacts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_workbook_structure_tenant_source_id",
        "workbook_structure_snapshots",
        type_="unique",
    )
    op.drop_constraint(
        "uq_s13_pr004_project_tenant_customer_id", "projects", type_="unique"
    )
    op.drop_constraint(
        "uq_s13_pr004_customer_tenant_id", "customers", type_="unique"
    )
    op.drop_constraint("uq_s13_pr004_user_tenant_id", "users", type_="unique")
