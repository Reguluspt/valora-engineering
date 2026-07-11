"""alter_project_asset_lines

Revision ID: a87a9b6da998
Revises: a87a9b6da997
Create Date: 2026-07-07 19:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a87a9b6da998"
down_revision = "a87a9b6da997"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns to project_asset_lines
    op.add_column(
        "project_asset_lines", sa.Column("suggested_taxonomy_node_id", sa.UUID(), nullable=True)
    )
    op.add_column(
        "project_asset_lines", sa.Column("approved_taxonomy_node_id", sa.UUID(), nullable=True)
    )
    op.add_column(
        "project_asset_lines", sa.Column("suggested_canonical_asset_id", sa.UUID(), nullable=True)
    )
    op.add_column(
        "project_asset_lines", sa.Column("approved_canonical_asset_id", sa.UUID(), nullable=True)
    )
    op.add_column(
        "project_asset_lines", sa.Column("suggested_asset_variant_id", sa.UUID(), nullable=True)
    )
    op.add_column(
        "project_asset_lines", sa.Column("approved_asset_variant_id", sa.UUID(), nullable=True)
    )

    # Add foreign key constraints
    op.create_foreign_key(
        "fk_pal_suggested_taxonomy_node",
        "project_asset_lines",
        "taxonomy_nodes",
        ["suggested_taxonomy_node_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_pal_approved_taxonomy_node",
        "project_asset_lines",
        "taxonomy_nodes",
        ["approved_taxonomy_node_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_pal_suggested_canonical_asset",
        "project_asset_lines",
        "canonical_assets",
        ["suggested_canonical_asset_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_pal_approved_canonical_asset",
        "project_asset_lines",
        "canonical_assets",
        ["approved_canonical_asset_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_pal_suggested_asset_variant",
        "project_asset_lines",
        "asset_variants",
        ["suggested_asset_variant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_pal_approved_asset_variant",
        "project_asset_lines",
        "asset_variants",
        ["approved_asset_variant_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_pal_approved_asset_variant", "project_asset_lines", type_="foreignkey")
    op.drop_constraint("fk_pal_suggested_asset_variant", "project_asset_lines", type_="foreignkey")
    op.drop_constraint("fk_pal_approved_canonical_asset", "project_asset_lines", type_="foreignkey")
    op.drop_constraint(
        "fk_pal_suggested_canonical_asset", "project_asset_lines", type_="foreignkey"
    )
    op.drop_constraint("fk_pal_approved_taxonomy_node", "project_asset_lines", type_="foreignkey")
    op.drop_constraint("fk_pal_suggested_taxonomy_node", "project_asset_lines", type_="foreignkey")

    op.drop_column("project_asset_lines", "approved_asset_variant_id")
    op.drop_column("project_asset_lines", "suggested_asset_variant_id")
    op.drop_column("project_asset_lines", "approved_canonical_asset_id")
    op.drop_column("project_asset_lines", "suggested_canonical_asset_id")
    op.drop_column("project_asset_lines", "approved_taxonomy_node_id")
    op.drop_column("project_asset_lines", "suggested_taxonomy_node_id")
