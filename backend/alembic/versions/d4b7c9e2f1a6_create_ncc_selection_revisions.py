"""Create NCC selection revisions with tenant-hardened quote references.

Revision ID: d4b7c9e2f1a6
Revises: c159fab13c3a
Create Date: 2026-09-05 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d4b7c9e2f1a6"
down_revision: Union[str, None] = "c159fab13c3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Tenant hardening for QuoteBatch and QuoteLine (ADR 0039 D3).
    # organization_id is nullable because existing rows that cannot be
    # backfilled unambiguously are retained as ineligible rather than
    # guessed. New eligible rows require organization_id in application
    # code. supplier_id is added to QuoteLine as nullable and resolved
    # at selection time.
    # ------------------------------------------------------------------
    op.add_column(
        "quote_batches",
        sa.Column("organization_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "idx_quote_batches_organization",
        "quote_batches",
        ["organization_id"],
    )

    # Backfill QuoteBatch.organization_id from creator's organization.
    # Subquery form is compatible with both PostgreSQL and SQLite.
    op.execute(
        """
        UPDATE quote_batches
        SET organization_id = (
            SELECT users.organization_id
            FROM users
            WHERE users.id = quote_batches.created_by
        )
        """
    )

    op.add_column(
        "quote_lines",
        sa.Column("organization_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "quote_lines",
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "idx_quote_lines_organization",
        "quote_lines",
        ["organization_id"],
    )
    op.create_index(
        "idx_quote_lines_supplier",
        "quote_lines",
        ["supplier_id"],
    )

    # Backfill QuoteLine.organization_id from its parent batch.
    op.execute(
        """
        UPDATE quote_lines
        SET organization_id = (
            SELECT quote_batches.organization_id
            FROM quote_batches
            WHERE quote_batches.id = quote_lines.quote_batch_id
        )
        """
    )

    # Foreign keys enforcing the new tenant columns.
    op.create_foreign_key(
        "fk_quote_batches_organization",
        "quote_batches",
        "organization_profiles",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_quote_lines_organization",
        "quote_lines",
        "organization_profiles",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_quote_lines_supplier",
        "quote_lines",
        "suppliers",
        ["supplier_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # SQLite requires composite foreign keys to reference explicit unique/primary
    # key columns. id is already a primary key, so these unique indexes are
    # semantically redundant but required for tenant-safe composite FKs.
    op.create_unique_constraint(
        "uq_quote_batches_tenant_id", "quote_batches", ["organization_id", "id"]
    )
    op.create_unique_constraint(
        "uq_quote_lines_tenant_id", "quote_lines", ["organization_id", "id"]
    )
    op.create_unique_constraint(
        "uq_suppliers_tenant_id", "suppliers", ["organization_id", "id"]
    )
    op.create_unique_constraint(
        "uq_projects_tenant_id", "projects", ["organization_id", "id"]
    )
    op.create_unique_constraint(
        "uq_project_asset_lines_project_id", "project_asset_lines", ["project_id", "id"]
    )

    # ------------------------------------------------------------------
    # Append-only NCC selection revisions (ADR 0039 D5).
    # ------------------------------------------------------------------
    op.create_table(
        "ncc_selection_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("project_asset_line_id", sa.Uuid(), nullable=False),
        sa.Column("selection_revision", sa.Integer(), nullable=False),
        sa.Column("quote_batch_id", sa.Uuid(), nullable=False),
        sa.Column("quote_line_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_file_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_name_snapshot", sa.String(255), nullable=False),
        sa.Column("quoted_unit_price_snapshot", sa.Numeric(15, 2), nullable=False),
        sa.Column("currency_snapshot", sa.String(10), nullable=False),
        sa.Column("quantity_snapshot", sa.Numeric(15, 4), nullable=True),
        sa.Column("unit_of_measure_snapshot", sa.String(50), nullable=True),
        sa.Column("quote_date_snapshot", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "quote_batch_revision_number_snapshot", sa.Integer(), nullable=False
        ),
        sa.Column("current_unit_price_snapshot", sa.Numeric(15, 2), nullable=True),
        sa.Column(
            "current_unit_price_currency_id_snapshot", sa.Uuid(), nullable=True
        ),
        sa.Column("difference_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("difference_percent", sa.Numeric(15, 6), nullable=True),
        sa.Column(
            "warning_codes",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "acknowledged_warning_codes",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_digest_sha256", sa.String(64), nullable=False),
        sa.Column("confirmed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "project_id",
            "project_asset_line_id",
            "selection_revision",
            name="uq_ncc_selection_revision",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_ncc_rev_idempotency_org",
        ),
        sa.UniqueConstraint(
            "organization_id", "id", name="uq_ncc_selection_revisions_tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organization_profiles.id"],
            name="fk_ncc_rev_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            name="fk_ncc_rev_project_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "project_asset_line_id"],
            ["project_asset_lines.project_id", "project_asset_lines.id"],
            name="fk_ncc_rev_asset_line_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "quote_batch_id"],
            ["quote_batches.organization_id", "quote_batches.id"],
            name="fk_ncc_rev_quote_batch_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "quote_line_id"],
            ["quote_lines.organization_id", "quote_lines.id"],
            name="fk_ncc_rev_quote_line_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "supplier_id"],
            ["suppliers.organization_id", "suppliers.id"],
            name="fk_ncc_rev_supplier_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["current_unit_price_currency_id_snapshot"],
            ["currencies.id"],
            name="fk_ncc_rev_current_currency",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_file_id"],
            ["evidence_files.id"],
            name="fk_ncc_rev_evidence",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by_user_id"],
            ["users.id"],
            name="fk_ncc_rev_confirmer",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "selection_revision > 0", name="chk_ncc_rev_selection_revision"
        ),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name="chk_ncc_rev_idempotency_trim",
        ),
        sa.CheckConstraint(
            "length(request_digest_sha256) = 64 "
            "AND request_digest_sha256 = lower(request_digest_sha256) "
            "AND request_digest_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_ncc_rev_request_digest",
        ),
    )
    op.create_index(
        "idx_ncc_rev_project_line",
        "ncc_selection_revisions",
        ["organization_id", "project_id", "project_asset_line_id"],
    )

    # ------------------------------------------------------------------
    # One current head per organization + project + asset line (ADR 0039 D5).
    # ------------------------------------------------------------------
    op.create_table(
        "ncc_selection_current_heads",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("project_asset_line_id", sa.Uuid(), nullable=False),
        sa.Column("current_revision_id", sa.Uuid(), nullable=False),
        sa.Column("selection_revision", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint(
            "organization_id", "project_id", "project_asset_line_id"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organization_profiles.id"],
            name="fk_ncc_head_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            name="fk_ncc_head_project_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "project_asset_line_id"],
            ["project_asset_lines.project_id", "project_asset_lines.id"],
            name="fk_ncc_head_asset_line_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "current_revision_id"],
            ["ncc_selection_revisions.organization_id", "ncc_selection_revisions.id"],
            name="fk_ncc_head_revision_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "selection_revision > 0", name="chk_ncc_head_selection_revision"
        ),
    )


def downgrade() -> None:
    op.drop_table("ncc_selection_current_heads")
    op.drop_index("idx_ncc_rev_project_line", table_name="ncc_selection_revisions")
    op.drop_table("ncc_selection_revisions")

    op.drop_constraint("uq_quote_lines_tenant_id", "quote_lines", type_="unique")
    op.drop_constraint("uq_quote_batches_tenant_id", "quote_batches", type_="unique")
    op.drop_constraint("uq_suppliers_tenant_id", "suppliers", type_="unique")
    op.drop_constraint("uq_projects_tenant_id", "projects", type_="unique")
    op.drop_constraint(
        "uq_project_asset_lines_project_id", "project_asset_lines", type_="unique"
    )

    op.drop_constraint("fk_quote_lines_supplier", "quote_lines", type_="foreignkey")
    op.drop_constraint("fk_quote_lines_organization", "quote_lines", type_="foreignkey")
    op.drop_constraint("fk_quote_batches_organization", "quote_batches", type_="foreignkey")

    op.drop_index("idx_quote_lines_supplier", table_name="quote_lines")
    op.drop_index("idx_quote_lines_organization", table_name="quote_lines")
    op.drop_column("quote_lines", "supplier_id")
    op.drop_column("quote_lines", "organization_id")

    op.drop_index("idx_quote_batches_organization", table_name="quote_batches")
    op.drop_column("quote_batches", "organization_id")
