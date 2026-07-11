"""create_change_request_tables

Revision ID: a87a9b6da9a1
Revises: a87a9b6da9a0
Create Date: 2026-07-08 26:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a87a9b6da9a1"
down_revision = "a87a9b6da9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. change_requests
    op.create_table(
        "change_requests",
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
        sa.Column("request_code", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("change_type", sa.String(length=50), nullable=False),
        sa.Column("requested_payload", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=False),
        sa.Column("requested_by", sa.UUID(), nullable=False),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("executed_by", sa.UUID(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["requested_by"], ["users.id"], name="fk_change_requests_requester", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"], ["users.id"], name="fk_change_requests_reviewer", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["executed_by"], ["users.id"], name="fk_change_requests_executor", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_code"),
    )

    # 2. review_decision_reversals
    op.create_table(
        "review_decision_reversals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("change_request_id", sa.UUID(), nullable=False),
        sa.Column("original_review_decision_id", sa.UUID(), nullable=False),
        sa.Column("reversal_review_decision_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["change_request_id"],
            ["change_requests.id"],
            name="fk_decision_reversals_request",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["original_review_decision_id"],
            ["review_decisions.id"],
            name="fk_decision_reversals_orig",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reversal_review_decision_id"],
            ["review_decisions.id"],
            name="fk_decision_reversals_rev",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_decision_reversals_creator", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("review_decision_reversals")
    op.drop_table("change_requests")
