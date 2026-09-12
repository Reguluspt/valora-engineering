"""Canonical document workspace persistence for UI/UX v2.3 PR-05."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
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
