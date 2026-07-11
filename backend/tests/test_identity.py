import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserStatus,
    Role,
    UserRole,
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


def test_organization_uniqueness(db_session: Session) -> None:
    """Verifies that organization_slug is unique."""
    org1 = OrganizationProfile(
        legal_name="Org One",
        organization_slug="org-slug",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add(org1)
    db_session.commit()

    org2 = OrganizationProfile(
        legal_name="Org Two",
        organization_slug="org-slug",  # duplicate slug
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add(org2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_user_email_uniqueness_per_organization(db_session: Session) -> None:
    """Verifies uq_user_org_email unique constraint on (organization_id, email)."""
    # 1. Setup two organizations
    org_a = OrganizationProfile(
        legal_name="Org A",
        organization_slug="org-a",
        status=OrganizationStatus.ACTIVE,
    )
    org_b = OrganizationProfile(
        legal_name="Org B",
        organization_slug="org-b",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add_all([org_a, org_b])
    db_session.commit()

    # 2. Add user in Org A
    user1 = User(
        organization_id=org_a.id,
        email="test@example.com",
        full_name="User One",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user1)
    db_session.commit()

    # 3. Add same email in different Org B (should pass)
    user2 = User(
        organization_id=org_b.id,
        email="test@example.com",
        full_name="User Two",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user2)
    db_session.commit()

    # 4. Add duplicate email in same Org A (should fail)
    user3 = User(
        organization_id=org_a.id,
        email="test@example.com",
        full_name="User Three",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user3)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_user_role_assignment_and_uniqueness(db_session: Session) -> None:
    """Verifies UserRole active relationship uniqueness constraint."""
    org = OrganizationProfile(
        legal_name="Test Org",
        organization_slug="test-org",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id,
        email="user@test.org",
        full_name="Test User",
        status=UserStatus.ACTIVE,
    )
    role = Role(
        code="appraiser",
        display_name="Appraiser",
        permissions=["project:create", "project:read"],
    )
    db_session.add_all([user, role])
    db_session.commit()

    # 1. Assign active role
    user_role1 = UserRole(
        user_id=user.id,
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user_role1)
    db_session.commit()

    # 2. Assign duplicate active role (should fail on uq_active_user_role index)
    user_role2 = UserRole(
        user_id=user.id,
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user_role2)
    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()

    # 3. Assign duplicate but inactive role (should pass)
    user_role3 = UserRole(
        user_id=user.id,
        role_id=role.id,
        is_active=False,
    )
    db_session.add(user_role3)
    db_session.commit()


def test_relationships_and_back_populates(db_session: Session) -> None:
    """Verifies model relationships populate correctly."""
    org = OrganizationProfile(
        legal_name="Relation Org",
        organization_slug="rel-org",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id,
        email="rel@rel.org",
        full_name="Rel User",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()

    # Verify back populates on OrganizationProfile
    db_session.refresh(org)
    assert len(org.users) == 1
    assert org.users[0].id == user.id
    assert org.users[0].organization.id == org.id
