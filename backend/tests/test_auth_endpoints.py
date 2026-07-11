import uuid
import pytest
import threading
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from app.db import get_db, Base
from app.core.config import get_settings
from app.core.security import hash_password
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserStatus,
    UserSession,
    RefreshTokenRecord,
    AuditEvent
)
from app.api.auth import hash_token, get_cookie_keys

settings = get_settings()

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
    org = OrganizationProfile(
        legal_name="Regulus Corp",
        organization_slug="regulus",
        status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    db_session.commit()

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
    
    # Call refresh API with Origin header to pass CSRF origin check
    client.headers["X-CSRF-Token"] = initial_csrf_token
    client.headers["Origin"] = "http://localhost:5173"
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200
    
    # Check that cookies were rotated
    rotated_refresh_token = client.cookies.get(ref_cookie_key)
    assert rotated_refresh_token != initial_refresh_token
    
    # Check that reusing the old token revokes everything
    clean_client = TestClient(app)
    clean_client.cookies.set(ref_cookie_key, initial_refresh_token)
    clean_client.headers["X-CSRF-Token"] = initial_csrf_token
    clean_client.headers["Origin"] = "http://localhost:5173"
    
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
    # CSRF token header missing -> should fail on state-changing logout with 403 Forbidden
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "CSRF_ERROR"

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

def test_inactive_org_fail_closed(client: TestClient, test_setup, db_session: Session):
    client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "secret_pass"
    })
    
    # Disable org
    org = test_setup["org"]
    org.status = OrganizationStatus.INACTIVE
    db_session.commit()
    
    # Try requesting /me
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401

def test_session_idle_timeout(client: TestClient, test_setup, db_session: Session):
    client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "secret_pass"
    })
    acc_cookie_key, ref_cookie_key = get_cookie_keys()
    
    # Mutate db session to be idle-expired
    sess = db_session.query(UserSession).filter(UserSession.status == "active").first()
    sess.idle_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()
    
    # Try me
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401

def test_session_absolute_timeout(client: TestClient, test_setup, db_session: Session):
    client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "secret_pass"
    })
    
    # Mutate db session to absolute-expired
    sess = db_session.query(UserSession).filter(UserSession.status == "active").first()
    sess.absolute_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()
    
    # Try me
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401

def test_csrf_origin_exact_match(client: TestClient, test_setup):
    client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "secret_pass"
    })
    
    csrf_token = client.cookies.get("XSRF-TOKEN")
    
    # Test attacker substring domain in Origin
    client.headers["X-CSRF-Token"] = csrf_token
    client.headers["Origin"] = "http://localhost:5173.attacker.com"
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 403
    
    # Test valid origin succeeds
    client.headers["Origin"] = "http://localhost:5173"
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200

def test_x_user_id_spoofing_ignored(client: TestClient, test_setup):
    # Try to spoof X-User-Id header directly
    client.headers["X-User-Id"] = str(test_setup["user"].id)
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401

def test_audit_events_created(client: TestClient, test_setup, db_session: Session):
    client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "secret_pass"
    })
    
    # Verify audit event session.created exists
    evt = db_session.query(AuditEvent).filter(AuditEvent.event_name == "auth.session.created").first()
    assert evt is not None
    assert evt.payload["session_id"] is not None

def test_csrf_centrally_enforced_on_mutations(client: TestClient, test_setup):
    # Authenticate first
    client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "secret_pass"
    })
    # Remove CSRF token header
    if "X-CSRF-Token" in client.headers:
        del client.headers["X-CSRF-Token"]
        
    # Unsafe method POST to projects endpoint (or master data endpoint) should block centrally
    resp = client.post("/api/v1/projects")
    assert resp.status_code == 403

def test_postgres_concurrent_refresh_locking():
    # Skip if PG is not reachable
    pg_url = "postgresql+psycopg://valora:valora_local_password@localhost:5432/valora"
    try:
        engine = create_engine(pg_url)
        with engine.connect():
            pass
    except Exception:
        pytest.skip("PostgreSQL not available. Skipping integration test.")
        return

    # Run migrations on pg database to ensure clean schema
    import subprocess
    subprocess.run(["alembic", "upgrade", "head"], cwd="backend", check=True)
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Create Org, User, UserSession, RefreshTokenRecord
        org = OrganizationProfile(
            legal_name="PG Concurrency Org",
            organization_slug="pg-org",
            status=OrganizationStatus.ACTIVE
        )
        db.add(org)
        db.commit()

        user = User(
            organization_id=org.id,
            email="pg@regulus.com",
            full_name="PG User",
            password_hash=hash_password("password"),
            status=UserStatus.ACTIVE
        )
        db.add(user)
        db.commit()

        now = datetime.now(timezone.utc)
        session = UserSession(
            user_id=user.id,
            organization_id=org.id,
            access_token_hash="pg-acc-hash",
            csrf_token_hash="pg-csrf-hash",
            status="active",
            created_at=now,
            last_seen_at=now,
            access_expires_at=now + timedelta(minutes=15),
            idle_expires_at=now + timedelta(minutes=30),
            absolute_expires_at=now + timedelta(days=7)
        )
        db.add(session)
        db.commit()

        ref_record = RefreshTokenRecord(
            user_session_id=session.id,
            token_hash="pg-ref-hash",
            token_family_id=uuid.uuid4(),
            status="active",
            issued_at=now,
            expires_at=now + timedelta(days=30)
        )
        db.add(ref_record)
        db.commit()

        results = []
        barrier = threading.Barrier(2)

        def thread_func(name):
            thread_db = SessionLocal()
            try:
                barrier.wait()
                # Simulate /refresh atomic transaction lock
                rec = thread_db.query(RefreshTokenRecord).filter(
                    RefreshTokenRecord.token_hash == "pg-ref-hash"
                ).with_for_update().first()
                
                if rec and rec.status == "active":
                    rec.status = "rotated"
                    thread_db.commit()
                    results.append((name, "success"))
                else:
                    results.append((name, "reused/failed"))
            except Exception as e:
                results.append((name, str(e)))
            finally:
                thread_db.close()

        t1 = threading.Thread(target=thread_func, args=("t1",))
        t2 = threading.Thread(target=thread_func, args=("t2",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # One should succeed, the other should fail to rotate
        statuses = [r[1] for r in results]
        assert "success" in statuses
        assert "reused/failed" in statuses

    finally:
        db.close()
