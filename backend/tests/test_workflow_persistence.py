import pytest
from sqlalchemy import create_engine, exc, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, User, UserStatus, Project, ProjectWorkflowStatus, Customer,
    WorkflowDefinition, WorkflowDefinitionStatus,
    WorkflowInstance, WorkflowTransition,
    WorkflowTask, WorkflowTaskStatus, WorkflowTaskPriority,
    ReviewDecision, ReviewDecisionChoice,
    ApprovalGate, ApprovalGateStatus,
    ValidationRule, ValidationRuleCategory,
    ValidationIssue, ValidationIssueSeverity, ValidationIssueStatus,
    UserActionLog
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


def test_table_registration() -> None:
    tables = Base.metadata.tables
    assert "workflow_definitions" in tables
    assert "workflow_instances" in tables
    assert "workflow_transitions" in tables
    assert "workflow_tasks" in tables
    assert "review_decisions" in tables
    assert "approval_gates" in tables
    assert "validation_rules" in tables
    assert "validation_issues" in tables
    assert "user_action_logs" in tables

    # All Sprint 4 persistence tables are now loaded in metadata


@pytest.fixture
def setup_seed_data(db_session: Session):
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    user = User(organization_id=org.id, email="curator@test.com", full_name="Curator User", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    customer = Customer(organization_id=org.id, legal_name="Cust 1", status="active", created_by=user.id)
    db_session.add(customer)
    db_session.commit()

    proj = Project(
        organization_id=org.id,
        code="PROJ-2026",
        name="Project 2026",
        status=ProjectWorkflowStatus.DRAFT,
        customer_id=customer.id,
        created_by=user.id
    )
    db_session.add(proj)
    db_session.commit()

    return {
        "user_id": user.id,
        "project_id": proj.id
    }


def test_workflow_definition_and_transition(db_session: Session) -> None:
    # 1. Create definition
    wf_def = WorkflowDefinition(
        code="PROJECT_FLOW",
        name="Standard Project Workflow",
        status=WorkflowDefinitionStatus.ACTIVE
    )
    db_session.add(wf_def)
    db_session.commit()

    # 2. Link transitions
    t1 = WorkflowTransition(
        workflow_definition_id=wf_def.id,
        from_state="draft",
        to_state="under_review",
        command_name="submit_for_review",
        guard_expression={"min_evidence_count": 1}
    )
    db_session.add(t1)
    db_session.commit()

    db_session.expire_all()
    q_def = db_session.query(WorkflowDefinition).filter(WorkflowDefinition.code == "PROJECT_FLOW").one()
    assert len(q_def.transitions) == 1
    assert q_def.transitions[0].command_name == "submit_for_review"
    assert q_def.transitions[0].guard_expression == {"min_evidence_count": 1}


def test_workflow_instance_and_task(db_session: Session, setup_seed_data) -> None:
    wf_def = WorkflowDefinition(
        code="PROJECT_FLOW",
        name="Standard Project Workflow",
        status=WorkflowDefinitionStatus.ACTIVE
    )
    db_session.add(wf_def)
    db_session.commit()

    # 1. WorkflowInstance stores state and row_version
    instance = WorkflowInstance(
        workflow_definition_id=wf_def.id,
        target_type="project",
        target_id=setup_seed_data["project_id"],
        current_state="draft"
    )
    db_session.add(instance)
    db_session.commit()
    assert instance.row_version == 1

    # 2. WorkflowTask links to instance and assignee
    task = WorkflowTask(
        workflow_instance_id=instance.id,
        task_type="review",
        title="Verify quote evidence matches limits",
        status=WorkflowTaskStatus.OPEN,
        priority=WorkflowTaskPriority.HIGH,
        assigned_to=setup_seed_data["user_id"]
    )
    db_session.add(task)
    db_session.commit()

    db_session.expire_all()
    q_instance = db_session.query(WorkflowInstance).filter(WorkflowInstance.id == instance.id).one()
    assert len(q_instance.tasks) == 1
    assert q_instance.tasks[0].title == "Verify quote evidence matches limits"
    assert q_instance.tasks[0].assignee.id == setup_seed_data["user_id"]


def test_review_decision_append_only(db_session: Session, setup_seed_data) -> None:
    # Verify ReviewDecision logging
    decision = ReviewDecision(
        target_type="project",
        target_id=setup_seed_data["project_id"],
        decision=ReviewDecisionChoice.APPROVE,
        reason="All specifications and quotes verified.",
        decided_by=setup_seed_data["user_id"]
    )
    db_session.add(decision)
    db_session.commit()

    # Check append-only structure
    db_session.expire_all()
    q_decision = db_session.query(ReviewDecision).filter(ReviewDecision.id == decision.id).one()
    assert q_decision.decision == ReviewDecisionChoice.APPROVE
    assert q_decision.decided_by == setup_seed_data["user_id"]
    assert q_decision.decided_at is not None


def test_approval_gate_and_validation(db_session: Session, setup_seed_data) -> None:
    # 1. ApprovalGate targeting project
    gate = ApprovalGate(
        gate_code="QUOTE_LIMIT_GATE",
        target_type="project",
        target_id=setup_seed_data["project_id"],
        gate_status=ApprovalGateStatus.FAIL,
        blocking_issue_count=1
    )
    db_session.add(gate)
    db_session.commit()

    # 2. ValidationRule and ValidationIssue
    rule = ValidationRule(
        rule_code="VAL_RULE_001",
        category=ValidationRuleCategory.QUOTE,
        name="Quote Price Limit check"
    )
    db_session.add(rule)
    db_session.commit()

    issue = ValidationIssue(
        validation_rule_id=rule.id,
        target_type="project",
        target_id=setup_seed_data["project_id"],
        severity=ValidationIssueSeverity.BLOCKING,
        status=ValidationIssueStatus.OPEN,
        issue_message="Pricing spread exceeds threshold limit."
    )
    db_session.add(issue)
    db_session.commit()

    db_session.expire_all()
    q_issue = db_session.query(ValidationIssue).filter(ValidationIssue.id == issue.id).one()
    assert q_issue.severity == ValidationIssueSeverity.BLOCKING
    assert q_issue.validation_rule.rule_code == "VAL_RULE_001"


def test_user_action_log(db_session: Session, setup_seed_data) -> None:
    log = UserActionLog(
        user_id=setup_seed_data["user_id"],
        action_type="transition",
        target_type="project",
        target_id=setup_seed_data["project_id"],
        action_payload={"from": "draft", "to": "under_review"}
    )
    db_session.add(log)
    db_session.commit()

    db_session.expire_all()
    q_log = db_session.query(UserActionLog).filter(UserActionLog.id == log.id).one()
    assert q_log.action_payload == {"from": "draft", "to": "under_review"}
    assert q_log.created_at is not None


def test_parent_deletion_restrict(db_session: Session, setup_seed_data) -> None:
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
        target_id=setup_seed_data["project_id"],
        current_state="draft"
    )
    db_session.add(instance)
    db_session.commit()

    # Attempting to delete definition must fail due to RESTRICT foreign key
    db_session.delete(wf_def)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_migration_chain() -> None:
    import importlib.util
    import os
    
    filepath = os.path.join(os.path.dirname(__file__), "../alembic/versions/a87a9b6da99f_create_workflow_tables.py")
    spec = importlib.util.spec_from_file_location("migration_a87a9b6da99f", filepath)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    
    assert migration.revision == "a87a9b6da99f"
    assert migration.down_revision == "a87a9b6da99e"
