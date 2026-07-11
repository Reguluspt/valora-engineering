import uuid
import pytest
from sqlalchemy import create_engine, exc, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserStatus,
    Project,
    ProjectWorkflowStatus,
    Customer,
    ReviewDecision,
    ReviewDecisionChoice,
    ChangeRequest,
    ChangeRequestStatus,
    ChangeRequestType,
    ChangeRequestPriority,
    ReviewDecisionReversal,
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
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
    assert "change_requests" in tables
    assert "review_decision_reversals" in tables


@pytest.fixture
def setup_seed_data(db_session: Session):
    org = OrganizationProfile(
        legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id,
        email="curator@test.com",
        full_name="Curator User",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()

    customer = Customer(
        organization_id=org.id, legal_name="Cust 1", status="active", created_by=user.id
    )
    db_session.add(customer)
    db_session.commit()

    proj = Project(
        organization_id=org.id,
        code="PROJ-2026",
        name="Project 2026",
        status=ProjectWorkflowStatus.DRAFT,
        customer_id=customer.id,
        created_by=user.id,
    )
    db_session.add(proj)
    db_session.commit()

    return {"user_id": user.id, "project_id": proj.id}


def test_change_request_persistence(db_session: Session, setup_seed_data) -> None:
    # 1. Create a change request with row_version
    cr = ChangeRequest(
        request_code="CR-001",
        target_type="project",
        target_id=setup_seed_data["project_id"],
        change_type=ChangeRequestType.REOPEN,
        requested_payload={"status": "draft"},
        reason="Need to add extra quote evidence.",
        status=ChangeRequestStatus.PENDING_REVIEW,
        priority=ChangeRequestPriority.HIGH,
        requested_by=setup_seed_data["user_id"],
    )
    db_session.add(cr)
    db_session.commit()

    assert cr.row_version == 1
    assert cr.request_code == "CR-001"
    assert cr.requester.id == setup_seed_data["user_id"]


def test_review_decision_reversal_linking(db_session: Session, setup_seed_data) -> None:
    # 1. Create a change request
    cr = ChangeRequest(
        request_code="CR-002",
        target_type="project",
        target_id=setup_seed_data["project_id"],
        change_type=ChangeRequestType.REVERSE_REVIEW_DECISION,
        requested_payload={"original_decision_id": str(uuid.uuid4())},
        reason="Original decision was incorrect.",
        status=ChangeRequestStatus.APPROVED,
        priority=ChangeRequestPriority.HIGH,
        requested_by=setup_seed_data["user_id"],
    )
    db_session.add(cr)
    db_session.commit()

    # 2. Original ReviewDecision
    orig_dec = ReviewDecision(
        target_type="project",
        target_id=setup_seed_data["project_id"],
        decision=ReviewDecisionChoice.APPROVE,
        reason="Approved initial draft",
        decided_by=setup_seed_data["user_id"],
    )
    db_session.add(orig_dec)

    # 3. Reversal ReviewDecision
    rev_dec = ReviewDecision(
        target_type="project",
        target_id=setup_seed_data["project_id"],
        decision=ReviewDecisionChoice.REJECT,
        reason="Reversed initial approval",
        decided_by=setup_seed_data["user_id"],
    )
    db_session.add(rev_dec)
    db_session.commit()

    # 4. ReviewDecisionReversal link
    reversal = ReviewDecisionReversal(
        change_request_id=cr.id,
        original_review_decision_id=orig_dec.id,
        reversal_review_decision_id=rev_dec.id,
        reason="Correcting incorrect appraisal data",
        created_by=setup_seed_data["user_id"],
    )
    db_session.add(reversal)
    db_session.commit()

    db_session.expire_all()
    q_reversal = (
        db_session.query(ReviewDecisionReversal)
        .filter(ReviewDecisionReversal.id == reversal.id)
        .one()
    )
    assert q_reversal.original_decision.decision == ReviewDecisionChoice.APPROVE
    assert q_reversal.reversal_decision.decision == ReviewDecisionChoice.REJECT


def test_parent_deletion_restrict(db_session: Session, setup_seed_data) -> None:
    cr = ChangeRequest(
        request_code="CR-003",
        target_type="project",
        target_id=setup_seed_data["project_id"],
        change_type=ChangeRequestType.REOPEN,
        requested_payload={"status": "draft"},
        reason="Reopen reason",
        status=ChangeRequestStatus.DRAFT,
        priority=ChangeRequestPriority.NORMAL,
        requested_by=setup_seed_data["user_id"],
    )
    db_session.add(cr)
    db_session.commit()

    orig_dec = ReviewDecision(
        target_type="project",
        target_id=setup_seed_data["project_id"],
        decision=ReviewDecisionChoice.APPROVE,
        reason="Approved",
        decided_by=setup_seed_data["user_id"],
    )
    rev_dec = ReviewDecision(
        target_type="project",
        target_id=setup_seed_data["project_id"],
        decision=ReviewDecisionChoice.REJECT,
        reason="Reversed",
        decided_by=setup_seed_data["user_id"],
    )
    db_session.add_all([orig_dec, rev_dec])
    db_session.commit()

    reversal = ReviewDecisionReversal(
        change_request_id=cr.id,
        original_review_decision_id=orig_dec.id,
        reversal_review_decision_id=rev_dec.id,
        reason="Reversal reason",
        created_by=setup_seed_data["user_id"],
    )
    db_session.add(reversal)
    db_session.commit()

    # Deleting change request must fail due to RESTRICT on reversal
    db_session.delete(cr)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_migration_chain() -> None:
    import importlib.util
    import os

    filepath = os.path.join(
        os.path.dirname(__file__),
        "../alembic/versions/a87a9b6da9a1_create_change_request_tables.py",
    )
    spec = importlib.util.spec_from_file_location("migration_a87a9b6da9a1", filepath)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "a87a9b6da9a1"
    assert migration.down_revision == "a87a9b6da9a0"
