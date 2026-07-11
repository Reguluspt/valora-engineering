"""create_queue_conflict_tables

Revision ID: a87a9b6da99e
Revises: a87a9b6da99d
Create Date: 2026-07-07 25:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a87a9b6da99e"
down_revision = "a87a9b6da99d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create knowledge_queue_items
    op.create_table(
        "knowledge_queue_items",
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
        sa.Column("target_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("auto_rejected", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("auto_reject_reason", sa.String(length=255), nullable=True),
        sa.Column("reviewer_id", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by", sa.UUID(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_manual", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_pinned", sa.Boolean(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["reviewer_id"], ["users.id"], name="fk_knowledge_queue_reviewer", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["claimed_by"], ["users.id"], name="fk_knowledge_queue_claimant", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Create knowledge_confidence
    op.create_table(
        "knowledge_confidence",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("confidence_source", sa.String(length=100), nullable=False),
        sa.Column("source_metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. Create knowledge_conflicts
    op.create_table(
        "knowledge_conflicts",
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
        sa.Column("target_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("conflict_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("calculated_value", sa.Float(), nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.UUID(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["resolved_by"],
            ["users.id"],
            name="fk_knowledge_conflicts_resolver",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("knowledge_conflicts")
    op.drop_table("knowledge_confidence")
    op.drop_table("knowledge_queue_items")
