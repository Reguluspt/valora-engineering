"""Create sealed M365 content baselines and revalidation observations.

Revision ID: a6d9e4c2b8f1
Revises: f4c8d2a1b7e9
Create Date: 2026-09-12 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a6d9e4c2b8f1"
down_revision: Union[str, None] = "f4c8d2a1b7e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _digest_check(column: str, *, nullable: bool = False) -> str:
    expression = (
        f"length({column}) = 64 "
        f"AND {column} = lower({column}) "
        f"AND {column} ~ '^[0-9a-f]{{64}}$'"
    )
    return f"{column} IS NULL OR ({expression})" if nullable else expression


def upgrade() -> None:
    op.create_table(
        "m365_managed_content_baselines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_revision_id", sa.Uuid(), nullable=False),
        sa.Column("binding_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("drive_id", sa.String(255), nullable=False),
        sa.Column("drive_item_id", sa.String(255), nullable=False),
        sa.Column("source_content_sha256", sa.String(64), nullable=False),
        sa.Column("source_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("source_e_tag", sa.String(512), nullable=False),
        sa.Column("source_c_tag", sa.String(512), nullable=True),
        sa.Column("bind_metadata_digest_sha256", sa.String(64), nullable=False),
        sa.Column("authority_ref", sa.String(255), nullable=False),
        sa.Column("parser_contract_version", sa.String(64), nullable=False),
        sa.Column("fingerprint_contract_version", sa.String(64), nullable=False),
        sa.Column("managed_region_manifest_digest_sha256", sa.String(64), nullable=False),
        sa.Column("outside_managed_digest_sha256", sa.String(64), nullable=False),
        sa.Column("whole_canonical_digest_sha256", sa.String(64), nullable=False),
        sa.Column("provenance_kind", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_digest_sha256", sa.String(64), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "binding_id", name="uq_m365_content_baseline_binding"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_m365_content_baseline_idempotency",
        ),
        sa.UniqueConstraint(
            "organization_id", "id", name="uq_m365_content_baselines_tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "binding_id"],
            ["m365_revision_bindings.organization_id", "m365_revision_bindings.id"],
            name="fk_m365_content_baseline_binding_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id", "document_revision_id"],
            [
                "document_revisions.organization_id",
                "document_revisions.project_id",
                "document_revisions.document_id",
                "document_revisions.id",
            ],
            name="fk_m365_content_baseline_revision_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "connection_id"],
            ["onedrive_connections.organization_id", "onedrive_connections.id"],
            name="fk_m365_content_baseline_connection_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_m365_content_baseline_actor_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("source_size_bytes >= 0", name="chk_m365_content_baseline_size"),
        sa.CheckConstraint(
            "provenance_kind IN ('existing_binding_verified', 'new_binding_atomic')",
            name="chk_m365_content_baseline_provenance",
        ),
        sa.CheckConstraint(
            "length(trim(authority_ref)) > 0",
            name="chk_m365_content_baseline_authority",
        ),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name="chk_m365_content_baseline_idempotency_trim",
        ),
        sa.CheckConstraint(
            _digest_check("source_content_sha256"),
            name="chk_m365_content_baseline_source_digest",
        ),
        sa.CheckConstraint(
            _digest_check("bind_metadata_digest_sha256"),
            name="chk_m365_content_baseline_metadata_digest",
        ),
        sa.CheckConstraint(
            _digest_check("managed_region_manifest_digest_sha256"),
            name="chk_m365_content_baseline_manifest_digest",
        ),
        sa.CheckConstraint(
            _digest_check("outside_managed_digest_sha256"),
            name="chk_m365_content_baseline_outside_digest",
        ),
        sa.CheckConstraint(
            _digest_check("whole_canonical_digest_sha256"),
            name="chk_m365_content_baseline_whole_digest",
        ),
        sa.CheckConstraint(
            _digest_check("request_digest_sha256"),
            name="chk_m365_content_baseline_request_digest",
        ),
    )
    op.create_index(
        "idx_m365_content_baseline_revision",
        "m365_managed_content_baselines",
        ["organization_id", "project_id", "document_id", "document_revision_id"],
    )

    op.create_table(
        "m365_managed_region_baselines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("content_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("region_key", sa.String(128), nullable=False),
        sa.Column("locator", sa.String(255), nullable=False),
        sa.Column("locator_digest_sha256", sa.String(64), nullable=False),
        sa.Column("semantic_type", sa.String(32), nullable=False),
        sa.Column("normalization_contract", sa.String(64), nullable=False),
        sa.Column("normalized_value_digest_sha256", sa.String(64), nullable=False),
        sa.Column("structural_digest_sha256", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "content_baseline_id",
            "region_key",
            name="uq_m365_region_baseline_key",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "content_baseline_id",
            "position",
            name="uq_m365_region_baseline_position",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "content_baseline_id"],
            [
                "m365_managed_content_baselines.organization_id",
                "m365_managed_content_baselines.id",
            ],
            name="fk_m365_region_baseline_parent_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("position >= 0", name="chk_m365_region_baseline_position"),
        sa.CheckConstraint(
            "length(trim(region_key)) > 0 AND length(trim(locator)) > 0",
            name="chk_m365_region_baseline_identity",
        ),
        sa.CheckConstraint(
            _digest_check("locator_digest_sha256"),
            name="chk_m365_region_baseline_locator_digest",
        ),
        sa.CheckConstraint(
            _digest_check("normalized_value_digest_sha256"),
            name="chk_m365_region_baseline_value_digest",
        ),
        sa.CheckConstraint(
            _digest_check("structural_digest_sha256"),
            name="chk_m365_region_baseline_structure_digest",
        ),
    )
    op.create_index(
        "idx_m365_region_baseline_parent",
        "m365_managed_region_baselines",
        ["organization_id", "content_baseline_id"],
    )

    op.create_table(
        "m365_revalidation_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_revision_id", sa.Uuid(), nullable=False),
        sa.Column("binding_id", sa.Uuid(), nullable=False),
        sa.Column("content_baseline_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("trigger", sa.String(40), nullable=False),
        sa.Column("classification", sa.String(48), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("observed_drive_id", sa.String(255), nullable=True),
        sa.Column("observed_drive_item_id", sa.String(255), nullable=True),
        sa.Column("observed_graph_version_id", sa.String(255), nullable=True),
        sa.Column("observed_e_tag", sa.String(512), nullable=True),
        sa.Column("observed_c_tag", sa.String(512), nullable=True),
        sa.Column("observed_last_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("observed_name", sa.String(255), nullable=True),
        sa.Column("observed_path", sa.String(2048), nullable=True),
        sa.Column("observed_web_url", sa.String(2048), nullable=True),
        sa.Column("observed_content_sha256", sa.String(64), nullable=True),
        sa.Column("observed_whole_canonical_digest_sha256", sa.String(64), nullable=True),
        sa.Column("observed_outside_managed_digest_sha256", sa.String(64), nullable=True),
        sa.Column("parser_contract_version", sa.String(64), nullable=True),
        sa.Column("fingerprint_contract_version", sa.String(64), nullable=True),
        sa.Column("affected_region_keys", sa.JSON(), nullable=False),
        sa.Column("affected_region_digests", sa.JSON(), nullable=False),
        sa.Column("reason_category", sa.String(64), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_digest_sha256", sa.String(64), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_m365_revalidation_idempotency"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "binding_id"],
            ["m365_revision_bindings.organization_id", "m365_revision_bindings.id"],
            name="fk_m365_revalidation_binding_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "content_baseline_id"],
            [
                "m365_managed_content_baselines.organization_id",
                "m365_managed_content_baselines.id",
            ],
            name="fk_m365_revalidation_baseline_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id", "document_revision_id"],
            [
                "document_revisions.organization_id",
                "document_revisions.project_id",
                "document_revisions.document_id",
                "document_revisions.id",
            ],
            name="fk_m365_revalidation_revision_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "connection_id"],
            ["onedrive_connections.organization_id", "onedrive_connections.id"],
            name="fk_m365_revalidation_connection_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "actor_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_m365_revalidation_actor_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "trigger IN ('explicit_refresh', 'freshness_required_action', 'reconnect')",
            name="chk_m365_revalidation_trigger",
        ),
        sa.CheckConstraint(
            "classification IN ("
            "'no_change', 'external_change_outside_managed', "
            "'external_change_in_managed', 'file_replaced_or_moved', "
            "'access_unavailable')",
            name="chk_m365_revalidation_classification",
        ),
        sa.CheckConstraint(
            "observed_size_bytes IS NULL OR observed_size_bytes >= 0",
            name="chk_m365_revalidation_size",
        ),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name="chk_m365_revalidation_idempotency_trim",
        ),
        sa.CheckConstraint(
            _digest_check("observed_content_sha256", nullable=True),
            name="chk_m365_revalidation_content_digest",
        ),
        sa.CheckConstraint(
            _digest_check("observed_whole_canonical_digest_sha256", nullable=True),
            name="chk_m365_revalidation_whole_digest",
        ),
        sa.CheckConstraint(
            _digest_check("observed_outside_managed_digest_sha256", nullable=True),
            name="chk_m365_revalidation_outside_digest",
        ),
        sa.CheckConstraint(
            _digest_check("request_digest_sha256"),
            name="chk_m365_revalidation_request_digest",
        ),
    )
    op.create_index(
        "idx_m365_revalidation_current",
        "m365_revalidation_observations",
        [
            "organization_id",
            "project_id",
            "document_id",
            "document_revision_id",
            "completed_at",
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_m365_revalidation_current", table_name="m365_revalidation_observations"
    )
    op.drop_table("m365_revalidation_observations")
    op.drop_index(
        "idx_m365_region_baseline_parent", table_name="m365_managed_region_baselines"
    )
    op.drop_table("m365_managed_region_baselines")
    op.drop_index(
        "idx_m365_content_baseline_revision",
        table_name="m365_managed_content_baselines",
    )
    op.drop_table("m365_managed_content_baselines")
