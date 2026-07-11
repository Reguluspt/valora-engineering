import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.main import app
from app.db import Base, get_db
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserStatus,
    Role,
    UserRole,
    Province,
    Country,
    ReferenceStatus,
    AuditEvent,
    Customer,
    CustomerStatus,
    CustomerAlias,
    Supplier,
    SupplierStatus,
    SupplierAlias,
    SignerProfile
)

from sqlalchemy.pool import StaticPool

# Test setup for sqlite in-memory db session override
@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
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
    # Override get_db dependency to use the in-memory test database
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_master_data_rbac_and_audit(client: TestClient, db_session: Session) -> None:
    # 1. Seed org and users with different roles
    org = OrganizationProfile(
        legal_name="Master Org",
        organization_slug="master-org",
        status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    db_session.commit()

    # Role setup
    role_admin = Role(
        code="admin",
        display_name="Admin",
        permissions=["master_data:customer:create", "master_data:customer:read", "master_data:customer:update", "master_data:customer:deactivate", "master_data:customer:merge", "master_data:reference:create", "master_data:reference:read"]
    )
    role_viewer = Role(
        code="viewer",
        display_name="Viewer",
        permissions=["master_data:customer:read", "master_data:reference:read"]
    )
    db_session.add_all([role_admin, role_viewer])
    db_session.commit()

    user_admin = User(
        organization_id=org.id,
        email="admin@test.com",
        full_name="Admin User",
        status=UserStatus.ACTIVE
    )
    user_viewer = User(
        organization_id=org.id,
        email="viewer@test.com",
        full_name="Viewer User",
        status=UserStatus.ACTIVE
    )
    db_session.add_all([user_admin, user_viewer])
    db_session.commit()

    ur_admin = UserRole(user_id=user_admin.id, role_id=role_admin.id, is_active=True)
    ur_viewer = UserRole(user_id=user_viewer.id, role_id=role_viewer.id, is_active=True)
    db_session.add_all([ur_admin, ur_viewer])
    db_session.commit()

    # 2. Test Country creation and lists
    headers_viewer = {"X-User-Id": str(user_viewer.id)}
    headers_admin = {"X-User-Id": str(user_admin.id)}

    # Viewer tries to create Country -> 403
    resp = client.post(
        "/api/v1/master-data/countries",
        headers=headers_viewer,
        json={"iso2": "VN", "iso3": "VNM", "name_vi": "Việt Nam"}
    )
    assert resp.status_code == 403

    # Admin creates Country successfully -> 201
    resp = client.post(
        "/api/v1/master-data/countries",
        headers=headers_admin,
        json={"iso2": "VN", "iso3": "VNM", "name_vi": "Việt Nam"}
    )
    assert resp.status_code == 201
    country_id = resp.json()["id"]

    # Verify audit log was created
    audit = db_session.query(AuditEvent).filter(AuditEvent.event_name == "CountryCreated").first()
    assert audit is not None
    assert audit.actor_user_id == user_admin.id

    # Create Province using country_id
    resp = client.post(
        "/api/v1/master-data/provinces",
        headers=headers_admin,
        json={"country_id": country_id, "name": "Gia Lai", "code": "GL"}
    )
    assert resp.status_code == 201
    prov_id = resp.json()["id"]

    # 3. Create Customer
    # Admin creates customer -> 201
    resp = client.post(
        "/api/v1/master-data/customers",
        headers=headers_admin,
        json={
            "legal_name": "Ban Quản lý Diên Hồng",
            "display_name": "BQL Diên Hồng",
            "tax_code": "TAX123",
            "province_id": prov_id
        }
    )
    assert resp.status_code == 201
    cust1_id = resp.json()["id"]
    assert resp.json()["status"] == "active"
    
    # Assert warning list empty since no similar customer exists
    assert resp.json()["warnings"] == []

    # Verify audit event for CustomerCreated exists
    audit_cust = db_session.query(AuditEvent).filter(AuditEvent.event_name == "CustomerCreated").first()
    assert audit_cust is not None
    assert audit_cust.entity_id == uuid.UUID(cust1_id)

    # Try creating another customer with SAME tax code in SAME org -> 409
    resp = client.post(
        "/api/v1/master-data/customers",
        headers=headers_admin,
        json={
            "legal_name": "Another Name",
            "tax_code": "TAX123"
        }
    )
    assert resp.status_code == 409

    # Create customer with same normalized name -> returns warnings
    resp = client.post(
        "/api/v1/master-data/customers",
        headers=headers_admin,
        json={
            "legal_name": "BAN QUẢN LÝ DIÊN HỒNG",
            "tax_code": "TAX456"
        }
    )
    assert resp.status_code == 201
    cust2_id = resp.json()["id"]
    assert len(resp.json()["warnings"]) > 0
    assert "Fuzzy duplicate customer found" in resp.json()["warnings"][0]

    # Create customer in DIFFERENT organization with same tax code (allowed)
    other_org = OrganizationProfile(
        legal_name="Other Org",
        organization_slug="other-org",
        status=OrganizationStatus.ACTIVE
    )
    db_session.add(other_org)
    db_session.commit()

    other_user_admin = User(
        organization_id=other_org.id,
        email="other_admin@test.com",
        full_name="Other Admin User",
        status=UserStatus.ACTIVE
    )
    db_session.add(other_user_admin)
    db_session.commit()

    ur_other = UserRole(user_id=other_user_admin.id, role_id=role_admin.id, is_active=True)
    db_session.add(ur_other)
    db_session.commit()

    headers_other = {"X-User-Id": str(other_user_admin.id)}
    resp = client.post(
        "/api/v1/master-data/customers",
        headers=headers_other,
        json={
            "legal_name": "Ban Quản lý Diên Hồng",
            "tax_code": "TAX123"  # Same tax code as cust1 but different org
        }
    )
    assert resp.status_code == 201

    # 4. Patch Customer
    resp = client.patch(
        f"/api/v1/master-data/customers/{cust1_id}",
        headers=headers_admin,
        json={"display_name": "Updated BQL"}
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Updated BQL"

    # Verify audit event for CustomerUpdated
    audit_update = db_session.query(AuditEvent).filter(AuditEvent.event_name == "CustomerUpdated").first()
    assert audit_update is not None

    # 5. Deactivate Customer
    resp = client.post(
        f"/api/v1/master-data/customers/{cust1_id}/deactivate",
        headers=headers_admin,
        json={"reason": "Retiring"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "inactive"

    # Deactive instead of delete check: record is still in database
    cust_record = db_session.query(Customer).filter(Customer.id == uuid.UUID(cust1_id)).first()
    assert cust_record is not None
    assert cust_record.status == CustomerStatus.INACTIVE

    # 6. Merge Customers
    # Activate cust1 back for merge test, or create a new active source cust
    cust_source = Customer(
        organization_id=org.id,
        legal_name="Source Corp",
        tax_code="TAXSOURCE",
        created_by=user_admin.id,
        status=CustomerStatus.ACTIVE
    )
    cust_target = Customer(
        organization_id=org.id,
        legal_name="Target Corp",
        tax_code="TAXTARGET",
        created_by=user_admin.id,
        status=CustomerStatus.ACTIVE
    )
    db_session.add_all([cust_source, cust_target])
    db_session.commit()

    resp = client.post(
        "/api/v1/master-data/customers/merge",
        headers=headers_admin,
        json={
            "source_customer_id": str(cust_source.id),
            "target_customer_id": str(cust_target.id),
            "reason": "Duplicate"
        }
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == str(cust_target.id)

    db_session.refresh(cust_source)
    assert cust_source.status == CustomerStatus.MERGED
    assert cust_source.merged_into_customer_id == cust_target.id

    # Verify alias preserved on target
    aliases = db_session.query(CustomerAlias).filter(CustomerAlias.customer_id == cust_target.id).all()
    assert len(aliases) == 1
    assert aliases[0].alias_name == "Source Corp"




def test_supplier_contract_and_tenant_scoping(client: TestClient, db_session: Session) -> None:
    # Seed org and users
    org = OrganizationProfile(legal_name="Supp Org", organization_slug="supp-org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    role_admin = Role(
        code="admin",
        display_name="Admin",
        permissions=[
            "master_data:supplier:create", "master_data:supplier:read",
            "master_data:supplier:update", "master_data:supplier:deactivate",
            "master_data:supplier:merge", "master_data:reference:create"
        ]
    )
    db_session.add(role_admin)
    db_session.commit()

    user = User(organization_id=org.id, email="supp_admin@test.com", full_name="Supplier Admin", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    ur = UserRole(user_id=user.id, role_id=role_admin.id, is_active=True)
    db_session.add(ur)
    db_session.commit()

    headers = {"X-User-Id": str(user.id)}

    # Create Country and Province first
    country = Country(iso2="SG", iso3="SGP", name_vi="Singapore", status=ReferenceStatus.ACTIVE)
    db_session.add(country)
    db_session.commit()
    province = Province(country_id=country.id, name="Singapore City", code="SG-01", status=ReferenceStatus.ACTIVE)
    db_session.add(province)
    db_session.commit()

    # 1. Create Supplier -> 201
    resp = client.post(
        "/api/v1/master-data/suppliers",
        headers=headers,
        json={
            "legal_name": "Supplier A",
            "display_name": "Supp A",
            "tax_code": "TAXSUPP1",
            "province_id": str(province.id),
            "reliability_score": 0.95
        }
    )
    assert resp.status_code == 201
    supp1_id = resp.json()["id"]

    # Verify duplicate tax code -> 409
    resp = client.post(
        "/api/v1/master-data/suppliers",
        headers=headers,
        json={"legal_name": "Supplier B", "tax_code": "TAXSUPP1"}
    )
    assert resp.status_code == 409

    # Create fuzzy duplicate supplier -> returns warnings
    resp = client.post(
        "/api/v1/master-data/suppliers",
        headers=headers,
        json={"legal_name": "supplier a", "tax_code": "TAXSUPP2"}
    )
    assert resp.status_code == 201
    assert len(resp.json()["warnings"]) > 0

    # 2. Get Suppliers with filters
    resp = client.get("/api/v1/master-data/suppliers?q=Supp&min_reliability=0.9", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 3. Patch Supplier
    resp = client.patch(
        f"/api/v1/master-data/suppliers/{supp1_id}",
        headers=headers,
        json={"display_name": "Updated Supp A", "reliability_score": 0.88}
    )
    assert resp.status_code == 200
    assert resp.json()["reliability_score"] == 0.88

    # 4. Deactivate Supplier
    resp = client.post(
        f"/api/v1/master-data/suppliers/{supp1_id}/deactivate",
        headers=headers,
        json={"reason": "Out of business"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "inactive"

    # 5. Merge Suppliers
    s_source = Supplier(organization_id=org.id, legal_name="S Source", tax_code="TAXSS", created_by=user.id, status=SupplierStatus.ACTIVE)
    s_target = Supplier(organization_id=org.id, legal_name="S Target", tax_code="TAXST", created_by=user.id, status=SupplierStatus.ACTIVE)
    db_session.add_all([s_source, s_target])
    db_session.commit()

    resp = client.post(
        "/api/v1/master-data/suppliers/merge",
        headers=headers,
        json={
            "source_supplier_id": str(s_source.id),
            "target_supplier_id": str(s_target.id),
            "reason": "Duplicate supplier"
        }
    )
    assert resp.status_code == 200
    db_session.refresh(s_source)
    assert s_source.status == SupplierStatus.MERGED
    assert s_source.merged_into_supplier_id == s_target.id

    # Verify alias preserved on target
    aliases = db_session.query(SupplierAlias).filter(SupplierAlias.supplier_id == s_target.id).all()
    assert len(aliases) == 1
    assert aliases[0].alias_name == "S Source"


def test_brands_and_manufacturers(client: TestClient, db_session: Session) -> None:
    # Seed org/user with reference and brand/mfg privileges
    org = OrganizationProfile(legal_name="Brand Org", organization_slug="brand-org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    role = Role(
        code="admin",
        display_name="Admin",
        permissions=[
            "master_data:reference:create", "master_data:brand:create", "master_data:brand:read",
            "master_data:manufacturer:create", "master_data:manufacturer:read"
        ]
    )
    db_session.add(role)
    db_session.commit()

    user = User(organization_id=org.id, email="brand_admin@test.com", full_name="Brand Admin", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    ur = UserRole(user_id=user.id, role_id=role.id, is_active=True)
    db_session.add(ur)
    db_session.commit()

    headers = {"X-User-Id": str(user.id)}

    # Create Country
    country = Country(iso2="VN", iso3="VNM", name_vi="Việt Nam", status=ReferenceStatus.ACTIVE)
    db_session.add(country)
    db_session.commit()

    # 1. Create Manufacturer
    resp = client.post(
        "/api/v1/master-data/manufacturers",
        headers=headers,
        json={"legal_name": "Rang Dong Joint Stock", "country_id": str(country.id), "website": "https://rangdong.com"}
    )
    assert resp.status_code == 201
    mfg_id = resp.json()["id"]

    # 2. List Manufacturers
    resp = client.get("/api/v1/master-data/manufacturers", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 3. Create Brand
    resp = client.post(
        "/api/v1/master-data/brands",
        headers=headers,
        json={"name": "Rang Dong", "country_id": str(country.id), "manufacturer_id": mfg_id}
    )
    assert resp.status_code == 201
    brand_id = resp.json()["id"]

    # Try duplicate brand name (case-insensitive) -> 409
    resp = client.post(
        "/api/v1/master-data/brands",
        headers=headers,
        json={"name": "rang dong"}
    )
    assert resp.status_code == 409

    # 4. List Brands
    resp = client.get("/api/v1/master-data/brands?q=Dong", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_units_and_currencies(client: TestClient, db_session: Session) -> None:
    # Seed org/user
    org = OrganizationProfile(legal_name="Unit Org", organization_slug="unit-org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    role = Role(
        code="admin",
        display_name="Admin",
        permissions=[
            "master_data:unit:create", "master_data:unit:read",
            "master_data:currency:create", "master_data:reference:read"
        ]
    )
    db_session.add(role)
    db_session.commit()

    user = User(organization_id=org.id, email="unit_admin@test.com", full_name="Unit Admin", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    ur = UserRole(user_id=user.id, role_id=role.id, is_active=True)
    db_session.add(ur)
    db_session.commit()

    headers = {"X-User-Id": str(user.id)}

    # 1. Create Unit -> 201
    resp = client.post(
        "/api/v1/master-data/units",
        headers=headers,
        json={"code": "kg", "display_name": "Kilogram", "symbol": "kg", "unit_type": "weight"}
    )
    assert resp.status_code == 201

    # Try duplicate unit code -> 409
    resp = client.post(
        "/api/v1/master-data/units",
        headers=headers,
        json={"code": "kg", "display_name": "Kilo"}
    )
    assert resp.status_code == 409

    # 2. List Units -> 200
    resp = client.get("/api/v1/master-data/units", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # 3. Create Currency -> 201
    resp = client.post(
        "/api/v1/master-data/currencies",
        headers=headers,
        json={"code": "USD", "display_name": "US Dollar", "symbol": "$", "decimal_places": 2}
    )
    assert resp.status_code == 201

    # Try duplicate currency code -> 409
    resp = client.post(
        "/api/v1/master-data/currencies",
        headers=headers,
        json={"code": "USD", "display_name": "Dollar"}
    )
    assert resp.status_code == 409

    # 4. List Currencies -> 200
    resp = client.get("/api/v1/master-data/currencies", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_signers_contract(client: TestClient, db_session: Session) -> None:
    # Seed org/user
    org = OrganizationProfile(legal_name="Sign Org", organization_slug="sign-org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    role = Role(
        code="admin",
        display_name="Admin",
        permissions=["master_data:signer:create", "master_data:signer:update", "master_data:reference:read"]
    )
    db_session.add(role)
    db_session.commit()

    user = User(organization_id=org.id, email="sign_admin@test.com", full_name="Sign Admin", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    ur = UserRole(user_id=user.id, role_id=role.id, is_active=True)
    db_session.add(ur)
    db_session.commit()

    headers = {"X-User-Id": str(user.id)}

    # 1. Create Signer A (default=True)
    resp = client.post(
        "/api/v1/master-data/signers",
        headers=headers,
        json={"full_name": "Signer A", "title": "Director", "certificate_number": "CERT-1", "is_default": True}
    )
    assert resp.status_code == 201
    s1_id = resp.json()["id"]

    # 2. Create Signer B (default=True) - should unset Signer A's default
    resp = client.post(
        "/api/v1/master-data/signers",
        headers=headers,
        json={"full_name": "Signer B", "title": "Manager", "certificate_number": "CERT-2", "is_default": True}
    )
    assert resp.status_code == 201
    s2_id = resp.json()["id"]

    # Verify defaults in database
    db_session.expire_all()
    s1 = db_session.query(SignerProfile).filter(SignerProfile.id == uuid.UUID(s1_id)).first()
    s2 = db_session.query(SignerProfile).filter(SignerProfile.id == uuid.UUID(s2_id)).first()
    assert s1.is_default is False
    assert s2.is_default is True

    # 3. Patch Signer A to title="CEO"
    resp = client.patch(
        f"/api/v1/master-data/signers/{s1_id}",
        headers=headers,
        json={"title": "CEO"}
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "CEO"

    # 4. List Signers
    resp = client.get("/api/v1/master-data/signers", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_openapi_json_loads(client: TestClient) -> None:
    # Verifies that openapi.json is loaded correctly
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "paths" in data
    assert "/api/v1/master-data/customers" in data["paths"]

