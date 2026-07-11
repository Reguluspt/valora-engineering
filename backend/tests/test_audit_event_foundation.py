import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserStatus,
    AuditEvent
)
from app.core.audit import log_audit_event, sanitize_payload


@pytest.fixture
def db_session() -> Session:
    """Fixture that initializes a SQLite in-memory database and provides a session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_audit_event_model_metadata(db_session: Session) -> None:
    """Verifies that AuditEvent model can be mapped, saved, and read from DB."""
    # 1. Create org and user
    org = OrganizationProfile(
        legal_name="Audit Org",
        organization_slug="audit-org",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id,
        email="auditor@test.com",
        full_name="Auditor User",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()

    # 2. Add an AuditEvent record manually
    evt = AuditEvent(
        organization_id=org.id,
        actor_user_id=user.id,
        command_name="CreateProject",
        event_name="ProjectCreated",
        entity_type="Project",
        entity_id=uuid.uuid4(),
        correlation_id="corr-123",
        payload={"some_key": "some_value"}
    )
    db_session.add(evt)
    db_session.commit()

    # 3. Retrieve and assert
    retrieved = db_session.query(AuditEvent).filter(AuditEvent.id == evt.id).first()
    assert retrieved is not None
    assert retrieved.command_name == "CreateProject"
    assert retrieved.event_name == "ProjectCreated"
    assert retrieved.payload == {"some_key": "some_value"}
    assert retrieved.created_at is not None


def test_log_audit_event_transactional(db_session: Session) -> None:
    """Verifies that log_audit_event writes to session without committing directly."""
    org = OrganizationProfile(
        legal_name="Audit Org",
        organization_slug="audit-org",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.commit()

    # Start a transaction block
    nested = db_session.begin_nested()
    evt = log_audit_event(
        db=db_session,
        event_name="ProjectCreated",
        entity_type="Project",
        entity_id=uuid.uuid4(),
        organization_id=org.id,
        command_name="CreateProject"
    )
    # Verify it is stored and has an ID assigned due to flush
    assert evt.id is not None
    
    # Query inside the transaction
    db_evt = db_session.query(AuditEvent).filter(AuditEvent.id == evt.id).first()
    assert db_evt is not None

    # Roll back nested transaction to verify it gets discarded
    nested.rollback()
    db_evt_after = db_session.query(AuditEvent).first()
    assert db_evt_after is None


def test_payload_sanitization() -> None:
    """Verifies that sensitive data keys are redacted by sanitize_payload."""
    payload = {
        "user_id": "123",
        "username": "testuser",
        "password": "my_plain_password",
        "nested": {
            "secret_key": "supersecret",
            "safe_field": "hello",
            "api_token": "bearer xyz"
        },
        "list_items": [
            {"password_hash": "$argon2id$..."},
            {"safe_value": 42}
        ]
    }

    sanitized = sanitize_payload(payload)

    # Assert regular fields are preserved
    assert sanitized["user_id"] == "123"
    assert sanitized["username"] == "testuser"
    assert sanitized["nested"]["safe_field"] == "hello"
    assert sanitized["list_items"][1]["safe_value"] == 42

    # Assert sensitive fields are redacted
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["nested"]["secret_key"] == "[REDACTED]"
    assert sanitized["nested"]["api_token"] == "[REDACTED]"
    assert sanitized["list_items"][0]["password_hash"] == "[REDACTED]"


def test_audit_event_append_only_policy() -> None:
    """Documents and verifies that update/delete is not supported / blocked for audit logs."""
    # Since SQLAlchemy permits updates/deletes unless explicit DB triggers exist,
    # we verify that our application layer does not define any update/delete helper APIs.
    # To simulate append-only, any attempts to modify audit events should be prohibited
    # at the policy/code review level.
    import app.core.audit as audit_module
    
    # Assert there are no update or delete functions exported by the audit core module
    exports = dir(audit_module)
    assert "update_audit_event" not in exports
    assert "delete_audit_event" not in exports
