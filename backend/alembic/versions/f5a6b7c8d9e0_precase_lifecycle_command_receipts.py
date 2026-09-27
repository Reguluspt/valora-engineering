"""Durable receipts for Pre-case Customer binding and current-batch switching.

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "preliminary_project_lifecycle_command_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("command_type", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_digest_sha256", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("expected_project_version", sa.Integer(), nullable=False),
        sa.Column("committed_project_version", sa.Integer(), nullable=False),
        sa.Column("target_customer_id", sa.Uuid(), nullable=True),
        sa.Column("previous_import_batch_id", sa.Uuid(), nullable=True),
        sa.Column("target_import_batch_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "(command_type = 'BindPreliminaryProjectCustomer' "
            "AND target_customer_id IS NOT NULL AND target_import_batch_id IS NULL "
            "AND previous_import_batch_id IS NULL) OR "
            "(command_type = 'SwitchCurrentPreliminaryImportBatch' "
            "AND target_customer_id IS NULL AND target_import_batch_id IS NOT NULL "
            "AND previous_import_batch_id IS NOT NULL)",
            name="chk_preliminary_lifecycle_outcome_shape",
        ),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) > 0", name="chk_preliminary_lifecycle_key"
        ),
        sa.CheckConstraint(
            "request_digest_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_preliminary_lifecycle_digest",
        ),
        sa.CheckConstraint(
            "expected_project_version > 0 AND committed_project_version = expected_project_version + 1",
            name="chk_preliminary_lifecycle_versions",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id"], ["projects.organization_id", "projects.id"],
            name="fk_preliminary_lifecycle_project_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "actor_user_id"], ["users.organization_id", "users.id"],
            name="fk_preliminary_lifecycle_actor_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "target_customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_preliminary_lifecycle_customer_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "target_import_batch_id"],
            ["project_asset_import_batches.organization_id",
             "project_asset_import_batches.project_id", "project_asset_import_batches.id"],
            name="fk_preliminary_lifecycle_target_batch_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "previous_import_batch_id"],
            ["project_asset_import_batches.organization_id",
             "project_asset_import_batches.project_id", "project_asset_import_batches.id"],
            name="fk_preliminary_lifecycle_previous_batch_tenant", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_preliminary_lifecycle_idempotency"
        ),
    )
    op.create_index(
        "idx_preliminary_lifecycle_project", "preliminary_project_lifecycle_command_receipts",
        ["organization_id", "project_id"],
    )


def downgrade() -> None:
    if op.get_bind().execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM preliminary_project_lifecycle_command_receipts)"
    )).scalar_one():
        raise RuntimeError("G1.1B downgrade refused: committed lifecycle receipts cannot be discarded")
    op.drop_index(
        "idx_preliminary_lifecycle_project",
        table_name="preliminary_project_lifecycle_command_receipts",
    )
    op.drop_table("preliminary_project_lifecycle_command_receipts")
