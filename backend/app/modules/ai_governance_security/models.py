"""Design Book v1.2 security records used by protected mutation paths.

Only the append-only audit primitives required by S14-R-001 are implemented
here.  Broader AI-governance runtime behavior remains outside this slice.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base_class import Base
from app.db.mixins import UUIDMixin, utc_now


class SecuritySeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TenantBoundaryResult(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"


class SecurityEvent(Base, UUIDMixin):
    """Append-only security finding/event."""

    __tablename__ = "security_events"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("organization_profiles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    event_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="chk_security_event_severity",
        ),
        Index("idx_security_event_org_created", "organization_id", "created_at"),
        Index("idx_security_event_user_created", "user_id", "created_at"),
        Index("idx_security_event_type_created", "event_type", "created_at"),
    )


class SecurityAuditLog(Base, UUIDMixin):
    """Append-only audit trail for security commands and enforcement."""

    __tablename__ = "security_audit_logs"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("organization_profiles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    action_type: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(String(128), nullable=False)
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    before_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    after_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_security_audit_org_created", "organization_id", "created_at"),
        Index("idx_security_audit_actor_created", "actor_id", "created_at"),
        Index("idx_security_audit_action_created", "action_type", "created_at"),
    )


class TenantBoundaryCheck(Base, UUIDMixin):
    """Append-only result of a high-risk organization boundary check."""

    __tablename__ = "tenant_boundary_checks"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organization_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "result IN ('pass', 'fail')",
            name="chk_tenant_boundary_result",
        ),
        CheckConstraint(
            "(result = 'pass' AND failure_reason IS NULL) OR "
            "(result = 'fail' AND failure_reason IS NOT NULL)",
            name="chk_tenant_boundary_failure_reason",
        ),
        Index(
            "idx_tenant_boundary_org_resource_created",
            "organization_id",
            "resource_type",
            "resource_id",
            "created_at",
        ),
    )
