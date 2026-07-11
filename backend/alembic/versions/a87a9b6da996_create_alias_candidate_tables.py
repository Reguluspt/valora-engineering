"""create_alias_candidate_tables

Revision ID: a87a9b6da996
Revises: a87a9b6da995
Create Date: 2026-07-07 17:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a87a9b6da996"
down_revision = "a87a9b6da995"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. asset_aliases
    op.create_table(
        "asset_aliases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("alias_scope", sa.String(length=50), nullable=False),
        sa.Column("canonical_asset_id", sa.UUID(), nullable=True),
        sa.Column("asset_variant_id", sa.UUID(), nullable=True),
        sa.Column("raw_alias", sa.String(length=255), nullable=False),
        sa.Column("normalized_alias", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_variant_id"], ["asset_variants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["canonical_asset_id"], ["canonical_assets.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "normalized_alias", "asset_variant_id", name="uq_alias_normalized_variant"
        ),
        sa.UniqueConstraint(
            "normalized_alias", "canonical_asset_id", name="uq_alias_normalized_canonical"
        ),
    )
    op.create_index("ix_asset_aliases_normalized_alias", "asset_aliases", ["normalized_alias"])

    # 2. identity_candidates
    op.create_table(
        "identity_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_asset_line_id", sa.UUID(), nullable=False),
        sa.Column("proposed_canonical_asset_id", sa.UUID(), nullable=True),
        sa.Column("proposed_asset_variant_id", sa.UUID(), nullable=True),
        sa.Column("proposed_taxonomy_node_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("match_method", sa.String(length=50), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_asset_line_id"], ["project_asset_lines.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["proposed_asset_variant_id"], ["asset_variants.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["proposed_canonical_asset_id"], ["canonical_assets.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["proposed_taxonomy_node_id"], ["taxonomy_nodes.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. similarity_scores
    op.create_table(
        "similarity_scores",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("identity_candidate_id", sa.UUID(), nullable=False),
        sa.Column("component", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("metadata_info", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["identity_candidate_id"], ["identity_candidates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("similarity_scores")
    op.drop_table("identity_candidates")
    op.drop_index("ix_asset_aliases_normalized_alias", table_name="asset_aliases")
    op.drop_table("asset_aliases")
