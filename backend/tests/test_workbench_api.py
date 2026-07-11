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
    resp = client.get(f"/api/v1/workbench/sessions/{session_id}", headers=headers_viewer)
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
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    # Create session
    resp = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_rbac_users["project_id"]},
        headers=headers_admin
    )
    session_id = resp.json()["id"]

    # 1. POST /api/v1/workbench/sessions/{session_id}/selection (Save selection)
    target_ids = [str(uuid.uuid4())]
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
    resp = client.get(f"/api/v1/workbench/sessions/{session_id}/selection", headers=headers_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 3. POST /api/v1/workbench/sessions/{session_id}/inline-edit (Save inline edit draft)
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/inline-edit",
        json={
            "target_type": "project_asset_line",
            "target_id": str(uuid.uuid4()),
            "field_key": "standard_name",
            "draft_value": {"val": "New Transformer Name"}
        },
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"

    # 4. GET /api/v1/workbench/sessions/{session_id}/inline-edits
    resp = client.get(f"/api/v1/workbench/sessions/{session_id}/inline-edits", headers=headers_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_autosave_checkpoints_and_stack(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

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
        json={"checkpoint_payload": {"drafts": [{"field": "standard_name"}]}},
        headers=headers_admin
    )
    assert resp.status_code == 200

    # 2. Add an inline edit to populate the undo/redo stack
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/inline-edit",
        json={
            "target_type": "project_asset_line",
            "target_id": str(uuid.uuid4()),
            "field_key": "standard_name",
            "draft_value": {"val": "New Transformer Name"}
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


# ChangeRequest is now in scope
