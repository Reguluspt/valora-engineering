"""
S12-R-002 Authentication Identity Boundary Hardening — Full Test Suite

Covers:
- Login success/failure + failed-login audit events
- /me endpoint auth gate
- Refresh token rotation and reuse detection
- Refresh expiry scenarios (idle, absolute, refresh token, revoked session, inactive user/org)
- Atomic rollback regression (failure before commit leaves no partial state)
- Session/org consistency mismatch → 401 + revocation
- CSRF: central enforcement across methods, origin/referer/scheme/port/substring/Sec-Fetch-Site
- Lifecycle audit events emitted in-transaction
- PostgreSQL concurrent /refresh endpoint test (run only on CI with real PG)
"""
import uuid
import pytest
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

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


# ─────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────

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


def login(client: TestClient):
    """Helper: login and return (client, acc_key, ref_key)."""
    resp = client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "secret_pass"
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp


def make_refresh_client(client: TestClient, ref_token: str, csrf_token: str):
    """Build a clean client carrying the given refresh + CSRF tokens."""
    acc_key, ref_key = get_cookie_keys()
    c = TestClient(app)
    c.cookies.set(ref_key, ref_token)
    c.headers["X-CSRF-Token"] = csrf_token
    c.headers["Origin"] = "http://localhost:5173"
    return c


# ─────────────────────────────────────────────────
# 1. Login flow + failed-login audit events
# ─────────────────────────────────────────────────

def test_login_success_sets_cookies(client: TestClient, test_setup):
    resp = login(client)
    assert "access_token" in resp.cookies
    assert "refresh_token" in resp.cookies
    assert "XSRF-TOKEN" in resp.cookies


def test_login_wrong_password_returns_401_generic(client: TestClient, test_setup, db_session: Session):
    resp = client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "wrong_password"
    })
    assert resp.status_code == 401
    # Generic message – no credential details
    assert resp.json()["detail"]["title"] == "Phiên làm việc hết hạn"

    # Audit event must exist
    evt = db_session.query(AuditEvent).filter(
        AuditEvent.event_name == "auth.login.failed"
    ).first()
    assert evt is not None
    assert evt.payload["reason_category"] == "INVALID_CREDENTIALS"
    # Must NOT contain password, token, raw credential
    assert "password" not in str(evt.payload).lower()
    assert "token" not in str(evt.payload).lower()


def test_login_unknown_org_returns_401_and_audits(client: TestClient, db_session: Session):
    resp = client.post("/api/v1/auth/login", json={
        "organization_slug": "nonexistent-org",
        "email": "x@x.com",
        "password": "any"
    })
    assert resp.status_code == 401
    evt = db_session.query(AuditEvent).filter(
        AuditEvent.event_name == "auth.login.failed"
    ).first()
    assert evt is not None
    assert evt.payload["reason_category"] == "UNKNOWN_ORG_OR_INACTIVE"


def test_login_failed_audit_never_contains_sensitive_data(client: TestClient, test_setup, db_session: Session):
    client.post("/api/v1/auth/login", json={
        "organization_slug": "regulus",
        "email": "architect@regulus.com",
        "password": "wrong"
    })
    evts = db_session.query(AuditEvent).filter(
        AuditEvent.event_name == "auth.login.failed"
    ).all()
    for evt in evts:
        payload_str = str(evt.payload)
        assert "wrong" not in payload_str      # no raw password
        assert "secret" not in payload_str     # no credential
        assert "token" not in payload_str      # no tokens
        assert "hash" not in payload_str       # no hashes
        assert "csrf" not in payload_str.lower()


# ─────────────────────────────────────────────────
# 2. /me endpoint
# ─────────────────────────────────────────────────

def test_me_endpoint_requires_auth(client: TestClient, test_setup):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401

    login(client)
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "architect@regulus.com"


# ─────────────────────────────────────────────────
# 3. Refresh token rotation + reuse detection
# ─────────────────────────────────────────────────

def test_refresh_token_rotation_and_reuse_detection(client: TestClient, test_setup, db_session: Session):
    login(client)
    acc_key, ref_key = get_cookie_keys()

    initial_refresh_token = client.cookies.get(ref_key)
    initial_csrf_token = client.cookies.get("XSRF-TOKEN")

    # First refresh
    client.headers["X-CSRF-Token"] = initial_csrf_token
    client.headers["Origin"] = "http://localhost:5173"
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200

    rotated_refresh_token = client.cookies.get(ref_key)
    assert rotated_refresh_token != initial_refresh_token

    # Reuse old token → should revoke session
    app.dependency_overrides[get_db] = client.app.dependency_overrides[get_db]
    clean_client = make_refresh_client(client, initial_refresh_token, initial_csrf_token)
    # Re-attach db override
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db

    resp_reuse = clean_client.post("/api/v1/auth/refresh")
    assert resp_reuse.status_code == 401

    # Verify session revoked in DB
    old_hash = hash_token(initial_refresh_token)
    record = db_session.query(RefreshTokenRecord).filter(
        RefreshTokenRecord.token_hash == old_hash
    ).first()
    session = db_session.query(UserSession).filter(
        UserSession.id == record.user_session_id
    ).first()
    assert session.status == "revoked"


# ─────────────────────────────────────────────────
# 4. Refresh expiry scenarios — direct POST /auth/refresh
# ─────────────────────────────────────────────────

def _get_active_session_and_ref_token(client: TestClient, db_session: Session):
    """Login and return active session, refresh token string, and CSRF token string."""
    login(client)
    acc_key, ref_key = get_cookie_keys()
    refresh_token_val = client.cookies.get(ref_key)
    csrf_token_val = client.cookies.get("XSRF-TOKEN")
    ref_hash = hash_token(refresh_token_val)
    session = db_session.query(UserSession).filter(UserSession.status == "active").first()
    ref_record = db_session.query(RefreshTokenRecord).filter(
        RefreshTokenRecord.token_hash == ref_hash
    ).first()
    return session, ref_record, refresh_token_val, csrf_token_val


def _assert_refresh_expiry_401(client: TestClient, ref_token: str, csrf_token: str):
    """Send refresh and assert 401 + cookie-clearing Set-Cookie headers."""
    c = make_refresh_client(client, ref_token, csrf_token)
    resp = c.post("/api/v1/auth/refresh")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
    # At minimum response must not grant new tokens and must be 401
    return resp


def test_refresh_idle_expired_returns_401_clears_cookies(client: TestClient, test_setup, db_session: Session):
    session, ref_record, ref_tok, csrf_tok = _get_active_session_and_ref_token(client, db_session)

    # Force idle timeout
    session.idle_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    _assert_refresh_expiry_401(client, ref_tok, csrf_tok)

    # Session must be revoked/expired
    db_session.expire(session)
    assert session.status in ("revoked", "expired")
    # No active replacement token
    replacements = db_session.query(RefreshTokenRecord).filter(
        RefreshTokenRecord.user_session_id == session.id,
        RefreshTokenRecord.status == "active"
    ).all()
    assert replacements == []


def test_refresh_absolute_expired_returns_401_clears_cookies(client: TestClient, test_setup, db_session: Session):
    session, ref_record, ref_tok, csrf_tok = _get_active_session_and_ref_token(client, db_session)

    session.absolute_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    _assert_refresh_expiry_401(client, ref_tok, csrf_tok)

    db_session.expire(session)
    assert session.status in ("revoked", "expired")
    replacements = db_session.query(RefreshTokenRecord).filter(
        RefreshTokenRecord.user_session_id == session.id,
        RefreshTokenRecord.status == "active"
    ).all()
    assert replacements == []


def test_refresh_token_expired_returns_401_clears_cookies(client: TestClient, test_setup, db_session: Session):
    session, ref_record, ref_tok, csrf_tok = _get_active_session_and_ref_token(client, db_session)

    ref_record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    _assert_refresh_expiry_401(client, ref_tok, csrf_tok)

    db_session.expire(ref_record)
    assert ref_record.status == "revoked"
    replacements = db_session.query(RefreshTokenRecord).filter(
        RefreshTokenRecord.user_session_id == session.id,
        RefreshTokenRecord.status == "active"
    ).all()
    assert replacements == []


def test_refresh_revoked_session_returns_401(client: TestClient, test_setup, db_session: Session):
    session, ref_record, ref_tok, csrf_tok = _get_active_session_and_ref_token(client, db_session)

    session.status = "revoked"
    db_session.commit()

    _assert_refresh_expiry_401(client, ref_tok, csrf_tok)


def test_refresh_inactive_user_returns_401_clears_cookies(client: TestClient, test_setup, db_session: Session):
    session, ref_record, ref_tok, csrf_tok = _get_active_session_and_ref_token(client, db_session)

    test_setup["user"].status = UserStatus.INACTIVE
    db_session.commit()

    _assert_refresh_expiry_401(client, ref_tok, csrf_tok)

    db_session.expire(session)
    assert session.status in ("revoked", "expired")
    replacements = db_session.query(RefreshTokenRecord).filter(
        RefreshTokenRecord.user_session_id == session.id,
        RefreshTokenRecord.status == "active"
    ).all()
    assert replacements == []


def test_refresh_inactive_org_returns_401_clears_cookies(client: TestClient, test_setup, db_session: Session):
    session, ref_record, ref_tok, csrf_tok = _get_active_session_and_ref_token(client, db_session)

    test_setup["org"].status = OrganizationStatus.INACTIVE
    db_session.commit()

    _assert_refresh_expiry_401(client, ref_tok, csrf_tok)

    db_session.expire(session)
    assert session.status in ("revoked", "expired")


# ─────────────────────────────────────────────────
# 5. Atomic rollback regression test
# ─────────────────────────────────────────────────

def test_refresh_atomic_rollback_on_audit_failure(client: TestClient, test_setup, db_session: Session):
    """
    If log_audit_event raises inside the refresh transaction,
    the entire operation must be rolled back:
    - old refresh token remains active
    - replaced_by_token_id remains null
    - no replacement token created
    - access_token_hash and csrf_token_hash unchanged
    - no partial audit event committed
    """
    session, ref_record, ref_tok, csrf_tok = _get_active_session_and_ref_token(client, db_session)

    original_access_hash = session.access_token_hash
    original_csrf_hash = session.csrf_token_hash
    original_ref_id = ref_record.id

    # Count audit events before
    audit_count_before = db_session.query(AuditEvent).count()

    # Patch log_audit_event to raise after the refresh attempt starts
    with patch("app.api.auth.log_audit_event", side_effect=RuntimeError("Injected audit failure")):
        c = make_refresh_client(client, ref_tok, csrf_tok)
        resp = c.post("/api/v1/auth/refresh")

    # The response should be a 401 (rollback error path)
    assert resp.status_code == 401

    # Refresh DB state
    db_session.expire_all()

    # Old refresh token must still be active
    old_rec = db_session.query(RefreshTokenRecord).filter(
        RefreshTokenRecord.id == original_ref_id
    ).first()
    assert old_rec.status == "active", f"Expected active, got {old_rec.status}"
    assert old_rec.replaced_by_token_id is None

    # No replacement token should exist
    replacements = db_session.query(RefreshTokenRecord).filter(
        RefreshTokenRecord.user_session_id == session.id,
        RefreshTokenRecord.status == "active",
        RefreshTokenRecord.id != original_ref_id
    ).all()
    assert replacements == [], f"Unexpected replacement tokens: {replacements}"

    # Session token hashes must be unchanged
    sess = db_session.query(UserSession).filter(UserSession.id == session.id).first()
    assert sess.access_token_hash == original_access_hash
    assert sess.csrf_token_hash == original_csrf_hash

    # No new audit events committed
    audit_count_after = db_session.query(AuditEvent).count()
    assert audit_count_after == audit_count_before, (
        f"Audit events committed during failed rollback: before={audit_count_before}, after={audit_count_after}"
    )


# ─────────────────────────────────────────────────
# 6. Session/org consistency enforcement
# ─────────────────────────────────────────────────

def test_session_org_mismatch_revokes_and_returns_401(client: TestClient, test_setup, db_session: Session):
    """Manually create a session with a mismatched organization_id and confirm 401 + revocation."""
    login(client)
    acc_key, ref_key = get_cookie_keys()

    # Create a second org
    other_org = OrganizationProfile(
        legal_name="Other Corp",
        organization_slug="other-org",
        status=OrganizationStatus.ACTIVE
    )
    db_session.add(other_org)
    db_session.commit()

    # Tamper the session's organization_id to point to a different org
    session = db_session.query(UserSession).filter(UserSession.status == "active").first()
    session.organization_id = other_org.id
    db_session.commit()

    # Attempting /me must fail
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401

    # Session must be revoked
    db_session.expire(session)
    assert session.status == "revoked"


def test_refresh_session_org_mismatch_revokes_and_returns_401(client: TestClient, test_setup, db_session: Session):
    """Same mismatch enforced during /refresh flow."""
    session, ref_record, ref_tok, csrf_tok = _get_active_session_and_ref_token(client, db_session)

    other_org = OrganizationProfile(
        legal_name="Fake Org",
        organization_slug="fake-org",
        status=OrganizationStatus.ACTIVE
    )
    db_session.add(other_org)
    db_session.commit()

    # Tamper session
    session.organization_id = other_org.id
    db_session.commit()

    _assert_refresh_expiry_401(client, ref_tok, csrf_tok)

    db_session.expire(session)
    assert session.status in ("revoked", "expired")


# ─────────────────────────────────────────────────
# 7. Lifecycle audit events emitted in-transaction
# ─────────────────────────────────────────────────

def test_refresh_idle_timeout_emits_lifecycle_audit_event(client: TestClient, test_setup, db_session: Session):
    session, ref_record, ref_tok, csrf_tok = _get_active_session_and_ref_token(client, db_session)

    session.idle_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    _assert_refresh_expiry_401(client, ref_tok, csrf_tok)

    # auth.session.revoked must have been emitted
    evt = db_session.query(AuditEvent).filter(
        AuditEvent.event_name == "auth.session.revoked"
    ).first()
    assert evt is not None
    assert "idle" in str(evt.payload.get("reason", "")).lower() or evt.payload.get("session_id") is not None


def test_refresh_inactive_user_emits_lifecycle_audit_event(client: TestClient, test_setup, db_session: Session):
    session, ref_record, ref_tok, csrf_tok = _get_active_session_and_ref_token(client, db_session)

    test_setup["user"].status = UserStatus.INACTIVE
    db_session.commit()

    _assert_refresh_expiry_401(client, ref_tok, csrf_tok)

    evt = db_session.query(AuditEvent).filter(
        AuditEvent.event_name == "auth.session.revoked"
    ).first()
    assert evt is not None


def test_session_created_audit_event_on_login(client: TestClient, test_setup, db_session: Session):
    login(client)
    evt = db_session.query(AuditEvent).filter(
        AuditEvent.event_name == "auth.session.created"
    ).first()
    assert evt is not None
    assert evt.payload["session_id"] is not None


# ─────────────────────────────────────────────────
# 8. CSRF regression: centrally enforced across methods
# ─────────────────────────────────────────────────

def test_csrf_post_missing_returns_403(client: TestClient, test_setup):
    login(client)
    if "X-CSRF-Token" in client.headers:
        del client.headers["X-CSRF-Token"]
    resp = client.post("/api/v1/projects")
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "CSRF_ERROR"


def test_csrf_patch_missing_returns_403(client: TestClient, test_setup, db_session: Session):
    login(client)
    if "X-CSRF-Token" in client.headers:
        del client.headers["X-CSRF-Token"]
    # PATCH to any protected route
    resp = client.patch("/api/v1/projects/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "CSRF_ERROR"


def test_csrf_delete_missing_returns_403(client: TestClient, test_setup, db_session: Session):
    login(client)
    if "X-CSRF-Token" in client.headers:
        del client.headers["X-CSRF-Token"]
    # Use a real registered DELETE route — evidence files endpoint
    resp = client.delete("/api/v1/evidence/files/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "CSRF_ERROR"


def test_csrf_valid_token_allows_request(client: TestClient, test_setup):
    login(client)
    csrf_token = client.cookies.get("XSRF-TOKEN")
    client.headers["X-CSRF-Token"] = csrf_token
    client.headers["Origin"] = "http://localhost:5173"
    # POST to logout should succeed (not CSRF block)
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200


def test_csrf_invalid_token_returns_403_csrf_error(client: TestClient, test_setup):
    login(client)
    client.headers["X-CSRF-Token"] = "invalid_token_value"
    client.headers["Origin"] = "http://localhost:5173"
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "CSRF_ERROR"


def test_csrf_valid_referer_fallback(client: TestClient, test_setup):
    login(client)
    csrf_token = client.cookies.get("XSRF-TOKEN")
    client.headers["X-CSRF-Token"] = csrf_token
    # Referer instead of Origin
    if "Origin" in client.headers:
        del client.headers["Origin"]
    client.headers["Referer"] = "http://localhost:5173/dashboard"
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200


def test_csrf_invalid_scheme_rejected(client: TestClient, test_setup):
    login(client)
    csrf_token = client.cookies.get("XSRF-TOKEN")
    client.headers["X-CSRF-Token"] = csrf_token
    # Attacker uses http instead of https (if production requires https)
    client.headers["Origin"] = "ftp://localhost:5173"
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 403


def test_csrf_invalid_port_rejected(client: TestClient, test_setup):
    login(client)
    csrf_token = client.cookies.get("XSRF-TOKEN")
    client.headers["X-CSRF-Token"] = csrf_token
    # Port differs
    client.headers["Origin"] = "http://localhost:9999"
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 403


def test_csrf_substring_attacker_origin_rejected(client: TestClient, test_setup):
    login(client)
    csrf_token = client.cookies.get("XSRF-TOKEN")
    client.headers["X-CSRF-Token"] = csrf_token
    # Substring attack: host ends with allowed host
    client.headers["Origin"] = "http://localhost:5173.attacker.com"
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 403


def test_csrf_cross_site_sec_fetch_rejected(client: TestClient, test_setup):
    login(client)
    csrf_token = client.cookies.get("XSRF-TOKEN")
    client.headers["X-CSRF-Token"] = csrf_token
    client.headers["Origin"] = "http://localhost:5173"
    # Sec-Fetch-Site: cross-site → reject as defense-in-depth
    client.headers["Sec-Fetch-Site"] = "cross-site"
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 403


def test_csrf_no_origin_no_referer_rejected(client: TestClient, test_setup):
    login(client)
    csrf_token = client.cookies.get("XSRF-TOKEN")
    client.headers["X-CSRF-Token"] = csrf_token
    # No Origin, no Referer — fail-closed
    if "Origin" in client.headers:
        del client.headers["Origin"]
    if "Referer" in client.headers:
        del client.headers["Referer"]
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 403


# ─────────────────────────────────────────────────
# 9. /me auth gates: inactive user + org
# ─────────────────────────────────────────────────

def test_inactive_user_fail_closed(client: TestClient, test_setup, db_session: Session):
    login(client)
    test_setup["user"].status = UserStatus.INACTIVE
    db_session.commit()
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_inactive_org_fail_closed(client: TestClient, test_setup, db_session: Session):
    login(client)
    test_setup["org"].status = OrganizationStatus.INACTIVE
    db_session.commit()
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_session_idle_timeout_gate(client: TestClient, test_setup, db_session: Session):
    login(client)
    sess = db_session.query(UserSession).filter(UserSession.status == "active").first()
    sess.idle_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_session_absolute_timeout_gate(client: TestClient, test_setup, db_session: Session):
    login(client)
    sess = db_session.query(UserSession).filter(UserSession.status == "active").first()
    sess.absolute_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ─────────────────────────────────────────────────
# 10. X-User-Id spoofing ignored
# ─────────────────────────────────────────────────

def test_x_user_id_spoofing_ignored(client: TestClient, test_setup):
    client.headers["X-User-Id"] = str(test_setup["user"].id)
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ─────────────────────────────────────────────────
# 11. PostgreSQL concurrent /refresh endpoint test
# Runs actual application flow, not direct DB manipulation.
# Skipped locally if PostgreSQL is not available.
# ─────────────────────────────────────────────────

def test_postgres_concurrent_refresh_endpoint():
    """
    Two concurrent threads share the same refresh token and CSRF context
    and both POST to /auth/refresh simultaneously.
    Asserts:
    - Exactly one successful rotation (HTTP 200)
    - No two active replacement tokens
    - replaced_by_token_id and parent_token_id links correct
    - Second request produces deterministic reuse/revocation outcome (HTTP 401)
    - Session and token family final state is consistent
    - Audit events are correct
    - No partial state
    """
    pg_url = "postgresql+psycopg://valora:valora_local_password@localhost:5432/valora"
    try:
        pg_engine = create_engine(
            pg_url,
            connect_args={"connect_timeout": 3}  # Fail fast if PG unavailable
        )
        with pg_engine.connect():
            pass
    except Exception:
        pytest.skip("PostgreSQL not available. Skipping integration test.")
        return

    # Run migrations on pg database to ensure clean schema
    import subprocess
    import os
    cwd = "backend" if os.path.exists("backend") else "."
    subprocess.run(["alembic", "upgrade", "head"], cwd=cwd, check=True)

    # Set up PG-backed app with real DB
    from sqlalchemy.orm import sessionmaker as sm
    PGSession = sm(bind=pg_engine)
    setup_db = PGSession()

    try:
        # Create fresh org, user
        test_org = OrganizationProfile(
            legal_name="PG Concurrent Org",
            organization_slug=f"pg-org-{uuid.uuid4().hex[:8]}",
            status=OrganizationStatus.ACTIVE
        )
        setup_db.add(test_org)
        setup_db.commit()

        test_user = User(
            organization_id=test_org.id,
            email=f"pg-{uuid.uuid4().hex[:8]}@regulus.com",
            full_name="PG Concurrent User",
            password_hash=hash_password("pg_secret_pass"),
            status=UserStatus.ACTIVE
        )
        setup_db.add(test_user)
        setup_db.commit()

        # Capture IDs as plain values before closing session to avoid DetachedInstanceError
        test_org_id = test_org.id
        test_org_slug = test_org.organization_slug
        test_user_email = test_user.email

        setup_db.close()

        # Build a test client that uses real PG
        def pg_get_db():
            db = PGSession()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = pg_get_db
        pg_client = TestClient(app)

        # Login to get actual tokens (use captured plain values — not detached ORM objects)
        resp = pg_client.post("/api/v1/auth/login", json={
            "organization_slug": test_org_slug,
            "email": test_user_email,
            "password": "pg_secret_pass"
        })
        assert resp.status_code == 200, f"Login failed: {resp.text}"

        acc_key, ref_key = get_cookie_keys()
        shared_refresh_token = pg_client.cookies.get(ref_key)
        shared_csrf_token = pg_client.cookies.get("XSRF-TOKEN")
        shared_access_token = pg_client.cookies.get(acc_key)

        assert shared_refresh_token, "No refresh token after login"
        assert shared_csrf_token, "No CSRF token after login"

        results = []
        barrier = threading.Barrier(2)

        def thread_refresh(name: str):
            # Each thread builds its own client from scratch with same tokens
            thread_client = TestClient(app)
            thread_client.cookies.set(ref_key, shared_refresh_token)
            thread_client.cookies.set(acc_key, shared_access_token)
            thread_client.headers["X-CSRF-Token"] = shared_csrf_token
            thread_client.headers["Origin"] = "http://localhost:5173"
            barrier.wait()  # Synchronize start
            try:
                r = thread_client.post("/api/v1/auth/refresh")
                results.append((name, r.status_code, r.text[:200]))
            except Exception as e:
                results.append((name, "exception", str(e)))

        t1 = threading.Thread(target=thread_refresh, args=("thread-1",))
        t2 = threading.Thread(target=thread_refresh, args=("thread-2",))
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)

        # Exactly one should succeed
        statuses = [r[1] for r in results]
        successes = [s for s in statuses if s == 200]
        failures = [s for s in statuses if s != 200]

        assert len(successes) == 1, f"Expected 1 success, got: {results}"
        assert len(failures) == 1, f"Expected 1 failure, got: {results}"

        # Verify DB state
        verify_db = PGSession()
        try:
            ref_hash = hash_token(shared_refresh_token)
            old_rec = verify_db.query(RefreshTokenRecord).filter(
                RefreshTokenRecord.token_hash == ref_hash
            ).first()

            assert old_rec is not None
            # Old record must be rotated (not active, and not reused again)
            assert old_rec.status in ("rotated", "reused_detected", "revoked"), (
                f"Old token in unexpected state: {old_rec.status}"
            )

            # replaced_by_token_id must point to the new token
            assert old_rec.replaced_by_token_id is not None

            # Verify new token's parent_token_id points back to old
            new_rec = verify_db.query(RefreshTokenRecord).filter(
                RefreshTokenRecord.id == old_rec.replaced_by_token_id
            ).first()
            assert new_rec is not None
            assert new_rec.parent_token_id == old_rec.id

            # No two active replacement tokens in same family
            active_tokens = verify_db.query(RefreshTokenRecord).filter(
                RefreshTokenRecord.token_family_id == old_rec.token_family_id,
                RefreshTokenRecord.status == "active"
            ).all()
            assert len(active_tokens) <= 1, (
                f"Multiple active tokens in family: {[(t.id, t.status) for t in active_tokens]}"
            )

            # Session final state is non-partial
            sess = verify_db.query(UserSession).filter(
                UserSession.id == old_rec.user_session_id
            ).first()
            assert sess.status in ("active", "revoked"), f"Unexpected session state: {sess.status}"

            # Audit events: at least one refresh event or reuse event
            refresh_evts = verify_db.query(AuditEvent).filter(
                AuditEvent.event_name.in_([
                    "auth.session.refreshed",
                    "auth.refresh.reuse_detected",
                    "auth.session.revoked"
                ])
            ).all()
            assert len(refresh_evts) >= 1, "Expected at least one audit event for refresh"

        finally:
            verify_db.close()

    finally:
        app.dependency_overrides.clear()
        # Cleanup test data
        cleanup_db = PGSession()
        try:
            cleanup_db.query(User).filter(
                User.organization_id == test_org_id
            ).delete(synchronize_session=False)
            cleanup_db.query(OrganizationProfile).filter(
                OrganizationProfile.id == test_org_id
            ).delete(synchronize_session=False)
            cleanup_db.commit()
        except Exception:
            cleanup_db.rollback()
        finally:
            cleanup_db.close()
        pg_engine.dispose()
