from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import get_cookie_keys, hash_token
from app.core.rbac import get_current_user
from app.db import Base, get_db
from app.main import app
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, User, UserSession, UserStatus,
)


@pytest.fixture
def authenticated_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org = OrganizationProfile(legal_name="Compatibility test", organization_slug="compat",
                                  status=OrganizationStatus.ACTIVE)
        db.add(org)
        db.flush()
        user = User(organization_id=org.id, email="compat@example.test", full_name="Reader",
                    password_hash="unused", status=UserStatus.ACTIVE)
        db.add(user)
        db.flush()
        now = datetime.now(timezone.utc)
        session = UserSession(user_id=user.id, organization_id=org.id,
                              access_token_hash=hash_token("compat-test-cookie"),
                              access_expires_at=now + timedelta(minutes=5),
                              idle_expires_at=now + timedelta(minutes=5),
                              absolute_expires_at=now + timedelta(hours=1))
        db.add(session)
        db.commit()
        previous = app.dependency_overrides.copy()
        # Exercise production cookie authentication rather than conftest's X-User-Id shortcut.
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                yield client, session, db, user
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous)
    engine.dispose()


def test_exact_authenticated_read_only_contract(authenticated_client):
    client, session, db, user = authenticated_client
    client.cookies.set(get_cookie_keys()[0], "compat-test-cookie")
    response = client.get("/api/v1/client-compatibility")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "contract": "valora.client-compat/1", "api_contract": "valora.api/1",
        "web_contract": "valora.web/1", "required_native_protocol": "valora.native/2",
        "minimum_client_compatibility": 1, "recommended_client_compatibility": 1,
    }
    assert db.query(User).count() == 1
    assert db.query(UserSession).count() == 1
    assert client.get("/api/v1/.valora-native/v2/selected/" + "a" * 48).status_code == 404


@pytest.mark.parametrize("failure", ["missing", "invalid", "expired", "revoked", "inactive-user"])
def test_production_authentication_fails_closed(authenticated_client, failure):
    client, session, db, user = authenticated_client
    if failure != "missing":
        client.cookies.set(get_cookie_keys()[0], "invalid-cookie" if failure == "invalid" else "compat-test-cookie")
    if failure == "expired":
        session.access_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    if failure == "revoked":
        session.status = "revoked"
    if failure == "inactive-user":
        user.status = UserStatus.INACTIVE
    db.commit()
    response = client.get("/api/v1/client-compatibility", headers={"X-User-Id": str(user.id)})
    assert response.status_code == 401
    assert "required_native_protocol" not in response.json()
