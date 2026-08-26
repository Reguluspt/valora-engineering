"""Create source-backed dossier extraction snapshots, tables and rows.

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-08-26 20:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b0c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_dossier_file_tenant_bundle_id",
        "dossier_source_files",
        ["organization_id", "dossier_bundle_id", "id"],
    )
    op.create_table(
        "dossier_extraction_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_bundle_id", sa.Uuid(), nullable=False),
        sa.Column("source_file_id", sa.Uuid(), nullable=False),
        sa.Column("source_checksum_sha256", sa.String(64), nullable=False),
        sa.Column("source_kind", sa.String(16), nullable=False),
        sa.Column("parser_name", sa.String(64), nullable=False),
        sa.Column("parser_version", sa.String(32), nullable=False),
        sa.Column("extraction_schema_version", sa.String(32), nullable=False),
        sa.Column("created_by_job_id", sa.Uuid(), nullable=False),
        sa.Column("generation_token", sa.Integer(), nullable=False),
        sa.Column("table_count", sa.Integer(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("extraction_digest_sha256", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_file_id",
            "source_checksum_sha256",
            "parser_name",
            "parser_version",
            "extraction_schema_version",
            name="uq_dossier_extraction_source_parser",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "dossier_bundle_id",
            "id",
            name="uq_dossier_extraction_tenant_bundle_id",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "dossier_bundle_id", "source_file_id"],
            [
                "dossier_source_files.organization_id",
                "dossier_source_files.dossier_bundle_id",
                "dossier_source_files.id",
            ],
            name="fk_dossier_extraction_source_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_job_id"],
            ["task_jobs.organization_id", "task_jobs.id"],
            name="fk_dossier_extraction_job_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "source_kind IN ('excel', 'docx', 'pdf')",
            name="chk_dossier_extraction_source_kind",
        ),
        sa.CheckConstraint(
            "generation_token > 0", name="chk_dossier_extraction_generation"
        ),
        sa.CheckConstraint(
            "table_count >= 0 AND row_count >= 0",
            name="chk_dossier_extraction_counts",
        ),
        sa.CheckConstraint(
            "length(source_checksum_sha256) = 64 "
            "AND source_checksum_sha256 = lower(source_checksum_sha256)",
            name="chk_dossier_extraction_source_checksum",
        ),
        sa.CheckConstraint(
            "length(extraction_digest_sha256) = 64 "
            "AND extraction_digest_sha256 = lower(extraction_digest_sha256)",
            name="chk_dossier_extraction_digest",
        ),
    )
    op.create_index(
        "idx_dossier_extraction_bundle",
        "dossier_extraction_snapshots",
        ["organization_id", "dossier_bundle_id"],
    )
    op.create_index(
        "idx_dossier_extraction_source",
        "dossier_extraction_snapshots",
        ["source_file_id"],
    )

    op.create_table(
        "dossier_extracted_tables",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_bundle_id", sa.Uuid(), nullable=False),
        sa.Column("source_file_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("table_index", sa.Integer(), nullable=False),
        sa.Column("source_kind", sa.String(16), nullable=False),
        sa.Column("table_role_candidate", sa.String(64), nullable=False),
        sa.Column("role_confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("raw_title", sa.String(255), nullable=True),
        sa.Column("sheet_name", sa.String(255), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("header_row_index", sa.Integer(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("col_count", sa.Integer(), nullable=False),
        sa.Column("locator_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "extraction_snapshot_id",
            "table_index",
            name="uq_dossier_extracted_table_index",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "dossier_bundle_id",
            "id",
            name="uq_dossier_extracted_table_tenant_bundle_id",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "dossier_bundle_id", "extraction_snapshot_id"],
            [
                "dossier_extraction_snapshots.organization_id",
                "dossier_extraction_snapshots.dossier_bundle_id",
                "dossier_extraction_snapshots.id",
            ],
            name="fk_dossier_extracted_table_snapshot_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "dossier_bundle_id", "source_file_id"],
            [
                "dossier_source_files.organization_id",
                "dossier_source_files.dossier_bundle_id",
                "dossier_source_files.id",
            ],
            name="fk_dossier_extracted_table_source_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("table_index >= 0", name="chk_dossier_extracted_table_index"),
        sa.CheckConstraint(
            "source_kind IN ('excel', 'docx', 'pdf')",
            name="chk_dossier_extracted_table_source_kind",
        ),
        sa.CheckConstraint(
            "table_role_candidate IN ('excel_customer_asset_table', "
            "'word_technical_asset_table', 'word_quote_comparison_table', "
            "'word_final_result_table', 'unknown')",
            name="chk_dossier_extracted_table_role",
        ),
        sa.CheckConstraint(
            "role_confidence >= 0 AND role_confidence <= 1",
            name="chk_dossier_extracted_table_confidence",
        ),
        sa.CheckConstraint(
            "row_count >= 0 AND col_count >= 0",
            name="chk_dossier_extracted_table_counts",
        ),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="chk_dossier_extracted_table_page",
        ),
    )
    op.create_index(
        "idx_dossier_extracted_table_bundle",
        "dossier_extracted_tables",
        ["organization_id", "dossier_bundle_id"],
    )

    op.create_table(
        "dossier_extracted_rows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_bundle_id", sa.Uuid(), nullable=False),
        sa.Column("source_file_id", sa.Uuid(), nullable=False),
        sa.Column("extracted_table_id", sa.Uuid(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("is_header", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cells_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "normalized_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("locator_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_fingerprint_sha256", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "extracted_table_id", "row_index", name="uq_dossier_extracted_row_index"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "dossier_bundle_id",
            "id",
            name="uq_dossier_extracted_row_tenant_bundle_id",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "dossier_bundle_id", "extracted_table_id"],
            [
                "dossier_extracted_tables.organization_id",
                "dossier_extracted_tables.dossier_bundle_id",
                "dossier_extracted_tables.id",
            ],
            name="fk_dossier_extracted_row_table_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "dossier_bundle_id", "source_file_id"],
            [
                "dossier_source_files.organization_id",
                "dossier_source_files.dossier_bundle_id",
                "dossier_source_files.id",
            ],
            name="fk_dossier_extracted_row_source_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("row_index >= 0", name="chk_dossier_extracted_row_index"),
        sa.CheckConstraint(
            "length(content_fingerprint_sha256) = 64 "
            "AND content_fingerprint_sha256 = lower(content_fingerprint_sha256)",
            name="chk_dossier_extracted_row_fingerprint",
        ),
    )
    op.create_index(
        "idx_dossier_extracted_row_table",
        "dossier_extracted_rows",
        ["extracted_table_id"],
    )


def downgrade() -> None:
    op.drop_table("dossier_extracted_rows")
    op.drop_table("dossier_extracted_tables")
    op.drop_table("dossier_extraction_snapshots")
    op.drop_constraint(
        "uq_dossier_file_tenant_bundle_id", "dossier_source_files", type_="unique"
    )
