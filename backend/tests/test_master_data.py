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
    CustomerAlias,
    Supplier,
    SupplierStatus,
    Brand,
    BrandStatus,
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
    """Sets up basic Org and User to reference in master data creations."""
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

    return {
        "org_a_id": org_a.id,
        "org_b_id": org_b.id,
        "user_a_id": user_a.id,
        "user_b_id": user_b.id,
    }


def test_customer_tax_code_uniqueness_per_organization(
    db_session: Session, setup_data
) -> None:
    """Verifies uq_customer_tax_org unique constraint."""
    # 1. Create customer in Org A
    c1 = Customer(
        organization_id=setup_data["org_a_id"],
        legal_name="Customer 1",
        tax_code="TAX123",
        status=CustomerStatus.ACTIVE,
        created_by=setup_data["user_a_id"],
    )
    db_session.add(c1)
    db_session.commit()

    # 2. Add same tax code in different Org B (should succeed)
    c2 = Customer(
        organization_id=setup_data["org_b_id"],
        legal_name="Customer 2",
        tax_code="TAX123",
        status=CustomerStatus.ACTIVE,
        created_by=setup_data["user_b_id"],
    )
    db_session.add(c2)
    db_session.commit()

    # 3. Add duplicate tax code in same Org A (should fail)
    c3 = Customer(
        organization_id=setup_data["org_a_id"],
        legal_name="Customer 3",
        tax_code="TAX123",
        status=CustomerStatus.ACTIVE,
        created_by=setup_data["user_a_id"],
    )
    db_session.add(c3)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_supplier_tax_code_uniqueness_per_organization(
    db_session: Session, setup_data
) -> None:
    """Verifies uq_supplier_tax_org unique constraint."""
    # 1. Create supplier in Org A
    s1 = Supplier(
        organization_id=setup_data["org_a_id"],
        legal_name="Supplier 1",
        tax_code="SUP123",
        status=SupplierStatus.ACTIVE,
        created_by=setup_data["user_a_id"],
    )
    db_session.add(s1)
    db_session.commit()

    # 2. Add same tax code in different Org B (should succeed)
    s2 = Supplier(
        organization_id=setup_data["org_b_id"],
        legal_name="Supplier 2",
        tax_code="SUP123",
        status=SupplierStatus.ACTIVE,
        created_by=setup_data["user_b_id"],
    )
    db_session.add(s2)
    db_session.commit()

    # 3. Add duplicate tax code in same Org A (should fail)
    s3 = Supplier(
        organization_id=setup_data["org_a_id"],
        legal_name="Supplier 3",
        tax_code="SUP123",
        status=SupplierStatus.ACTIVE,
        created_by=setup_data["user_a_id"],
    )
    db_session.add(s3)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_brand_name_case_insensitive_uniqueness(db_session: Session) -> None:
    """Verifies case-insensitive name uniqueness constraint on Brands."""
    b1 = Brand(
        name="Dell",
        status=BrandStatus.ACTIVE,
    )
    db_session.add(b1)
    db_session.commit()

    # Duplicate name in different casing (should fail)
    b2 = Brand(
        name="dell",
        status=BrandStatus.ACTIVE,
    )
    db_session.add(b2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_customer_supplier_alias_cascade_deletion(
    db_session: Session, setup_data
) -> None:
    """Verifies cascade deletion of aliases when parent is deleted."""
    # 1. Create Customer with Aliases
    customer = Customer(
        organization_id=setup_data["org_a_id"],
        legal_name="Main Customer",
        status=CustomerStatus.ACTIVE,
        created_by=setup_data["user_a_id"],
    )
    db_session.add(customer)
    db_session.commit()

    alias1 = CustomerAlias(
        customer_id=customer.id,
        alias_name="Main Cust Alias A",
        confidence_score=0.9500,
    )
    alias2 = CustomerAlias(
        customer_id=customer.id,
        alias_name="Main Cust Alias B",
        confidence_score=0.8800,
    )
    db_session.add_all([alias1, alias2])
    db_session.commit()

    # Assert aliases exist
    assert len(customer.aliases) == 2

    # 2. Delete Customer
    db_session.delete(customer)
    db_session.commit()

    # Verify aliases are cascade deleted
    aliases = db_session.scalars(select(CustomerAlias)).all()
    assert len(aliases) == 0


def test_optimistic_locking_increments(db_session: Session, setup_data) -> None:
    """Asserts row_version increments correctly on mutable master data tables."""
    customer = Customer(
        organization_id=setup_data["org_a_id"],
        legal_name="Initial Name",
        status=CustomerStatus.ACTIVE,
        created_by=setup_data["user_a_id"],
    )
    db_session.add(customer)
    db_session.commit()

    # Initial version must be 1
    assert customer.row_version == 1

    # Perform update
    customer.legal_name = "Updated Name"
    db_session.commit()

    # Assert version incremented to 2
    assert customer.row_version == 2
