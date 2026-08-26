"""Append-only security audit helpers for protected mutation services."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.ai_governance_security.models import (
    SecurityAuditLog,
    SecurityEvent,
    TenantBoundaryCheck,
)


@dataclass(frozen=True)
class BoundaryAuditRecords:
    boundary_check: TenantBoundaryCheck
    security_event: SecurityEvent | None
    security_audit_log: SecurityAuditLog


def record_tenant_boundary_check(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    resource_type: str,
    resource_id: uuid.UUID,
    passed: bool,
    failure_reason: str | None = None,
) -> BoundaryAuditRecords:
    """Stage the Design Book boundary records in the caller's transaction."""
    if passed and failure_reason is not None:
        raise ValueError("A passing tenant boundary check cannot have a failure reason.")
    if not passed and not failure_reason:
        raise ValueError("A failed tenant boundary check requires a bounded reason code.")

    boundary = TenantBoundaryCheck(
        organization_id=organization_id,
        resource_type=resource_type,
        resource_id=resource_id,
        result="pass" if passed else "fail",
        failure_reason=failure_reason,
    )
    security_event = None
    if not passed:
        security_event = SecurityEvent(
            organization_id=organization_id,
            user_id=actor_id,
            event_type="cross_tenant_access_attempt",
            severity="high",
            target_type=resource_type,
            target_id=resource_id,
            event_metadata={"reason_code": failure_reason},
        )
        db.add(security_event)

    audit_log = SecurityAuditLog(
        organization_id=organization_id,
        actor_id=actor_id,
        action_type=(
            "tenant_boundary_check_passed" if passed else "tenant_boundary_check_failed"
        ),
        target_type=resource_type,
        target_id=resource_id,
    )
    db.add_all([boundary, audit_log])
    db.flush()
    return BoundaryAuditRecords(boundary, security_event, audit_log)


def record_authorization_denial(
    db: Session,
    *,
    organization_id: uuid.UUID,
    actor_id: uuid.UUID,
    permission_code: str,
    target_type: str,
    target_id: uuid.UUID,
) -> tuple[SecurityEvent, SecurityAuditLog]:
    """Stage a denied protected command without exposing target contents."""
    event = SecurityEvent(
        organization_id=organization_id,
        user_id=actor_id,
        event_type="authorization_denied",
        severity="medium",
        target_type=target_type,
        target_id=target_id,
        event_metadata={"permission_code": permission_code},
    )
    audit = SecurityAuditLog(
        organization_id=organization_id,
        actor_id=actor_id,
        action_type="authorization_denied",
        target_type=target_type,
        target_id=target_id,
    )
    db.add_all([event, audit])
    db.flush()
    return event, audit
