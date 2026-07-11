"""create_technical_specification_knowledge_tables

Revision ID: a87a9b6da99b
Revises: a87a9b6da99a
Create Date: 2026-07-07 22:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a87a9b6da99b"
down_revision = "a87a9b6da99a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create technical_specifications
    op.create_table(
        "technical_specifications",
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.Column("canonical_asset_id", sa.UUID(), nullable=True),
        sa.Column("asset_variant_id", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["canonical_asset_id"],
            ["canonical_assets.id"],
            name="fk_tech_spec_canonical",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["asset_variant_id"],
            ["asset_variants.id"],
            name="fk_tech_spec_variant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_tech_spec_creator", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Create technical_specification_versions
    op.create_table(
        "technical_specification_versions",
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("technical_specification_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("attribute_values", sa.JSON(), nullable=False),
        sa.Column("source_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("source_project_id", sa.UUID(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["technical_specification_id"],
            ["technical_specifications.id"],
            name="fk_tech_spec_ver_spec",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_project_id"],
            ["projects.id"],
            name="fk_tech_spec_ver_project",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_tech_spec_ver_creator", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"], ["users.id"], name="fk_tech_spec_ver_approver", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "technical_specification_id", "version_number", name="uq_tech_spec_version_num"
        ),
    )

    # 3. Create knowledge_versions
    op.create_table(
        "knowledge_versions",
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.Column("knowledge_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("concrete_version_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("canonical_asset_id", sa.UUID(), nullable=True),
        sa.Column("asset_variant_id", sa.UUID(), nullable=True),
        sa.Column("source_project_id", sa.UUID(), nullable=True),
        sa.Column("source_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["canonical_asset_id"],
            ["canonical_assets.id"],
            name="fk_knowledge_version_canonical",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["asset_variant_id"],
            ["asset_variants.id"],
            name="fk_knowledge_version_variant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_project_id"],
            ["projects.id"],
            name="fk_knowledge_version_project",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_knowledge_version_active",
        "knowledge_versions",
        ["canonical_asset_id", "asset_variant_id", "knowledge_type", "status"],
    )

    # 4. Create knowledge_lineage
    op.create_table(
        "knowledge_lineage",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("knowledge_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("concrete_version_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("source_project_id", sa.UUID(), nullable=True),
        sa.Column("source_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_project_id"],
            ["projects.id"],
            name="fk_knowledge_lineage_project",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name="fk_knowledge_lineage_actor", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("knowledge_lineage")
    op.drop_index("idx_knowledge_version_active", table_name="knowledge_versions")
    op.drop_table("knowledge_versions")
    op.drop_table("technical_specification_versions")
    op.drop_table("technical_specifications")
