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
    ProjectWorkflowStatus, Customer, ReviewDecision, ReviewDecisionChoice,
    ReviewDecisionReversal, ProjectAssetLine
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
def setup_acceptance_data(db_session: Session):
    org = OrganizationProfile(legal_name="Acceptance Org", organization_slug="acceptance-org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    role_admin = Role(
        code="admin",
        display_name="Admin",
        permissions=[
            "workflow:read",
            "workflow:instance:manage",
            "workflow:task:assign",
            "workflow:task:complete",
            "workflow:decision:create",
            "workflow:override_gate",
            "workbench:open",
            "workbench:read",
            "workbench:edit",
            "workbench:undo_redo",
            "workflow:change_request:create",
            "workflow:change_request:review",
            "workflow:change_request:execute"
        ]
    )
    role_viewer = Role(
        code="viewer",
        display_name="Viewer",
        permissions=[
            "workflow:read",
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
        code="PROJ-ACCEPTANCE",
        name="Project Acceptance",
        status=ProjectWorkflowStatus.DRAFT,
        customer_id=customer.id,
        created_by=user_admin.id
    )
    db_session.add(proj)
    db_session.commit()

    # Original ReviewDecision to reverse
    orig_dec = ReviewDecision(
        target_type="project",
        target_id=proj.id,
        decision=ReviewDecisionChoice.APPROVE,
        reason="Approved initial proposal",
        decided_by=user_admin.id
    )
    db_session.add(orig_dec)
    db_session.commit()

    # Seed an asset line for validation checks
    line = ProjectAssetLine(
        id=uuid.uuid4(),
        project_id=proj.id,
        asset_name="Acceptance Asset",
        quantity=1.0
    )
    db_session.add(line)
    db_session.commit()

    return {
        "admin_id": str(user_admin.id),
        "viewer_id": str(user_viewer.id),
        "project_id": str(proj.id),
        "original_decision_id": str(orig_dec.id),
        "line_id": str(line.id)
    }


def test_s4_acceptance_comprehensive_flow(client: TestClient, db_session: Session, setup_acceptance_data) -> None:
    headers_admin = {"X-User-Id": setup_acceptance_data["admin_id"]}
    headers_viewer = {"X-User-Id": setup_acceptance_data["viewer_id"]}

    # =========================================================================
    # 1. WORKBENCH SESSIONS & METADATA
    # =========================================================================
    # Admin creates session
    resp = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_acceptance_data["project_id"]},
        headers=headers_admin
    )
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    # Viewer fails to create session (RBAC block)
    resp = client.post(
        "/api/v1/workbench/sessions",
        json={"project_id": setup_acceptance_data["project_id"]},
        headers=headers_viewer
    )
    assert resp.status_code == 403

    # Admin posts heartbeat
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/heartbeat",
        json={"expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["row_version"] == 2

    # Heartbeat stale row version rejection (returns 409)
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/heartbeat",
        json={"expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 409

    # Save custom layout
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/layout",
        json={
            "layout_name": "Acceptance Layout",
            "layout_payload": {"panels": ["grid", "knowledge"]}
        },
        headers=headers_admin
    )
    assert resp.status_code == 200

    # Save grid-view with filters and sorting
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/grid-view",
        json={
            "view_name": "Active Items",
            "columns": {"code": True, "name": True},
            "filters": {"status": "active"},
            "sort": {"field": "code", "direction": "asc"}
        },
        headers=headers_admin
    )
    assert resp.status_code == 200

    # Save selection
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/selection",
        json={
            "selected_target_type": "project_asset_line",
            "selected_target_ids": [setup_acceptance_data["line_id"]]
        },
        headers=headers_admin
    )
    assert resp.status_code == 200

    # =========================================================================
    # 2. DRAFTS, CHECKPOINTS, UNDO & REDO STACK
    # =========================================================================
    # Save inline draft edit (no official field mutations)
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/inline-edit",
        json={
            "target_type": "project_asset_line",
            "target_id": setup_acceptance_data["line_id"],
            "field_key": "standard_name",
            "draft_value": {"val": "Delta transformer"}
        },
        headers=headers_admin
    )
    assert resp.status_code == 200

    # Create autosave checkpoint
    resp = client.post(
        f"/api/v1/workbench/sessions/{session_id}/checkpoint",
        json={"checkpoint_payload": {"draft_count": 1}},
        headers=headers_admin
    )
    assert resp.status_code == 200

    # Execute undo
    resp = client.post(f"/api/v1/workbench/sessions/{session_id}/undo", headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["is_undone"] is True

    # Execute redo
    resp = client.post(f"/api/v1/workbench/sessions/{session_id}/redo", headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["is_undone"] is False

    # Undo/redo requires undo_redo RBAC, edit is insufficient
    # (Since admin possesses both, let's verify viewer cannot access undo)
    resp = client.post(f"/api/v1/workbench/sessions/{session_id}/undo", headers=headers_viewer)
    assert resp.status_code == 403

    # =========================================================================
    # 3. CHANGE REQUESTS & REVERSAL EXECUTION
    # =========================================================================
    # Create ChangeRequest
    resp = client.post(
        "/api/v1/workflow/change-requests",
        json={
            "target_type": "review_decision",
            "target_id": setup_acceptance_data["original_decision_id"],
            "change_type": "reverse_review_decision",
            "requested_payload": {"original_decision_id": setup_acceptance_data["original_decision_id"]},
            "reason": "Initial appraisal details were outdated."
        },
        headers=headers_admin
    )
    assert resp.status_code == 201
    cr_id = resp.json()["id"]

    # Reject change request fails if review note empty
    resp = client.post(
        f"/api/v1/workflow/change-requests/{cr_id}/reject",
        json={"expected_row_version": 1, "review_note": ""},
        headers=headers_admin
    )
    assert resp.status_code == 400

    # Approve change request
    resp = client.post(
        f"/api/v1/workflow/change-requests/{cr_id}/approve",
        json={"expected_row_version": 1, "review_note": "Approved decision reversal"},
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # Execute requires approved status and expected_row_version matching
    resp = client.post(
        f"/api/v1/workflow/change-requests/{cr_id}/execute?expected_row_version=1",
        headers=headers_admin
    )
    assert resp.status_code == 409  # row_version incremented to 2 on approval

    # Execute successfully
    resp = client.post(
        f"/api/v1/workflow/change-requests/{cr_id}/execute?expected_row_version=2",
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "executed"

    # Already executed request execution rejection
    resp = client.post(
        f"/api/v1/workflow/change-requests/{cr_id}/execute?expected_row_version=3",
        headers=headers_admin
    )
    assert resp.status_code == 400

    # Verify original decision is preserved
    db_session.expire_all()
    orig = db_session.query(ReviewDecision).filter(ReviewDecision.id == uuid.UUID(setup_acceptance_data["original_decision_id"])).one()
    assert orig.decision == ReviewDecisionChoice.APPROVE

    # Verify Reversal link was created
    reversal = db_session.query(ReviewDecisionReversal).filter(ReviewDecisionReversal.change_request_id == uuid.UUID(cr_id)).first()
    assert reversal is not None
    assert reversal.original_review_decision_id == orig.id
    assert reversal.reversal_decision.decision == ReviewDecisionChoice.REJECT
