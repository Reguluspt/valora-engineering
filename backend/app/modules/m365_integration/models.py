"""OneDrive Personal connection, vault envelope and immutable binding persistence."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDMixin, utc_now


def _sha256_check(column: str, *, nullable: bool = False) -> str:
    expression = (
        f"length({column}) = 64 "
        f"AND {column} = lower({column}) "
        f"AND {column} ~ '^[0-9a-f]{{64}}$'"
    )
    return f"{column} IS NULL OR ({expression})" if nullable else expression


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
        UniqueConstraint(
            "organization_id",
            "user_id",
            "id",
            name="uq_onedrive_connections_owner_id",
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
    requested_scope_profile: Mapped[str] = mapped_column(
        String(32), nullable=False, default="read_only"
    )
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
        CheckConstraint(
            "requested_scope_profile IN ('read_only', 'exchange_write')",
            name="chk_m365_oauth_state_scope_profile",
        ),
        Index("idx_m365_oauth_state_owner", "organization_id", "user_id"),
    )


class M365ConnectionGrantedScope(Base, UUIDMixin):
    """One normalized OAuth scope observed for the current connection grant."""

    __tablename__ = "m365_connection_granted_scopes"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    connection_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    normalized_scope: Mapped[str] = mapped_column(String(128), nullable=False)
    provenance: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "connection_id",
            "normalized_scope",
            name="uq_m365_granted_scope_connection_scope",
        ),
        ForeignKeyConstraint(
            ["organization_id", "user_id", "connection_id"],
            [
                "onedrive_connections.organization_id",
                "onedrive_connections.user_id",
                "onedrive_connections.id",
            ],
            name="fk_m365_granted_scope_connection_owner",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "normalized_scope = lower(trim(normalized_scope)) "
            "AND length(normalized_scope) > 0",
            name="chk_m365_granted_scope_normalized",
        ),
        CheckConstraint(
            "provenance IN ('oauth_grant', 'legacy_files_read_contract')",
            name="chk_m365_granted_scope_provenance",
        ),
        Index(
            "idx_m365_granted_scopes_connection",
            "organization_id",
            "connection_id",
        ),
    )


class M365ConnectionCapability(Base, UUIDMixin):
    """Durable capability projection derived from exact normalized OAuth grants."""

    __tablename__ = "m365_connection_capabilities"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    connection_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    capability_code: Mapped[str] = mapped_column(String(48), nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evidence_scope: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provenance: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "connection_id",
            "capability_code",
            name="uq_m365_connection_capability_code",
        ),
        ForeignKeyConstraint(
            ["organization_id", "user_id", "connection_id"],
            [
                "onedrive_connections.organization_id",
                "onedrive_connections.user_id",
                "onedrive_connections.id",
            ],
            name="fk_m365_connection_capability_owner",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "capability_code IN ('READ_AVAILABLE', 'APPFOLDER_WRITE_AVAILABLE')",
            name="chk_m365_connection_capability_code",
        ),
        CheckConstraint(
            "provenance IN ('oauth_grant', 'legacy_files_read_contract')",
            name="chk_m365_connection_capability_provenance",
        ),
        CheckConstraint(
            "(available AND evidence_scope IS NOT NULL "
            "AND evidence_scope = lower(trim(evidence_scope)) "
            "AND length(evidence_scope) > 0) "
            "OR (NOT available AND evidence_scope IS NULL)",
            name="chk_m365_connection_capability_evidence",
        ),
        Index(
            "idx_m365_connection_capabilities_connection",
            "organization_id",
            "connection_id",
        ),
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


class M365ManagedContentBaseline(Base, UUIDMixin):
    """Immutable content proof attached to one PR-05 revision binding."""

    __tablename__ = "m365_managed_content_baselines"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_revision_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    binding_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    connection_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    drive_id: Mapped[str] = mapped_column(String(255), nullable=False)
    drive_item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_e_tag: Mapped[str] = mapped_column(String(512), nullable=False)
    source_c_tag: Mapped[str | None] = mapped_column(String(512), nullable=True)
    bind_metadata_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    parser_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprint_contract_version: Mapped[str] = mapped_column(String(64), nullable=False)
    managed_region_manifest_digest_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    outside_managed_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    whole_canonical_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "binding_id", name="uq_m365_content_baseline_binding"
        ),
        UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_m365_content_baseline_idempotency"
        ),
        UniqueConstraint(
            "organization_id", "id", name="uq_m365_content_baselines_tenant_id"
        ),
        ForeignKeyConstraint(
            ["organization_id", "binding_id"],
            ["m365_revision_bindings.organization_id", "m365_revision_bindings.id"],
            name="fk_m365_content_baseline_binding_tenant",
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
            name="fk_m365_content_baseline_revision_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "connection_id"],
            ["onedrive_connections.organization_id", "onedrive_connections.id"],
            name="fk_m365_content_baseline_connection_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_m365_content_baseline_actor_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint("source_size_bytes >= 0", name="chk_m365_content_baseline_size"),
        CheckConstraint(
            "provenance_kind IN ('existing_binding_verified', 'new_binding_atomic')",
            name="chk_m365_content_baseline_provenance",
        ),
        CheckConstraint(
            "length(trim(authority_ref)) > 0",
            name="chk_m365_content_baseline_authority",
        ),
        CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name="chk_m365_content_baseline_idempotency_trim",
        ),
        CheckConstraint(
            _sha256_check("source_content_sha256"),
            name="chk_m365_content_baseline_source_digest",
        ),
        CheckConstraint(
            _sha256_check("bind_metadata_digest_sha256"),
            name="chk_m365_content_baseline_metadata_digest",
        ),
        CheckConstraint(
            _sha256_check("managed_region_manifest_digest_sha256"),
            name="chk_m365_content_baseline_manifest_digest",
        ),
        CheckConstraint(
            _sha256_check("outside_managed_digest_sha256"),
            name="chk_m365_content_baseline_outside_digest",
        ),
        CheckConstraint(
            _sha256_check("whole_canonical_digest_sha256"),
            name="chk_m365_content_baseline_whole_digest",
        ),
        CheckConstraint(
            _sha256_check("request_digest_sha256"),
            name="chk_m365_content_baseline_request_digest",
        ),
        Index(
            "idx_m365_content_baseline_revision",
            "organization_id",
            "project_id",
            "document_id",
            "document_revision_id",
        ),
    )


class M365ManagedRegionBaseline(Base, UUIDMixin):
    """Digest-only snapshot of one Managed Region in a sealed content baseline."""

    __tablename__ = "m365_managed_region_baselines"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    content_baseline_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    region_key: Mapped[str] = mapped_column(String(128), nullable=False)
    locator: Mapped[str] = mapped_column(String(255), nullable=False)
    locator_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    semantic_type: Mapped[str] = mapped_column(String(32), nullable=False)
    normalization_contract: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_value_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    structural_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "content_baseline_id",
            "region_key",
            name="uq_m365_region_baseline_key",
        ),
        UniqueConstraint(
            "organization_id",
            "content_baseline_id",
            "position",
            name="uq_m365_region_baseline_position",
        ),
        ForeignKeyConstraint(
            ["organization_id", "content_baseline_id"],
            [
                "m365_managed_content_baselines.organization_id",
                "m365_managed_content_baselines.id",
            ],
            name="fk_m365_region_baseline_parent_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint("position >= 0", name="chk_m365_region_baseline_position"),
        CheckConstraint(
            "length(trim(region_key)) > 0 AND length(trim(locator)) > 0",
            name="chk_m365_region_baseline_identity",
        ),
        CheckConstraint(
            _sha256_check("locator_digest_sha256"),
            name="chk_m365_region_baseline_locator_digest",
        ),
        CheckConstraint(
            _sha256_check("normalized_value_digest_sha256"),
            name="chk_m365_region_baseline_value_digest",
        ),
        CheckConstraint(
            _sha256_check("structural_digest_sha256"),
            name="chk_m365_region_baseline_structure_digest",
        ),
        Index(
            "idx_m365_region_baseline_parent",
            "organization_id",
            "content_baseline_id",
        ),
    )


class M365ExchangeOperation(Base, UUIDMixin, TimestampMixin):
    """Durable provider mutation/reconciliation attempt for Exchange."""

    __tablename__ = "m365_exchange_operations"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    connection_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_role: Mapped[str] = mapped_column(String(16), nullable=False)
    media: Mapped[str | None] = mapped_column(String(16), nullable=True)
    drive_id: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_parent_item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_name: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_drive_item_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_e_tag: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pre_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pre_byte_length: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    post_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    post_byte_length: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    prepared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    provider_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_m365_exchange_operation_idempotency"
        ),
        UniqueConstraint(
            "organization_id", "id", name="uq_m365_exchange_operations_tenant_id"
        ),
        ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            name="fk_m365_exchange_operation_project_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "connection_id"],
            ["onedrive_connections.organization_id", "onedrive_connections.id"],
            name="fk_m365_exchange_operation_connection_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "artifact_id"],
            ["m365_exchange_artifacts.organization_id", "m365_exchange_artifacts.id"],
            name="fk_m365_exchange_operation_artifact_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "operation_kind IN ('ENSURE_FOLDER', 'CREATE_WORKING', 'CREATE_EXPORT')",
            name="chk_m365_exchange_operation_kind",
        ),
        CheckConstraint(
            "target_role IN ('inbox', 'working', 'export')",
            name="chk_m365_exchange_operation_role",
        ),
        CheckConstraint(
            "(operation_kind = 'ENSURE_FOLDER' AND media IS NULL) OR "
            "(operation_kind IN ('CREATE_WORKING', 'CREATE_EXPORT') "
            "AND media IN ('docx', 'xlsx'))",
            name="chk_m365_exchange_operation_media",
        ),
        CheckConstraint(
            "state IN ('PREPARED', 'PROVIDER_UNKNOWN', 'PROVIDER_VERIFIED', "
            "'FINALIZED', 'FAILED_ACTION_REQUIRED')",
            name="chk_m365_exchange_operation_state",
        ),
        CheckConstraint(
            "length(trim(idempotency_key)) > 0 "
            "AND length(trim(drive_id)) > 0 "
            "AND length(trim(destination_parent_item_id)) > 0 "
            "AND length(trim(destination_name)) > 0",
            name="chk_m365_exchange_operation_identity",
        ),
        CheckConstraint(
            _sha256_check("request_digest_sha256"),
            name="chk_m365_exchange_operation_request_digest",
        ),
        CheckConstraint(
            _sha256_check("pre_sha256", nullable=True),
            name="chk_m365_exchange_operation_pre_digest",
        ),
        CheckConstraint(
            _sha256_check("post_sha256", nullable=True),
            name="chk_m365_exchange_operation_post_digest",
        ),
        CheckConstraint(
            "(pre_sha256 IS NULL AND pre_byte_length IS NULL) OR "
            "(pre_sha256 IS NOT NULL AND pre_byte_length >= 0)",
            name="chk_m365_exchange_operation_pre_integrity",
        ),
        CheckConstraint(
            "(post_sha256 IS NULL AND post_byte_length IS NULL) OR "
            "(post_sha256 IS NOT NULL AND post_byte_length >= 0)",
            name="chk_m365_exchange_operation_post_integrity",
        ),
        Index(
            "idx_m365_exchange_operations_project_state",
            "organization_id",
            "project_id",
            "state",
        ),
    )


class M365RevalidationObservation(Base, UUIDMixin):
    """Append-only terminal fact for one provider-backed revalidation attempt."""

    __tablename__ = "m365_revalidation_observations"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_revision_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    binding_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    content_baseline_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    connection_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    trigger: Mapped[str] = mapped_column(String(40), nullable=False)
    classification: Mapped[str] = mapped_column(String(48), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    observed_drive_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observed_drive_item_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observed_graph_version_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observed_e_tag: Mapped[str | None] = mapped_column(String(512), nullable=True)
    observed_c_tag: Mapped[str | None] = mapped_column(String(512), nullable=True)
    observed_last_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observed_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    observed_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observed_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    observed_web_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    observed_content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_whole_canonical_digest_sha256: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    observed_outside_managed_digest_sha256: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    parser_contract_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fingerprint_contract_version: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    affected_region_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    affected_region_digests: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    reason_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_m365_revalidation_idempotency",
        ),
        ForeignKeyConstraint(
            ["organization_id", "binding_id"],
            ["m365_revision_bindings.organization_id", "m365_revision_bindings.id"],
            name="fk_m365_revalidation_binding_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "content_baseline_id"],
            [
                "m365_managed_content_baselines.organization_id",
                "m365_managed_content_baselines.id",
            ],
            name="fk_m365_revalidation_baseline_tenant",
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
            name="fk_m365_revalidation_revision_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "connection_id"],
            ["onedrive_connections.organization_id", "onedrive_connections.id"],
            name="fk_m365_revalidation_connection_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "actor_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_m365_revalidation_actor_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "trigger IN ('explicit_refresh', 'freshness_required_action', 'reconnect')",
            name="chk_m365_revalidation_trigger",
        ),
        CheckConstraint(
            "classification IN ("
            "'no_change', 'external_change_outside_managed', "
            "'external_change_in_managed', 'file_replaced_or_moved', "
            "'access_unavailable')",
            name="chk_m365_revalidation_classification",
        ),
        CheckConstraint(
            "observed_size_bytes IS NULL OR observed_size_bytes >= 0",
            name="chk_m365_revalidation_size",
        ),
        CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name="chk_m365_revalidation_idempotency_trim",
        ),
        CheckConstraint(
            _sha256_check("observed_content_sha256", nullable=True),
            name="chk_m365_revalidation_content_digest",
        ),
        CheckConstraint(
            _sha256_check("observed_whole_canonical_digest_sha256", nullable=True),
            name="chk_m365_revalidation_whole_digest",
        ),
        CheckConstraint(
            _sha256_check("observed_outside_managed_digest_sha256", nullable=True),
            name="chk_m365_revalidation_outside_digest",
        ),
        CheckConstraint(
            _sha256_check("request_digest_sha256"),
            name="chk_m365_revalidation_request_digest",
        ),
        Index(
            "idx_m365_revalidation_current",
            "organization_id",
            "project_id",
            "document_id",
            "document_revision_id",
            "completed_at",
        ),
    )


class M365ExchangeArtifact(Base, UUIDMixin, TimestampMixin):
    """Non-authoritative observation of one bounded Exchange file."""

    __tablename__ = "m365_exchange_artifacts"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    connection_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    media: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    drive_id: Mapped[str] = mapped_column(String(255), nullable=False)
    drive_item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    logical_namespace: Mapped[str] = mapped_column(String(512), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    e_tag: Mapped[str] = mapped_column(String(512), nullable=False)
    c_tag: Mapped[str | None] = mapped_column(String(512), nullable=True)
    provider_version_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observed_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_byte_length: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_authority_type: Mapped[str] = mapped_column(String(32), nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    document_revision_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    excel_import_batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    excel_source_artifact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "connection_id",
            "drive_id",
            "drive_item_id",
            name="uq_m365_exchange_artifact_provider_identity",
        ),
        UniqueConstraint(
            "organization_id", "id", name="uq_m365_exchange_artifacts_tenant_id"
        ),
        ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            name="fk_m365_exchange_artifact_project_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "connection_id"],
            ["onedrive_connections.organization_id", "onedrive_connections.id"],
            name="fk_m365_exchange_artifact_connection_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id"],
            [
                "document_records.organization_id",
                "document_records.project_id",
                "document_records.id",
            ],
            name="fk_m365_exchange_artifact_document_tenant",
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
            name="fk_m365_exchange_artifact_revision_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "project_id", "excel_import_batch_id"],
            [
                "project_asset_import_batches.organization_id",
                "project_asset_import_batches.project_id",
                "project_asset_import_batches.id",
            ],
            name="fk_m365_exchange_artifact_batch_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
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
        CheckConstraint(
            "role IN ('inbox', 'working', 'export')",
            name="chk_m365_exchange_artifact_role",
        ),
        CheckConstraint(
            "media IN ('docx', 'xlsx')",
            name="chk_m365_exchange_artifact_media",
        ),
        CheckConstraint(
            "state IN ('OBSERVED', 'IMPORTED', 'AVAILABLE', 'MISSING', "
            "'FAILED_ACTION_REQUIRED')",
            name="chk_m365_exchange_artifact_state",
        ),
        CheckConstraint(
            "source_authority_type IN "
            "('PROVIDER_TRANSPORT', 'DOCUMENT_REVISION', 'EXCEL_SOURCE_ARTIFACT')",
            name="chk_m365_exchange_artifact_source_type",
        ),
        CheckConstraint(
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
        CheckConstraint(
            "observed_byte_length >= 0", name="chk_m365_exchange_artifact_size"
        ),
        CheckConstraint(
            _sha256_check("observed_sha256"),
            name="chk_m365_exchange_artifact_digest",
        ),
        CheckConstraint(
            "length(trim(drive_id)) > 0 AND length(trim(drive_item_id)) > 0 "
            "AND length(trim(logical_namespace)) > 0 "
            "AND length(trim(display_name)) > 0 AND length(trim(e_tag)) > 0",
            name="chk_m365_exchange_artifact_identity",
        ),
        Index(
            "idx_m365_exchange_artifacts_project",
            "organization_id",
            "project_id",
            "role",
        ),
    )
