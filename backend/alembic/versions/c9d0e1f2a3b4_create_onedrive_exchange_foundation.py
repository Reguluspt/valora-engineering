"""Create the offline OneDrive Exchange capability and persistence foundation.

Revision ID: c9d0e1f2a3b4
Revises: b8d9e0f1a2b3
Create Date: 2026-09-20 18:00:00.000000
"""
from __future__ import annotations

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _digest_check(column: str, *, nullable: bool = False) -> str:
    expression = (
        f"length({column}) = 64 AND {column} = lower({column}) "
        f"AND {column} ~ '^[0-9a-f]{{64}}$'"
    )
    return f"{column} IS NULL OR ({expression})" if nullable else expression


def upgrade() -> None:
    op.add_column(
        "m365_oauth_states",
        sa.Column(
            "requested_scope_profile",
            sa.String(32),
            nullable=False,
            server_default="read_only",
        ),
    )
    op.create_check_constraint(
        "chk_m365_oauth_state_scope_profile",
        "m365_oauth_states",
        "requested_scope_profile IN ('read_only', 'exchange_write')",
    )
    op.create_unique_constraint(
        "uq_onedrive_connections_owner_id",
        "onedrive_connections",
        ["organization_id", "user_id", "id"],
    )
    op.add_column(
        "document_storage_execution_intents",
        sa.Column(
            "intent_kind",
            sa.String(32),
            nullable=False,
            server_default="NEXT_REVISION",
        ),
    )
    op.add_column(
        "document_storage_execution_intents",
        sa.Column("initial_data_snapshot_digest_sha256", sa.String(64), nullable=True),
    )
    op.alter_column(
        "document_storage_execution_intents",
        "expected_revision_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.drop_constraint(
        "chk_storage_intent_revision",
        "document_storage_execution_intents",
        type_="check",
    )
    op.create_check_constraint(
        "chk_storage_intent_revision",
        "document_storage_execution_intents",
        "(intent_kind = 'NEXT_REVISION' AND expected_revision_id IS NOT NULL "
        "AND expected_document_revision > 0 "
        "AND initial_data_snapshot_digest_sha256 IS NULL) OR "
        "(intent_kind = 'INITIAL_REVISION' AND expected_revision_id IS NULL "
        "AND expected_document_revision = 0 "
        "AND initial_data_snapshot_digest_sha256 IS NOT NULL)",
    )
    op.create_check_constraint(
        "chk_storage_intent_initial_snapshot",
        "document_storage_execution_intents",
        "initial_data_snapshot_digest_sha256 IS NULL OR ("
        + _digest_check("initial_data_snapshot_digest_sha256")
        + ")",
    )

    op.create_table(
        "m365_connection_granted_scopes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("normalized_scope", sa.String(128), nullable=False),
        sa.Column("provenance", sa.String(32), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "connection_id",
            "normalized_scope",
            name="uq_m365_granted_scope_connection_scope",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id", "connection_id"],
            [
                "onedrive_connections.organization_id",
                "onedrive_connections.user_id",
                "onedrive_connections.id",
            ],
            name="fk_m365_granted_scope_connection_owner",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "normalized_scope = lower(trim(normalized_scope)) "
            "AND length(normalized_scope) > 0",
            name="chk_m365_granted_scope_normalized",
        ),
        sa.CheckConstraint(
            "provenance IN ('oauth_grant', 'legacy_files_read_contract')",
            name="chk_m365_granted_scope_provenance",
        ),
    )
    op.create_index(
        "idx_m365_granted_scopes_connection",
        "m365_connection_granted_scopes",
        ["organization_id", "connection_id"],
    )
    op.create_table(
        "m365_connection_capabilities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("capability_code", sa.String(48), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("evidence_scope", sa.String(128), nullable=True),
        sa.Column("provenance", sa.String(32), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "connection_id",
            "capability_code",
            name="uq_m365_connection_capability_code",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id", "connection_id"],
            [
                "onedrive_connections.organization_id",
                "onedrive_connections.user_id",
                "onedrive_connections.id",
            ],
            name="fk_m365_connection_capability_owner",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "capability_code IN ('READ_AVAILABLE', 'APPFOLDER_WRITE_AVAILABLE')",
            name="chk_m365_connection_capability_code",
        ),
        sa.CheckConstraint(
            "provenance IN ('oauth_grant', 'legacy_files_read_contract')",
            name="chk_m365_connection_capability_provenance",
        ),
        sa.CheckConstraint(
            "(available AND evidence_scope IS NOT NULL "
            "AND evidence_scope = lower(trim(evidence_scope)) "
            "AND length(evidence_scope) > 0) "
            "OR (NOT available AND evidence_scope IS NULL)",
            name="chk_m365_connection_capability_evidence",
        ),
    )
    op.create_index(
        "idx_m365_connection_capabilities_connection",
        "m365_connection_capabilities",
        ["organization_id", "connection_id"],
    )

    connection = op.get_bind()
    legacy_connections = connection.execute(
        sa.text("SELECT id, organization_id, user_id FROM onedrive_connections")
    ).mappings()
    for legacy in legacy_connections:
        owner = {
            "organization_id": legacy["organization_id"],
            "user_id": legacy["user_id"],
            "connection_id": legacy["id"],
        }
        connection.execute(
            sa.text(
                "INSERT INTO m365_connection_granted_scopes "
                "(id, organization_id, user_id, connection_id, normalized_scope, provenance) "
                "VALUES (:id, :organization_id, :user_id, :connection_id, "
                "'files.read', 'legacy_files_read_contract')"
            ),
            {"id": uuid.uuid4(), **owner},
        )
        connection.execute(
            sa.text(
                "INSERT INTO m365_connection_capabilities "
                "(id, organization_id, user_id, connection_id, capability_code, available, "
                "evidence_scope, provenance) VALUES "
                "(:id, :organization_id, :user_id, :connection_id, "
                "'READ_AVAILABLE', true, 'files.read', 'legacy_files_read_contract')"
            ),
            {"id": uuid.uuid4(), **owner},
        )
        connection.execute(
            sa.text(
                "INSERT INTO m365_connection_capabilities "
                "(id, organization_id, user_id, connection_id, capability_code, available, "
                "evidence_scope, provenance) VALUES "
                "(:id, :organization_id, :user_id, :connection_id, "
                "'APPFOLDER_WRITE_AVAILABLE', false, NULL, "
                "'legacy_files_read_contract')"
            ),
            {"id": uuid.uuid4(), **owner},
        )

    op.create_table(
        "m365_exchange_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("media", sa.String(16), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("drive_id", sa.String(255), nullable=False),
        sa.Column("drive_item_id", sa.String(255), nullable=False),
        sa.Column("logical_namespace", sa.String(512), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("e_tag", sa.String(512), nullable=False),
        sa.Column("c_tag", sa.String(512), nullable=True),
        sa.Column("provider_version_id", sa.String(255), nullable=True),
        sa.Column("observed_sha256", sa.String(64), nullable=False),
        sa.Column("observed_byte_length", sa.BigInteger(), nullable=False),
        sa.Column("source_authority_type", sa.String(32), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("document_revision_id", sa.Uuid(), nullable=True),
        sa.Column("excel_import_batch_id", sa.Uuid(), nullable=True),
        sa.Column("excel_source_artifact_id", sa.Uuid(), nullable=True),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "connection_id",
            "drive_id",
            "drive_item_id",
            name="uq_m365_exchange_artifact_provider_identity",
        ),
        sa.UniqueConstraint(
            "organization_id", "id", name="uq_m365_exchange_artifacts_tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            name="fk_m365_exchange_artifact_project_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "connection_id"],
            ["onedrive_connections.organization_id", "onedrive_connections.id"],
            name="fk_m365_exchange_artifact_connection_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id"],
            [
                "document_records.organization_id",
                "document_records.project_id",
                "document_records.id",
            ],
            name="fk_m365_exchange_artifact_document_tenant",
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
            name="fk_m365_exchange_artifact_revision_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "excel_import_batch_id"],
            [
                "project_asset_import_batches.organization_id",
                "project_asset_import_batches.project_id",
                "project_asset_import_batches.id",
            ],
            name="fk_m365_exchange_artifact_batch_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            [
                "organization_id",
                "project_id",
                "excel_import_batch_id",
                "excel_source_artifact_id",
            ],
            [
                "import_source_artifacts.organization_id",
                "import_source_artifacts.project_id",
                "import_source_artifacts.import_batch_id",
                "import_source_artifacts.id",
            ],
            name="fk_m365_exchange_artifact_source_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "role IN ('inbox', 'working', 'export')",
            name="chk_m365_exchange_artifact_role",
        ),
        sa.CheckConstraint(
            "media IN ('docx', 'xlsx')", name="chk_m365_exchange_artifact_media"
        ),
        sa.CheckConstraint(
            "state IN ('OBSERVED', 'IMPORTED', 'AVAILABLE', 'MISSING', "
            "'FAILED_ACTION_REQUIRED')",
            name="chk_m365_exchange_artifact_state",
        ),
        sa.CheckConstraint(
            "source_authority_type IN "
            "('PROVIDER_TRANSPORT', 'DOCUMENT_REVISION', 'EXCEL_SOURCE_ARTIFACT')",
            name="chk_m365_exchange_artifact_source_type",
        ),
        sa.CheckConstraint(
            "(source_authority_type = 'PROVIDER_TRANSPORT' "
            "AND document_id IS NULL AND document_revision_id IS NULL "
            "AND excel_import_batch_id IS NULL AND excel_source_artifact_id IS NULL) OR "
            "(source_authority_type = 'DOCUMENT_REVISION' "
            "AND document_id IS NOT NULL AND document_revision_id IS NOT NULL "
            "AND excel_import_batch_id IS NULL AND excel_source_artifact_id IS NULL) OR "
            "(source_authority_type = 'EXCEL_SOURCE_ARTIFACT' "
            "AND document_id IS NULL AND document_revision_id IS NULL "
            "AND excel_import_batch_id IS NOT NULL "
            "AND excel_source_artifact_id IS NOT NULL)",
            name="chk_m365_exchange_artifact_source_lineage",
        ),
        sa.CheckConstraint(
            "observed_byte_length >= 0", name="chk_m365_exchange_artifact_size"
        ),
        sa.CheckConstraint(
            _digest_check("observed_sha256"),
            name="chk_m365_exchange_artifact_digest",
        ),
        sa.CheckConstraint(
            "length(trim(drive_id)) > 0 AND length(trim(drive_item_id)) > 0 "
            "AND length(trim(logical_namespace)) > 0 "
            "AND length(trim(display_name)) > 0 AND length(trim(e_tag)) > 0",
            name="chk_m365_exchange_artifact_identity",
        ),
    )
    op.create_index(
        "idx_m365_exchange_artifacts_project",
        "m365_exchange_artifacts",
        ["organization_id", "project_id", "role"],
    )

    op.create_table(
        "m365_exchange_operations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_digest_sha256", sa.String(64), nullable=False),
        sa.Column("operation_kind", sa.String(32), nullable=False),
        sa.Column("target_role", sa.String(16), nullable=False),
        sa.Column("media", sa.String(16), nullable=True),
        sa.Column("drive_id", sa.String(255), nullable=False),
        sa.Column("destination_parent_item_id", sa.String(255), nullable=False),
        sa.Column("destination_name", sa.String(255), nullable=False),
        sa.Column("expected_drive_item_id", sa.String(255), nullable=True),
        sa.Column("expected_e_tag", sa.String(512), nullable=True),
        sa.Column("pre_sha256", sa.String(64), nullable=True),
        sa.Column("pre_byte_length", sa.BigInteger(), nullable=True),
        sa.Column("post_sha256", sa.String(64), nullable=True),
        sa.Column("post_byte_length", sa.BigInteger(), nullable=True),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("provider_request_id", sa.String(255), nullable=True),
        sa.Column("failure_code", sa.String(64), nullable=True),
        sa.Column("artifact_id", sa.Uuid(), nullable=True),
        sa.Column(
            "prepared_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("provider_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_m365_exchange_operation_idempotency",
        ),
        sa.UniqueConstraint(
            "organization_id", "id", name="uq_m365_exchange_operations_tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            name="fk_m365_exchange_operation_project_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "connection_id"],
            ["onedrive_connections.organization_id", "onedrive_connections.id"],
            name="fk_m365_exchange_operation_connection_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "artifact_id"],
            ["m365_exchange_artifacts.organization_id", "m365_exchange_artifacts.id"],
            name="fk_m365_exchange_operation_artifact_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "operation_kind IN ('ENSURE_FOLDER', 'CREATE_WORKING', 'CREATE_EXPORT')",
            name="chk_m365_exchange_operation_kind",
        ),
        sa.CheckConstraint(
            "target_role IN ('inbox', 'working', 'export')",
            name="chk_m365_exchange_operation_role",
        ),
        sa.CheckConstraint(
            "(operation_kind = 'ENSURE_FOLDER' AND media IS NULL) OR "
            "(operation_kind IN ('CREATE_WORKING', 'CREATE_EXPORT') "
            "AND media IN ('docx', 'xlsx'))",
            name="chk_m365_exchange_operation_media",
        ),
        sa.CheckConstraint(
            "state IN ('PREPARED', 'PROVIDER_UNKNOWN', 'PROVIDER_VERIFIED', "
            "'FINALIZED', 'FAILED_ACTION_REQUIRED')",
            name="chk_m365_exchange_operation_state",
        ),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) > 0 "
            "AND length(trim(drive_id)) > 0 "
            "AND length(trim(destination_parent_item_id)) > 0 "
            "AND length(trim(destination_name)) > 0",
            name="chk_m365_exchange_operation_identity",
        ),
        sa.CheckConstraint(
            _digest_check("request_digest_sha256"),
            name="chk_m365_exchange_operation_request_digest",
        ),
        sa.CheckConstraint(
            _digest_check("pre_sha256", nullable=True),
            name="chk_m365_exchange_operation_pre_digest",
        ),
        sa.CheckConstraint(
            _digest_check("post_sha256", nullable=True),
            name="chk_m365_exchange_operation_post_digest",
        ),
        sa.CheckConstraint(
            "(pre_sha256 IS NULL AND pre_byte_length IS NULL) OR "
            "(pre_sha256 IS NOT NULL AND pre_byte_length >= 0)",
            name="chk_m365_exchange_operation_pre_integrity",
        ),
        sa.CheckConstraint(
            "(post_sha256 IS NULL AND post_byte_length IS NULL) OR "
            "(post_sha256 IS NOT NULL AND post_byte_length >= 0)",
            name="chk_m365_exchange_operation_post_integrity",
        ),
    )
    op.create_index(
        "idx_m365_exchange_operations_project_state",
        "m365_exchange_operations",
        ["organization_id", "project_id", "state"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    initial_intents = connection.execute(
        sa.text(
            "SELECT count(*) FROM document_storage_execution_intents "
            "WHERE intent_kind = 'INITIAL_REVISION'"
        )
    ).scalar_one()
    if initial_intents:
        raise RuntimeError("cannot downgrade while initial-revision storage intents exist")
    exchange_rows = connection.execute(
        sa.text(
            "SELECT "
            "(SELECT count(*) FROM m365_exchange_operations) + "
            "(SELECT count(*) FROM m365_exchange_artifacts)"
        )
    ).scalar_one()
    if exchange_rows:
        raise RuntimeError("cannot downgrade while OneDrive Exchange rows exist")

    op.drop_index(
        "idx_m365_exchange_operations_project_state",
        table_name="m365_exchange_operations",
    )
    op.drop_table("m365_exchange_operations")
    op.drop_index(
        "idx_m365_exchange_artifacts_project", table_name="m365_exchange_artifacts"
    )
    op.drop_table("m365_exchange_artifacts")
    op.drop_index(
        "idx_m365_connection_capabilities_connection",
        table_name="m365_connection_capabilities",
    )
    op.drop_table("m365_connection_capabilities")
    op.drop_index(
        "idx_m365_granted_scopes_connection",
        table_name="m365_connection_granted_scopes",
    )
    op.drop_table("m365_connection_granted_scopes")
    op.drop_constraint(
        "chk_storage_intent_initial_snapshot",
        "document_storage_execution_intents",
        type_="check",
    )
    op.drop_constraint(
        "chk_storage_intent_revision",
        "document_storage_execution_intents",
        type_="check",
    )
    op.alter_column(
        "document_storage_execution_intents",
        "expected_revision_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.create_check_constraint(
        "chk_storage_intent_revision",
        "document_storage_execution_intents",
        "expected_document_revision > 0",
    )
    op.drop_column(
        "document_storage_execution_intents",
        "initial_data_snapshot_digest_sha256",
    )
    op.drop_column("document_storage_execution_intents", "intent_kind")
    op.drop_constraint(
        "uq_onedrive_connections_owner_id", "onedrive_connections", type_="unique"
    )
    op.drop_constraint(
        "chk_m365_oauth_state_scope_profile", "m365_oauth_states", type_="check"
    )
    op.drop_column("m365_oauth_states", "requested_scope_profile")
