import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.security import hash_password


from app.main import app
from app.db import Base, get_db
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, User, UserStatus, Role, UserRole, Project,
    ProjectWorkflowStatus, Customer, WorkbenchNotification, WorkbenchNotificationType,
    ProjectAssetLine, InlineEditDraft, InlineEditDraftStatus, WorkbenchSessionStatus,
    WorkbenchSession
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
            "workbench:undo_redo",
            "project:update"
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
    assert resp2.status_code == 200
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


def test_permission_revocation(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    from app.modules.project_master_data.models import UserRole, WorkbenchSession, UserActionLog, WorkbenchSelection, PanelState
    # 1. User creates session when having permission
    login_user_in_test(client, db_session, uuid.UUID(setup_rbac_users["admin_id"]), setup_rbac_users["org_id"])

    resp = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_rbac_users["project_id"]}
    )
    assert resp.status_code == 201
    sid = resp.json()["id"]

    db_session.expire_all()
    session_before = db_session.get(WorkbenchSession, uuid.UUID(sid))
    row_ver_before = session_before.row_version
    last_act_before = session_before.last_active_at

    # Record initial counts
    log_count_before = db_session.query(UserActionLog).count()
    sel_count_before = db_session.query(WorkbenchSelection).count()
    panel_count_before = db_session.query(PanelState).count()

    # 2. Revoke UserRole
    db_session.query(UserRole).filter(UserRole.user_id == uuid.UUID(setup_rbac_users["admin_id"])).delete()
    db_session.commit()

    # 3. Heartbeat and state mutation using the old session -> Response 403
    resp_hb = client.post(f"/api/v1/workbench/sessions/{sid}/heartbeat", json={"expected_row_version": row_ver_before})
    assert resp_hb.status_code == 403

    resp_sel = client.post(f"/api/v1/workbench/sessions/{sid}/selection", json={
        "selected_target_type": "project_asset_line",
        "selected_target_ids": []
    })
    assert resp_sel.status_code == 403

    resp_panel = client.post(f"/api/v1/workbench/sessions/{sid}/panel-state", json={
        "panel_type": "knowledge_panel",
        "is_expanded": True
    })
    assert resp_panel.status_code == 403

    # Assert no mutation
    db_session.expire_all()
    session_after = db_session.get(WorkbenchSession, uuid.UUID(sid))
    assert session_after.row_version == row_ver_before
    assert session_after.last_active_at == last_act_before

    assert db_session.query(UserActionLog).count() == log_count_before
    assert db_session.query(WorkbenchSelection).count() == sel_count_before
    assert db_session.query(PanelState).count() == panel_count_before


def test_postgres_concurrent_session_create():
    """
    Two concurrent threads attempt to create a session for the same project/user on Postgres.
    In CI (CI=true), TEST_DATABASE_URL must be configured or the test fails (not skips).
    Locally without Postgres, it skips with a clear reason.
    """
    import os
    pg_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    is_ci = os.getenv("CI") == "true"

    if not pg_url or not pg_url.startswith("postgres"):
        if is_ci:
            pytest.fail(
                "CI=true but TEST_DATABASE_URL is not configured with a PostgreSQL URL. "
                "Concurrent session test cannot be skipped in CI."
            )
        pytest.skip(
            "PostgreSQL not configured (TEST_DATABASE_URL/DATABASE_URL absent or not postgres). "
            "Skipping concurrent integration test — awaiting CI with PostgreSQL service."
        )
        return

    pg_engine = None
    setup_db = None
    try:
        pg_engine = create_engine(
            pg_url,
            connect_args={"connect_timeout": 3}
        )
        with pg_engine.connect() as conn:
            # Pre-check: verify the partial unique index exists (CI ran alembic upgrade head)
            from sqlalchemy import text
            result = conn.execute(text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename='workbench_sessions' "
                "AND indexname='uq_active_session_per_user_project'"
            )).fetchall()
            if not result:
                if is_ci:
                    pytest.fail(
                        "Index 'uq_active_session_per_user_project' not found on workbench_sessions. "
                        "Alembic migration must run before concurrent test in CI."
                    )
                pytest.skip(
                    "Index 'uq_active_session_per_user_project' not found — "
                    "run 'alembic upgrade head' first."
                )
                return
    except Exception as exc:
        if is_ci:
            pytest.fail(
                f"PostgreSQL not available at configured URL in CI: {exc}. "
                "Concurrent session test cannot be skipped in CI."
            )
        pytest.skip(
            f"PostgreSQL not available at configured URL ({exc}). "
            "Skipping concurrent integration test."
        )
        return

    from sqlalchemy.orm import sessionmaker as sm
    from app.modules.project_master_data.models import (
        OrganizationProfile, OrganizationStatus, User, UserStatus, Role, UserRole, Project,
        ProjectWorkflowStatus, Customer, AuditEvent, WorkbenchSession, WorkbenchSessionStatus, UserActionLog
    )
    import threading

    PGSession = sm(bind=pg_engine)
    setup_db = PGSession()

    try:
        # Create fresh org, user, project
        test_org = OrganizationProfile(
            legal_name="PG Workbench Org",
            organization_slug=f"pg-wb-org-{uuid.uuid4().hex[:8]}",
            status=OrganizationStatus.ACTIVE
        )
        setup_db.add(test_org)
        setup_db.commit()

        test_user = User(
            organization_id=test_org.id,
            email=f"pg-wb-{uuid.uuid4().hex[:8]}@regulus.com",
            full_name="PG Workbench User",
            password_hash=hash_password("pg_secret_pass"),
            status=UserStatus.ACTIVE
        )
        setup_db.add(test_user)
        setup_db.commit()

        # Use a unique role code to avoid conflicts with existing roles
        unique_role_code = f"admin_{uuid.uuid4().hex[:8]}"
        role_admin = Role(
            code=unique_role_code,
            display_name="Admin",
            permissions=[
                "workbench:open",
                "workbench:read",
                "workbench:edit",
                "workbench:undo_redo"
            ]
        )
        setup_db.add(role_admin)
        setup_db.commit()

        setup_db.add(UserRole(user_id=test_user.id, role_id=role_admin.id, is_active=True))
        setup_db.commit()

        customer = Customer(organization_id=test_org.id, legal_name="PG Cust", status="active", created_by=test_user.id)
        setup_db.add(customer)
        setup_db.commit()

        project = Project(
            organization_id=test_org.id,
            code=f"PRJ-PG-{uuid.uuid4().hex[:4]}",
            name="PG Project",
            status=ProjectWorkflowStatus.DRAFT,
            customer_id=customer.id,
            created_by=test_user.id
        )
        setup_db.add(project)
        setup_db.commit()

        test_user_id = test_user.id
        test_org_slug = test_org.organization_slug
        test_user_email = test_user.email
        project_id = project.id
        project_id_str = str(project.id)

        setup_db.close()
        setup_db = None

        def pg_get_db():
            db = PGSession()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = pg_get_db
        pg_client = TestClient(app)

        # Login user
        resp = pg_client.post("/api/v1/auth/login", json={
            "organization_slug": test_org_slug,
            "email": test_user_email,
            "password": "pg_secret_pass"
        })
        assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"

        from app.api.auth import get_cookie_keys
        acc_key, _ = get_cookie_keys()
        shared_access_token = pg_client.cookies.get(acc_key)
        shared_csrf_token = pg_client.cookies.get("XSRF-TOKEN")

        results = []
        barrier = threading.Barrier(2)

        def thread_create_session(name: str):
            c = TestClient(app)
            c.cookies.set(acc_key, shared_access_token)
            c.cookies.set("XSRF-TOKEN", shared_csrf_token)
            c.headers["X-CSRF-Token"] = shared_csrf_token
            c.headers["Origin"] = "http://localhost:5173"
            barrier.wait()
            try:
                r = c.post("/api/v1/workbench/sessions", json={"project_id": project_id_str})
                results.append((name, r.status_code, r.json(), None))
            except Exception as e:
                results.append((name, "exception", None, str(e)))

        threads = [
            threading.Thread(target=thread_create_session, args=(f"T{i}",))
            for i in range(2)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No exceptions
        for r in results:
            assert r[3] is None, f"Thread {r[0]} encountered exception: {r[3]}"

        # Exactly one 201 and one 200
        status_codes = sorted([r[1] for r in results])
        assert status_codes == [200, 201], f"Expected [200, 201], got {status_codes}"

        # Both return the same session ID
        session_id_1 = results[0][2]["id"]
        session_id_2 = results[1][2]["id"]
        assert session_id_1 == session_id_2, (
            f"Threads returned different session IDs: {session_id_1} vs {session_id_2}"
        )

        # Verify database state
        verify_db = PGSession()
        try:
            active_sessions = verify_db.query(WorkbenchSession).filter(
                WorkbenchSession.user_id == test_user_id,
                WorkbenchSession.project_id == project_id,
                WorkbenchSession.status == WorkbenchSessionStatus.ACTIVE
            ).all()
            assert len(active_sessions) == 1, (
                f"Expected exactly 1 active session, found {len(active_sessions)}"
            )

            started_audits = verify_db.query(AuditEvent).filter(
                AuditEvent.event_name == "workbench.session.started",
                AuditEvent.actor_user_id == test_user_id
            ).all()
            assert len(started_audits) == 1, (
                f"Expected exactly 1 workbench.session.started audit event, found {len(started_audits)}"
            )

            start_action_logs = verify_db.query(UserActionLog).filter(
                UserActionLog.user_id == test_user_id,
                UserActionLog.action_type == "session_start"
            ).all()
            assert len(start_action_logs) == 1, (
                f"Expected exactly 1 session_start UserActionLog, found {len(start_action_logs)}"
            )
        finally:
            verify_db.close()

    finally:
        app.dependency_overrides.pop(get_db, None)
        if setup_db:
            setup_db.close()
        if pg_engine:
            pg_engine.dispose()


def test_create_session_unexpected_error_rolls_back(client: TestClient, db_session: Session, setup_rbac_users, monkeypatch) -> None:
    """
    When log_audit_event raises an unexpected RuntimeError during session creation,
    the endpoint must propagate the exception (not return 200 resume),
    and no committed audit event or action log must be written.

    Note: WorkbenchSession row-count assertions are skipped here because SQLite's
    StaticPool in-memory semantics differ from PostgreSQL for nested transaction releases.
    The authoritative zero-mutation evidence is absence of AuditEvent and UserActionLog rows.
    """
    import app.api.workbench as wb_module
    from app.modules.project_master_data.models import AuditEvent, UserActionLog

    login_user_in_test(client, db_session, uuid.UUID(setup_rbac_users["admin_id"]), setup_rbac_users["org_id"])

    audit_count_before = db_session.query(AuditEvent).count()
    log_count_before = db_session.query(UserActionLog).count()

    # Monkeypatch log_audit_event to raise RuntimeError
    def mock_log_audit_event(*args, **kwargs):
        raise RuntimeError("Simulated audit failure")
    monkeypatch.setattr(wb_module, "log_audit_event", mock_log_audit_event)

    # POST create session — must propagate the exception, not return 200/201 resume
    with pytest.raises(RuntimeError, match="Simulated audit failure"):
        client.post("/api/v1/workbench/sessions", json={"project_id": setup_rbac_users["project_id"]})

    # No committed AuditEvent or UserActionLog must exist.
    # These are the authoritative zero-mutation assertions because:
    #   - log_audit_event raised BEFORE db.commit() was called
    #   - db.rollback() was called by the exception handler
    # WorkbenchSession row-count and active-session status checks are skipped for SQLite
    # StaticPool because SQLite auto-commits on SAVEPOINT RELEASE, making session.rollback()
    # unable to revert flushed data in the shared single-connection pool.
    # These behaviours are covered by test_postgres_concurrent_session_create on PostgreSQL.
    db_session.expire_all()
    assert db_session.query(AuditEvent).count() == audit_count_before, (
        "No workbench.session.started AuditEvent should be committed after unexpected audit error"
    )
    assert db_session.query(UserActionLog).count() == log_count_before, (
        "No session_start UserActionLog should be committed after unexpected audit error"
    )



def test_postgres_create_session_unexpected_error_rolls_back():
    """
    PostgreSQL-backed evidence that when log_audit_event raises RuntimeError
    after WorkbenchSession has been flushed (savepoint released), the outer
    db.rollback() correctly reverts the entire transaction — leaving:
      - 0 ACTIVE WorkbenchSession for user + project
      - 0 workbench.session.started AuditEvent
      - 0 session_start UserActionLog

    In CI (CI=true): pytest.fail if TEST_DATABASE_URL is absent or index missing.
    Locally without PostgreSQL: pytest.skip with a clear reason.
    """
    import os
    pg_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    is_ci = os.getenv("CI") == "true"

    if not pg_url or not pg_url.startswith("postgres"):
        if is_ci:
            pytest.fail(
                "CI=true but TEST_DATABASE_URL is not configured with a PostgreSQL URL. "
                "PostgreSQL unexpected-error rollback test cannot be skipped in CI."
            )
        pytest.skip(
            "PostgreSQL not configured (TEST_DATABASE_URL/DATABASE_URL absent or not postgres). "
            "Skipping PostgreSQL unexpected-error rollback test — awaiting CI with PostgreSQL service."
        )
        return

    pg_engine = None
    setup_db = None
    try:
        pg_engine = create_engine(
            pg_url,
            connect_args={"connect_timeout": 3}
        )
        with pg_engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename='workbench_sessions' "
                "AND indexname='uq_active_session_per_user_project'"
            )).fetchall()
            if not result:
                if is_ci:
                    pytest.fail(
                        "Index 'uq_active_session_per_user_project' not found on workbench_sessions. "
                        "Alembic migration must run before this test in CI."
                    )
                pytest.skip(
                    "Index 'uq_active_session_per_user_project' not found — "
                    "run 'alembic upgrade head' first."
                )
                return
    except Exception as exc:
        if is_ci:
            pytest.fail(
                f"PostgreSQL not available at configured URL in CI: {exc}. "
                "Unexpected-error rollback test cannot be skipped in CI."
            )
        pytest.skip(
            f"PostgreSQL not available at configured URL ({exc}). "
            "Skipping PostgreSQL unexpected-error rollback test."
        )
        return

    from sqlalchemy.orm import sessionmaker as sm
    from app.modules.project_master_data.models import (
        OrganizationProfile, OrganizationStatus, User, UserStatus, Role, UserRole, Project,
        ProjectWorkflowStatus, Customer, AuditEvent, WorkbenchSession, WorkbenchSessionStatus, UserActionLog
    )
    import app.api.workbench as wb_module

    PGSession = sm(bind=pg_engine)
    setup_db = PGSession()

    try:
        # Create isolated org, user, role, customer, project
        test_org = OrganizationProfile(
            legal_name="PG Rollback Org",
            organization_slug=f"pg-rb-org-{uuid.uuid4().hex[:8]}",
            status=OrganizationStatus.ACTIVE
        )
        setup_db.add(test_org)
        setup_db.commit()

        test_user = User(
            organization_id=test_org.id,
            email=f"pg-rb-{uuid.uuid4().hex[:8]}@regulus.com",
            full_name="PG Rollback User",
            password_hash=hash_password("pg_rb_secret"),
            status=UserStatus.ACTIVE
        )
        setup_db.add(test_user)
        setup_db.commit()

        unique_role_code = f"admin_{uuid.uuid4().hex[:8]}"
        role_admin = Role(
            code=unique_role_code,
            display_name="Admin",
            permissions=[
                "workbench:open",
                "workbench:read",
                "workbench:edit",
                "workbench:undo_redo"
            ]
        )
        setup_db.add(role_admin)
        setup_db.commit()

        setup_db.add(UserRole(user_id=test_user.id, role_id=role_admin.id, is_active=True))
        setup_db.commit()

        customer = Customer(
            organization_id=test_org.id,
            legal_name="PG Rollback Cust",
            status="active",
            created_by=test_user.id
        )
        setup_db.add(customer)
        setup_db.commit()

        project = Project(
            organization_id=test_org.id,
            code=f"PRJ-RB-{uuid.uuid4().hex[:4]}",
            name="PG Rollback Project",
            status=ProjectWorkflowStatus.DRAFT,
            customer_id=customer.id,
            created_by=test_user.id
        )
        setup_db.add(project)
        setup_db.commit()

        test_user_id = test_user.id
        test_org_slug = test_org.organization_slug
        test_user_email = test_user.email
        project_id = project.id
        project_id_str = str(project.id)

        setup_db.close()
        setup_db = None

        def pg_get_db():
            db = PGSession()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = pg_get_db
        pg_client = TestClient(app)

        # Authenticate via real cookie login
        resp = pg_client.post("/api/v1/auth/login", json={
            "organization_slug": test_org_slug,
            "email": test_user_email,
            "password": "pg_rb_secret"
        })
        assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"

        from app.api.auth import get_cookie_keys
        acc_key, _ = get_cookie_keys()
        access_token = pg_client.cookies.get(acc_key)
        csrf_token = pg_client.cookies.get("XSRF-TOKEN")

        # Patch log_audit_event to raise RuntimeError AFTER flush
        original_log_audit_event = wb_module.log_audit_event

        def mock_log_audit_event(*args, **kwargs):
            raise RuntimeError("Simulated audit failure — PostgreSQL rollback test")

        wb_module.log_audit_event = mock_log_audit_event
        try:
            rb_client = TestClient(app)
            rb_client.cookies.set(acc_key, access_token)
            rb_client.cookies.set("XSRF-TOKEN", csrf_token)
            rb_client.headers["X-CSRF-Token"] = csrf_token
            rb_client.headers["Origin"] = "http://localhost:5173"

            # Request must propagate the RuntimeError, not silently return 200
            with pytest.raises(RuntimeError, match="Simulated audit failure"):
                rb_client.post("/api/v1/workbench/sessions", json={"project_id": project_id_str})
        finally:
            wb_module.log_audit_event = original_log_audit_event

        # Verify PostgreSQL state — all mutations must be absent
        verify_db = PGSession()
        try:
            active_sessions = verify_db.query(WorkbenchSession).filter(
                WorkbenchSession.user_id == test_user_id,
                WorkbenchSession.project_id == project_id,
                WorkbenchSession.status == WorkbenchSessionStatus.ACTIVE
            ).all()
            assert len(active_sessions) == 0, (
                f"Expected 0 ACTIVE WorkbenchSessions after rollback, found {len(active_sessions)}"
            )

            audit_events = verify_db.query(AuditEvent).filter(
                AuditEvent.event_name == "workbench.session.started",
                AuditEvent.actor_user_id == test_user_id
            ).all()
            assert len(audit_events) == 0, (
                f"Expected 0 workbench.session.started AuditEvents after rollback, found {len(audit_events)}"
            )

            action_logs = verify_db.query(UserActionLog).filter(
                UserActionLog.user_id == test_user_id,
                UserActionLog.action_type == "session_start"
            ).all()
            assert len(action_logs) == 0, (
                f"Expected 0 session_start UserActionLogs after rollback, found {len(action_logs)}"
            )
        finally:
            verify_db.close()

    finally:
        app.dependency_overrides.pop(get_db, None)
        if setup_db:
            setup_db.close()
        if pg_engine:
            pg_engine.dispose()



def test_heartbeat_atomic_rollback(client: TestClient, db_session: Session, setup_rbac_users, monkeypatch) -> None:
    from app.modules.project_master_data.models import WorkbenchSession, UserActionLog
    login_user_in_test(client, db_session, uuid.UUID(setup_rbac_users["admin_id"]), setup_rbac_users["org_id"])

    # Create session
    resp = client.post("/api/v1/workbench/sessions", json={"project_id": setup_rbac_users["project_id"]})
    assert resp.status_code == 201
    sid = resp.json()["id"]

    db_session.expire_all()
    session = db_session.get(WorkbenchSession, uuid.UUID(sid))
    row_ver_before = session.row_version
    last_act_before = session.last_active_at

    log_count_before = db_session.query(UserActionLog).count()

    # Monkeypatch log_action to raise an error
    import app.api.workbench as wb_module
    def mock_log_action(*args, **kwargs):
        raise RuntimeError("Simulated log_action failure")
    monkeypatch.setattr(wb_module, "log_action", mock_log_action)

    # Call heartbeat -> must fail (exception bubbles up in TestClient)
    with pytest.raises(RuntimeError, match="Simulated log_action failure"):
        client.post(f"/api/v1/workbench/sessions/{sid}/heartbeat", json={"expected_row_version": row_ver_before})

    # Expire and reload ORM state
    db_session.expire_all()
    session_after = db_session.get(WorkbenchSession, uuid.UUID(sid))

    # Assert fields are unmodified and no log created
    assert session_after.row_version == row_ver_before
    assert session_after.last_active_at == last_act_before
    assert db_session.query(UserActionLog).count() == log_count_before


def test_selection_atomic_rollback(client: TestClient, db_session: Session, setup_rbac_users, monkeypatch) -> None:
    from app.modules.project_master_data.models import ProjectAssetLine, WorkbenchSession, WorkbenchSelection, UserActionLog
    login_user_in_test(client, db_session, uuid.UUID(setup_rbac_users["admin_id"]), setup_rbac_users["org_id"])

    # Create session
    resp = client.post("/api/v1/workbench/sessions", json={"project_id": setup_rbac_users["project_id"]})
    assert resp.status_code == 201
    sid = resp.json()["id"]

    line_a = ProjectAssetLine(
        id=uuid.uuid4(),
        project_id=uuid.UUID(setup_rbac_users["project_id"]),
        asset_name="Line A",
        quantity=1.0
    )
    db_session.add(line_a)
    db_session.commit()

    # Initial selection save
    resp_ok = client.post(f"/api/v1/workbench/sessions/{sid}/selection", json={
        "selected_target_type": "project_asset_line",
        "selected_target_ids": [str(line_a.id)]
    })
    assert resp_ok.status_code == 200

    db_session.expire_all()
    session = db_session.get(WorkbenchSession, uuid.UUID(sid))
    initial_selection_cache = session.current_selection

    sel = db_session.query(WorkbenchSelection).filter(WorkbenchSelection.session_id == uuid.UUID(sid)).first()
    initial_sel_ids = list(sel.selected_target_ids)

    log_count_before = db_session.query(UserActionLog).count()

    # Monkeypatch log_action to raise an error
    import app.api.workbench as wb_module
    def mock_log_action(*args, **kwargs):
        raise RuntimeError("Simulated log_action failure")
    monkeypatch.setattr(wb_module, "log_action", mock_log_action)

    # Try updating selection -> fails
    with pytest.raises(RuntimeError, match="Simulated log_action failure"):
        client.post(f"/api/v1/workbench/sessions/{sid}/selection", json={
            "selected_target_type": "project_asset_line",
            "selected_target_ids": []
        })

    db_session.expire_all()
    session_after = db_session.get(WorkbenchSession, uuid.UUID(sid))
    sel_after = db_session.query(WorkbenchSelection).filter(WorkbenchSelection.session_id == uuid.UUID(sid)).first()

    # Assert unmodified
    assert session_after.current_selection == initial_selection_cache
    assert sel_after.selected_target_ids == initial_sel_ids
    assert db_session.query(UserActionLog).count() == log_count_before


def test_closed_session_matrix(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    from app.modules.project_master_data.models import (
        ProjectAssetLine, WorkbenchSession, AuditEvent, UserActionLog
    )
    login_user_in_test(client, db_session, uuid.UUID(setup_rbac_users["admin_id"]), setup_rbac_users["org_id"])

    # Create session
    resp = client.post("/api/v1/workbench/sessions", json={"project_id": setup_rbac_users["project_id"]})
    assert resp.status_code == 201
    sid = resp.json()["id"]

    line_a = ProjectAssetLine(
        id=uuid.uuid4(),
        project_id=uuid.UUID(setup_rbac_users["project_id"]),
        asset_name="Line A",
        quantity=1.0
    )
    db_session.add(line_a)
    db_session.commit()

    # Close session
    resp_close = client.post(f"/api/v1/workbench/sessions/{sid}/close")
    assert resp_close.status_code == 200

    # Capture DB state immediately after close
    db_session.expire_all()
    closed_session = db_session.get(WorkbenchSession, uuid.UUID(sid))
    status_val = closed_session.status
    # Handle both SQLite (string) and PostgreSQL (enum) representations
    if hasattr(status_val, "value"):
        status_val = status_val.value
    assert status_val == "closed", f"Session must be 'closed' after close endpoint, got {status_val!r}"
    audit_count_after_close = db_session.query(AuditEvent).count()
    log_count_after_close = db_session.query(UserActionLog).count()

    def assert_zero_mutation(label: str):
        """Assert no new DB rows were written by the rejected request."""
        db_session.expire_all()
        assert db_session.query(AuditEvent).count() == audit_count_after_close, (
            f"{label}: unexpected new AuditEvent row after 404"
        )
        assert db_session.query(UserActionLog).count() == log_count_after_close, (
            f"{label}: unexpected new UserActionLog row after 404"
        )

    # 1. GET session -> 404
    assert client.get(f"/api/v1/workbench/sessions/{sid}").status_code == 404
    assert_zero_mutation("GET session")

    # 2. POST heartbeat -> 404
    assert client.post(f"/api/v1/workbench/sessions/{sid}/heartbeat", json={"expected_row_version": 1}).status_code == 404
    assert_zero_mutation("POST heartbeat")

    # 3. POST layout -> 404
    assert client.post(f"/api/v1/workbench/sessions/{sid}/layout", json={"layout_name": "L", "layout_payload": {}}).status_code == 404
    assert_zero_mutation("POST layout")

    # 4. POST grid-view -> 404
    assert client.post(f"/api/v1/workbench/sessions/{sid}/grid-view", json={"view_name": "V", "columns": {}, "filters": {}, "sort": {}}).status_code == 404
    assert_zero_mutation("POST grid-view")

    # 5. GET grid-view -> 404
    assert client.get(f"/api/v1/workbench/sessions/{sid}/grid-view").status_code == 404
    assert_zero_mutation("GET grid-view")

    # 6. POST selection -> 404
    assert client.post(f"/api/v1/workbench/sessions/{sid}/selection", json={"selected_target_type": "project_asset_line", "selected_target_ids": []}).status_code == 404
    assert_zero_mutation("POST selection")

    # 7. GET selection -> 404
    assert client.get(f"/api/v1/workbench/sessions/{sid}/selection").status_code == 404
    assert_zero_mutation("GET selection")

    # 8. POST inline-edit -> 404
    assert client.post(f"/api/v1/workbench/sessions/{sid}/inline-edit", json={
        "target_type": "project_asset_line",
        "target_id": str(line_a.id),
        "field_key": "x",
        "draft_value": {},
        "base_value": {},
        "base_row_version": 1
    }).status_code == 404
    assert_zero_mutation("POST inline-edit")

    # 9. GET inline-edits -> 404
    assert client.get(f"/api/v1/workbench/sessions/{sid}/inline-edits").status_code == 404
    assert_zero_mutation("GET inline-edits")

    # 10. POST checkpoint -> 404
    assert client.post(f"/api/v1/workbench/sessions/{sid}/checkpoint", json={"checkpoint_payload": {}}).status_code == 404
    assert_zero_mutation("POST checkpoint")

    # 11. POST undo -> 404
    assert client.post(f"/api/v1/workbench/sessions/{sid}/undo").status_code == 404
    assert_zero_mutation("POST undo")

    # 12. POST redo -> 404
    assert client.post(f"/api/v1/workbench/sessions/{sid}/redo").status_code == 404
    assert_zero_mutation("POST redo")

    # 13. POST panel-state -> 404
    assert client.post(f"/api/v1/workbench/sessions/{sid}/panel-state", json={"panel_type": "knowledge_panel", "is_expanded": True}).status_code == 404
    assert_zero_mutation("POST panel-state")

    # 14. GET panel-state -> 404
    assert client.get(f"/api/v1/workbench/sessions/{sid}/panel-state").status_code == 404
    assert_zero_mutation("GET panel-state")

    # 15. GET notifications -> 404
    assert client.get(f"/api/v1/workbench/sessions/{sid}/notifications").status_code == 404
    assert_zero_mutation("GET notifications")


def test_selection_validation_isolation_and_rollback(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    from app.modules.project_master_data.models import ProjectAssetLine, Customer, Project, ProjectWorkflowStatus
    login_user_in_test(client, db_session, uuid.UUID(setup_rbac_users["admin_id"]), setup_rbac_users["org_id"])

    # Create session
    resp = client.post("/api/v1/workbench/sessions", json={"project_id": setup_rbac_users["project_id"]})
    assert resp.status_code == 201
    sid = resp.json()["id"]

    # Seed valid target line
    line_a = ProjectAssetLine(
        id=uuid.uuid4(),
        project_id=uuid.UUID(setup_rbac_users["project_id"]),
        asset_name="Line A",
        quantity=1.0
    )
    db_session.add(line_a)
    db_session.commit()

    # Seed cross-project target line (different tenant)
    cust = db_session.query(Customer).first()
    proj_other = Project(
        id=uuid.uuid4(),
        organization_id=setup_rbac_users["org_id"],
        customer_id=cust.id,
        code="PROJ-OTHER-SEL",
        name="Project Other Selection",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add(proj_other)
    db_session.commit()

    line_other = ProjectAssetLine(
        id=uuid.uuid4(),
        project_id=proj_other.id,
        asset_name="Line Other",
        quantity=1.0
    )
    db_session.add(line_other)
    db_session.commit()

    # 1. Valid targets -> success
    resp_ok = client.post(f"/api/v1/workbench/sessions/{sid}/selection", json={
        "selected_target_type": "project_asset_line",
        "selected_target_ids": [str(line_a.id)]
    })
    assert resp_ok.status_code == 200

    # 2. Target from other project -> 404
    resp_other = client.post(f"/api/v1/workbench/sessions/{sid}/selection", json={
        "selected_target_type": "project_asset_line",
        "selected_target_ids": [str(line_other.id)]
    })
    assert resp_other.status_code == 404

    # 3. Unknown target type -> 400
    resp_unknown = client.post(f"/api/v1/workbench/sessions/{sid}/selection", json={
        "selected_target_type": "unknown_type",
        "selected_target_ids": [str(line_a.id)]
    })
    assert resp_unknown.status_code == 400

    # 4. Mixed valid/invalid IDs rollback check
    # Try save mixed valid and invalid -> fails 404, selection is not mutated (stays with only line_a)
    resp_mixed = client.post(f"/api/v1/workbench/sessions/{sid}/selection", json={
        "selected_target_type": "project_asset_line",
        "selected_target_ids": [str(line_a.id), str(line_other.id)]
    })
    assert resp_mixed.status_code == 404

    # Get selection to verify it was NOT updated to the mixed set
    resp_get = client.get(f"/api/v1/workbench/sessions/{sid}/selection")
    assert resp_get.status_code == 200
    assert resp_get.json()[0]["selected_target_ids"] == [str(line_a.id)]


# ==========================================
# S12-R-004 TESTS
# ==========================================

def test_s12_r_004_direct_mutation_bypass(client: TestClient, db_session: Session, setup_rbac_users):
    headers = {"X-User-Id": setup_rbac_users["admin_id"]}
    cust = db_session.query(Customer).first()
    proj = Project(
        organization_id=setup_rbac_users["org_id"],
        customer_id=cust.id,
        code="PRJ-PATCH-BYPASS",
        name="Project Patch Bypass",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add(proj)
    db_session.commit()

    line = ProjectAssetLine(
        project_id=proj.id,
        asset_name="Original Name",
        description="Original Desc",
        quantity=1.0,
        appraised_unit_price=100.0,
        row_version=1
    )
    db_session.add(line)
    db_session.commit()

    # 1. Allowed mutations (e.g. quantity, asset_name) pass
    resp = client.patch(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}",
        json={"asset_name": "New Name", "row_version": 1},
        headers=headers
    )
    assert resp.status_code == 200

    # 2. Direct mutation of description is rejected
    resp = client.patch(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}",
        json={"description": "New Direct Desc", "row_version": 2},
        headers=headers
    )
    assert resp.status_code == 400

    # 3. Direct mutation of appraised_unit_price is rejected
    resp = client.patch(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}",
        json={"appraised_unit_price": 500.0, "row_version": 2},
        headers=headers
    )
    assert resp.status_code == 400

    # 4. Mixed payload with allowed and disallowed fields is rejected
    resp = client.patch(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}",
        json={"asset_name": "Another Name", "description": "Desc", "row_version": 2},
        headers=headers
    )
    assert resp.status_code == 400

    # 5. Direct mutation of status fields is rejected
    resp = client.patch(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}",
        json={"review_status": "accepted", "row_version": 2},
        headers=headers
    )
    assert resp.status_code == 400


def test_s12_r_004_exact_version_locking(client: TestClient, db_session: Session, setup_rbac_users):
    headers = {"X-User-Id": setup_rbac_users["admin_id"]}
    cust = db_session.query(Customer).first()
    proj = Project(
        organization_id=setup_rbac_users["org_id"],
        customer_id=cust.id,
        code="PRJ-LOCKING",
        name="Project Locking",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add(proj)
    db_session.commit()

    line = ProjectAssetLine(
        project_id=proj.id,
        asset_name="Line",
        description="Desc",
        appraised_unit_price=100.0,
        row_version=1
    )
    db_session.add(line)
    db_session.commit()

    # Create active session
    sess = WorkbenchSession(
        user_id=uuid.UUID(setup_rbac_users["admin_id"]),
        project_id=proj.id,
        status=WorkbenchSessionStatus.ACTIVE
    )
    db_session.add(sess)
    db_session.commit()

    # Save draft based on stale version (base version = 0)
    draft_stale = InlineEditDraft(
        session_id=sess.id,
        target_type="ProjectAssetLine",
        target_id=line.id,
        field_key="appraised_unit_price",
        draft_value={"value": 150.0},
        base_row_version=0,
        status=InlineEditDraftStatus.DRAFT
    )
    db_session.add(draft_stale)
    db_session.commit()

    # Commit stale draft fails with 409
    resp = client.post(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}/draft/commit",
        json={"field_keys": ["appraised_unit_price"], "confirm": True},
        headers=headers
    )
    assert resp.status_code == 409

    # Update draft to future version (base version = 5)
    db_session.delete(draft_stale)
    db_session.commit()

    draft_future = InlineEditDraft(
        session_id=sess.id,
        target_type="ProjectAssetLine",
        target_id=line.id,
        field_key="appraised_unit_price",
        draft_value={"value": 150.0},
        base_row_version=5,
        status=InlineEditDraftStatus.DRAFT
    )
    db_session.add(draft_future)
    db_session.commit()

    # Commit future draft fails with 409
    resp = client.post(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}/draft/commit",
        json={"field_keys": ["appraised_unit_price"], "confirm": True},
        headers=headers
    )
    assert resp.status_code == 409


def test_s12_r_004_typed_validation_rules(client: TestClient, db_session: Session, setup_rbac_users):
    headers = {"X-User-Id": setup_rbac_users["admin_id"]}
    cust = db_session.query(Customer).first()
    proj = Project(
        organization_id=setup_rbac_users["org_id"],
        customer_id=cust.id,
        code="PRJ-TYPED-WB",
        name="Project Typed WB",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add(proj)
    db_session.commit()

    line = ProjectAssetLine(
        project_id=proj.id,
        asset_name="Line",
        description="Desc",
        appraised_unit_price=100.0,
        row_version=1
    )
    db_session.add(line)
    db_session.commit()

    sess = WorkbenchSession(
        user_id=uuid.UUID(setup_rbac_users["admin_id"]),
        project_id=proj.id,
        status=WorkbenchSessionStatus.ACTIVE
    )
    db_session.add(sess)
    db_session.commit()

    # 1. Invalid description type (array)
    draft1 = InlineEditDraft(
        session_id=sess.id,
        target_type="ProjectAssetLine",
        target_id=line.id,
        field_key="description",
        draft_value={"value": ["an", "array"]},
        base_row_version=1,
        status=InlineEditDraftStatus.DRAFT
    )
    db_session.add(draft1)
    db_session.commit()

    resp = client.post(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}/draft/commit",
        json={"field_keys": ["description"], "confirm": True},
        headers=headers
    )
    assert resp.status_code == 400
    db_session.delete(draft1)
    db_session.commit()

    # 2. Invalid description type (dict)
    draft2 = InlineEditDraft(
        session_id=sess.id,
        target_type="ProjectAssetLine",
        target_id=line.id,
        field_key="description",
        draft_value={"value": {"some": "object"}},
        base_row_version=1,
        status=InlineEditDraftStatus.DRAFT
    )
    db_session.add(draft2)
    db_session.commit()

    resp = client.post(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}/draft/commit",
        json={"field_keys": ["description"], "confirm": True},
        headers=headers
    )
    assert resp.status_code == 400
    db_session.delete(draft2)
    db_session.commit()

    # 3. Invalid appraised_unit_price (negative)
    draft3 = InlineEditDraft(
        session_id=sess.id,
        target_type="ProjectAssetLine",
        target_id=line.id,
        field_key="appraised_unit_price",
        draft_value={"value": -50.0},
        base_row_version=1,
        status=InlineEditDraftStatus.DRAFT
    )
    db_session.add(draft3)
    db_session.commit()

    resp = client.post(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}/draft/commit",
        json={"field_keys": ["appraised_unit_price"], "confirm": True},
        headers=headers
    )
    assert resp.status_code == 400
    db_session.delete(draft3)
    db_session.commit()

    # 4. Invalid appraised_unit_price (boolean)
    draft4 = InlineEditDraft(
        session_id=sess.id,
        target_type="ProjectAssetLine",
        target_id=line.id,
        field_key="appraised_unit_price",
        draft_value={"value": True},
        base_row_version=1,
        status=InlineEditDraftStatus.DRAFT
    )
    db_session.add(draft4)
    db_session.commit()

    resp = client.post(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}/draft/commit",
        json={"field_keys": ["appraised_unit_price"], "confirm": True},
        headers=headers
    )
    assert resp.status_code == 400
    db_session.delete(draft4)
    db_session.commit()

    # 5. Invalid appraised_unit_price (non-numeric string)
    draft5 = InlineEditDraft(
        session_id=sess.id,
        target_type="ProjectAssetLine",
        target_id=line.id,
        field_key="appraised_unit_price",
        draft_value={"value": "garbage_string"},
        base_row_version=1,
        status=InlineEditDraftStatus.DRAFT
    )
    db_session.add(draft5)
    db_session.commit()

    resp = client.post(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}/draft/commit",
        json={"field_keys": ["appraised_unit_price"], "confirm": True},
        headers=headers
    )
    assert resp.status_code == 400
    db_session.delete(draft5)
    db_session.commit()

    # 6. Invalid appraised_unit_price (NaN/Inf)
    draft6 = InlineEditDraft(
        session_id=sess.id,
        target_type="ProjectAssetLine",
        target_id=line.id,
        field_key="appraised_unit_price",
        draft_value={"value": "NaN"},
        base_row_version=1,
        status=InlineEditDraftStatus.DRAFT
    )
    db_session.add(draft6)
    db_session.commit()

    resp = client.post(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}/draft/commit",
        json={"field_keys": ["appraised_unit_price"], "confirm": True},
        headers=headers
    )
    assert resp.status_code == 400
    db_session.delete(draft6)
    db_session.commit()


def test_s12_r_004_side_effects_prohibition(client: TestClient, db_session: Session, setup_rbac_users, monkeypatch):
    headers = {"X-User-Id": setup_rbac_users["admin_id"]}
    cust = db_session.query(Customer).first()
    proj = Project(
        organization_id=setup_rbac_users["org_id"],
        customer_id=cust.id,
        code="PRJ-SIDE-EFFECT",
        name="Project Side Effect",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add(proj)
    db_session.commit()

    line = ProjectAssetLine(
        project_id=proj.id,
        asset_name="Line",
        description="Desc",
        appraised_unit_price=100.0,
        row_version=1
    )
    db_session.add(line)
    db_session.commit()

    sess = WorkbenchSession(
        user_id=uuid.UUID(setup_rbac_users["admin_id"]),
        project_id=proj.id,
        status=WorkbenchSessionStatus.ACTIVE
    )
    db_session.add(sess)
    db_session.commit()

    draft = InlineEditDraft(
        session_id=sess.id,
        target_type="ProjectAssetLine",
        target_id=line.id,
        field_key="appraised_unit_price",
        draft_value={"value": 150.0},
        base_row_version=1,
        status=InlineEditDraftStatus.DRAFT
    )
    db_session.add(draft)
    db_session.commit()

    # Mock any hypothetical external background or AI approvals
    ai_called = False
    def mock_ai_governance(*args, **kwargs):
        nonlocal ai_called
        ai_called = True
        
    # Apply monkeypatch if modules exist
    try:
        import app.modules.ai_governance_security as ai_mod
        monkeypatch.setattr(ai_mod, "validate_approvals", mock_ai_governance)
    except (ImportError, AttributeError):
        pass

    resp = client.post(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}/draft/commit",
        json={"field_keys": ["appraised_unit_price"], "confirm": True},
        headers=headers
    )
    assert resp.status_code == 200
    assert not ai_called


def test_s12_r_004_draft_lifecycle(client: TestClient, db_session: Session, setup_rbac_users):
    headers = {"X-User-Id": setup_rbac_users["admin_id"]}
    cust = db_session.query(Customer).first()
    proj = Project(
        organization_id=setup_rbac_users["org_id"],
        customer_id=cust.id,
        code="PRJ-LIFECYCLE",
        name="Project Lifecycle",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add(proj)
    db_session.commit()

    line = ProjectAssetLine(
        project_id=proj.id,
        asset_name="Line",
        description="Desc",
        appraised_unit_price=100.0,
        row_version=1
    )
    db_session.add(line)
    db_session.commit()

    sess = WorkbenchSession(
        user_id=uuid.UUID(setup_rbac_users["admin_id"]),
        project_id=proj.id,
        status=WorkbenchSessionStatus.ACTIVE
    )
    db_session.add(sess)
    db_session.commit()

    # Draft for appraised price
    draft_price = InlineEditDraft(
        session_id=sess.id,
        target_type="ProjectAssetLine",
        target_id=line.id,
        field_key="appraised_unit_price",
        draft_value={"value": 150.0},
        base_row_version=1,
        status=InlineEditDraftStatus.DRAFT
    )
    # Draft for description
    draft_desc = InlineEditDraft(
        session_id=sess.id,
        target_type="ProjectAssetLine",
        target_id=line.id,
        field_key="description",
        draft_value={"value": "New Desc"},
        base_row_version=1,
        status=InlineEditDraftStatus.DRAFT
    )
    db_session.add_all([draft_price, draft_desc])
    db_session.commit()

    # Commit only appraised_unit_price
    resp = client.post(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}/draft/commit",
        json={"field_keys": ["appraised_unit_price"], "confirm": True},
        headers=headers
    )
    assert resp.status_code == 200

    # Verify committed field deleted, other field remains
    remaining = db_session.query(InlineEditDraft).filter(InlineEditDraft.session_id == sess.id).all()
    assert len(remaining) == 1
    assert remaining[0].field_key == "description"

    # Repeated commit fails with 400 since draft no longer exists
    resp_repeat = client.post(
        f"/api/v1/projects/{proj.id}/asset-lines/{line.id}/draft/commit",
        json={"field_keys": ["appraised_unit_price"], "confirm": True},
        headers=headers
    )
    assert resp_repeat.status_code == 400

