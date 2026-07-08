import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, User, UserStatus, Role, UserRole, Project,
    ProjectWorkflowStatus, Customer, ReviewDecision, ReviewDecisionChoice,
    ChangeRequest, ChangeRequestStatus, ChangeRequestType, ChangeRequestPriority,
    ReviewDecisionReversal
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
            "workflow:read",
            "workflow:change_request:create",
            "workflow:change_request:review",
            "workflow:change_request:execute"
        ]
    )
    role_viewer = Role(
        code="viewer",
        display_name="Viewer",
        permissions=[
            "workflow:read"
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


def test_change_request_crud_and_rbac(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    # 1. POST /api/v1/workflow/change-requests
    resp = client.post(
        "/api/v1/workflow/change-requests",
        json={
            "target_type": "project",
            "target_id": setup_rbac_users["project_id"],
            "change_type": "reopen",
            "requested_payload": {"status": "draft"},
            "reason": "Need to correct data specs."
        },
        headers=headers_admin
    )
    assert resp.status_code == 201
    cr_id = resp.json()["id"]

    # 2. GET /api/v1/workflow/change-requests
    resp = client.get("/api/v1/workflow/change-requests", headers=headers_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 3. GET /api/v1/workflow/change-requests/{change_request_id}
    resp = client.get(f"/api/v1/workflow/change-requests/{cr_id}", headers=headers_viewer)
    assert resp.status_code == 200
    assert resp.json()["request_code"].startswith("CR-")


def test_change_request_review_workflow(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    # Create change request
    resp = client.post(
        "/api/v1/workflow/change-requests",
        json={
            "target_type": "project",
            "target_id": setup_rbac_users["project_id"],
            "change_type": "reopen",
            "requested_payload": {"status": "draft"},
            "reason": "Reason 1"
        },
        headers=headers_admin
    )
    cr_id = resp.json()["id"]

    # 1. Reject change request
    resp = client.post(
        f"/api/v1/workflow/change-requests/{cr_id}/reject",
        json={"expected_row_version": 1, "review_note": "Rejection note"},
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    # Rejecting requires a note
    resp = client.post(
        f"/api/v1/workflow/change-requests/{cr_id}/reject",
        json={"expected_row_version": 2, "review_note": ""},
        headers=headers_admin
    )
    assert resp.status_code == 400

    # 2. Approve change request (row version has incremented to 2)
    resp = client.post(
        f"/api/v1/workflow/change-requests/{cr_id}/approve",
        json={"expected_row_version": 2, "review_note": "Looks good"},
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_reversal_execution_and_intact_original(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}

    # Create original ReviewDecision
    orig_dec = ReviewDecision(
        target_type="project",
        target_id=uuid.UUID(setup_rbac_users["project_id"]),
        decision=ReviewDecisionChoice.APPROVE,
        reason="Approved initial proposal",
        decided_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add(orig_dec)
    db_session.commit()

    # Create change request targeting decision reversal
    resp = client.post(
        "/api/v1/workflow/change-requests",
        json={
            "target_type": "review_decision",
            "target_id": str(orig_dec.id),
            "change_type": "reverse_review_decision",
            "requested_payload": {"original_decision_id": str(orig_dec.id)},
            "reason": "Initial appraisal details were obsolete."
        },
        headers=headers_admin
    )
    cr_id = resp.json()["id"]

    # Approve request first
    client.post(
        f"/api/v1/workflow/change-requests/{cr_id}/approve",
        json={"expected_row_version": 1, "review_note": "Approved reversal request"},
        headers=headers_admin
    )

    # Execute reversal (row version incremented to 2)
    resp = client.post(
        f"/api/v1/workflow/change-requests/{cr_id}/execute?expected_row_version=2",
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "executed"

    # Verify original ReviewDecision remains intact
    db_session.expire_all()
    q_orig = db_session.query(ReviewDecision).filter(ReviewDecision.id == orig_dec.id).one()
    assert q_orig.decision == ReviewDecisionChoice.APPROVE

    # Verify ReviewDecisionReversal was created linking them
    reversal = db_session.query(ReviewDecisionReversal).filter(ReviewDecisionReversal.change_request_id == uuid.UUID(cr_id)).first()
    assert reversal is not None
    assert reversal.original_review_decision_id == orig_dec.id
    assert reversal.reversal_decision.decision == ReviewDecisionChoice.REJECT


def test_unsupported_execution_types(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}

    # Create change request of type reopen (unsupported for direct automated execute)
    resp = client.post(
        "/api/v1/workflow/change-requests",
        json={
            "target_type": "project",
            "target_id": setup_rbac_users["project_id"],
            "change_type": "reopen",
            "requested_payload": {"status": "draft"},
            "reason": "Reopen review pipeline"
        },
        headers=headers_admin
    )
    cr_id = resp.json()["id"]

    # Approve request first
    client.post(
        f"/api/v1/workflow/change-requests/{cr_id}/approve",
        json={"expected_row_version": 1, "review_note": "Approved reopen request"},
        headers=headers_admin
    )

    # Try to execute - should return 422
    resp = client.post(
        f"/api/v1/workflow/change-requests/{cr_id}/execute?expected_row_version=2",
        headers=headers_admin
    )
    assert resp.status_code == 422
    assert "Reversal execution is not supported" in resp.json()["detail"]
