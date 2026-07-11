"""create_taxonomy_core_tables

Revision ID: a87a9b6da993
Revises: a87a9b6da992
Create Date: 2026-07-07 14:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a87a9b6da993"
down_revision = "a87a9b6da992"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. taxonomy_nodes
    op.create_table(
        "taxonomy_nodes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name_vi", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("is_system_seed", sa.Boolean(), nullable=False),
        sa.Column("merged_into_node_id", sa.UUID(), nullable=True),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["taxonomy_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["merged_into_node_id"], ["taxonomy_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # 2. asset_families
    op.create_table(
        "asset_families",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("taxonomy_node_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name_vi", sa.String(length=255), nullable=False),
        sa.Column("default_unit_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("is_system_seed", sa.Boolean(), nullable=False),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["default_unit_id"], ["units.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["taxonomy_node_id"], ["taxonomy_nodes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # 3. asset_dna
    op.create_table(
        "asset_dna",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("asset_family_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["asset_family_id"], ["asset_families.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Partial unique index for one active DNA per family
    op.create_index(
        "uq_active_dna_per_family",
        "asset_dna",
        ["asset_family_id"],
        unique=True,
        sqlite_where=sa.text("status = 'active'"),
        postgresql_where=sa.text("status = 'active'"),
    )

    # 4. asset_attribute_definitions
    op.create_table(
        "asset_attribute_definitions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("asset_dna_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("label_vi", sa.String(length=255), nullable=False),
        sa.Column("data_type", sa.String(length=50), nullable=False),
        sa.Column("unit_id", sa.UUID(), nullable=True),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("is_variant_defining", sa.Boolean(), nullable=False),
        sa.Column("is_searchable", sa.Boolean(), nullable=False),
        sa.Column("enum_values", sa.JSON(), nullable=True),
        sa.Column("validation_rule", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_dna_id"], ["asset_dna.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_dna_id", "key", name="uq_attribute_definition_dna_key"),
    )

    # 5. taxonomy_change_requests
    op.create_table(
        "taxonomy_change_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("change_type", sa.String(length=50), nullable=False),
        sa.Column("node_level", sa.String(length=50), nullable=False),
        sa.Column("parent_node_id", sa.UUID(), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name_vi", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["parent_node_id"], ["taxonomy_nodes.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("taxonomy_change_requests")
    op.drop_table("asset_attribute_definitions")
    op.drop_index("uq_active_dna_per_family", table_name="asset_dna")
    op.drop_table("asset_dna")
    op.drop_table("asset_families")
    op.drop_table("taxonomy_nodes")
