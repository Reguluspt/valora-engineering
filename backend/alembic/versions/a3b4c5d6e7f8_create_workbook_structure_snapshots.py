"""create workbook structure snapshots

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-07-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_source_artifact_tenant_scope_id",
        "import_source_artifacts",
        ["organization_id", "project_id", "import_batch_id", "id"],
    )
    op.create_table(
        "workbook_structure_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("import_batch_id", sa.UUID(), nullable=False),
        sa.Column("source_artifact_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_version", sa.Integer(), nullable=False),
        sa.Column("source_checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("adapter_name", sa.String(length=64), nullable=False),
        sa.Column("adapter_version", sa.String(length=64), nullable=False),
        sa.Column("disposition", sa.String(length=32), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("structure_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("analysis_digest_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "snapshot_version > 0",
            name="chk_workbook_structure_version_positive",
        ),
        sa.CheckConstraint(
            "candidate_count >= 0",
            name="chk_workbook_structure_candidate_count_nonneg",
        ),
        sa.CheckConstraint(
            "length(source_checksum_sha256) = 64",
            name="chk_workbook_structure_source_checksum_len",
        ),
        sa.CheckConstraint(
            "source_checksum_sha256 = lower(source_checksum_sha256)",
            name="chk_workbook_structure_source_checksum_lower",
        ),
        sa.CheckConstraint(
            "source_checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_workbook_structure_source_checksum_hex",
        ),
        sa.CheckConstraint(
            "disposition IN ('proposed', 'review_required')",
            name="chk_workbook_structure_disposition",
        ),
        sa.CheckConstraint(
            "length(analysis_digest_sha256) = 64",
            name="chk_workbook_structure_digest_len",
        ),
        sa.CheckConstraint(
            "analysis_digest_sha256 = lower(analysis_digest_sha256)",
            name="chk_workbook_structure_digest_lower",
        ),
        sa.CheckConstraint(
            "analysis_digest_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_workbook_structure_digest_hex",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
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
            name="fk_workbook_structure_source_tenant",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_artifact_id",
            "snapshot_version",
            name="uq_workbook_structure_artifact_version",
        ),
    )
    op.create_index(
        "idx_workbook_structure_org",
        "workbook_structure_snapshots",
        ["organization_id"],
    )
    op.create_index(
        "idx_workbook_structure_project",
        "workbook_structure_snapshots",
        ["project_id"],
    )
    op.create_index(
        "idx_workbook_structure_batch",
        "workbook_structure_snapshots",
        ["import_batch_id"],
    )
    op.create_index(
        "idx_workbook_structure_artifact",
        "workbook_structure_snapshots",
        ["source_artifact_id"],
    )
    op.create_index(
        "idx_workbook_structure_disposition",
        "workbook_structure_snapshots",
        ["disposition"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_workbook_structure_disposition",
        table_name="workbook_structure_snapshots",
    )
    op.drop_index(
        "idx_workbook_structure_artifact",
        table_name="workbook_structure_snapshots",
    )
    op.drop_index(
        "idx_workbook_structure_batch",
        table_name="workbook_structure_snapshots",
    )
    op.drop_index(
        "idx_workbook_structure_project",
        table_name="workbook_structure_snapshots",
    )
    op.drop_index(
        "idx_workbook_structure_org",
        table_name="workbook_structure_snapshots",
    )
    op.drop_table("workbook_structure_snapshots")
    op.drop_constraint(
        "uq_source_artifact_tenant_scope_id",
        "import_source_artifacts",
        type_="unique",
    )
