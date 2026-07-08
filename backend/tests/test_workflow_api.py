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
    OrganizationProfile, OrganizationStatus, User, UserStatus, Role, UserRole,
    WorkflowDefinition, WorkflowDefinitionStatus,
    WorkflowInstance, WorkflowInstanceStatus,
    WorkflowTransition,
    WorkflowTask, WorkflowTaskStatus, WorkflowTaskPriority,
    ReviewDecision, ReviewDecisionChoice,
    ApprovalGate, ApprovalGateStatus,
    ValidationRule, ValidationRuleCategory,
    ValidationIssue, ValidationIssueSeverity, ValidationIssueStatus
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
            "workflow:instance:manage",
            "workflow:task:assign",
            "workflow:task:complete",
            "workflow:decision:create",
            "workflow:override_gate"
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

    return {
        "admin_id": str(user_admin.id),
        "viewer_id": str(user_viewer.id),
        "org_id": org.id
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
    assert "/api/v1/workflow/instances" in openapi["paths"]
    assert "/api/v1/workflow/tasks" in openapi["paths"]


def test_workflow_instances_endpoints(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    wf_def = WorkflowDefinition(
        code="PROJECT_FLOW",
        name="Standard Project Workflow",
        status=WorkflowDefinitionStatus.ACTIVE
    )
    db_session.add(wf_def)
    db_session.commit()

    # 1. POST /api/v1/workflow/instances (Create with RBAC)
    target_id = uuid.uuid4()
    resp = client.post(
        "/api/v1/workflow/instances",
        json={
            "workflow_definition_id": str(wf_def.id),
            "target_type": "project",
            "target_id": str(target_id),
            "current_state": "draft"
        },
        headers=headers_admin
    )
    assert resp.status_code == 201
    instance_id = resp.json()["id"]

    # Deny by default check
    resp_unauth = client.post(
        "/api/v1/workflow/instances",
        json={
            "workflow_definition_id": str(wf_def.id),
            "target_type": "project",
            "target_id": str(target_id),
            "current_state": "draft"
        }
    )
    assert resp_unauth.status_code == 401

    # Viewer mutation block
    resp_view = client.post(
        "/api/v1/workflow/instances",
        json={
            "workflow_definition_id": str(wf_def.id),
            "target_type": "project",
            "target_id": str(target_id),
            "current_state": "draft"
        },
        headers=headers_viewer
    )
    assert resp_view.status_code == 403

    # 2. GET /api/v1/workflow/instances/{instance_id}
    resp = client.get(f"/api/v1/workflow/instances/{instance_id}", headers=headers_viewer)
    assert resp.status_code == 200
    assert resp.json()["current_state"] == "draft"


def test_workflow_transitions(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    wf_def = WorkflowDefinition(
        code="PROJECT_FLOW",
        name="Standard Project Workflow",
        status=WorkflowDefinitionStatus.ACTIVE
    )
    db_session.add(wf_def)
    db_session.commit()

    # Create transition path: draft -> under_review
    trans = WorkflowTransition(
        workflow_definition_id=wf_def.id,
        from_state="draft",
        to_state="under_review",
        command_name="StartImport",
        is_active=True
    )
    db_session.add(trans)

    target_id = uuid.uuid4()
    instance = WorkflowInstance(
        workflow_definition_id=wf_def.id,
        target_type="project",
        target_id=target_id,
        current_state="draft",
        status=WorkflowInstanceStatus.ACTIVE
    )
    db_session.add(instance)
    db_session.commit()

    # 1. Valid command updates state
    resp = client.post(
        f"/api/v1/workflow/instances/{instance.id}/transition",
        json={
            "command_name": "StartImport",
            "expected_row_version": 1
        },
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["current_state"] == "under_review"

    # 2. Stale row version returns 409
    resp = client.post(
        f"/api/v1/workflow/instances/{instance.id}/transition",
        json={
            "command_name": "StartImport",
            "expected_row_version": 1  # Should be 2 now
        },
        headers=headers_admin
    )
    assert resp.status_code == 409

    # 3. Invalid command returns 422
    resp = client.post(
        f"/api/v1/workflow/instances/{instance.id}/transition",
        json={
            "command_name": "InvalidCommand",
            "expected_row_version": 2
        },
        headers=headers_admin
    )
    assert resp.status_code == 422


def test_transition_blocking_by_validation_rules(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}

    wf_def = WorkflowDefinition(
        code="PROJECT_FLOW",
        name="Standard Project Workflow",
        status=WorkflowDefinitionStatus.ACTIVE
    )
    db_session.add(wf_def)
    db_session.commit()

    trans = WorkflowTransition(
        workflow_definition_id=wf_def.id,
        from_state="draft",
        to_state="under_review",
        command_name="StartImport",
        is_active=True
    )
    db_session.add(trans)

    target_id = uuid.uuid4()
    instance = WorkflowInstance(
        workflow_definition_id=wf_def.id,
        target_type="project",
        target_id=target_id,
        current_state="draft",
        status=WorkflowInstanceStatus.ACTIVE
    )
    db_session.add(instance)
    db_session.commit()

    rule = ValidationRule(
        rule_code="VAL_001",
        category=ValidationRuleCategory.QUOTE,
        name="Limit Check"
    )
    db_session.add(rule)
    db_session.commit()

    # Open blocking issue
    issue = ValidationIssue(
        validation_rule_id=rule.id,
        target_type="project",
        target_id=target_id,
        severity=ValidationIssueSeverity.BLOCKING,
        status=ValidationIssueStatus.OPEN,
        issue_message="Spread violation"
    )
    db_session.add(issue)
    db_session.commit()

    # 1. Direct transition fails due to blocking issue
    resp = client.post(
        f"/api/v1/workflow/instances/{instance.id}/transition",
        json={
            "command_name": "StartImport",
            "expected_row_version": 1
        },
        headers=headers_admin
    )
    assert resp.status_code == 400
    assert "blocked by open validation issues" in resp.json()["detail"]

    # 2. Transition succeeds if override reason is provided
    resp = client.post(
        f"/api/v1/workflow/instances/{instance.id}/transition",
        json={
            "command_name": "StartImport",
            "expected_row_version": 1,
            "override_reason": "Verified manually"
        },
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["current_state"] == "under_review"


def test_workflow_tasks_endpoints(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    wf_def = WorkflowDefinition(
        code="PROJECT_FLOW",
        name="Standard Project Workflow",
        status=WorkflowDefinitionStatus.ACTIVE
    )
    db_session.add(wf_def)
    db_session.commit()

    instance = WorkflowInstance(
        workflow_definition_id=wf_def.id,
        target_type="project",
        target_id=uuid.uuid4(),
        current_state="draft"
    )
    db_session.add(instance)
    db_session.commit()

    task = WorkflowTask(
        workflow_instance_id=instance.id,
        task_type="review",
        title="Check catalog identity",
        status=WorkflowTaskStatus.OPEN,
        priority=WorkflowTaskPriority.HIGH
    )
    db_session.add(task)
    db_session.commit()

    # 1. GET /api/v1/workflow/tasks
    resp = client.get("/api/v1/workflow/tasks", headers=headers_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 2. GET /api/v1/workflow/tasks/{task_id}
    resp = client.get(f"/api/v1/workflow/tasks/{task.id}", headers=headers_viewer)
    assert resp.status_code == 200

    # 3. PATCH /api/v1/workflow/tasks/{task_id}
    resp = client.patch(
        f"/api/v1/workflow/tasks/{task.id}",
        json={"title": "Updated checklist title", "expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 200

    # 4. POST /api/v1/workflow/tasks/{task_id}/complete
    resp = client.post(
        f"/api/v1/workflow/tasks/{task.id}/complete?expected_row_version=2",
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


def test_review_decisions_append_only(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    # 1. POST /api/v1/workflow/decisions (Create Review Decision)
    target_id = uuid.uuid4()
    resp = client.post(
        "/api/v1/workflow/decisions",
        json={
            "target_type": "project",
            "target_id": str(target_id),
            "decision": "approve",
            "reason": "All checks approved."
        },
        headers=headers_admin
    )
    assert resp.status_code == 201
    decision_id = resp.json()["id"]

    # 2. GET /api/v1/workflow/decisions/{decision_id}
    resp = client.get(f"/api/v1/workflow/decisions/{decision_id}", headers=headers_viewer)
    assert resp.status_code == 200

    # 3. Confirm that no PUT/PATCH/DELETE endpoints exist for decisions
    resp = client.patch(f"/api/v1/workflow/decisions/{decision_id}", json={"reason": "changed"}, headers=headers_admin)
    assert resp.status_code == 405  # Method Not Allowed

    resp = client.delete(f"/api/v1/workflow/decisions/{decision_id}", headers=headers_admin)
    assert resp.status_code == 405


def test_validation_endpoints(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    rule = ValidationRule(
        rule_code="VAL_002",
        category=ValidationRuleCategory.TAXONOMY,
        name="Category Check"
    )
    db_session.add(rule)
    db_session.commit()

    issue = ValidationIssue(
        validation_rule_id=rule.id,
        target_type="project",
        target_id=uuid.uuid4(),
        severity=ValidationIssueSeverity.BLOCKING,
        status=ValidationIssueStatus.OPEN,
        issue_message="Invalid category node"
    )
    db_session.add(issue)
    db_session.commit()

    # 1. GET /api/v1/workflow/validation-rules
    resp = client.get("/api/v1/workflow/validation-rules", headers=headers_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 2. GET /api/v1/workflow/validation-issues
    resp = client.get("/api/v1/workflow/validation-issues", headers=headers_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 3. GET /api/v1/workflow/validation-issues/{issue_id}
    resp = client.get(f"/api/v1/workflow/validation-issues/{issue.id}", headers=headers_viewer)
    assert resp.status_code == 200

    # 4. PATCH /api/v1/workflow/validation-issues/{issue_id}
    resp = client.patch(
        f"/api/v1/workflow/validation-issues/{issue.id}",
        json={"issue_message": "Updated spread error", "expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 200

    # 5. POST /api/v1/workflow/validation-issues/{issue_id}/resolve
    resp = client.post(
        f"/api/v1/workflow/validation-issues/{issue.id}/resolve",
        json={"resolution_notes": "Manually corrected", "expected_row_version": 2},
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


def test_gates_and_logs(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    gate = ApprovalGate(
        gate_code="G1",
        target_type="project",
        target_id=uuid.uuid4(),
        gate_status=ApprovalGateStatus.PASS,
        blocking_issue_count=0
    )
    db_session.add(gate)
    db_session.commit()

    # 1. GET /api/v1/workflow/approval-gates
    resp = client.get("/api/v1/workflow/approval-gates", headers=headers_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 2. GET /api/v1/workflow/action-logs
    resp = client.get("/api/v1/workflow/action-logs", headers=headers_viewer)
    assert resp.status_code == 200


def test_forbidden_apis_exist(client: TestClient) -> None:
    # Root validation issue resolve endpoint (without /workflow) is not configured and must return 404
    some_id = str(uuid.uuid4())
    resp = client.post(f"/api/v1/validation-issues/{some_id}/resolve")
    assert resp.status_code == 404
