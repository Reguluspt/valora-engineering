import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserStatus,
    Customer,
    CustomerStatus,
    Project,
    ProjectWorkflowStatus,
    KnowledgeUpdateStatus,
    ProjectAssetLine,
    AssetLineReviewStatus,
    AssetLineValidationStatus,
    ProjectFile,
    ProjectFileCategory,
    FileProcessingStatus,
)


@pytest.fixture
def db_session() -> Session:
    """Fixture that initializes a SQLite in-memory database and provides a session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def setup_data(db_session: Session):
    """Sets up basic Org, User, and Customer to reference in project creations."""
    org_a = OrganizationProfile(
        legal_name="Org A",
        organization_slug="org-a",
        status=OrganizationStatus.ACTIVE,
    )
    org_b = OrganizationProfile(
        legal_name="Org B",
        organization_slug="org-b",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add_all([org_a, org_b])
    db_session.commit()

    user_a = User(
        organization_id=org_a.id,
        email="admin@org-a.com",
        full_name="Admin A",
        status=UserStatus.ACTIVE,
    )
    user_b = User(
        organization_id=org_b.id,
        email="admin@org-b.com",
        full_name="Admin B",
        status=UserStatus.ACTIVE,
    )
    db_session.add_all([user_a, user_b])
    db_session.commit()

    cust_a = Customer(
        organization_id=org_a.id,
        legal_name="Cust A",
        status=CustomerStatus.ACTIVE,
        created_by=user_a.id,
    )
    cust_b = Customer(
        organization_id=org_b.id,
        legal_name="Cust B",
        status=CustomerStatus.ACTIVE,
        created_by=user_b.id,
    )
    db_session.add_all([cust_a, cust_b])
    db_session.commit()

    return {
        "org_a_id": org_a.id,
        "org_b_id": org_b.id,
        "user_a_id": user_a.id,
        "user_b_id": user_b.id,
        "cust_a_id": cust_a.id,
        "cust_b_id": cust_b.id,
    }


def test_project_code_uniqueness_per_organization(
    db_session: Session, setup_data
) -> None:
    """Verifies uq_project_code_org unique constraint."""
    # 1. Create project in Org A
    p1 = Project(
        organization_id=setup_data["org_a_id"],
        customer_id=setup_data["cust_a_id"],
        code="PRJ-100",
        name="Project 1",
        status=ProjectWorkflowStatus.DRAFT,
        knowledge_status=KnowledgeUpdateStatus.PENDING,
        created_by=setup_data["user_a_id"],
    )
    db_session.add(p1)
    db_session.commit()

    # 2. Add same code in different Org B (should succeed)
    p2 = Project(
        organization_id=setup_data["org_b_id"],
        customer_id=setup_data["cust_b_id"],
        code="PRJ-100",
        name="Project 2",
        status=ProjectWorkflowStatus.DRAFT,
        knowledge_status=KnowledgeUpdateStatus.PENDING,
        created_by=setup_data["user_b_id"],
    )
    db_session.add(p2)
    db_session.commit()

    # 3. Add duplicate code in same Org A (should fail)
    p3 = Project(
        organization_id=setup_data["org_a_id"],
        customer_id=setup_data["cust_a_id"],
        code="PRJ-100",
        name="Project 3",
        status=ProjectWorkflowStatus.DRAFT,
        knowledge_status=KnowledgeUpdateStatus.PENDING,
        created_by=setup_data["user_a_id"],
    )
    db_session.add(p3)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_project_fee_amount_non_negative_constraint(
    db_session: Session, setup_data
) -> None:
    """Verifies fee_amount CheckConstraint chk_project_fee_positive."""
    p = Project(
        organization_id=setup_data["org_a_id"],
        customer_id=setup_data["cust_a_id"],
        code="PRJ-NEG-FEE",
        name="Negative Fee Project",
        fee_amount=-150.00,  # Negative fee (should fail)
        status=ProjectWorkflowStatus.DRAFT,
        knowledge_status=KnowledgeUpdateStatus.PENDING,
        created_by=setup_data["user_a_id"],
    )
    db_session.add(p)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_asset_line_constraints_and_cascade(
    db_session: Session, setup_data
) -> None:
    """Verifies non-negative value constraints and cascade deletes on ProjectAssetLines."""
    p = Project(
        organization_id=setup_data["org_a_id"],
        customer_id=setup_data["cust_a_id"],
        code="PRJ-ASSET-TEST",
        name="Asset Test Project",
        status=ProjectWorkflowStatus.DRAFT,
        knowledge_status=KnowledgeUpdateStatus.PENDING,
        created_by=setup_data["user_a_id"],
    )
    db_session.add(p)
    db_session.commit()

    # 1. Create line item with valid details
    line = ProjectAssetLine(
        project_id=p.id,
        asset_name="Apples",
        quantity=5.5000,
        raw_price=10.00,
        review_status=AssetLineReviewStatus.PENDING,
        validation_status=AssetLineValidationStatus.UNVALIDATED,
    )
    db_session.add(line)
    db_session.commit()

    # 2. Add line with negative quantity (should fail)
    bad_line_qty = ProjectAssetLine(
        project_id=p.id,
        asset_name="Oranges",
        quantity=-1.0,
        review_status=AssetLineReviewStatus.PENDING,
        validation_status=AssetLineValidationStatus.UNVALIDATED,
    )
    db_session.add(bad_line_qty)
    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()

    # 3. Add line with negative raw_price (should fail)
    bad_line_price = ProjectAssetLine(
        project_id=p.id,
        asset_name="Grapes",
        quantity=2.0,
        raw_price=-5.00,
        review_status=AssetLineReviewStatus.PENDING,
        validation_status=AssetLineValidationStatus.UNVALIDATED,
    )
    db_session.add(bad_line_price)
    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()

    # 4. Verify cascade delete
    assert len(p.asset_lines) == 1
    db_session.delete(p)
    db_session.commit()

    lines = db_session.scalars(select(ProjectAssetLine)).all()
    assert len(lines) == 0


def test_project_file_constraints_and_cascade(
    db_session: Session, setup_data
) -> None:
    """Verifies file size check constraint and cascade delete on ProjectFiles."""
    p = Project(
        organization_id=setup_data["org_a_id"],
        customer_id=setup_data["cust_a_id"],
        code="PRJ-FILE-TEST",
        name="File Test Project",
        status=ProjectWorkflowStatus.DRAFT,
        knowledge_status=KnowledgeUpdateStatus.PENDING,
        created_by=setup_data["user_a_id"],
    )
    db_session.add(p)
    db_session.commit()

    # 1. Create file with negative file size (should fail)
    bad_file = ProjectFile(
        project_id=p.id,
        file_name="invoice.pdf",
        file_category=ProjectFileCategory.INPUT_CONTRACT,
        file_size=-1000,  # Negative size
        mime_type="application/pdf",
        storage_object_key="key/path",
        checksum_sha256="abc123sha",
        processing_status=FileProcessingStatus.PENDING,
        uploaded_by=setup_data["user_a_id"],
    )
    db_session.add(bad_file)
    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()

    # 2. Add valid file
    good_file = ProjectFile(
        project_id=p.id,
        file_name="contract.pdf",
        file_category=ProjectFileCategory.INPUT_CONTRACT,
        file_size=2048,
        mime_type="application/pdf",
        storage_object_key="contracts/contract_1.pdf",
        checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        processing_status=FileProcessingStatus.PENDING,
        uploaded_by=setup_data["user_a_id"],
    )
    db_session.add(good_file)
    db_session.commit()

    # Verify relationship
    assert len(p.files) == 1

    # 3. Delete Project and verify cascade delete on files
    db_session.delete(p)
    db_session.commit()

    files = db_session.scalars(select(ProjectFile)).all()
    assert len(files) == 0
