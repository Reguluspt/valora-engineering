"""create_asset_import_staging_tables

Revision ID: a87a9b6da9a4
Revises: a87a9b6da9a3
Create Date: 2026-07-11 09:15:00.000000

"""

from typing import Sequence, Optional, Union
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a87a9b6da9a4"
down_revision: Optional[str] = "a87a9b6da9a3"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    # 1. project_asset_import_batches
    op.create_table(
        "project_asset_import_batches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("source_sheet_name", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("valid_rows", sa.Integer(), nullable=False),
        sa.Column("invalid_rows", sa.Integer(), nullable=False),
        sa.Column("warning_rows", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )

    op.create_index("idx_import_batch_org", "project_asset_import_batches", ["organization_id"])
    op.create_index("idx_import_batch_project", "project_asset_import_batches", ["project_id"])

    # 2. project_asset_import_staging_rows
    op.create_table(
        "project_asset_import_staging_rows",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("import_batch_id", sa.UUID(), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("raw_values", sa.JSON(), nullable=False),
        sa.Column("mapped_values", sa.JSON(), nullable=False),
        sa.Column("normalized_preview", sa.JSON(), nullable=False),
        sa.Column("validation_status", sa.String(length=50), nullable=False),
        sa.Column("validation_errors", sa.JSON(), nullable=False),
        sa.Column("validation_warnings", sa.JSON(), nullable=False),
        sa.Column("proposed_asset_name", sa.String(length=255), nullable=True),
        sa.Column("proposed_description", sa.Text(), nullable=True),
        sa.Column("proposed_quantity", sa.String(length=50), nullable=True),
        sa.Column("proposed_unit", sa.String(length=50), nullable=True),
        sa.Column("proposed_raw_price", sa.String(length=50), nullable=True),
        sa.Column("proposed_currency", sa.String(length=10), nullable=True),
        sa.Column("proposed_appraised_unit_price", sa.String(length=50), nullable=True),
        sa.Column("proposed_review_status", sa.String(length=50), nullable=True),
        sa.Column("proposed_validation_status", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["import_batch_id"], ["project_asset_import_batches.id"], ondelete="CASCADE"
        ),
    )

    op.create_index("idx_staging_row_org", "project_asset_import_staging_rows", ["organization_id"])
    op.create_index("idx_staging_row_project", "project_asset_import_staging_rows", ["project_id"])
    op.create_index(
        "idx_staging_row_batch", "project_asset_import_staging_rows", ["import_batch_id"]
    )
    op.create_index(
        "idx_staging_row_validation", "project_asset_import_staging_rows", ["validation_status"]
    )


def downgrade() -> None:
    op.drop_index("idx_staging_row_validation", table_name="project_asset_import_staging_rows")
    op.drop_index("idx_staging_row_batch", table_name="project_asset_import_staging_rows")
    op.drop_index("idx_staging_row_project", table_name="project_asset_import_staging_rows")
    op.drop_index("idx_staging_row_org", table_name="project_asset_import_staging_rows")
    op.drop_table("project_asset_import_staging_rows")

    op.drop_index("idx_import_batch_project", table_name="project_asset_import_batches")
    op.drop_index("idx_import_batch_org", table_name="project_asset_import_batches")
    op.drop_table("project_asset_import_batches")
