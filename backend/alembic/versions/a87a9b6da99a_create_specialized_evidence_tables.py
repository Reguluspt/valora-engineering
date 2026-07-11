"""create_specialized_evidence_tables

Revision ID: a87a9b6da99a
Revises: a87a9b6da999
Create Date: 2026-07-07 21:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a87a9b6da99a"
down_revision = "a87a9b6da999"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create supplier_quote_evidences
    op.create_table(
        "supplier_quote_evidences",
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
        sa.Column("evidence_file_id", sa.UUID(), nullable=False),
        sa.Column("supplier_name", sa.String(length=255), nullable=False),
        sa.Column("quote_number", sa.String(length=128), nullable=True),
        sa.Column("quote_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_amount", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.ForeignKeyConstraint(
            ["evidence_file_id"],
            ["evidence_files.id"],
            name="fk_supplier_quote_evidences_file",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Create catalogue_evidences
    op.create_table(
        "catalogue_evidences",
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
        sa.Column("evidence_file_id", sa.UUID(), nullable=False),
        sa.Column("manufacturer_name", sa.String(length=255), nullable=False),
        sa.Column("catalogue_name", sa.String(length=255), nullable=False),
        sa.Column("page_number", sa.String(length=50), nullable=True),
        sa.Column("product_code", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(
            ["evidence_file_id"],
            ["evidence_files.id"],
            name="fk_catalogue_evidences_file",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. Create internet_evidences
    op.create_table(
        "internet_evidences",
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
        sa.Column("evidence_file_id", sa.UUID(), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("site_name", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["evidence_file_id"],
            ["evidence_files.id"],
            name="fk_internet_evidences_file",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. Create image_evidences
    op.create_table(
        "image_evidences",
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
        sa.Column("evidence_file_id", sa.UUID(), nullable=False),
        sa.Column("resolution", sa.String(length=50), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("camera_metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["evidence_file_id"],
            ["evidence_files.id"],
            name="fk_image_evidences_file",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 5. Create email_evidences
    op.create_table(
        "email_evidences",
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
        sa.Column("evidence_file_id", sa.UUID(), nullable=False),
        sa.Column("sender", sa.String(length=255), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=512), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["evidence_file_id"],
            ["evidence_files.id"],
            name="fk_email_evidences_file",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 6. Create evidence_extraction_results
    op.create_table(
        "evidence_extraction_results",
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
        sa.Column("evidence_file_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("extracted_payload", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["evidence_file_id"],
            ["evidence_files.id"],
            name="fk_evidence_extraction_results_file",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 7. Create evidence_review_decisions
    op.create_table(
        "evidence_review_decisions",
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
        sa.Column("evidence_file_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("reviewer_id", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["evidence_file_id"],
            ["evidence_files.id"],
            name="fk_evidence_review_decisions_file",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            name="fk_evidence_review_decisions_reviewer",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("evidence_review_decisions")
    op.drop_table("evidence_extraction_results")
    op.drop_table("email_evidences")
    op.drop_table("image_evidences")
    op.drop_table("internet_evidences")
    op.drop_table("catalogue_evidences")
    op.drop_table("supplier_quote_evidences")
