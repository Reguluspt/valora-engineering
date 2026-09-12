"""Create OneDrive Personal document and integration foundation.

Revision ID: f4c8d2a1b7e9
Revises: d4b7c9e2f1a6
Create Date: 2026-09-12 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4c8d2a1b7e9"
down_revision: Union[str, None] = "d4b7c9e2f1a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _digest_check(column: str) -> str:
    return (
        f"length({column}) = 64 "
        f"AND {column} = lower({column}) "
        f"AND {column} ~ '^[0-9a-f]{{64}}$'"
    )


def upgrade() -> None:
    op.create_table(
        "document_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "project_id", "id", name="uq_document_records_tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            name="fk_document_record_project_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_document_record_creator_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "length(trim(document_type)) > 0", name="chk_document_record_type_trim"
        ),
        sa.CheckConstraint("length(trim(title)) > 0", name="chk_document_record_title_trim"),
    )
    op.create_index(
        "idx_document_records_project",
        "document_records",
        ["organization_id", "project_id"],
    )

    op.create_table(
        "document_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_revision", sa.Integer(), nullable=False),
        sa.Column("data_snapshot_digest_sha256", sa.String(64), nullable=False),
        sa.Column("content_checksum_sha256", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_digest_sha256", sa.String(64), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "project_id",
            "document_id",
            "document_revision",
            name="uq_document_revision_number",
        ),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_document_revision_idempotency"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "project_id",
            "document_id",
            "id",
            name="uq_document_revisions_tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id"],
            [
                "document_records.organization_id",
                "document_records.project_id",
                "document_records.id",
            ],
            name="fk_document_revision_record_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_document_revision_creator_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "document_revision > 0", name="chk_document_revision_positive"
        ),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name="chk_document_revision_idempotency_trim",
        ),
        sa.CheckConstraint(
            _digest_check("data_snapshot_digest_sha256"),
            name="chk_document_revision_snapshot_digest",
        ),
        sa.CheckConstraint(
            _digest_check("content_checksum_sha256"),
            name="chk_document_revision_content_checksum",
        ),
        sa.CheckConstraint(
            _digest_check("request_digest_sha256"),
            name="chk_document_revision_request_digest",
        ),
    )
    op.create_index(
        "idx_document_revisions_record",
        "document_revisions",
        ["organization_id", "project_id", "document_id"],
    )

    op.create_table(
        "document_revision_current_heads",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("current_revision_id", sa.Uuid(), nullable=False),
        sa.Column("document_revision", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("organization_id", "project_id", "document_id"),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id"],
            [
                "document_records.organization_id",
                "document_records.project_id",
                "document_records.id",
            ],
            name="fk_document_head_record_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id", "current_revision_id"],
            [
                "document_revisions.organization_id",
                "document_revisions.project_id",
                "document_revisions.document_id",
                "document_revisions.id",
            ],
            name="fk_document_head_revision_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "document_revision > 0", name="chk_document_head_revision_positive"
        ),
    )

    op.create_table(
        "m365_encrypted_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("key_version", sa.String(64), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "user_id", "id", name="uq_m365_credentials_owner_id"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            name="fk_m365_credential_user_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "purpose IN ('oauth_flow', 'token_cache')",
            name="chk_m365_credential_purpose",
        ),
        sa.CheckConstraint(
            "length(trim(key_version)) > 0", name="chk_m365_credential_key_version"
        ),
    )
    op.create_index(
        "idx_m365_credentials_owner",
        "m365_encrypted_credentials",
        ["organization_id", "user_id"],
    )

    op.create_table(
        "onedrive_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("consumer_issuer", sa.String(255), nullable=False),
        sa.Column("microsoft_account_subject", sa.String(255), nullable=False),
        sa.Column("drive_id", sa.String(255), nullable=False),
        sa.Column("credential_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "last_verified_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "user_id", name="uq_onedrive_connection_user"
        ),
        sa.UniqueConstraint(
            "organization_id",
            "consumer_issuer",
            "microsoft_account_subject",
            name="uq_onedrive_connection_account",
        ),
        sa.UniqueConstraint(
            "organization_id", "id", name="uq_onedrive_connections_tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            name="fk_onedrive_connection_user_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id", "credential_id"],
            [
                "m365_encrypted_credentials.organization_id",
                "m365_encrypted_credentials.user_id",
                "m365_encrypted_credentials.id",
            ],
            name="fk_onedrive_connection_credential_owner",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'error', 'revoked')",
            name="chk_onedrive_connection_status",
        ),
        sa.CheckConstraint(
            "length(trim(microsoft_account_subject)) > 0",
            name="chk_onedrive_connection_subject",
        ),
        sa.CheckConstraint(
            "length(trim(drive_id)) > 0", name="chk_onedrive_connection_drive"
        ),
    )
    op.create_index(
        "idx_onedrive_connections_owner",
        "onedrive_connections",
        ["organization_id", "user_id"],
    )

    op.create_table(
        "m365_oauth_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("user_session_id", sa.Uuid(), nullable=False),
        sa.Column("state_hash", sa.String(64), nullable=False),
        sa.Column("flow_credential_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_hash", name="uq_m365_oauth_state_hash"),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            name="fk_m365_oauth_state_user_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_session_id"],
            ["user_sessions.id"],
            name="fk_m365_oauth_state_session",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "user_id", "flow_credential_id"],
            [
                "m365_encrypted_credentials.organization_id",
                "m365_encrypted_credentials.user_id",
                "m365_encrypted_credentials.id",
            ],
            name="fk_m365_oauth_state_credential_owner",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            _digest_check("state_hash"), name="chk_m365_oauth_state_hash"
        ),
    )
    op.create_index(
        "idx_m365_oauth_state_owner",
        "m365_oauth_states",
        ["organization_id", "user_id"],
    )

    op.create_table(
        "m365_revision_bindings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_revision_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("drive_id", sa.String(255), nullable=False),
        sa.Column("drive_item_id", sa.String(255), nullable=False),
        sa.Column("graph_version_id", sa.String(255), nullable=True),
        sa.Column("e_tag", sa.String(512), nullable=False),
        sa.Column("c_tag", sa.String(512), nullable=True),
        sa.Column("last_modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("path", sa.String(2048), nullable=True),
        sa.Column("web_url", sa.String(2048), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_digest_sha256", sa.String(64), nullable=False),
        sa.Column("bound_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "bound_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "document_revision_id", name="uq_m365_binding_revision"
        ),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_m365_binding_idempotency"
        ),
        sa.UniqueConstraint(
            "organization_id", "id", name="uq_m365_revision_bindings_tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id"],
            [
                "document_records.organization_id",
                "document_records.project_id",
                "document_records.id",
            ],
            name="fk_m365_binding_document_tenant",
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
            name="fk_m365_binding_revision_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "connection_id"],
            ["onedrive_connections.organization_id", "onedrive_connections.id"],
            name="fk_m365_binding_connection_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "bound_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_m365_binding_actor_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("size_bytes >= 0", name="chk_m365_binding_size"),
        sa.CheckConstraint(
            "length(trim(drive_id)) > 0 AND length(trim(drive_item_id)) > 0",
            name="chk_m365_binding_identity",
        ),
        sa.CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name="chk_m365_binding_idempotency_trim",
        ),
        sa.CheckConstraint(
            _digest_check("request_digest_sha256"),
            name="chk_m365_binding_request_digest",
        ),
    )
    op.create_index(
        "idx_m365_binding_item",
        "m365_revision_bindings",
        ["organization_id", "drive_id", "drive_item_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_m365_binding_item", table_name="m365_revision_bindings")
    op.drop_table("m365_revision_bindings")
    op.drop_index("idx_m365_oauth_state_owner", table_name="m365_oauth_states")
    op.drop_table("m365_oauth_states")
    op.drop_index("idx_onedrive_connections_owner", table_name="onedrive_connections")
    op.drop_table("onedrive_connections")
    op.drop_index("idx_m365_credentials_owner", table_name="m365_encrypted_credentials")
    op.drop_table("m365_encrypted_credentials")
    op.drop_table("document_revision_current_heads")
    op.drop_index("idx_document_revisions_record", table_name="document_revisions")
    op.drop_table("document_revisions")
    op.drop_index("idx_document_records_project", table_name="document_records")
    op.drop_table("document_records")
