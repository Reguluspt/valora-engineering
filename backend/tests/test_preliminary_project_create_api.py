import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.auth import get_cookie_keys
from app.core.rbac import get_current_user
from app.db.session import SessionLocal
from app.main import app
from app.modules.project_master_data.models import Role, User, UserRole, UserSession
from tests.test_preliminary_project_create import command
from tests.test_preliminary_project_create_postgresql import principal as principal_fixture, facts

principal = principal_fixture


@pytest.fixture
def client(principal):
    override = app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as client:
        client.cookies.set(get_cookie_keys()[0], str(principal.session_id))
        client.headers.update(
            {"Origin": "http://localhost:5173", "X-CSRF-Token": "issue217-synthetic-csrf"}
        )
        yield client
    if override is not None:
        app.dependency_overrides[get_current_user] = override


def test_a01_api_replay_get_and_legacy_resolver(client, principal):
    body = command().model_dump()
    response = client.post("/api/v1/projects/preliminary-create", json=body)
    assert response.status_code == 201, response.text
    result = response.json()
    assert client.post("/api/v1/projects/preliminary-create", json=body).json() == result
    assert (
        client.get(f"/api/v1/projects/preliminary-create-requests/{body['request_id']}").json()
        == result
    )
    legacy = client.post("/api/v1/projects", json={"code": "Legacy-217", "name": "Legacy"})
    assert legacy.status_code == 201, legacy.text
    for ref in (result["project"]["id"], result["project"]["code"], "Legacy-217", "legacy-217"):
        resolved = client.get("/api/v1/projects/resolve", params={"ref": ref})
        assert resolved.status_code == 200, resolved.text
    assert facts(principal) == (2, 2, 1)


@pytest.mark.parametrize(
    "body",
    [
        '{"name":"A","name":"B"}',
        '{"request_id":"x","request_id":"y","name":"A"}',
        "[]",
        "null",
        "{",
        '{"name":NaN}',
    ],
)
def test_a02_route_local_json_rejection(client, principal, body):
    response = client.post("/api/v1/projects/preliminary-create", content=body)
    assert response.status_code == 422 and isinstance(response.json()["detail"], list)
    assert facts(principal) == (0, 0, 0)


@pytest.mark.parametrize(
    "change",
    [{"name": 1}, {"name": "a\ud800"}, {"code": "manual"}, {"request_id": str(uuid.uuid1())}],
)
def test_a02_invalid_schema_422(client, principal, change):
    response = client.post(
        "/api/v1/projects/preliminary-create",
        content=json.dumps({**command().model_dump(), **change}),
    )
    assert response.status_code == 422, response.text
    assert facts(principal) == (0, 0, 0)


@pytest.mark.parametrize(
    "headers,status",
    [
        ({"X-CSRF-Token": "wrong"}, 403),
        ({"Origin": "http://localhost:5174"}, 403),
        ({"Origin": "https://foreign.invalid", "Referer": "http://localhost:5173/"}, 403),
        ({"Sec-Fetch-Site": "cross-site"}, 403),
        ({"Origin": ""}, 403),
        ({"Origin": "", "Referer": "http://localhost:5173/"}, 201),
        ({"Sec-Fetch-Site": "none"}, 201),
    ],
)
def test_a20_csrf_origin_metadata_matrix(client, principal, headers, status):
    response = client.post(
        "/api/v1/projects/preliminary-create", json=command().model_dump(), headers=headers
    )
    assert response.status_code == status, response.text
    if status == 403:
        assert response.json()["detail"]["code"] == "CSRF_ERROR" and facts(principal) == (0, 0, 0)


@pytest.mark.parametrize(
    "condition",
    [
        "expired",
        "idle_expired",
        "absolute_expired",
        "revoked",
        "inactive",
        "inactive_org",
        "tenant_mismatch",
        "viewer",
        "no_roles",
    ],
)
def test_a20_session_permission_matrix(client, principal, condition):
    with SessionLocal() as db:
        session = db.get(UserSession, principal.session_id)
        user = db.get(User, principal.actor_user_id)
        if condition == "expired":
            session.access_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        elif condition in ("idle_expired", "absolute_expired"):
            setattr(
                session,
                "idle_expires_at" if condition == "idle_expired" else "absolute_expires_at",
                datetime.now(timezone.utc) - timedelta(seconds=1),
            )
        elif condition == "inactive_org":
            from app.modules.project_master_data.models import OrganizationProfile

            db.get(OrganizationProfile, principal.organization_id).status = "inactive"
        elif condition == "revoked":
            session.status = "revoked"
        elif condition == "inactive":
            user.status = "inactive"
        elif condition == "tenant_mismatch":
            pass
        else:
            role = db.query(Role).join(UserRole).filter(UserRole.user_id == user.id).one()
            role.permissions = ["project:read"] if condition == "viewer" else []
        if condition == "tenant_mismatch":
            # Use another persisted org, preserving FK validity.
            from app.modules.project_master_data.models import OrganizationProfile

            org = OrganizationProfile(
                legal_name="Other synthetic", organization_slug=f"i217-{uuid.uuid4().hex}"
            )
            db.add(org)
            db.flush()
            session.organization_id = org.id
        db.commit()
    response = client.post("/api/v1/projects/preliminary-create", json=command().model_dump())
    assert response.status_code == (
        403 if condition in ("viewer", "no_roles") else 401
    ), response.text
    assert facts(principal)[0::2] == (0, 0)


def test_a10_a20_foreign_actor_nonce_is_independent(client, principal):
    body = command().model_dump()
    result = client.post("/api/v1/projects/preliminary-create", json=body).json()
    with SessionLocal() as db:
        user = User(
            organization_id=principal.organization_id,
            email="other@example.invalid",
            full_name="Other actor",
        )
        db.add(user)
        db.flush()
        role_id = (
            db.query(UserRole.role_id).filter(UserRole.user_id == principal.actor_user_id).scalar()
        )
        db.add(UserRole(user_id=user.id, role_id=role_id))
        session = db.get(UserSession, principal.session_id)
        session.user_id = user.id
        db.commit()
    foreign = client.get(f"/api/v1/projects/preliminary-create-requests/{body['request_id']}")
    assert foreign.status_code == 404 and result["project"]["id"] not in foreign.text
    own = client.post("/api/v1/projects/preliminary-create", json=body)
    assert own.status_code == 201 and own.json()["project"] != result["project"]
