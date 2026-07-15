"""add_project_asset_line_import_lineage

Revision ID: e1f2a3b4c5d6
Revises: db5977424e7b
Create Date: 2026-07-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "db5977424e7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_asset_lines",
        sa.Column("source_import_batch_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "project_asset_lines",
        sa.Column("source_staging_row_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_project_asset_lines_source_import_batch_id",
        "project_asset_lines",
        ["source_import_batch_id"],
    )
    op.create_index(
        "ix_project_asset_lines_source_staging_row_id",
        "project_asset_lines",
        ["source_staging_row_id"],
        unique=True,
    )
    op.create_foreign_key(
        "fk_project_asset_lines_source_import_batch_id",
        "project_asset_lines",
        "project_asset_import_batches",
        ["source_import_batch_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_project_asset_lines_source_staging_row_id",
        "project_asset_lines",
        "project_asset_import_staging_rows",
        ["source_staging_row_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_project_asset_lines_source_staging_row_id",
        "project_asset_lines",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_project_asset_lines_source_import_batch_id",
        "project_asset_lines",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_project_asset_lines_source_staging_row_id",
        table_name="project_asset_lines",
    )
    op.drop_index(
        "ix_project_asset_lines_source_import_batch_id",
        table_name="project_asset_lines",
    )
    op.drop_column("project_asset_lines", "source_staging_row_id")
    op.drop_column("project_asset_lines", "source_import_batch_id")
