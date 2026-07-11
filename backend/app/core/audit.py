import uuid
from typing import Optional, Any
from sqlalchemy.orm import Session
from app.modules.project_master_data.models import AuditEvent

# Sensitive keys to redact
SENSITIVE_KEY_SUBSTRINGS = {
    "password",
    "secret",
    "token",
    "key",
    "credential",
    "hash",
    "passphrase"
}

def sanitize_payload(payload: Any) -> Any:
    """
    Recursively sanitizes a JSON/dict payload to redact sensitive keys.
    """
    if isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            k_lower = k.lower()
            if any(sub in k_lower for sub in SENSITIVE_KEY_SUBSTRINGS):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_payload(v)
        return sanitized
    elif isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    return payload


def log_audit_event(
    db: Session,
    event_name: str,
    entity_type: str,
    entity_id: Optional[uuid.UUID] = None,
    organization_id: Optional[uuid.UUID] = None,
    actor_user_id: Optional[uuid.UUID] = None,
    command_name: Optional[str] = None,
    correlation_id: Optional[str] = None,
    payload: Optional[dict] = None
) -> AuditEvent:
    """
    Creates and persists an AuditEvent record inside the existing DB transaction.
    Crucially, it does NOT call db.commit() itself, which allows the event to
    be written atomically as part of the overall transaction.
    """
    # Sanitize the payload if provided
    sanitized_payload = None
    if payload is not None:
        sanitized_payload = sanitize_payload(payload)

    audit_event = AuditEvent(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        command_name=command_name,
        event_name=event_name,
        entity_type=entity_type,
        entity_id=entity_id,
        correlation_id=correlation_id,
        payload=sanitized_payload
    )

    db.add(audit_event)
    db.flush()  # Populates audit_event.id and timestamps in current transaction

    return audit_event
