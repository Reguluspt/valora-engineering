import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, User, UserStatus, Role, UserRole, Project,
    ProjectWorkflowStatus, Customer, WorkbenchNotification, WorkbenchNotificationType
)

@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()


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
def setup_rbac_users(db_session: Session):
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    role_admin = Role(
        code="admin",
        display_name="Admin",
        permissions=[
            "workbench:open",
            "workbench:read",
            "workbench:edit",
            "workbench:undo_redo"
        ]
    )
    role_viewer = Role(
        code="viewer",
        display_name="Viewer",
        permissions=[
            "workbench:read"
        ]
    )
    db_session.add_all([role_admin, role_viewer])
    db_session.commit()

    user_admin = User(organization_id=org.id, email="admin@test.com", full_name="Admin User", status=UserStatus.ACTIVE)
    user_viewer = User(organization_id=org.id, email="viewer@test.com", full_name="Viewer User", status=UserStatus.ACTIVE)
    db_session.add_all([user_admin, user_viewer])
    db_session.commit()

    db_session.add(UserRole(user_id=user_admin.id, role_id=role_admin.id, is_active=True))
    db_session.add(UserRole(user_id=user_viewer.id, role_id=role_viewer.id, is_active=True))
    db_session.commit()

    customer = Customer(organization_id=org.id, legal_name="Cust 1", status="active", created_by=user_admin.id)
    db_session.add(customer)
    db_session.commit()

    proj = Project(
        organization_id=org.id,
        code="PROJ-2026",
        name="Project 2026",
        status=ProjectWorkflowStatus.DRAFT,
        customer_id=customer.id,
        created_by=user_admin.id
    )
    db_session.add(proj)
    db_session.commit()

    return {
        "admin_id": str(user_admin.id),
        "viewer_id": str(user_viewer.id),
        "org_id": org.id,
        "project_id": str(proj.id)
    }


def test_openapi_and_health(client: TestClient) -> None:
    # 1. Health check passes
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    # 2. OpenAPI schemas load
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    openapi = resp.json()
    assert "paths" in openapi
    assert "/api/v1/workbench/sessions" in openapi["paths"]


def test_workbench_sessions_endpoints(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    # 1. POST /api/v1/workbench/sessions (Create session with RBAC)
    resp = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_rbac_users["project_id"]},
        headers=headers_admin
    )
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    # Deny by default check
    resp_unauth = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_rbac_users["project_id"]}
    )
    assert resp_unauth.status_code == 401

    # Viewer mutation block
    resp_view = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_rbac_users["project_id"]},
        headers=headers_viewer
    )
    assert resp_view.status_code == 403

    # 2. GET /api/v1/workbench/sessions/{session_id}
    resp = client.get(f"/api/v1/workbench/sessions/{session_id}", headers=headers_admin)
    assert resp.status_code == 200

    # 3. POST /api/v1/workbench/sessions/{session_id}/heartbeat
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/heartbeat",
        json={"expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["row_version"] == 2

    # Heartbeat row version mismatch check (raises 409)
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/heartbeat",
        json={"expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 409


def test_layouts_and_grid_views(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    # Create session
    resp = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_rbac_users["project_id"]},
        headers=headers_admin
    )
    session_id = resp.json()["id"]

    # 1. POST /api/v1/workbench/sessions/{session_id}/layout (Save Layout)
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/layout",
        json={
            "layout_name": "Standard Layout",
            "layout_payload": {"panels": ["main", "price"]}
        },
        headers=headers_admin
    )
    assert resp.status_code == 200

    # 2. POST /api/v1/workbench/sessions/{session_id}/grid-view (Save View)
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/grid-view",
        json={
            "view_name": "Transformer grid",
            "columns": {"id": True, "title": True}
        },
        headers=headers_admin
    )
    assert resp.status_code == 200

    # 3. GET /api/v1/workbench/sessions/{session_id}/grid-view
    resp = client.get(f"/api/v1/workbench/sessions/{session_id}/grid-view", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_selections_and_drafts(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    from app.modules.project_master_data.models import ProjectAssetLine
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    # Seed an asset line for validation
    line = ProjectAssetLine(
        id=uuid.uuid4(),
        project_id=uuid.UUID(setup_rbac_users["project_id"]),
        asset_name="Test Asset",
        quantity=1.0
    )
    db_session.add(line)
    db_session.commit()
    line_id = str(line.id)

    # Create session
    resp = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_rbac_users["project_id"]},
        headers=headers_admin
    )
    session_id = resp.json()["id"]

    # 1. POST /api/v1/workbench/sessions/{session_id}/selection (Save selection)
    target_ids = [line_id]
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/selection",
        json={
            "selected_target_type": "project_asset_line",
            "selected_target_ids": target_ids
        },
        headers=headers_admin
    )
    assert resp.status_code == 200

    # 2. GET /api/v1/workbench/sessions/{session_id}/selection
    resp = client.get(f"/api/v1/workbench/sessions/{session_id}/selection", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 3. POST /api/v1/workbench/sessions/{session_id}/inline-edit (Save inline edit draft)
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/inline-edit",
        json={
            "target_type": "project_asset_line",
            "target_id": line_id,
            "field_key": "appraised_unit_price",
            "draft_value": {"val": 150.0},
            "base_value": {"val": 100.0},
            "base_row_version": 1
        },
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"

    # 4. GET /api/v1/workbench/sessions/{session_id}/inline-edits
    resp = client.get(f"/api/v1/workbench/sessions/{session_id}/inline-edits", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_autosave_checkpoints_and_stack(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    from app.modules.project_master_data.models import ProjectAssetLine
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    # Seed an asset line for validation
    line = ProjectAssetLine(
        id=uuid.uuid4(),
        project_id=uuid.UUID(setup_rbac_users["project_id"]),
        asset_name="Test Asset 2",
        quantity=1.0
    )
    db_session.add(line)
    db_session.commit()
    line_id = str(line.id)

    # Create session
    resp = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_rbac_users["project_id"]},
        headers=headers_admin
    )
    session_id = resp.json()["id"]

    # 1. POST /api/v1/workbench/sessions/{session_id}/checkpoint (Create checkpoint)
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/checkpoint",
        json={"checkpoint_payload": {"drafts": [{"field": "appraised_unit_price"}]}},
        headers=headers_admin
    )
    assert resp.status_code == 200

    # 2. Add an inline edit to populate the undo/redo stack
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/inline-edit",
        json={
            "target_type": "project_asset_line",
            "target_id": line_id,
            "field_key": "appraised_unit_price",
            "draft_value": {"val": 150.0},
            "base_value": {"val": 100.0},
            "base_row_version": 1
        },
        headers=headers_admin
    )
    assert resp.status_code == 200

    # 3. POST /api/v1/workbench/sessions/{session_id}/undo
    resp = client.post(f"/api/v1/workbench/sessions/{session_id}/undo", headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["is_undone"] is True

    # 4. POST /api/v1/workbench/sessions/{session_id}/redo
    resp = client.post(f"/api/v1/workbench/sessions/{session_id}/redo", headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["is_undone"] is False


def test_panel_states_and_notifications(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    # Create session
    resp = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_rbac_users["project_id"]},
        headers=headers_admin
    )
    session_id = resp.json()["id"]

    # 1. POST /api/v1/workbench/sessions/{session_id}/panel-state (Save panel state)
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/panel-state",
        json={
            "panel_type": "lineage_viewer",
            "is_expanded": True,
            "width": 350
        },
        headers=headers_admin
    )
    assert resp.status_code == 200

    # 2. GET /api/v1/workbench/sessions/{session_id}/panel-state
    resp = client.get(f"/api/v1/workbench/sessions/{session_id}/panel-state", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 3. Seed notification
    notif = WorkbenchNotification(
        user_id=uuid.UUID(setup_rbac_users["admin_id"]),
        session_id=uuid.UUID(session_id),
        notification_type=WorkbenchNotificationType.INFO,
        message="Background pricing conflict review completed"
    )
    db_session.add(notif)
    db_session.commit()

    # 4. GET /api/v1/workbench/sessions/{session_id}/notifications
    resp = client.get(f"/api/v1/workbench/sessions/{session_id}/notifications", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def login_user_in_test(client: TestClient, db_session: Session, user_id: uuid.UUID, org_id: uuid.UUID):
    from app.api.auth import get_cookie_keys, hash_token
    import secrets
    from app.modules.project_master_data.models import UserSession
    from datetime import datetime, timedelta, timezone

    token = secrets.token_hex(32)
    token_hash = hash_token(token)

    csrf_token = secrets.token_hex(32)
    csrf_hash = hash_token(csrf_token)

    session = UserSession(
        user_id=user_id,
        organization_id=org_id,
        access_token_hash=token_hash,
        csrf_token_hash=csrf_hash,
        status="active",
        access_expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        idle_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        absolute_expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    db_session.add(session)
    db_session.commit()

    acc_key, _ = get_cookie_keys()
    client.cookies.set(acc_key, token)
    client.cookies.set("XSRF-TOKEN", csrf_token)
    client.headers["X-CSRF-Token"] = csrf_token
    client.headers["Origin"] = "http://localhost:5173"
    return {"token": token, "csrf_token": csrf_token}


def test_workbench_tenant_and_user_isolation(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    from app.modules.project_master_data.models import (
        OrganizationProfile, OrganizationStatus, User, UserStatus, Role, UserRole, Project,
        ProjectWorkflowStatus, Customer
    )
    from app.api.auth import get_cookie_keys

    # 1. Tenant Isolation: Create Org B, User B, Project B
    org_b = OrganizationProfile(
        id=uuid.uuid4(),
        legal_name="Org B",
        organization_slug="org_b",
        status=OrganizationStatus.ACTIVE
    )
    db_session.add(org_b)
    db_session.commit()

    user_b = User(
        id=uuid.uuid4(),
        email="user_b@valora.com",
        full_name="User B",
        password_hash="...",
        status=UserStatus.ACTIVE,
        organization_id=org_b.id
    )
    db_session.add(user_b)
    db_session.commit()

    # Add role to User B so they have workbench open/edit permissions
    role_edit = db_session.query(Role).filter(Role.code == "admin").first()

    ur_b = UserRole(user_id=user_b.id, role_id=role_edit.id, is_active=True)
    db_session.add(ur_b)

    customer_b = Customer(
        id=uuid.uuid4(),
        organization_id=org_b.id,
        legal_name="Customer B",
        tax_code="0987654321",
        status="active",
        created_by=user_b.id
    )
    db_session.add(customer_b)
    db_session.commit()

    project_b = Project(
        id=uuid.uuid4(),
        organization_id=org_b.id,
        customer_id=customer_b.id,
        code="PROJ-B",
        name="Project B",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=user_b.id
    )
    db_session.add(project_b)
    db_session.commit()

    # User A tries to create session in Project B -> 404 (safe 404)
    auth_a = login_user_in_test(client, db_session, uuid.UUID(setup_rbac_users["admin_id"]), setup_rbac_users["org_id"])
    resp = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": str(project_b.id)}
    )
    assert resp.status_code == 404

    # User B creates session in Project B successfully
    auth_b = login_user_in_test(client, db_session, user_b.id, org_b.id)
    resp = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": str(project_b.id)}
    )
    assert resp.status_code == 201
    session_b_id = resp.json()["id"]

    # User A tries to get/heartbeat/close User B's session -> 404
    acc_key, _ = get_cookie_keys()
    client.cookies.set(acc_key, auth_a["token"])
    client.cookies.set("XSRF-TOKEN", auth_a["csrf_token"])
    client.headers["X-CSRF-Token"] = auth_a["csrf_token"]
    resp = client.get(f"/api/v1/workbench/sessions/{session_b_id}")
    assert resp.status_code == 404

    resp = client.post(f"/api/v1/workbench/sessions/{session_b_id}/heartbeat", json={"expected_row_version": 1})
    assert resp.status_code == 404

    resp = client.post(f"/api/v1/workbench/sessions/{session_b_id}/close")
    assert resp.status_code == 404

    # User B (different tenant) tries to close User A's session -> 404
    client.cookies.set(acc_key, auth_a["token"])
    client.cookies.set("XSRF-TOKEN", auth_a["csrf_token"])
    client.headers["X-CSRF-Token"] = auth_a["csrf_token"]
    resp = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_rbac_users["project_id"]}
    )
    session_a_id = resp.json()["id"]

    client.cookies.set(acc_key, auth_b["token"])
    client.cookies.set("XSRF-TOKEN", auth_b["csrf_token"])
    client.headers["X-CSRF-Token"] = auth_b["csrf_token"]
    resp = client.post(f"/api/v1/workbench/sessions/{session_a_id}/close")
    assert resp.status_code == 404


def test_active_session_policy_resume(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    login_user_in_test(client, db_session, uuid.UUID(setup_rbac_users["admin_id"]), setup_rbac_users["org_id"])

    # Create first session
    resp1 = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_rbac_users["project_id"]}
    )
    assert resp1.status_code == 201
    sid1 = resp1.json()["id"]

    # Create session again for same project -> returns same session (resumes)
    resp2 = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_rbac_users["project_id"]}
    )
    assert resp2.status_code == 201
    assert resp2.json()["id"] == sid1

    # Close session
    resp_close = client.post(f"/api/v1/workbench/sessions/{sid1}/close")
    assert resp_close.status_code == 200
    assert resp_close.json()["status"] == "closed"

    # Mutating action on closed session fails with 404
    resp_hb = client.post(f"/api/v1/workbench/sessions/{sid1}/heartbeat", json={"expected_row_version": 1})
    assert resp_hb.status_code == 404

    # Create session again -> gets a NEW active session
    resp3 = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_rbac_users["project_id"]}
    )
    assert resp3.status_code == 201
    assert resp3.json()["id"] != sid1


def test_explicit_target_validation(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    from app.modules.project_master_data.models import ProjectAssetLine, Customer, Project, ProjectWorkflowStatus
    login_user_in_test(client, db_session, uuid.UUID(setup_rbac_users["admin_id"]), setup_rbac_users["org_id"])

    # Create session
    resp = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_rbac_users["project_id"]}
    )
    sid = resp.json()["id"]

    # Create asset line in project A
    line_a = ProjectAssetLine(
        id=uuid.uuid4(),
        project_id=uuid.UUID(setup_rbac_users["project_id"]),
        asset_name="Asset A",
        quantity=1.0
    )
    db_session.add(line_a)
    db_session.commit()

    # Create asset line not in project A (different project/tenant)
    cust = db_session.query(Customer).first()
    proj_other = Project(
        id=uuid.uuid4(),
        organization_id=setup_rbac_users["org_id"],
        customer_id=cust.id,
        code="PROJ-OTHER",
        name="Project Other",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add(proj_other)
    db_session.commit()

    line_other = ProjectAssetLine(
        id=uuid.uuid4(),
        project_id=proj_other.id,
        asset_name="Asset Other",
        quantity=1.0
    )
    db_session.add(line_other)
    db_session.commit()

    # Inline edit with correct target -> 200
    resp_edit = client.post(
        f"/api/v1/workbench/sessions/{sid}/inline-edit",
        json={
            "target_type": "project_asset_line",
            "target_id": str(line_a.id),
            "field_key": "appraised_unit_price",
            "draft_value": {"val": 100.0},
            "base_value": {"val": 90.0},
            "base_row_version": 1
        }
    )
    assert resp_edit.status_code == 200

    # Inline edit with invalid target ID -> 404
    resp_edit_invalid = client.post(
        f"/api/v1/workbench/sessions/{sid}/inline-edit",
        json={
            "target_type": "project_asset_line",
            "target_id": str(line_other.id),
            "field_key": "appraised_unit_price",
            "draft_value": {"val": 100.0},
            "base_value": {"val": 90.0},
            "base_row_version": 1
        }
    )
    assert resp_edit_invalid.status_code == 404
