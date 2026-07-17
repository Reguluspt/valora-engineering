"""create import_source_artifacts and batch current pointer

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_import_batch_tenant_id",
        "project_asset_import_batches",
        ["organization_id", "project_id", "id"],
    )

    op.create_table(
        "import_source_artifacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("import_batch_id", sa.UUID(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("detected_format", sa.String(length=16), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_object_key", sa.String(length=1024), nullable=False),
        sa.Column("storage_etag", sa.String(length=128), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("adapter_name", sa.String(length=64), nullable=True),
        sa.Column("adapter_version", sa.String(length=64), nullable=True),
        sa.Column(
            "adapter_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("orphaned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("generation > 0", name="chk_source_artifact_generation_positive"),
        sa.CheckConstraint("file_size_bytes >= 0", name="chk_source_artifact_size_nonneg"),
        sa.CheckConstraint("length(checksum_sha256) = 64", name="chk_source_artifact_checksum_len"),
        sa.CheckConstraint(
            "checksum_sha256 = lower(checksum_sha256)",
            name="chk_source_artifact_checksum_lower",
        ),
        sa.CheckConstraint(
            "checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_source_artifact_checksum_hex",
        ),
        sa.CheckConstraint(
            "state IN ('pending', 'available', 'failed', 'orphaned')",
            name="chk_source_artifact_state",
        ),
        sa.CheckConstraint(
            "detected_format IN ('xls', 'xlsx')",
            name="chk_source_artifact_format",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["project_asset_import_batches.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organization_profiles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id"],
            [
                "project_asset_import_batches.organization_id",
                "project_asset_import_batches.project_id",
                "project_asset_import_batches.id",
            ],
            name="fk_source_artifact_batch_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("import_batch_id", "generation", name="uq_source_artifact_batch_generation"),
        sa.UniqueConstraint("storage_object_key", name="uq_source_artifact_object_key"),
        sa.UniqueConstraint("import_batch_id", "id", name="uq_source_artifact_batch_id"),
    )
    op.create_index("idx_source_artifact_org", "import_source_artifacts", ["organization_id"])
    op.create_index("idx_source_artifact_project", "import_source_artifacts", ["project_id"])
    op.create_index("idx_source_artifact_batch", "import_source_artifacts", ["import_batch_id"])
    op.create_index("idx_source_artifact_state", "import_source_artifacts", ["state"])

    op.add_column(
        "project_asset_import_batches",
        sa.Column("current_source_artifact_id", sa.UUID(), nullable=True),
    )
    # Same-batch invariant: (batch.id, current_source_artifact_id) → (artifact.import_batch_id, artifact.id)
    op.create_foreign_key(
        "fk_batch_current_artifact_same_batch",
        "project_asset_import_batches",
        "import_source_artifacts",
        ["id", "current_source_artifact_id"],
        ["import_batch_id", "id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_batch_current_artifact_same_batch",
        "project_asset_import_batches",
        type_="foreignkey",
    )
    op.drop_column("project_asset_import_batches", "current_source_artifact_id")
    op.drop_index("idx_source_artifact_state", table_name="import_source_artifacts")
    op.drop_index("idx_source_artifact_batch", table_name="import_source_artifacts")
    op.drop_index("idx_source_artifact_project", table_name="import_source_artifacts")
    op.drop_index("idx_source_artifact_org", table_name="import_source_artifacts")
    op.drop_table("import_source_artifacts")
    op.drop_constraint("uq_import_batch_tenant_id", "project_asset_import_batches", type_="unique")
