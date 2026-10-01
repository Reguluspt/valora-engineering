"""Post-migration standard-role proof on the CI PostgreSQL database."""

import os
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.rbac import derive_effective_permissions
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, Role, User, UserRole, UserStatus,
)


COMMAND_PERMISSIONS = {
    "project:preliminary_analysis:finalize",
    "project:preliminary_result:generate",
    "project:official_intake:commit",
}


def _engine():
    url = os.getenv("TEST_DATABASE_URL")
    if not url or not url.startswith("postgres"):
        if os.getenv("CI") == "true":
            pytest.fail("CI requires PostgreSQL TEST_DATABASE_URL for G1.1E RBAC proof")
        pytest.skip("G1.1E RBAC proof requires PostgreSQL TEST_DATABASE_URL")
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    with engine.connect() as connection:
        head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert head == "e2f3a4b5c6d7"
    return engine


def test_migrated_role_grants_and_effective_permission_boundaries():
    engine = _engine()
    db = Session(engine)
    try:
        roles = {role.code: role for role in db.query(Role).filter(Role.code.in_(
            ("owner", "appraiser", "admin", "reviewer", "knowledge_curator", "viewer")
        )).all()}
        assert set(roles) == {
            "owner", "appraiser", "admin", "reviewer", "knowledge_curator", "viewer",
        }
        for code in ("owner", "appraiser"):
            assert COMMAND_PERMISSIONS <= set(roles[code].permissions)
        for code in ("admin", "reviewer", "knowledge_curator", "viewer"):
            assert not COMMAND_PERMISSIONS & set(roles[code].permissions)
        assert "project:update" in roles["admin"].permissions

        org = OrganizationProfile(
            legal_name="G1.1E RBAC test", organization_slug=f"g11e-rbac-{uuid.uuid4().hex}",
            status=OrganizationStatus.ACTIVE,
        )
        db.add(org)
        db.flush()
        users = {}
        for code, role in roles.items():
            user = User(
                organization_id=org.id, email=f"{code}-{uuid.uuid4().hex}@example.com",
                full_name=code, status=UserStatus.ACTIVE,
            )
            db.add(user)
            db.flush()
            db.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))
            users[code] = user
        db.flush()
        db.expire_all()
        for code, user in users.items():
            permissions = derive_effective_permissions(user, db)
            if code in {"owner", "appraiser"}:
                assert COMMAND_PERMISSIONS <= permissions
            else:
                assert not COMMAND_PERMISSIONS & permissions

        owner = users["owner"]
        binding = owner.roles[0]
        binding.is_active = False
        db.flush()
        assert not COMMAND_PERMISSIONS & derive_effective_permissions(owner, db)
        binding.is_active = True
        binding.revoked_at = datetime.now(timezone.utc)
        db.flush()
        assert not COMMAND_PERMISSIONS & derive_effective_permissions(owner, db)
        binding.revoked_at = None
        owner.status = UserStatus.INACTIVE
        db.flush()
        assert not COMMAND_PERMISSIONS & derive_effective_permissions(owner, db)
        owner.status = UserStatus.ACTIVE
        org.status = OrganizationStatus.INACTIVE
        db.flush()
        assert not COMMAND_PERMISSIONS & derive_effective_permissions(owner, db)
    finally:
        db.rollback()
        db.close()
        engine.dispose()
