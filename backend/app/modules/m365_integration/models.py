"""OneDrive Personal connection, vault envelope and immutable binding persistence."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDMixin, utc_now


class M365EncryptedCredential(Base, UUIDMixin, TimestampMixin):
    """Infrastructure-only authenticated ciphertext; plaintext never enters ORM state."""

    __tablename__ = "m365_encrypted_credentials"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    key_version: Mapped[str] = mapped_column(String(64), nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "user_id", "id", name="uq_m365_credentials_owner_id"
        ),
        ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            name="fk_m365_credential_user_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "purpose IN ('oauth_flow', 'token_cache')",
            name="chk_m365_credential_purpose",
        ),
        CheckConstraint(
            "length(trim(key_version)) > 0", name="chk_m365_credential_key_version"
        ),
        Index("idx_m365_credentials_owner", "organization_id", "user_id"),
    )


class OneDriveConnection(Base, UUIDMixin, TimestampMixin):
    """Non-secret link between a VALORA user and one personal Microsoft drive."""

    __tablename__ = "onedrive_connections"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    consumer_issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    microsoft_account_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    drive_id: Mapped[str] = mapped_column(String(255), nullable=False)
    credential_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "user_id", name="uq_onedrive_connection_user"
        ),
        UniqueConstraint(
            "organization_id",
            "consumer_issuer",
            "microsoft_account_subject",
            name="uq_onedrive_connection_account",
        ),
        UniqueConstraint(
            "organization_id", "id", name="uq_onedrive_connections_tenant_id"
        ),
        ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            name="fk_onedrive_connection_user_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "user_id", "credential_id"],
            [
                "m365_encrypted_credentials.organization_id",
                "m365_encrypted_credentials.user_id",
                "m365_encrypted_credentials.id",
            ],
            name="fk_onedrive_connection_credential_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('active', 'error', 'revoked')",
            name="chk_onedrive_connection_status",
        ),
        CheckConstraint(
            "length(trim(microsoft_account_subject)) > 0",
            name="chk_onedrive_connection_subject",
        ),
        CheckConstraint(
            "length(trim(drive_id)) > 0", name="chk_onedrive_connection_drive"
        ),
        Index("idx_onedrive_connections_owner", "organization_id", "user_id"),
    )


class M365OAuthState(Base, UUIDMixin):
    """Single-use authorization transaction linked to encrypted flow material."""

    __tablename__ = "m365_oauth_states"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    user_session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    flow_credential_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("state_hash", name="uq_m365_oauth_state_hash"),
        ForeignKeyConstraint(
            ["organization_id", "user_id"],
            ["users.organization_id", "users.id"],
            name="fk_m365_oauth_state_user_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["user_session_id"],
            ["user_sessions.id"],
            name="fk_m365_oauth_state_session",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "user_id", "flow_credential_id"],
            [
                "m365_encrypted_credentials.organization_id",
                "m365_encrypted_credentials.user_id",
                "m365_encrypted_credentials.id",
            ],
            name="fk_m365_oauth_state_credential_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "length(state_hash) = 64 "
            "AND state_hash = lower(state_hash) "
            "AND state_hash ~ '^[0-9a-f]{64}$'",
            name="chk_m365_oauth_state_hash",
        ),
        Index("idx_m365_oauth_state_owner", "organization_id", "user_id"),
    )


class M365RevisionBinding(Base, UUIDMixin):
    """Immutable OneDrive metadata baseline for one canonical document revision."""

    __tablename__ = "m365_revision_bindings"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_revision_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    connection_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    drive_id: Mapped[str] = mapped_column(String(255), nullable=False)
    drive_item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    graph_version_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    e_tag: Mapped[str] = mapped_column(String(512), nullable=False)
    c_tag: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    web_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    bound_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    bound_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "document_revision_id", name="uq_m365_binding_revision"
        ),
        UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_m365_binding_idempotency"
        ),
        UniqueConstraint(
            "organization_id", "id", name="uq_m365_revision_bindings_tenant_id"
        ),
        ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id"],
            [
                "document_records.organization_id",
                "document_records.project_id",
                "document_records.id",
            ],
            name="fk_m365_binding_document_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
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
        ForeignKeyConstraint(
            ["organization_id", "connection_id"],
            ["onedrive_connections.organization_id", "onedrive_connections.id"],
            name="fk_m365_binding_connection_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "bound_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_m365_binding_actor_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint("size_bytes >= 0", name="chk_m365_binding_size"),
        CheckConstraint(
            "length(trim(drive_id)) > 0 AND length(trim(drive_item_id)) > 0",
            name="chk_m365_binding_identity",
        ),
        CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name="chk_m365_binding_idempotency_trim",
        ),
        CheckConstraint(
            "length(request_digest_sha256) = 64 "
            "AND request_digest_sha256 = lower(request_digest_sha256) "
            "AND request_digest_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_m365_binding_request_digest",
        ),
        Index(
            "idx_m365_binding_item", "organization_id", "drive_id", "drive_item_id"
        ),
    )
