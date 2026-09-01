"""Create preliminary-result artifacts and official-intake commits.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-09-01 23:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "preliminary_result_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("content_checksum_sha256", sa.String(64), nullable=False),
        sa.Column("storage_object_key", sa.String(1024), nullable=False),
        sa.Column("source_snapshot_sha256", sa.String(64), nullable=False),
        sa.Column(
            "lineage_manifest",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "project_id",
            "version",
            name="uq_preliminary_result_project_version",
        ),
        sa.UniqueConstraint(
            "storage_object_key", name="uq_preliminary_result_storage_object"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "customer_id",
            "project_id",
            "id",
            name="uq_preliminary_result_tenant_project_id",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id", "project_id"],
            ["projects.organization_id", "projects.customer_id", "projects.id"],
            name="fk_preliminary_result_project_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_preliminary_result_creator_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("version > 0", name="chk_preliminary_result_version"),
        sa.CheckConstraint("file_size_bytes >= 0", name="chk_preliminary_result_size"),
        sa.CheckConstraint(
            "length(content_checksum_sha256) = 64 "
            "AND content_checksum_sha256 = lower(content_checksum_sha256) "
            "AND content_checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_preliminary_result_content_checksum",
        ),
        sa.CheckConstraint(
            "length(source_snapshot_sha256) = 64 "
            "AND source_snapshot_sha256 = lower(source_snapshot_sha256) "
            "AND source_snapshot_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_preliminary_result_source_snapshot",
        ),
    )
    op.create_index(
        "idx_preliminary_result_project",
        "preliminary_result_artifacts",
        ["organization_id", "project_id"],
    )

    op.create_table(
        "project_official_intake_commits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("preliminary_result_artifact_id", sa.Uuid(), nullable=False),
        sa.Column("preliminary_result_version", sa.Integer(), nullable=False),
        sa.Column("preliminary_result_sha256", sa.String(64), nullable=False),
        sa.Column("source_snapshot_sha256", sa.String(64), nullable=False),
        sa.Column("project_version_before", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_digest_sha256", sa.String(64), nullable=False),
        sa.Column("committed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "committed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "project_id", name="uq_official_intake_project"
        ),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_official_intake_idempotency"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "customer_id", "project_id"],
            ["projects.organization_id", "projects.customer_id", "projects.id"],
            name="fk_official_intake_project_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            [
                "organization_id",
                "customer_id",
                "project_id",
                "preliminary_result_artifact_id",
            ],
            [
                "preliminary_result_artifacts.organization_id",
                "preliminary_result_artifacts.customer_id",
                "preliminary_result_artifacts.project_id",
                "preliminary_result_artifacts.id",
            ],
            name="fk_official_intake_artifact_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "committed_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_official_intake_actor_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "preliminary_result_version > 0", name="chk_official_intake_artifact_version"
        ),
        sa.CheckConstraint(
            "project_version_before > 0", name="chk_official_intake_project_version"
        ),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) > 0", name="chk_official_intake_idempotency"
        ),
        sa.CheckConstraint(
            "length(preliminary_result_sha256) = 64 "
            "AND preliminary_result_sha256 = lower(preliminary_result_sha256) "
            "AND preliminary_result_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_official_intake_result_checksum",
        ),
        sa.CheckConstraint(
            "length(source_snapshot_sha256) = 64 "
            "AND source_snapshot_sha256 = lower(source_snapshot_sha256) "
            "AND source_snapshot_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_official_intake_source_snapshot",
        ),
        sa.CheckConstraint(
            "length(request_digest_sha256) = 64 "
            "AND request_digest_sha256 = lower(request_digest_sha256) "
            "AND request_digest_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_official_intake_request_digest",
        ),
    )
    op.create_index(
        "idx_official_intake_project",
        "project_official_intake_commits",
        ["organization_id", "project_id"],
    )


def downgrade() -> None:
    op.drop_table("project_official_intake_commits")
    op.drop_table("preliminary_result_artifacts")
