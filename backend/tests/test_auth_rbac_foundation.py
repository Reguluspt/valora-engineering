import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserStatus,
    Role,
    UserRole,
)
from app.core.security import hash_password, verify_password
from app.core.rbac import (
    derive_effective_permissions,
    get_current_user,
    require_permission
)

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


def test_password_hashing() -> None:
    """Verifies that password hashing does not store plaintext and verifies correctly."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    # Assert that plaintext is not stored directly
    assert hashed != password
    assert "SuperSecretPassword123!" not in hashed

    # Verify correct password succeeds
    assert verify_password(password, hashed) is True

    # Verify incorrect password fails
    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False


def test_rbac_effective_permission_resolution(db_session: Session) -> None:
    """Verifies effective permission resolution from active roles."""
    # 1. Create active organization
    org = OrganizationProfile(
        legal_name="Test Organization",
        organization_slug="test-org",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.commit()

    # 2. Create active user
    user = User(
        organization_id=org.id,
        email="appraiser@test.com",
        full_name="Appraiser User",
        password_hash=hash_password("password"),
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()

    # 3. Create role
    role_appraiser = Role(
        code="appraiser",
        display_name="Appraiser",
        permissions=["project:create", "project:read", "project:update"]
    )
    db_session.add(role_appraiser)
    db_session.commit()

    # 4. Associate role with active UserRole
    user_role = UserRole(
        user_id=user.id,
        role_id=role_appraiser.id,
        is_active=True,
        revoked_at=None
    )
    db_session.add(user_role)
    db_session.commit()

    # 5. Resolve permissions
    perms = derive_effective_permissions(user, db_session)
    assert perms == {"project:create", "project:read", "project:update"}


def test_rbac_inactive_user_role(db_session: Session) -> None:
    """Verifies that inactive/revoked UserRole records do not grant permission."""
    org = OrganizationProfile(
        legal_name="Test Organization",
        organization_slug="test-org",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id,
        email="test@test.com",
        full_name="Test User",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()

    role = Role(
        code="appraiser",
        display_name="Appraiser",
        permissions=["project:create"]
    )
    db_session.add(role)
    db_session.commit()

    # Create inactive UserRole
    user_role_inactive = UserRole(
        user_id=user.id,
        role_id=role.id,
        is_active=False,
        revoked_at=None
    )
    db_session.add(user_role_inactive)
    db_session.commit()

    # Check effective permissions (should be empty)
    assert derive_effective_permissions(user, db_session) == set()

    # Create active but revoked UserRole
    user_role_revoked = UserRole(
        user_id=user.id,
        role_id=role.id,
        is_active=True,
        revoked_at=datetime.now(timezone.utc)
    )
    # Clear the session first
    db_session.delete(user_role_inactive)
    db_session.add(user_role_revoked)
    db_session.commit()

    assert derive_effective_permissions(user, db_session) == set()


def test_rbac_inactive_user_or_org(db_session: Session) -> None:
    """Verifies that inactive organization or user returns no permissions."""
    org_inactive = OrganizationProfile(
        legal_name="Test Organization Inactive",
        organization_slug="test-org-inactive",
        status=OrganizationStatus.INACTIVE,
    )
    org_active = OrganizationProfile(
        legal_name="Test Organization Active",
        organization_slug="test-org-active",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add_all([org_inactive, org_active])
    db_session.commit()

    # Case A: Active User but Inactive Org
    user_a = User(
        organization_id=org_inactive.id,
        email="user_a@test.com",
        full_name="User A",
        status=UserStatus.ACTIVE,
    )
    # Case B: Inactive User in Active Org
    user_b = User(
        organization_id=org_active.id,
        email="user_b@test.com",
        full_name="User B",
        status=UserStatus.INACTIVE,
    )
    db_session.add_all([user_a, user_b])
    db_session.commit()

    role = Role(
        code="appraiser",
        display_name="Appraiser",
        permissions=["project:create"]
    )
    db_session.add(role)
    db_session.commit()

    ur_a = UserRole(user_id=user_a.id, role_id=role.id, is_active=True, revoked_at=None)
    ur_b = UserRole(user_id=user_b.id, role_id=role.id, is_active=True, revoked_at=None)
    db_session.add_all([ur_a, ur_b])
    db_session.commit()

    # Permissions must be empty for both
    assert derive_effective_permissions(user_a, db_session) == set()
    assert derive_effective_permissions(user_b, db_session) == set()


def test_rbac_deny_by_default(db_session: Session) -> None:
    """Verifies deny-by-default behavior (e.g. unassigned permissions are missing)."""
    org = OrganizationProfile(
        legal_name="Test Organization",
        organization_slug="test-org",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id,
        email="test@test.com",
        full_name="Test User",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()

    # No role assigned, effective permissions must be empty
    assert derive_effective_permissions(user, db_session) == set()


def test_require_permission_dependency(db_session: Session) -> None:
    """Verifies require_permission dependency raises HTTP 403 when permission is missing."""
    org = OrganizationProfile(
        legal_name="Test Organization",
        organization_slug="test-org",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id,
        email="test@test.com",
        full_name="Test User",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()

    role = Role(
        code="viewer",
        display_name="Viewer",
        permissions=["project:read"]
    )
    db_session.add(role)
    db_session.commit()

    user_role = UserRole(user_id=user.id, role_id=role.id, is_active=True)
    db_session.add(user_role)
    db_session.commit()

    # Test the dependency logic directly
    dependency_func = require_permission("project:read")
    # Should succeed and return current user
    assert dependency_func(current_user=user, db=db_session) == user

    # Should raise HTTP 403 for project:create
    dependency_func_create = require_permission("project:create")
    with pytest.raises(HTTPException) as exc_info:
        dependency_func_create(current_user=user, db=db_session)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Missing permission"


def test_get_current_user_dependency(db_session: Session) -> None:
    """Verifies get_current_user behaves correctly with headers."""
    org = OrganizationProfile(
        legal_name="Test Organization",
        organization_slug="test-org",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id,
        email="test@test.com",
        full_name="Test User",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()

    # 1. No header raises HTTP 401
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=db_session, x_user_id=None)
    assert exc_info.value.status_code == 401

    # 2. Invalid header format raises HTTP 401
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=db_session, x_user_id="not-a-uuid")
    assert exc_info.value.status_code == 401

    # 3. Non-existent user raises HTTP 401
    random_uuid = str(uuid.uuid4())
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(db=db_session, x_user_id=random_uuid)
    assert exc_info.value.status_code == 401

    # 4. Valid user ID header returns user
    res_user = get_current_user(db=db_session, x_user_id=str(user.id))
    assert res_user.id == user.id
