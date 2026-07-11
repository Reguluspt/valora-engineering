"""create_canonical_asset_tables

Revision ID: a87a9b6da994
Revises: a87a9b6da993
Create Date: 2026-07-07 15:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a87a9b6da994"
down_revision = "a87a9b6da993"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. canonical_assets
    op.create_table(
        "canonical_assets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("asset_family_id", sa.UUID(), nullable=False),
        sa.Column("primary_taxonomy_node_id", sa.UUID(), nullable=False),
        sa.Column("standard_name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=128), nullable=True),
        sa.Column("brand_id", sa.UUID(), nullable=True),
        sa.Column("manufacturer_id", sa.UUID(), nullable=True),
        sa.Column("country_id", sa.UUID(), nullable=True),
        sa.Column("model_code", sa.String(length=128), nullable=True),
        sa.Column("maturity_level", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("merged_into_asset_id", sa.UUID(), nullable=True),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["asset_family_id"], ["asset_families.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["manufacturer_id"], ["manufacturers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["merged_into_asset_id"], ["canonical_assets.id"]),
        sa.ForeignKeyConstraint(
            ["primary_taxonomy_node_id"], ["taxonomy_nodes.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. canonical_asset_attribute_values
    op.create_table(
        "canonical_asset_attribute_values",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("canonical_asset_id", sa.UUID(), nullable=False),
        sa.Column("attribute_definition_id", sa.UUID(), nullable=False),
        sa.Column("value_string", sa.Text(), nullable=True),
        sa.Column("value_number", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("value_boolean", sa.Boolean(), nullable=True),
        sa.Column("value_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.ForeignKeyConstraint(
            ["attribute_definition_id"], ["asset_attribute_definitions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["canonical_asset_id"], ["canonical_assets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("canonical_asset_attribute_values")
    op.drop_table("canonical_assets")
