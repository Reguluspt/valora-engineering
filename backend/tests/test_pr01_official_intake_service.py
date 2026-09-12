"""Focused proof for the PR-01 durable official-intake command foundation."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
import app.modules.excel_import.models  # noqa: F401
import app.modules.project_master_data.application.official_intake_service as service
from app.modules.project_master_data.application.official_intake_service import (
    commit_project_official_intake,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    Customer,
    CustomerStatus,
    OrganizationProfile,
    OrganizationStatus,
    PreliminaryResultArtifact,
    Project,
    ProjectAssetLine,
    ProjectOfficialIntakeCommit,
    ProjectWorkflowStatus,
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


OFFICIAL_INTAKE_PERMISSION = "project:official_intake:commit"


@pytest.fixture
def intake_db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _seed(
    intake_db: Session,
    *,
    suffix: str = "a",
    grant_permission: bool = True,
) -> dict:
    org = OrganizationProfile(
        legal_name=f"Official Intake Org {suffix}",
        organization_slug=f"official-intake-{suffix}-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE,
    )
    intake_db.add(org)
    intake_db.flush()
    actor = User(
        organization_id=org.id,
        email=f"official-intake-{suffix}-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Official Intake Human",
        status=UserStatus.ACTIVE,
    )
    intake_db.add(actor)
    intake_db.flush()
    role = Role(
        code=f"official-intake-{suffix}-{uuid.uuid4().hex[:8]}",
        display_name="Official Intake Fixture",
        permissions=[OFFICIAL_INTAKE_PERMISSION] if grant_permission else [],
    )
    intake_db.add(role)
    intake_db.flush()
    user_role = UserRole(user_id=actor.id, role_id=role.id, is_active=True)
    intake_db.add(user_role)
    customer = Customer(
        organization_id=org.id,
        legal_name=f"Official Intake Customer {suffix}",
        status=CustomerStatus.ACTIVE,
        created_by=actor.id,
    )
    intake_db.add(customer)
    intake_db.flush()
    project = Project(
        organization_id=org.id,
        customer_id=customer.id,
        code=f"OI-{suffix}-{uuid.uuid4().hex[:6]}",
        name=f"Official Intake Project {suffix}",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=actor.id,
    )
    intake_db.add(project)
    intake_db.flush()
    artifact = PreliminaryResultArtifact(
        organization_id=org.id,
        customer_id=customer.id,
        project_id=project.id,
        version=1,
        original_filename="ket-qua-so-bo-v1.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=1024,
        content_checksum_sha256="a" * 64,
        storage_object_key=f"preliminary-results/{project.id}/v1.xlsx",
        source_snapshot_sha256="b" * 64,
        lineage_manifest={"contract": "preliminary-result-v1", "source_refs": ["fixture"]},
        created_by_user_id=actor.id,
    )
    intake_db.add(artifact)
    intake_db.commit()
    return {
        "org": org,
        "actor": actor,
        "role": role,
        "user_role": user_role,
        "customer": customer,
        "project": project,
        "artifact": artifact,
    }


def _commit(intake_db: Session, seeded: dict, **overrides):
    values = {
        "actor": seeded["actor"],
        "org_id": seeded["org"].id,
        "project_id": seeded["project"].id,
        "preliminary_result_artifact_id": seeded["artifact"].id,
        "expected_project_version": seeded["project"].row_version,
        "expected_preliminary_result_version": seeded["artifact"].version,
        "idempotency_key": "official-intake-command-1",
        "confirmed": True,
        "correlation_id": "corr-official-intake-1",
    }
    values.update(overrides)
    return commit_project_official_intake(intake_db, **values)


def _assert_error(exc: pytest.ExceptionInfo[HTTPException], status: int, code: str) -> None:
    assert exc.value.status_code == status
    assert exc.value.detail["error_code"] == code


def test_commit_persists_one_fact_and_atomic_audit_without_legacy_status_change(
    intake_db: Session,
) -> None:
    seeded = _seed(intake_db)

    committed = _commit(intake_db, seeded)

    assert committed.project_id == seeded["project"].id
    assert committed.preliminary_result_artifact_id == seeded["artifact"].id
    assert committed.preliminary_result_version == 1
    assert committed.preliminary_result_sha256 == "a" * 64
    assert committed.source_snapshot_sha256 == "b" * 64
    assert committed.project_version_before == 1
    assert committed.committed_by_user_id == seeded["actor"].id
    assert intake_db.get(Project, seeded["project"].id).status == ProjectWorkflowStatus.DRAFT

    audits = (
        intake_db.query(AuditEvent)
        .filter(AuditEvent.event_name == "ProjectOfficialIntakeCommitted")
        .all()
    )
    assert len(audits) == 1
    assert audits[0].entity_id == committed.id
    assert audits[0].command_name == "CommitProjectOfficialIntake"


def test_same_idempotency_key_and_request_replays_without_new_fact_or_audit(
    intake_db: Session,
) -> None:
    seeded = _seed(intake_db)
    first = _commit(intake_db, seeded)

    replay = _commit(intake_db, seeded)

    assert replay.id == first.id
    assert intake_db.query(ProjectOfficialIntakeCommit).count() == 1
    assert (
        intake_db.query(AuditEvent)
        .filter(AuditEvent.event_name == "ProjectOfficialIntakeCommitted")
        .count()
        == 1
    )


def test_missing_permission_denies_without_fact_or_success_audit(intake_db: Session) -> None:
    seeded = _seed(intake_db, grant_permission=False)

    with pytest.raises(HTTPException) as exc:
        _commit(intake_db, seeded)

    _assert_error(exc, 403, "official_intake_forbidden")
    assert intake_db.query(ProjectOfficialIntakeCommit).count() == 0
    assert (
        intake_db.query(AuditEvent)
        .filter(AuditEvent.event_name == "ProjectOfficialIntakeCommitted")
        .count()
        == 0
    )


@pytest.mark.parametrize("binding_state", ["inactive", "revoked"])
def test_inactive_or_revoked_role_binding_does_not_grant_permission(
    intake_db: Session,
    binding_state: str,
) -> None:
    seeded = _seed(intake_db)
    if binding_state == "inactive":
        seeded["user_role"].is_active = False
    else:
        seeded["user_role"].revoked_at = datetime.now(timezone.utc)
    intake_db.commit()

    with pytest.raises(HTTPException) as exc:
        _commit(intake_db, seeded)

    _assert_error(exc, 403, "official_intake_forbidden")
    assert intake_db.query(ProjectOfficialIntakeCommit).count() == 0
    assert intake_db.query(AuditEvent).count() == 0


def test_permission_is_rechecked_before_idempotent_replay(intake_db: Session) -> None:
    seeded = _seed(intake_db)
    committed = _commit(intake_db, seeded)
    seeded["user_role"].revoked_at = datetime.now(timezone.utc)
    intake_db.commit()

    with pytest.raises(HTTPException) as exc:
        _commit(intake_db, seeded)

    _assert_error(exc, 403, "official_intake_forbidden")
    assert intake_db.query(ProjectOfficialIntakeCommit).one().id == committed.id
    assert (
        intake_db.query(AuditEvent)
        .filter(AuditEvent.event_name == "ProjectOfficialIntakeCommitted")
        .count()
        == 1
    )


def test_permission_is_organization_scoped_without_project_acl(intake_db: Session) -> None:
    seeded = _seed(intake_db)
    second_actor = User(
        organization_id=seeded["org"].id,
        email=f"official-intake-peer-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Official Intake Peer",
        status=UserStatus.ACTIVE,
    )
    intake_db.add(second_actor)
    intake_db.flush()
    intake_db.add(
        UserRole(
            user_id=second_actor.id,
            role_id=seeded["role"].id,
            is_active=True,
        )
    )
    intake_db.commit()

    committed = _commit(intake_db, seeded, actor=second_actor)

    assert committed.committed_by_user_id == second_actor.id


def test_reused_idempotency_key_with_different_request_is_rejected(intake_db: Session) -> None:
    seeded = _seed(intake_db)
    _commit(intake_db, seeded)

    with pytest.raises(HTTPException) as exc:
        _commit(intake_db, seeded, expected_preliminary_result_version=2)

    _assert_error(exc, 409, "idempotency_key_reused")
    assert intake_db.query(ProjectOfficialIntakeCommit).count() == 1


def test_second_command_for_committed_project_is_rejected(intake_db: Session) -> None:
    seeded = _seed(intake_db)
    _commit(intake_db, seeded)

    with pytest.raises(HTTPException) as exc:
        _commit(intake_db, seeded, idempotency_key="official-intake-command-2")

    _assert_error(exc, 409, "official_intake_already_committed")
    assert intake_db.query(ProjectOfficialIntakeCommit).count() == 1


@pytest.mark.parametrize(
    ("overrides", "status", "code"),
    [
        ({"confirmed": False}, 400, "official_intake_confirmation_required"),
        ({"expected_project_version": 2}, 409, "project_version_conflict"),
        (
            {"expected_preliminary_result_version": 2},
            409,
            "preliminary_result_version_conflict",
        ),
    ],
)
def test_confirmation_and_versions_fail_without_persistence(
    intake_db: Session, overrides: dict, status: int, code: str
) -> None:
    seeded = _seed(intake_db)

    with pytest.raises(HTTPException) as exc:
        _commit(intake_db, seeded, **overrides)

    _assert_error(exc, status, code)
    assert intake_db.query(ProjectOfficialIntakeCommit).count() == 0
    assert intake_db.query(AuditEvent).count() == 0


def test_cross_tenant_project_is_safe_not_found(intake_db: Session) -> None:
    seeded = _seed(intake_db, suffix="owner")
    other = _seed(intake_db, suffix="other")

    with pytest.raises(HTTPException) as exc:
        _commit(
            intake_db,
            seeded,
            actor=other["actor"],
            org_id=other["org"].id,
        )

    _assert_error(exc, 404, "project_not_found")
    assert intake_db.query(ProjectOfficialIntakeCommit).count() == 0


@pytest.mark.parametrize("inactive_target", ["actor", "organization"])
def test_inactive_actor_or_organization_is_forbidden(
    intake_db: Session, inactive_target: str
) -> None:
    seeded = _seed(intake_db)
    if inactive_target == "actor":
        seeded["actor"].status = UserStatus.INACTIVE
    else:
        seeded["org"].status = OrganizationStatus.INACTIVE
    intake_db.commit()

    with pytest.raises(HTTPException) as exc:
        _commit(intake_db, seeded)

    _assert_error(exc, 403, "official_intake_forbidden")
    assert intake_db.query(ProjectOfficialIntakeCommit).count() == 0


def _add_asset_line(intake_db: Session, seeded: dict) -> ProjectAssetLine:
    line = ProjectAssetLine(
        project_id=seeded["project"].id,
        asset_name=f"Official intake asset {uuid.uuid4().hex[:6]}",
        quantity=1,
    )
    intake_db.add(line)
    intake_db.commit()
    return line


def _add_issue(
    intake_db: Session,
    seeded: dict,
    severity: ValidationIssueSeverity,
    *,
    status: ValidationIssueStatus = ValidationIssueStatus.OPEN,
    target_type: str = "project",
    target_id: uuid.UUID | None = None,
    rule_is_blocking: bool | None = None,
    rule_is_active: bool = True,
    rule_category: ValidationRuleCategory = ValidationRuleCategory.EVIDENCE,
) -> None:
    rule = ValidationRule(
        rule_code=f"OI-{severity.value}-{uuid.uuid4().hex[:6]}",
        category=rule_category,
        name="Official intake fixture rule",
        is_blocking=(
            severity == ValidationIssueSeverity.BLOCKING
            if rule_is_blocking is None
            else rule_is_blocking
        ),
        is_active=rule_is_active,
    )
    intake_db.add(rule)
    intake_db.flush()
    intake_db.add(
        ValidationIssue(
            validation_rule_id=rule.id,
            target_type=target_type,
            target_id=target_id or seeded["project"].id,
            severity=severity,
            status=status,
            issue_message="Fixture issue",
        )
    )
    intake_db.commit()


@pytest.mark.parametrize(
    ("target_type", "target_kind"),
    [
        ("project", "project"),
        ("Project", "project"),
        ("project_asset_line", "line"),
        ("ProjectAssetLine", "line"),
    ],
)
def test_exact_v1_target_spellings_block_open_blocking_issues(
    intake_db: Session,
    target_type: str,
    target_kind: str,
) -> None:
    blocked = _seed(intake_db, suffix=f"blocked-{target_kind}")
    target_id = (
        blocked["project"].id
        if target_kind == "project"
        else _add_asset_line(intake_db, blocked).id
    )
    _add_issue(
        intake_db,
        blocked,
        ValidationIssueSeverity.BLOCKING,
        target_type=target_type,
        target_id=target_id,
    )

    with pytest.raises(HTTPException) as exc:
        _commit(intake_db, blocked)
    _assert_error(exc, 409, "official_intake_blocked")
    assert intake_db.query(ProjectOfficialIntakeCommit).count() == 0
    assert intake_db.query(AuditEvent).count() == 0


@pytest.mark.parametrize(
    ("severity", "status", "target_type"),
    [
        (ValidationIssueSeverity.WARNING, ValidationIssueStatus.OPEN, "Project"),
        (ValidationIssueSeverity.WARNING, ValidationIssueStatus.OPEN, "ProjectAssetLine"),
        (ValidationIssueSeverity.BLOCKING, ValidationIssueStatus.RESOLVED, "project"),
        (ValidationIssueSeverity.BLOCKING, ValidationIssueStatus.IGNORED, "project"),
    ],
)
def test_warning_resolved_and_ignored_issues_do_not_block(
    intake_db: Session,
    severity: ValidationIssueSeverity,
    status: ValidationIssueStatus,
    target_type: str,
) -> None:
    seeded = _seed(intake_db, suffix=f"allowed-{status.value}")
    target_id = (
        _add_asset_line(intake_db, seeded).id
        if target_type == "ProjectAssetLine"
        else seeded["project"].id
    )
    _add_issue(
        intake_db,
        seeded,
        severity,
        status=status,
        target_type=target_type,
        target_id=target_id,
    )

    committed = _commit(intake_db, seeded)

    assert committed.project_id == seeded["project"].id


@pytest.mark.parametrize(
    ("rule_is_blocking", "rule_is_active", "rule_category"),
    [
        (False, True, ValidationRuleCategory.QUOTE),
        (True, False, ValidationRuleCategory.TECHNICAL_SPEC),
    ],
)
def test_issue_severity_and_status_are_the_only_v1_rule_filters(
    intake_db: Session,
    rule_is_blocking: bool,
    rule_is_active: bool,
    rule_category: ValidationRuleCategory,
) -> None:
    seeded = _seed(intake_db, suffix="rule-flags")
    _add_issue(
        intake_db,
        seeded,
        ValidationIssueSeverity.BLOCKING,
        rule_is_blocking=rule_is_blocking,
        rule_is_active=rule_is_active,
        rule_category=rule_category,
    )

    with pytest.raises(HTTPException) as exc:
        _commit(intake_db, seeded)

    _assert_error(exc, 409, "official_intake_blocked")


def test_unknown_and_other_project_targets_do_not_block(intake_db: Session) -> None:
    seeded = _seed(intake_db, suffix="target-scope")
    other = _seed(intake_db, suffix="same-tenant-other")
    _add_issue(
        intake_db,
        seeded,
        ValidationIssueSeverity.BLOCKING,
        target_type="future_target",
    )
    _add_issue(
        intake_db,
        seeded,
        ValidationIssueSeverity.BLOCKING,
        target_type="Project",
        target_id=other["project"].id,
    )
    other_line = _add_asset_line(intake_db, other)
    _add_issue(
        intake_db,
        seeded,
        ValidationIssueSeverity.BLOCKING,
        target_type="ProjectAssetLine",
        target_id=other_line.id,
    )

    committed = _commit(intake_db, seeded)

    assert committed.project_id == seeded["project"].id


def test_cross_tenant_project_and_line_issues_do_not_block(intake_db: Session) -> None:
    seeded = _seed(intake_db, suffix="tenant-owner")
    other_tenant = _seed(intake_db, suffix="tenant-other")
    other_line = _add_asset_line(intake_db, other_tenant)
    _add_issue(
        intake_db,
        seeded,
        ValidationIssueSeverity.BLOCKING,
        target_type="project",
        target_id=other_tenant["project"].id,
    )
    _add_issue(
        intake_db,
        seeded,
        ValidationIssueSeverity.BLOCKING,
        target_type="project_asset_line",
        target_id=other_line.id,
    )

    committed = _commit(intake_db, seeded)

    assert committed.project_id == seeded["project"].id


def test_empty_lineage_is_rejected(intake_db: Session) -> None:
    seeded = _seed(intake_db)
    seeded["artifact"].lineage_manifest = {}
    intake_db.commit()

    with pytest.raises(HTTPException) as exc:
        _commit(intake_db, seeded)

    _assert_error(exc, 409, "preliminary_result_lineage_incomplete")
    assert intake_db.query(ProjectOfficialIntakeCommit).count() == 0


def test_audit_failure_rolls_back_fact(intake_db: Session, monkeypatch) -> None:
    seeded = _seed(intake_db)

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(service, "log_audit_event", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        _commit(intake_db, seeded)

    assert intake_db.query(ProjectOfficialIntakeCommit).count() == 0
    assert intake_db.query(AuditEvent).count() == 0
