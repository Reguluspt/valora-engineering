"""Harden dossier ownership and reliable job fencing.

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-08-26 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b0c1d2e3f4a5"
down_revision: Union[str, None] = "a9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _require_unreleased_tables_to_be_empty() -> None:
    """Refuse to reinterpret any locally-created S15 rows."""
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM dossier_source_files LIMIT 1)
                   OR EXISTS (SELECT 1 FROM dossier_bundles LIMIT 1)
                   OR EXISTS (SELECT 1 FROM task_job_attempts LIMIT 1)
                   OR EXISTS (SELECT 1 FROM task_jobs LIMIT 1) THEN
                    RAISE EXCEPTION
                        'S15 hardening requires empty unreleased dossier/job tables; '
                        'export and review local rows before migration';
                END IF;
            END
            $$;
            """
        )
    )


def upgrade() -> None:
    _require_unreleased_tables_to_be_empty()

    op.alter_column("dossier_bundles", "customer_id", nullable=False)
    op.create_unique_constraint(
        "uq_dossier_bundle_tenant_id",
        "dossier_bundles",
        ["organization_id", "id"],
    )
    op.create_foreign_key(
        "fk_dossier_bundle_customer_tenant",
        "dossier_bundles",
        "customers",
        ["organization_id", "customer_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_dossier_bundle_project_tenant",
        "dossier_bundles",
        "projects",
        ["organization_id", "customer_id", "project_id"],
        ["organization_id", "customer_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_dossier_bundle_creator_tenant",
        "dossier_bundles",
        "users",
        ["organization_id", "created_by_user_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "chk_dossier_bundle_status",
        "dossier_bundles",
        "status IN ('pending', 'processing', 'aligned', 'completed', 'failed')",
    )

    op.drop_constraint(
        "uq_dossier_bundle_file_role", "dossier_source_files", type_="unique"
    )
    op.create_foreign_key(
        "fk_dossier_file_bundle_tenant",
        "dossier_source_files",
        "dossier_bundles",
        ["organization_id", "dossier_bundle_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_dossier_bundle_storage_object",
        "dossier_source_files",
        ["dossier_bundle_id", "storage_object_key"],
    )
    op.create_check_constraint(
        "chk_dossier_file_role",
        "dossier_source_files",
        "file_role IN ('customer_asset_list', 'final_appraisal_report', "
        "'comparison_table', 'supplier_quote', 'catalogue', 'approval_or_qc', "
        "'other_evidence')",
    )
    op.create_check_constraint(
        "chk_dossier_file_size_positive",
        "dossier_source_files",
        "file_size_bytes > 0",
    )
    op.create_check_constraint(
        "chk_dossier_file_checksum",
        "dossier_source_files",
        "length(checksum_sha256) = 64 AND checksum_sha256 = lower(checksum_sha256)",
    )
    op.create_check_constraint(
        "chk_dossier_file_storage_key",
        "dossier_source_files",
        "length(trim(storage_object_key)) > 0",
    )
    op.create_index(
        "uq_dossier_primary_file_role",
        "dossier_source_files",
        ["dossier_bundle_id", "file_role"],
        unique=True,
        postgresql_where=sa.text(
            "file_role IN ('customer_asset_list', 'final_appraisal_report')"
        ),
    )

    op.alter_column(
        "task_jobs",
        "payload",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="payload::jsonb",
    )
    op.alter_column(
        "task_jobs",
        "result_payload",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="result_payload::jsonb",
    )
    op.alter_column(
        "task_jobs",
        "generation_token",
        server_default=sa.text("0"),
    )
    op.add_column(
        "task_jobs",
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column("task_jobs", sa.Column("correlation_id", sa.String(128)))
    op.add_column("task_jobs", sa.Column("causation_id", sa.String(128)))
    op.add_column("task_jobs", sa.Column("last_error_code", sa.String(64)))
    op.add_column("task_jobs", sa.Column("last_error_message", sa.Text()))
    op.add_column(
        "task_jobs", sa.Column("completed_at", sa.DateTime(timezone=True))
    )
    op.add_column(
        "task_jobs", sa.Column("cancelled_at", sa.DateTime(timezone=True))
    )
    op.create_unique_constraint(
        "uq_task_job_tenant_id", "task_jobs", ["organization_id", "id"]
    )
    op.create_foreign_key(
        "fk_task_job_creator_tenant",
        "task_jobs",
        "users",
        ["organization_id", "created_by_user_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "chk_task_job_status",
        "task_jobs",
        "status IN ('pending', 'claimed', 'completed', 'failed', "
        "'dead_letter', 'cancelled')",
    )
    op.create_check_constraint(
        "chk_task_job_type_nonempty", "task_jobs", "length(trim(job_type)) > 0"
    )
    op.create_check_constraint(
        "chk_task_job_idempotency_nonempty",
        "task_jobs",
        "length(trim(idempotency_key)) > 0",
    )
    op.create_check_constraint(
        "chk_task_job_generation_nonnegative",
        "task_jobs",
        "generation_token >= 0",
    )
    op.create_check_constraint(
        "chk_task_job_attempt_bounds",
        "task_jobs",
        "attempt_count >= 0 AND max_attempts > 0 AND attempt_count <= max_attempts",
    )
    op.create_check_constraint(
        "chk_task_job_lease_shape",
        "task_jobs",
        "(status = 'claimed' AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL) "
        "OR (status <> 'claimed' AND lease_owner IS NULL AND lease_expires_at IS NULL)",
    )
    op.create_check_constraint(
        "chk_task_job_completed_shape",
        "task_jobs",
        "(status = 'completed' AND completed_at IS NOT NULL) "
        "OR (status <> 'completed' AND completed_at IS NULL)",
    )
    op.create_check_constraint(
        "chk_task_job_cancelled_shape",
        "task_jobs",
        "(status = 'cancelled' AND cancelled_at IS NOT NULL) "
        "OR (status <> 'cancelled' AND cancelled_at IS NULL)",
    )
    op.create_index(
        "idx_task_job_claimable",
        "task_jobs",
        ["status", "available_at", "created_at"],
    )

    op.add_column(
        "task_job_attempts",
        sa.Column(
            "generation_token", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
    )
    op.add_column(
        "task_job_attempts",
        sa.Column(
            "lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column("task_job_attempts", sa.Column("error_code", sa.String(64)))
    op.alter_column("task_job_attempts", "generation_token", server_default=None)
    op.alter_column("task_job_attempts", "lease_expires_at", server_default=None)
    op.create_foreign_key(
        "fk_task_job_attempt_job_tenant",
        "task_job_attempts",
        "task_jobs",
        ["organization_id", "job_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_task_job_attempt_no", "task_job_attempts", ["job_id", "attempt_no"]
    )
    op.create_unique_constraint(
        "uq_task_job_attempt_generation",
        "task_job_attempts",
        ["job_id", "generation_token"],
    )
    op.create_check_constraint(
        "chk_task_job_attempt_no_positive", "task_job_attempts", "attempt_no > 0"
    )
    op.create_check_constraint(
        "chk_task_job_attempt_generation_positive",
        "task_job_attempts",
        "generation_token > 0",
    )
    op.create_check_constraint(
        "chk_task_job_attempt_status",
        "task_job_attempts",
        "status IN ('running', 'succeeded', 'failed', 'timed_out', 'cancelled')",
    )
    op.create_check_constraint(
        "chk_task_job_attempt_finished_shape",
        "task_job_attempts",
        "(status = 'running' AND finished_at IS NULL) "
        "OR (status <> 'running' AND finished_at IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "chk_task_job_attempt_finished_shape", "task_job_attempts", type_="check"
    )
    op.drop_constraint(
        "chk_task_job_attempt_status", "task_job_attempts", type_="check"
    )
    op.drop_constraint(
        "chk_task_job_attempt_generation_positive",
        "task_job_attempts",
        type_="check",
    )
    op.drop_constraint(
        "chk_task_job_attempt_no_positive", "task_job_attempts", type_="check"
    )
    op.drop_constraint(
        "uq_task_job_attempt_generation", "task_job_attempts", type_="unique"
    )
    op.drop_constraint(
        "uq_task_job_attempt_no", "task_job_attempts", type_="unique"
    )
    op.drop_constraint(
        "fk_task_job_attempt_job_tenant", "task_job_attempts", type_="foreignkey"
    )
    op.drop_column("task_job_attempts", "error_code")
    op.drop_column("task_job_attempts", "lease_expires_at")
    op.drop_column("task_job_attempts", "generation_token")

    op.drop_index("idx_task_job_claimable", table_name="task_jobs")
    op.drop_constraint("chk_task_job_cancelled_shape", "task_jobs", type_="check")
    op.drop_constraint("chk_task_job_completed_shape", "task_jobs", type_="check")
    op.drop_constraint("chk_task_job_lease_shape", "task_jobs", type_="check")
    op.drop_constraint("chk_task_job_attempt_bounds", "task_jobs", type_="check")
    op.drop_constraint(
        "chk_task_job_generation_nonnegative", "task_jobs", type_="check"
    )
    op.drop_constraint(
        "chk_task_job_idempotency_nonempty", "task_jobs", type_="check"
    )
    op.drop_constraint("chk_task_job_type_nonempty", "task_jobs", type_="check")
    op.drop_constraint("chk_task_job_status", "task_jobs", type_="check")
    op.drop_constraint("fk_task_job_creator_tenant", "task_jobs", type_="foreignkey")
    op.drop_constraint("uq_task_job_tenant_id", "task_jobs", type_="unique")
    op.drop_column("task_jobs", "cancelled_at")
    op.drop_column("task_jobs", "completed_at")
    op.drop_column("task_jobs", "last_error_message")
    op.drop_column("task_jobs", "last_error_code")
    op.drop_column("task_jobs", "causation_id")
    op.drop_column("task_jobs", "correlation_id")
    op.drop_column("task_jobs", "available_at")
    op.alter_column("task_jobs", "generation_token", server_default=sa.text("1"))
    op.alter_column(
        "task_jobs",
        "result_payload",
        type_=sa.JSON(),
        postgresql_using="result_payload::json",
    )
    op.alter_column(
        "task_jobs",
        "payload",
        type_=sa.JSON(),
        postgresql_using="payload::json",
    )

    op.drop_index("uq_dossier_primary_file_role", table_name="dossier_source_files")
    op.drop_constraint(
        "chk_dossier_file_storage_key", "dossier_source_files", type_="check"
    )
    op.drop_constraint(
        "chk_dossier_file_checksum", "dossier_source_files", type_="check"
    )
    op.drop_constraint(
        "chk_dossier_file_size_positive", "dossier_source_files", type_="check"
    )
    op.drop_constraint("chk_dossier_file_role", "dossier_source_files", type_="check")
    op.drop_constraint(
        "uq_dossier_bundle_storage_object", "dossier_source_files", type_="unique"
    )
    op.drop_constraint(
        "fk_dossier_file_bundle_tenant",
        "dossier_source_files",
        type_="foreignkey",
    )
    op.create_unique_constraint(
        "uq_dossier_bundle_file_role",
        "dossier_source_files",
        ["dossier_bundle_id", "file_role"],
    )

    op.drop_constraint("chk_dossier_bundle_status", "dossier_bundles", type_="check")
    op.drop_constraint(
        "fk_dossier_bundle_creator_tenant", "dossier_bundles", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_dossier_bundle_project_tenant", "dossier_bundles", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_dossier_bundle_customer_tenant", "dossier_bundles", type_="foreignkey"
    )
    op.drop_constraint(
        "uq_dossier_bundle_tenant_id", "dossier_bundles", type_="unique"
    )
    op.alter_column("dossier_bundles", "customer_id", nullable=True)
