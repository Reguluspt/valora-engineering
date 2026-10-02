"""Focused mutation and tenant regression for the ADR 0048 writer prerequisites."""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, update
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import projects, workflow
from app.db import Base
from app.modules.project_master_data.commands.commit_asset_line_draft import (
    execute_commit_asset_line_draft,
)
from app.modules.project_master_data.models import (
    AuditEvent, InlineEditDraft, OrganizationProfile, Project, ProjectAssetLine,
    ProjectOfficialIntakeCommit, Role, User, UserRole,
    ValidationIssue, ValidationRule, WorkbenchSession,
)
from app.modules.project_master_data.schemas import (
    ProjectAssetLineCreate, ProjectAssetLineUpdate,
)
from app.modules.project_master_data.workflow_schemas import (
    ValidationIssueResolveRequest, ValidationIssueUpdate,
)
from app.modules.project_master_data.workbench_schemas import (
    ProjectAssetImportBatchApplyRequest, ProjectAssetImportBatchValidateRequest,
)


@pytest.fixture
def writer_db():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org = OrganizationProfile(legal_name="Writer test", organization_slug=uuid.uuid4().hex)
        db.add(org)
        db.flush()
        actor = User(organization_id=org.id, email=f"{uuid.uuid4().hex}@example.test",
                     full_name="Writer")
        db.add(actor)
        db.flush()
        role = Role(code=uuid.uuid4().hex, display_name="Writer", permissions=["workbench:edit"])
        db.add(role)
        db.flush()
        db.add(UserRole(user_id=actor.id, role_id=role.id, is_active=True))
        project = Project(organization_id=org.id, code="GUARD", name="Writer project",
                          created_by=actor.id)
        db.add(project)
        db.commit()
        yield db, actor, project
    engine.dispose()


def _intake(db, actor, project):
    fact = ProjectOfficialIntakeCommit(
        organization_id=actor.organization_id, customer_id=uuid.uuid4(), project_id=project.id,
        preliminary_result_artifact_id=uuid.uuid4(), preliminary_result_version=1,
        preliminary_result_sha256="1" * 64, source_snapshot_sha256="2" * 64,
        project_version_before=1, idempotency_key=uuid.uuid4().hex,
        request_digest_sha256="3" * 64, committed_by_user_id=actor.id,
    )
    db.add(fact)
    db.commit()


def _locked_entities(db):
    observed = []

    @event.listens_for(db, "do_orm_execute")
    def observe(execution):
        stmt = execution.statement
        if getattr(stmt, "_for_update_arg", None) is not None:
            observed.append(stmt.column_descriptions[0]["entity"])

    return observed


@pytest.mark.parametrize("existing_line", [False, True])
def test_manual_creation_closed_after_intake_with_zero_writes(writer_db, existing_line):
    db, actor, project = writer_db
    _intake(db, actor, project)
    if existing_line:
        db.add(ProjectAssetLine(project_id=project.id, asset_name="Existing authority", quantity=1))
        db.commit()
    before_lines = db.query(ProjectAssetLine).count()
    before_audits = db.query(AuditEvent).count()
    with pytest.raises(HTTPException) as denied:
        projects.create_project_asset_line(
            project.id, ProjectAssetLineCreate(asset_name="Manual bypass"), db, actor,
        )
    assert denied.value.status_code == 409
    assert denied.value.detail["error_code"] == "asset_line_membership_closed"
    assert db.query(ProjectAssetLine).count() == before_lines
    assert db.query(AuditEvent).count() == before_audits


def test_pre_intake_manual_creation_keeps_existing_behavior(writer_db):
    db, actor, project = writer_db
    locks = _locked_entities(db)
    line = projects.create_project_asset_line(
        project.id, ProjectAssetLineCreate(asset_name="Allowed legacy line"), db, actor,
    )
    assert line.asset_name == "Allowed legacy line"
    assert db.query(ProjectAssetLine).count() == 1
    assert db.query(AuditEvent).count() == 1
    assert locks[0] is Project


@pytest.mark.parametrize("operation", [projects.archive_project, projects.cancel_project])
def test_project_status_writer_locks_project(writer_db, operation):
    db, actor, project = writer_db
    locks = _locked_entities(db)
    operation(project.id, db, actor)
    assert locks == [Project]


def test_direct_line_patch_reloads_version_and_serializes_project_first(writer_db):
    db, actor, project = writer_db
    line = ProjectAssetLine(project_id=project.id, asset_name="Original", quantity=1)
    db.add(line)
    db.commit()
    _ = line.asset_name  # Retain a stale ORM identity while another writer commits.
    with db.bind.begin() as connection:
        connection.execute(update(ProjectAssetLine).where(ProjectAssetLine.id == line.id).values(
            asset_name="New winner", row_version=2,
        ))
    locks = _locked_entities(db)
    with pytest.raises(HTTPException) as denied:
        projects.update_project_asset_line(
            project.id, line.id, ProjectAssetLineUpdate(asset_name="Stale overwrite", row_version=1),
            db, actor,
        )
    assert denied.value.status_code == 409
    assert locks == [Project, ProjectAssetLine]
    assert line.asset_name == "New winner"
    assert db.query(AuditEvent).count() == 0


def test_draft_commit_serializes_project_before_official_line(writer_db):
    db, actor, project = writer_db
    line = ProjectAssetLine(project_id=project.id, asset_name="Draft line", quantity=1)
    session = WorkbenchSession(project_id=project.id, user_id=actor.id)
    db.add_all([line, session])
    db.flush()
    db.add(InlineEditDraft(session_id=session.id, target_type="ProjectAssetLine", target_id=line.id,
                           field_key="description", draft_value={"value": "Committed"},
                           base_row_version=1))
    db.commit()
    locks = _locked_entities(db)
    execute_commit_asset_line_draft(db, actor, project.id, line.id, ["description"], True, "1")
    db.commit()
    assert locks == [Project, ProjectAssetLine]
    assert line.description == "Committed"
    assert line.row_version == 2


def _issue(db, target_type, target_id):
    rule = ValidationRule(rule_code=uuid.uuid4().hex, category="data_quality", name="Writer rule")
    db.add(rule)
    db.flush()
    issue = ValidationIssue(validation_rule_id=rule.id, target_type=target_type, target_id=target_id,
                            severity="blocking", status="open", issue_message="Blocker")
    db.add(issue)
    db.commit()
    return issue


@pytest.mark.parametrize("target_type", ["project", "Project", "project_asset_line", "ProjectAssetLine"])
@pytest.mark.parametrize("resolve", [False, True])
def test_scoped_issue_writer_locks_owning_project_first(writer_db, target_type, resolve):
    db, actor, project = writer_db
    target_id = project.id
    if "line" in target_type.lower():
        line = ProjectAssetLine(project_id=project.id, asset_name="Issue target", quantity=1)
        db.add(line)
        db.commit()
        target_id = line.id
    issue = _issue(db, target_type, target_id)
    locks = _locked_entities(db)
    if resolve:
        workflow.resolve_validation_issue(issue.id, ValidationIssueResolveRequest(
            expected_row_version=1, resolution_notes="Resolved"), db, actor)
        assert issue.status == "resolved"
    else:
        workflow.update_validation_issue(issue.id, ValidationIssueUpdate(
            expected_row_version=1, issue_message="Changed"), db, actor)
        assert issue.issue_message == "Changed"
    assert locks == [Project, ValidationIssue]
    assert issue.row_version == 2


@pytest.mark.parametrize("resolve", [False, True])
def test_issue_cross_tenant_writer_denied_without_mutation_or_audit(writer_db, resolve):
    db, actor, project = writer_db
    outsider = OrganizationProfile(legal_name="Outside", organization_slug=uuid.uuid4().hex)
    db.add(outsider)
    db.flush()
    outside_project = Project(organization_id=outsider.id, code="OUT", name="Outside",
                              created_by=actor.id)
    db.add(outside_project)
    db.commit()
    issue = _issue(db, "Project", outside_project.id)
    with pytest.raises(HTTPException) as denied:
        if resolve:
            workflow.resolve_validation_issue(issue.id, ValidationIssueResolveRequest(
                expected_row_version=1, resolution_notes="Bypass"), db, actor)
        else:
            workflow.update_validation_issue(issue.id, ValidationIssueUpdate(
                expected_row_version=1, severity="warning"), db, actor)
    assert denied.value.status_code == 404
    db.refresh(issue)
    assert issue.severity == "blocking"
    assert issue.status == "open"
    assert issue.row_version == 1
    assert db.query(AuditEvent).count() == 0


def test_apply_adapter_passes_successor_preconditions(writer_db, monkeypatch):
    db, actor, project = writer_db

    class CapturedRequest(Exception):
        pass

    def guarded_command(**kwargs):
        assert kwargs["contract_version"] == "s12-post-intake-guarded-apply-v2"
        assert kwargs["expected_case_version"] == "a" * 64
        assert kwargs["confirm"] is True
        raise CapturedRequest

    monkeypatch.setattr(projects, "apply_project_asset_import_batch", guarded_command)
    with pytest.raises(CapturedRequest):
        projects.apply_project_asset_import_batch_endpoint(
            project_id=project.id, batch_id=uuid.uuid4(), db=db, current_user=actor,
            payload=ProjectAssetImportBatchApplyRequest(
                confirm=True, contract_version="s12-post-intake-guarded-apply-v2",
                expected_case_version="a" * 64,
            ),
        )


@pytest.mark.parametrize("has_payload", [False, True])
def test_validate_adapter_keeps_optional_body_and_forwards_case_version(
    writer_db, monkeypatch, has_payload,
):
    db, actor, project = writer_db

    class CapturedRequest(Exception):
        pass

    def guarded_command(**kwargs):
        assert kwargs["expected_case_version"] == ("b" * 64 if has_payload else None)
        raise CapturedRequest

    monkeypatch.setattr(projects, "validate_project_asset_import_batch", guarded_command)
    payload = ProjectAssetImportBatchValidateRequest(expected_case_version="b" * 64)
    with pytest.raises(CapturedRequest):
        projects.validate_project_asset_import_batch_endpoint(
            project_id=project.id, batch_id=uuid.uuid4(), db=db, current_user=actor,
            payload=payload if has_payload else None,
        )
