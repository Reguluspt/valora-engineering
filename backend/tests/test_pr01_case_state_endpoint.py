"""HTTP contract tests for the PR-01 Global Case State read endpoint."""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.modules.project_master_data.application.case_state_projection import ProjectionError
from app.modules.project_master_data.models import (
    AuditEvent,
    Customer,
    CustomerStatus,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    Role,
    User,
    UserRole,
    UserStatus,
    ValidationIssue,
    ValidationIssueSeverity,
    ValidationIssueStatus,
    ValidationRule,
    ValidationRuleCategory,
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _seed_project(
    db: Session,
    *,
    permissions: list[str] | None = None,
    user_status: UserStatus = UserStatus.ACTIVE,
) -> tuple[OrganizationProfile, User, Project]:
    suffix = uuid.uuid4().hex[:8]
    organization = OrganizationProfile(
        legal_name=f"Case State Org {suffix}",
        organization_slug=f"case-state-{suffix}",
        status=OrganizationStatus.ACTIVE,
    )
    db.add(organization)
    db.flush()
    user = User(
        organization_id=organization.id,
        email=f"case-state-{suffix}@example.com",
        full_name="Case State Reader",
        status=user_status,
    )
    db.add(user)
    db.flush()
    role = Role(
        code=f"case-state-{suffix}",
        display_name="Case State Reader",
        permissions=permissions if permissions is not None else ["project:read"],
    )
    db.add(role)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))
    customer = Customer(
        organization_id=organization.id,
        legal_name=f"Case State Customer {suffix}",
        status=CustomerStatus.ACTIVE,
        created_by=user.id,
    )
    db.add(customer)
    db.flush()
    project = Project(
        organization_id=organization.id,
        customer_id=customer.id,
        code=f"CASE-{suffix}",
        name="Case State Project",
        created_by=user.id,
    )
    db.add(project)
    db.commit()
    return organization, user, project


def test_case_state_endpoint_returns_bounded_public_projection(
    client: TestClient, db_session: Session
) -> None:
    _, user, project = _seed_project(db_session)
    audit_count = db_session.query(AuditEvent).count()

    response = client.get(
        f"/api/v1/projects/{project.id}/case-state",
        headers={"X-User-Id": str(user.id)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["case_version"]) == 64
    assert payload["current_stage"] == "PRELIMINARY_REQUEST"
    assert payload["next_action"] == {
        "kind": "PENDING",
        "stage": "PRELIMINARY_REQUEST",
        "semantic_route_key": "preliminary_request_pending",
        "validation_issue_id": None,
    }
    assert len(payload["stages"]) == 16
    assert payload["stages"][0] == {
        "stage": "PRELIMINARY_REQUEST",
        "result": "INCOMPLETE",
        "provider_key": "preliminary_request_v1",
    }
    assert all(stage["result"] == "NOT_AVAILABLE" for stage in payload["stages"][4:])
    assert payload["blockers"] == []
    assert payload["warnings"] == []
    assert payload["stale"] == []
    assert len(payload["capabilities"]) == 16
    assert "facts" not in payload
    assert all("fact_token" not in stage for stage in payload["stages"])
    assert db_session.query(AuditEvent).count() == audit_count
    assert not db_session.new
    assert not db_session.dirty
    assert not db_session.deleted


def test_case_state_endpoint_auth_and_safe_not_found(
    client: TestClient, db_session: Session
) -> None:
    organization, user, project = _seed_project(db_session)
    _, foreign_user, foreign_project = _seed_project(db_session)
    _, no_permission_user, _ = _seed_project(db_session, permissions=[])
    _, inactive_user, _ = _seed_project(db_session, user_status=UserStatus.INACTIVE)

    assert client.get(f"/api/v1/projects/{project.id}/case-state").status_code == 401

    forbidden = client.get(
        f"/api/v1/projects/{project.id}/case-state",
        headers={"X-User-Id": str(no_permission_user.id)},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["error_code"] == "case_state_forbidden"

    inactive = client.get(
        f"/api/v1/projects/{project.id}/case-state",
        headers={"X-User-Id": str(inactive_user.id)},
    )
    assert inactive.status_code == 403
    assert inactive.json()["detail"]["error_code"] == "case_state_forbidden"

    headers = {"X-User-Id": str(user.id)}
    missing = client.get(f"/api/v1/projects/{uuid.uuid4()}/case-state", headers=headers)
    cross_tenant = client.get(
        f"/api/v1/projects/{foreign_project.id}/case-state", headers=headers
    )
    assert missing.status_code == cross_tenant.status_code == 404
    assert missing.json()["detail"] == cross_tenant.json()["detail"]
    assert missing.json()["detail"]["error_code"] == "project_not_found"
    assert organization.id != foreign_user.organization_id


def test_case_state_endpoint_serializes_blocker_and_warning(
    client: TestClient, db_session: Session
) -> None:
    _, user, project = _seed_project(db_session)
    blocking_rule = ValidationRule(
        rule_code=f"CASE-B-{uuid.uuid4().hex[:8]}",
        category=ValidationRuleCategory.EVIDENCE,
        name="Case state blocker",
        is_blocking=True,
        is_active=True,
    )
    warning_rule = ValidationRule(
        rule_code=f"CASE-W-{uuid.uuid4().hex[:8]}",
        category=ValidationRuleCategory.EVIDENCE,
        name="Case state warning",
        is_blocking=False,
        is_active=True,
    )
    db_session.add_all([blocking_rule, warning_rule])
    db_session.flush()
    blocker = ValidationIssue(
        validation_rule_id=blocking_rule.id,
        target_type="project",
        target_id=project.id,
        severity=ValidationIssueSeverity.BLOCKING,
        status=ValidationIssueStatus.OPEN,
        issue_message="Blocking issue",
    )
    warning = ValidationIssue(
        validation_rule_id=warning_rule.id,
        target_type="project",
        target_id=project.id,
        severity=ValidationIssueSeverity.WARNING,
        status=ValidationIssueStatus.OPEN,
        issue_message="Warning issue",
    )
    db_session.add_all([blocker, warning])
    db_session.commit()

    response = client.get(
        f"/api/v1/projects/{project.id}/case-state",
        headers={"X-User-Id": str(user.id)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_action"] == {
        "kind": "BLOCKER",
        "stage": "OFFICIAL_INTAKE",
        "semantic_route_key": None,
        "validation_issue_id": str(blocker.id),
    }
    assert payload["stages"][3]["result"] == "BLOCKED"
    assert payload["blockers"] == [
        {
            "id": str(blocker.id),
            "target_type": "project",
            "target_id": str(project.id),
            "severity": "blocking",
            "status": "open",
            "row_version": blocker.row_version,
        }
    ]
    assert payload["warnings"] == [
        {
            "id": str(warning.id),
            "target_type": "project",
            "target_id": str(project.id),
            "severity": "warning",
            "status": "open",
            "row_version": warning.row_version,
        }
    ]


def test_case_state_endpoint_maps_provider_failure_to_typed_safe_error(
    client: TestClient, db_session: Session
) -> None:
    _, user, project = _seed_project(db_session)
    with patch(
        "app.api.projects.get_case_state_projection",
        side_effect=ProjectionError("sensitive internal detail"),
    ):
        response = client.get(
            f"/api/v1/projects/{project.id}/case-state",
            headers={"X-User-Id": str(user.id)},
        )

    assert response.status_code == 500
    assert response.json()["detail"] == {
        "error_code": "case_state_projection_failed",
        "detail": "Không thể tải trạng thái hồ sơ.",
    }
    assert "sensitive internal detail" not in response.text
