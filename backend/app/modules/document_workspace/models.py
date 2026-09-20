"""Canonical document workspace persistence for UI/UX v2.3 PR-05."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.mixins import TimestampMixin, UUIDMixin, utc_now


class DocumentRecord(Base, UUIDMixin, TimestampMixin):
    """Stable VALORA document identity, separate from generated render outputs."""

    __tablename__ = "document_records"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "project_id", "id", name="uq_document_records_tenant_id"
        ),
        ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            name="fk_document_record_project_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_document_record_creator_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "length(trim(document_type)) > 0",
            name="chk_document_record_type_trim",
        ),
        CheckConstraint("length(trim(title)) > 0", name="chk_document_record_title_trim"),
        Index("idx_document_records_project", "organization_id", "project_id"),
    )


class DocumentRevision(Base, UUIDMixin):
    """Append-only business revision bound to one immutable Data Snapshot digest."""

    __tablename__ = "document_revisions"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_revision: Mapped[int] = mapped_column(nullable=False)
    data_snapshot_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
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
            "organization_id",
            "project_id",
            "document_id",
            "document_revision",
            name="uq_document_revision_number",
        ),
        UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_document_revision_idempotency"
        ),
        UniqueConstraint(
            "organization_id",
            "project_id",
            "document_id",
            "id",
            name="uq_document_revisions_tenant_id",
        ),
        UniqueConstraint(
            "organization_id",
            "project_id",
            "document_id",
            "id",
            "content_checksum_sha256",
            name="uq_document_revision_content_checksum",
        ),
        ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id"],
            [
                "document_records.organization_id",
                "document_records.project_id",
                "document_records.id",
            ],
            name="fk_document_revision_record_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "created_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_document_revision_creator_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "document_revision > 0", name="chk_document_revision_positive"
        ),
        CheckConstraint(
            "length(trim(idempotency_key)) > 0",
            name="chk_document_revision_idempotency_trim",
        ),
        CheckConstraint(
            "length(data_snapshot_digest_sha256) = 64 "
            "AND data_snapshot_digest_sha256 = lower(data_snapshot_digest_sha256) "
            "AND data_snapshot_digest_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_document_revision_snapshot_digest",
        ),
        CheckConstraint(
            "length(content_checksum_sha256) = 64 "
            "AND content_checksum_sha256 = lower(content_checksum_sha256) "
            "AND content_checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_document_revision_content_checksum",
        ),
        CheckConstraint(
            "length(request_digest_sha256) = 64 "
            "AND request_digest_sha256 = lower(request_digest_sha256) "
            "AND request_digest_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_document_revision_request_digest",
        ),
        Index(
            "idx_document_revisions_record",
            "organization_id",
            "project_id",
            "document_id",
        ),
    )


class DocumentRevisionCurrentHead(Base):
    """One explicit current revision pointer per canonical document."""

    __tablename__ = "document_revision_current_heads"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, primary_key=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, primary_key=True)
    current_revision_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_revision: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id"],
            [
                "document_records.organization_id",
                "document_records.project_id",
                "document_records.id",
            ],
            name="fk_document_head_record_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
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
        CheckConstraint(
            "document_revision > 0", name="chk_document_head_revision_positive"
        ),
    )


def _sha256_check(column: str) -> str:
    return (
        f"length({column}) = 64 AND {column} = lower({column}) "
        f"AND {column} ~ '^[0-9a-f]{{64}}$'"
    )


class DocumentStorageExecutionIntent(Base, UUIDMixin):
    """Immutable command that freezes a document head before storage I/O."""

    __tablename__ = "document_storage_execution_intents"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    expected_revision_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    expected_document_revision: Mapped[int] = mapped_column(nullable=False)
    expected_content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key", name="uq_storage_intent_idempotency"),
        UniqueConstraint("organization_id", "id", name="uq_storage_intent_tenant_id"),
        ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id"],
            [
                "document_records.organization_id",
                "document_records.project_id",
                "document_records.id",
            ],
            name="fk_storage_intent_document_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id", "expected_revision_id"],
            [
                "document_revisions.organization_id",
                "document_revisions.project_id",
                "document_revisions.document_id",
                "document_revisions.id",
            ],
            name="fk_storage_intent_revision_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "requested_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_storage_intent_actor_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint("expected_document_revision > 0", name="chk_storage_intent_revision"),
        CheckConstraint("length(trim(idempotency_key)) > 0", name="chk_storage_intent_idempotency"),
        CheckConstraint(_sha256_check("expected_content_sha256"), name="chk_storage_intent_content"),
        CheckConstraint(_sha256_check("request_digest_sha256"), name="chk_storage_intent_request"),
        CheckConstraint(_sha256_check("plan_digest_sha256"), name="chk_storage_intent_plan"),
        CheckConstraint(_sha256_check("decision_digest_sha256"), name="chk_storage_intent_decision"),
        Index("idx_storage_intent_document", "organization_id", "project_id", "document_id"),
    )


class DocumentStorageCandidate(Base, UUIDMixin):
    """One deterministic immutable-object target for an execution intent."""

    __tablename__ = "document_storage_candidates"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    execution_intent_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    storage_profile_id: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    container_name: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_length: Mapped[int] = mapped_column(BigInteger, nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    generator_version: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "execution_intent_id", name="uq_storage_candidate_intent"),
        UniqueConstraint("organization_id", "id", name="uq_storage_candidate_tenant_id"),
        UniqueConstraint(
            "storage_profile_id", "container_name", "object_key", name="uq_storage_candidate_target"
        ),
        UniqueConstraint(
            "organization_id", "id", "content_sha256", "byte_length",
            name="uq_storage_candidate_integrity",
        ),
        ForeignKeyConstraint(
            ["organization_id", "execution_intent_id"],
            ["document_storage_execution_intents.organization_id", "document_storage_execution_intents.id"],
            name="fk_storage_candidate_intent_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "provider_kind IN ('fake', 'local')", name="chk_storage_candidate_provider"
        ),
        CheckConstraint("byte_length >= 0", name="chk_storage_candidate_size"),
        CheckConstraint(
            "length(trim(storage_profile_id)) > 0 AND length(trim(container_name)) > 0 "
            "AND length(trim(object_key)) > 0 AND length(trim(media_type)) > 0 "
            "AND length(trim(generator_version)) > 0",
            name="chk_storage_candidate_identity",
        ),
        CheckConstraint(_sha256_check("content_sha256"), name="chk_storage_candidate_content"),
    )


class DocumentStorageExecutionEvent(Base, UUIDMixin):
    """Append-only durable fact for one storage-intent transition."""

    __tablename__ = "document_storage_execution_events"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    execution_intent_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    sequence: Mapped[int] = mapped_column(nullable=False)
    event_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observed_object_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observed_etag: Mapped[str | None] = mapped_column(String(512), nullable=True)
    observed_object_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observed_content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_byte_length: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "execution_intent_id", "sequence", name="uq_storage_event_sequence"
        ),
        ForeignKeyConstraint(
            ["organization_id", "execution_intent_id"],
            ["document_storage_execution_intents.organization_id", "document_storage_execution_intents.id"],
            name="fk_storage_event_intent_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "recorded_by_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_storage_event_actor_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint("sequence > 0", name="chk_storage_event_sequence"),
        CheckConstraint("length(trim(event_code)) > 0", name="chk_storage_event_code"),
        CheckConstraint(
            "observed_byte_length IS NULL OR observed_byte_length >= 0",
            name="chk_storage_event_size",
        ),
        CheckConstraint(
            "observed_content_sha256 IS NULL OR (" + _sha256_check("observed_content_sha256") + ")",
            name="chk_storage_event_content",
        ),
    )


class DocumentStorageExecutionState(Base):
    """One-row-per-intent rebuildable projection used by guarded transitions."""

    __tablename__ = "document_storage_execution_states"

    execution_intent_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    current_state: Mapped[str] = mapped_column(String(48), nullable=False)
    state_version: Mapped[int] = mapped_column(nullable=False, default=1)
    last_event_sequence: Mapped[int] = mapped_column(nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now(), onupdate=utc_now
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "execution_intent_id"],
            ["document_storage_execution_intents.organization_id", "document_storage_execution_intents.id"],
            name="fk_storage_state_intent_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint("state_version > 0", name="chk_storage_state_version"),
        CheckConstraint("last_event_sequence > 0", name="chk_storage_state_sequence"),
        CheckConstraint(
            "current_state IN ('PREPARED', 'CANDIDATE_GENERATED', 'CREATE_DISPATCHED', "
            "'CREATE_OUTCOME_UNKNOWN', 'OBJECT_OBSERVED', 'OBJECT_VERIFIED', 'FINALIZING', "
            "'STORAGE_UNAVAILABLE', 'RECONCILIATION_REQUIRED', 'SUPERSEDED', 'ABANDONED', 'FINALIZED')",
            name="chk_storage_state_value",
        ),
    )


class StorageObjectBinding(Base, UUIDMixin):
    """Append-only authoritative-object proof for a newly finalized revision."""

    __tablename__ = "storage_object_bindings"

    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    document_revision_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    execution_intent_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    storage_candidate_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    storage_profile_id: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    container_name: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    provider_object_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checksum_algorithm: Mapped[str] = mapped_column(String(16), nullable=False, default="SHA256")
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_length: Mapped[int] = mapped_column(BigInteger, nullable=False)
    observed_etag: Mapped[str | None] = mapped_column(String(512), nullable=True)
    object_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bound_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    retention_policy_code: Mapped[str] = mapped_column(String(64), nullable=False)
    retention_anchor_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    minimum_retain_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "document_revision_id", name="uq_storage_binding_revision"),
        UniqueConstraint("organization_id", "execution_intent_id", name="uq_storage_binding_intent"),
        UniqueConstraint("organization_id", "storage_candidate_id", name="uq_storage_binding_candidate"),
        UniqueConstraint(
            "storage_profile_id", "container_name", "object_key", name="uq_storage_binding_target"
        ),
        ForeignKeyConstraint(
            ["organization_id", "project_id", "document_id", "document_revision_id", "content_sha256"],
            [
                "document_revisions.organization_id",
                "document_revisions.project_id",
                "document_revisions.document_id",
                "document_revisions.id",
                "document_revisions.content_checksum_sha256",
            ],
            name="fk_storage_binding_revision_content",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "execution_intent_id"],
            ["document_storage_execution_intents.organization_id", "document_storage_execution_intents.id"],
            name="fk_storage_binding_intent_tenant",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["organization_id", "storage_candidate_id", "content_sha256", "byte_length"],
            [
                "document_storage_candidates.organization_id",
                "document_storage_candidates.id",
                "document_storage_candidates.content_sha256",
                "document_storage_candidates.byte_length",
            ],
            name="fk_storage_binding_candidate_integrity",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "provider_kind IN ('fake', 'local')", name="chk_storage_binding_provider"
        ),
        CheckConstraint("checksum_algorithm = 'SHA256'", name="chk_storage_binding_checksum_algorithm"),
        CheckConstraint("byte_length >= 0", name="chk_storage_binding_size"),
        CheckConstraint(
            "minimum_retain_until >= retention_anchor_at", name="chk_storage_binding_retention"
        ),
        CheckConstraint(_sha256_check("content_sha256"), name="chk_storage_binding_content"),
    )
