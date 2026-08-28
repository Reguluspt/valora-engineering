"""Create source-pair alignment runs and reviewable row candidates.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-08-26 20:32:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dossier_alignment_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_bundle_id", sa.Uuid(), nullable=False),
        sa.Column("excel_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("report_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("algorithm_version", sa.String(32), nullable=False),
        sa.Column("source_pair_digest_sha256", sa.String(64), nullable=False),
        sa.Column("created_by_job_id", sa.Uuid(), nullable=False),
        sa.Column("generation_token", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("total_excel_rows", sa.Integer(), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("review_required_count", sa.Integer(), nullable=False),
        sa.Column("unresolved_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "dossier_bundle_id",
            "source_pair_digest_sha256",
            "algorithm_version",
            name="uq_dossier_alignment_run_pair_algorithm",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "dossier_bundle_id",
            "id",
            name="uq_dossier_alignment_run_tenant_bundle_id",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "dossier_bundle_id"],
            ["dossier_bundles.organization_id", "dossier_bundles.id"],
            name="fk_dossier_alignment_run_bundle_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "dossier_bundle_id", "excel_snapshot_id"],
            [
                "dossier_extraction_snapshots.organization_id",
                "dossier_extraction_snapshots.dossier_bundle_id",
                "dossier_extraction_snapshots.id",
            ],
            name="fk_dossier_alignment_run_excel_snapshot",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "dossier_bundle_id", "report_snapshot_id"],
            [
                "dossier_extraction_snapshots.organization_id",
                "dossier_extraction_snapshots.dossier_bundle_id",
                "dossier_extraction_snapshots.id",
            ],
            name="fk_dossier_alignment_run_report_snapshot",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_job_id"],
            ["task_jobs.organization_id", "task_jobs.id"],
            name="fk_dossier_alignment_run_job_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "generation_token > 0", name="chk_dossier_alignment_run_generation"
        ),
        sa.CheckConstraint(
            "status IN ('candidate', 'review_required')",
            name="chk_dossier_alignment_run_status",
        ),
        sa.CheckConstraint(
            "total_excel_rows >= 0 AND candidate_count >= 0 "
            "AND review_required_count >= 0 AND unresolved_count >= 0 "
            "AND candidate_count + review_required_count + unresolved_count = total_excel_rows",
            name="chk_dossier_alignment_run_counts",
        ),
        sa.CheckConstraint(
            "length(source_pair_digest_sha256) = 64 "
            "AND source_pair_digest_sha256 = lower(source_pair_digest_sha256)",
            name="chk_dossier_alignment_run_digest",
        ),
    )
    op.create_index(
        "idx_dossier_alignment_run_bundle",
        "dossier_alignment_runs",
        ["organization_id", "dossier_bundle_id"],
    )

    op.create_table(
        "dossier_row_alignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_bundle_id", sa.Uuid(), nullable=False),
        sa.Column("alignment_run_id", sa.Uuid(), nullable=False),
        sa.Column("excel_row_id", sa.Uuid(), nullable=False),
        sa.Column("technical_row_id", sa.Uuid(), nullable=True),
        sa.Column("comparison_row_id", sa.Uuid(), nullable=True),
        sa.Column("final_result_row_id", sa.Uuid(), nullable=True),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("match_basis", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("conflicts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "alignment_run_id",
            "excel_row_id",
            name="uq_dossier_row_alignment_run_excel",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "dossier_bundle_id", "alignment_run_id"],
            [
                "dossier_alignment_runs.organization_id",
                "dossier_alignment_runs.dossier_bundle_id",
                "dossier_alignment_runs.id",
            ],
            name="fk_dossier_row_alignment_run_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "dossier_bundle_id", "excel_row_id"],
            [
                "dossier_extracted_rows.organization_id",
                "dossier_extracted_rows.dossier_bundle_id",
                "dossier_extracted_rows.id",
            ],
            name="fk_dossier_row_alignment_excel_row",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "dossier_bundle_id", "technical_row_id"],
            [
                "dossier_extracted_rows.organization_id",
                "dossier_extracted_rows.dossier_bundle_id",
                "dossier_extracted_rows.id",
            ],
            name="fk_dossier_row_alignment_technical_row",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "dossier_bundle_id", "comparison_row_id"],
            [
                "dossier_extracted_rows.organization_id",
                "dossier_extracted_rows.dossier_bundle_id",
                "dossier_extracted_rows.id",
            ],
            name="fk_dossier_row_alignment_comparison_row",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "dossier_bundle_id", "final_result_row_id"],
            [
                "dossier_extracted_rows.organization_id",
                "dossier_extracted_rows.dossier_bundle_id",
                "dossier_extracted_rows.id",
            ],
            name="fk_dossier_row_alignment_final_row",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "reviewed_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_dossier_row_alignment_reviewer_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "state IN ('candidate', 'review_required', 'confirmed', 'rejected', 'unresolved')",
            name="chk_dossier_row_alignment_state",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="chk_dossier_row_alignment_confidence",
        ),
        sa.CheckConstraint(
            "state = 'unresolved' OR technical_row_id IS NOT NULL "
            "OR comparison_row_id IS NOT NULL OR final_result_row_id IS NOT NULL",
            name="chk_dossier_row_alignment_target_shape",
        ),
        sa.CheckConstraint(
            "(state IN ('confirmed', 'rejected') AND reviewed_by_user_id IS NOT NULL "
            "AND reviewed_at IS NOT NULL) OR "
            "(state NOT IN ('confirmed', 'rejected') AND reviewed_by_user_id IS NULL "
            "AND reviewed_at IS NULL)",
            name="chk_dossier_row_alignment_review_shape",
        ),
    )
    op.create_index(
        "idx_dossier_row_alignment_bundle",
        "dossier_row_alignments",
        ["organization_id", "dossier_bundle_id"],
    )
    op.create_index(
        "idx_dossier_row_alignment_state", "dossier_row_alignments", ["state"]
    )


def downgrade() -> None:
    op.drop_table("dossier_row_alignments")
    op.drop_table("dossier_alignment_runs")
