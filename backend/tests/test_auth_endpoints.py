import uuid
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.main import app
from app.db import get_db
from app.core.security import hash_password
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserStatus,
    UserSession,
    RefreshTokenRecord
)
from app.api.auth import hash_token, get_cookie_keys

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from app.db import Base

# Setup in-memory SQLite fixtures
@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session: Session) -> TestClient:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def test_setup(db_session: Session):
    # Create active org
    org = OrganizationProfile(
        legal_name="Regulus Corp",
        organization_slug="regulus",
        status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    db_session.commit()

    # Create active user
    pw_hash = hash_password("secret_pass")
    user = User(
        organization_id=org.id,
        email="architect@regulus.com",
        full_name="Senior Architect",
        password_hash=pw_hash,
        status=UserStatus.ACTIVE
    )
    db_session.add(user)
    db_session.commit()
    
    return {"org": org, "user": user}

def test_login_flow_success_and_failure(client: TestClient, test_setup):
    # 1. Test wrong password fails
    resp = client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "wrong_password"
    })
    assert resp.status_code == 401
    assert resp.json()["detail"]["title"] == "Phiên làm việc hết hạn"

    # 2. Test success
    resp = client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "secret_pass"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies
    assert "XSRF-TOKEN" in resp.cookies

def test_me_endpoint_requires_auth(client: TestClient, test_setup):
    # 1. Unauthorized
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    
    # 2. Login first
    client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "secret_pass"
    })
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "architect@regulus.com"

def test_refresh_token_rotation_and_reuse_detection(client: TestClient, test_setup, db_session: Session):
    # Login to get initial cookies
    client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "secret_pass"
    })
    acc_cookie_key, ref_cookie_key = get_cookie_keys()
    
    initial_refresh_token = client.cookies.get(ref_cookie_key)
    initial_csrf_token = client.cookies.get("XSRF-TOKEN")
    
    # Call refresh API
    client.headers["X-CSRF-Token"] = initial_csrf_token
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200
    
    # Check that cookies were rotated
    rotated_refresh_token = client.cookies.get(ref_cookie_key)
    assert rotated_refresh_token != initial_refresh_token
    
    # Check that reusing the old token revokes everything
    # Create a fresh client and set the old cookies
    clean_client = TestClient(app)
    clean_client.cookies.set(ref_cookie_key, initial_refresh_token)
    clean_client.headers["X-CSRF-Token"] = initial_csrf_token
    
    resp_reuse = clean_client.post("/api/v1/auth/refresh")
    assert resp_reuse.status_code == 401
    
    # Check in DB that the session has been revoked
    old_hash = hash_token(initial_refresh_token)
    record = db_session.query(RefreshTokenRecord).filter(
        RefreshTokenRecord.token_hash == old_hash
    ).first()
    
    session = db_session.query(UserSession).filter(
        UserSession.id == record.user_session_id
    ).first()
    assert session.status == "revoked"

def test_csrf_missing_fails(client: TestClient, test_setup):
    client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "secret_pass"
    })
    # CSRF token header missing -> should fail on state-changing logout
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 401
    assert "CSRF" in resp.json()["detail"]["title"]

def test_inactive_user_fail_closed(client: TestClient, test_setup, db_session: Session):
    client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "secret_pass"
    })
    
    # Disable user
    user = test_setup["user"]
    user.status = UserStatus.INACTIVE
    db_session.commit()
    
    # Try requesting /me
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
