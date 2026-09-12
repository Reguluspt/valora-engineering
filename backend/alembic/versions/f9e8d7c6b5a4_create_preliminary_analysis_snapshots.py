"""Create preliminary analysis snapshots.

Revision ID: f9e8d7c6b5a4
Revises: e3f4a5b6c7d8
Create Date: 2026-09-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f9e8d7c6b5a4"
down_revision: Union[str, None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_mapping_usage_generation_id",
        "column_mapping_profile_usages",
        [
            "organization_id",
            "project_id",
            "import_batch_id",
            "source_artifact_id",
            "structure_snapshot_id",
            "id",
        ],
    )
    op.create_table(
        "preliminary_analysis_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("import_batch_id", sa.Uuid(), nullable=False),
        sa.Column("source_artifact_id", sa.Uuid(), nullable=False),
        sa.Column("structure_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("mapping_decision_id", sa.Uuid(), nullable=False),
        sa.Column("mapping_profile_usage_id", sa.Uuid(), nullable=False),
        sa.Column("source_artifact_generation", sa.Integer(), nullable=False),
        sa.Column("mapping_decision_digest_sha256", sa.String(64), nullable=False),
        sa.Column("profile_usage_mapping_digest_sha256", sa.String(64), nullable=False),
        sa.Column(
            "line_manifest",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("line_manifest_digest_sha256", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_digest_sha256", sa.String(64), nullable=False),
        sa.Column("finalized_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "finalized_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "project_id",
            "version",
            name="uq_preliminary_analysis_project_version",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_preliminary_analysis_idempotency",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id", "project_id"],
            ["projects.organization_id", "projects.customer_id", "projects.id"],
            name="fk_preliminary_analysis_project_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id"],
            [
                "project_asset_import_batches.organization_id",
                "project_asset_import_batches.project_id",
                "project_asset_import_batches.id",
            ],
            name="fk_preliminary_analysis_batch_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
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
            name="fk_preliminary_analysis_artifact_tenant",
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
            name="fk_preliminary_analysis_structure_tenant",
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
                "mapping_decision_id",
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
            name="fk_preliminary_analysis_decision_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            [
                "organization_id",
                "project_id",
                "import_batch_id",
                "source_artifact_id",
                "structure_snapshot_id",
                "mapping_profile_usage_id",
            ],
            [
                "column_mapping_profile_usages.organization_id",
                "column_mapping_profile_usages.project_id",
                "column_mapping_profile_usages.import_batch_id",
                "column_mapping_profile_usages.source_artifact_id",
                "column_mapping_profile_usages.structure_snapshot_id",
                "column_mapping_profile_usages.id",
            ],
            name="fk_preliminary_analysis_usage_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "finalized_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_preliminary_analysis_actor_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("version > 0", name="chk_preliminary_analysis_version"),
        sa.CheckConstraint(
            "source_artifact_generation > 0",
            name="chk_preliminary_analysis_generation",
        ),
        sa.CheckConstraint(
            "length(mapping_decision_digest_sha256) = 64 "
            "AND mapping_decision_digest_sha256 = lower(mapping_decision_digest_sha256) "
            "AND mapping_decision_digest_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_preliminary_analysis_decision_digest",
        ),
        sa.CheckConstraint(
            "length(profile_usage_mapping_digest_sha256) = 64 "
            "AND profile_usage_mapping_digest_sha256 = lower(profile_usage_mapping_digest_sha256) "
            "AND profile_usage_mapping_digest_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_preliminary_analysis_usage_digest",
        ),
        sa.CheckConstraint(
            "length(line_manifest_digest_sha256) = 64 "
            "AND line_manifest_digest_sha256 = lower(line_manifest_digest_sha256) "
            "AND line_manifest_digest_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_preliminary_analysis_line_manifest_digest",
        ),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name="chk_preliminary_analysis_idempotency",
        ),
        sa.CheckConstraint(
            "length(request_digest_sha256) = 64 "
            "AND request_digest_sha256 = lower(request_digest_sha256) "
            "AND request_digest_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_preliminary_analysis_request_digest",
        ),
    )
    op.create_index(
        "idx_preliminary_analysis_project",
        "preliminary_analysis_snapshots",
        ["organization_id", "project_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_preliminary_analysis_project",
        table_name="preliminary_analysis_snapshots",
    )
    op.drop_table("preliminary_analysis_snapshots")
    op.drop_constraint(
        "uq_mapping_usage_generation_id",
        "column_mapping_profile_usages",
        type_="unique",
    )
