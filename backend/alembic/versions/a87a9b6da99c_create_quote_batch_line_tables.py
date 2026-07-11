"""create_quote_batch_line_tables

Revision ID: a87a9b6da99c
Revises: a87a9b6da99b
Create Date: 2026-07-07 23:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a87a9b6da99c"
down_revision = "a87a9b6da99b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create quote_batches
    op.create_table(
        "quote_batches",
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
        sa.Column("canonical_asset_id", sa.UUID(), nullable=True),
        sa.Column("asset_variant_id", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("revision_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("previous_quote_batch_id", sa.UUID(), nullable=True),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("override_blocking_conflict_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["canonical_asset_id"],
            ["canonical_assets.id"],
            name="fk_quote_batches_canonical",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["asset_variant_id"],
            ["asset_variants.id"],
            name="fk_quote_batches_variant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_quote_batches_creator", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"], ["users.id"], name="fk_quote_batches_approver", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["previous_quote_batch_id"],
            ["quote_batches.id"],
            name="fk_quote_batches_previous",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Create quote_lines
    op.create_table(
        "quote_lines",
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
        sa.Column("quote_batch_id", sa.UUID(), nullable=False),
        sa.Column("evidence_file_id", sa.UUID(), nullable=True),
        sa.Column("supplier_name", sa.String(length=255), nullable=False),
        sa.Column("quoted_unit_price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("unit_of_measure", sa.String(length=50), nullable=True),
        sa.Column("quote_label", sa.String(length=255), nullable=True),
        sa.Column("quote_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(
            ["quote_batch_id"],
            ["quote_batches.id"],
            name="fk_quote_lines_batch",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_file_id"],
            ["evidence_files.id"],
            name="fk_quote_lines_evidence",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("quote_lines")
    op.drop_table("quote_batches")
