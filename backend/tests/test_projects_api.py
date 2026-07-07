import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserStatus,
    Role,
    UserRole,
    Customer,
    CustomerStatus,
    Currency,
    ReferenceStatus,
    Project,
    ProjectWorkflowStatus,
    ProjectAssetLine,
    ProjectFile,
    AuditEvent,
    Unit
)

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
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_projects_api_full_flow(client: TestClient, db_session: Session) -> None:
    # 1. Seed org, users, roles, and master data
    org = OrganizationProfile(legal_name="Proj Org", organization_slug="proj-org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    role_admin = Role(
        code="admin",
        display_name="Admin",
        permissions=[
            "project:create", "project:read", "project:update",
            "project:archive", "project:cancel", "project:file:upload",
            "project:asset_line:read"
        ]
    )
    role_viewer = Role(
        code="viewer",
        display_name="Viewer",
        permissions=["project:read", "project:asset_line:read"]
    )
    db_session.add_all([role_admin, role_viewer])
    db_session.commit()

    user_admin = User(organization_id=org.id, email="admin@proj.com", full_name="Proj Admin", status=UserStatus.ACTIVE)
    user_viewer = User(organization_id=org.id, email="viewer@proj.com", full_name="Proj Viewer", status=UserStatus.ACTIVE)
    db_session.add_all([user_admin, user_viewer])
    db_session.commit()

    ur_admin = UserRole(user_id=user_admin.id, role_id=role_admin.id, is_active=True)
    ur_viewer = UserRole(user_id=user_viewer.id, role_id=role_viewer.id, is_active=True)
    db_session.add_all([ur_admin, ur_viewer])
    db_session.commit()

    headers_admin = {"X-User-Id": str(user_admin.id)}
    headers_viewer = {"X-User-Id": str(user_viewer.id)}

    # Seed active and inactive customer in org
    cust_active = Customer(
        organization_id=org.id,
        legal_name="Active Customer",
        status=CustomerStatus.ACTIVE,
        created_by=user_admin.id
    )
    cust_inactive = Customer(
        organization_id=org.id,
        legal_name="Inactive Customer",
        status=CustomerStatus.INACTIVE,
        created_by=user_admin.id
    )
    db_session.add_all([cust_active, cust_inactive])
    db_session.commit()

    # Seed currency and unit
    currency = Currency(code="VND", display_name="Dong", status=ReferenceStatus.ACTIVE)
    unit = Unit(code="item", display_name="Item", status=ReferenceStatus.ACTIVE)
    db_session.add_all([currency, unit])
    db_session.commit()

    # 2. RBAC check on project creation (Viewer gets 403)
    resp = client.post(
        "/api/v1/projects",
        headers=headers_viewer,
        json={"code": "P01", "name": "Project 1", "customer_id": str(cust_active.id)}
    )
    assert resp.status_code == 403

    # 3. Create project with inactive customer -> 422
    resp = client.post(
        "/api/v1/projects",
        headers=headers_admin,
        json={"code": "P01", "name": "Project 1", "customer_id": str(cust_inactive.id)}
    )
    assert resp.status_code == 422

    # 4. Create project with customer from DIFFERENT organization -> 404
    other_org = OrganizationProfile(legal_name="Other Org", organization_slug="other-org", status=OrganizationStatus.ACTIVE)
    db_session.add(other_org)
    db_session.commit()
    cust_other_org = Customer(
        organization_id=other_org.id,
        legal_name="Other Customer",
        status=CustomerStatus.ACTIVE,
        created_by=user_admin.id
    )
    db_session.add(cust_other_org)
    db_session.commit()

    resp = client.post(
        "/api/v1/projects",
        headers=headers_admin,
        json={"code": "P01", "name": "Project 1", "customer_id": str(cust_other_org.id)}
    )
    assert resp.status_code == 404

    # 5. Create project successfully -> 201
    resp = client.post(
        "/api/v1/projects",
        headers=headers_admin,
        json={
            "code": "P01",
            "name": "Project 1",
            "customer_id": str(cust_active.id),
            "fee_amount": 1000000.0,
            "fee_currency_id": str(currency.id)
        }
    )
    assert resp.status_code == 201
    proj_id = resp.json()["id"]
    assert resp.json()["status"] == "draft"

    # Verify audit event for ProjectCreated
    audit = db_session.query(AuditEvent).filter(AuditEvent.event_name == "ProjectCreated").first()
    assert audit is not None
    assert audit.organization_id == org.id

    # Create project with duplicate code -> 409
    resp = client.post(
        "/api/v1/projects",
        headers=headers_admin,
        json={"code": "P01", "name": "Project 2", "customer_id": str(cust_active.id)}
    )
    assert resp.status_code == 409

    # 6. List and Get Projects
    resp = client.get("/api/v1/projects?q=Proj", headers=headers_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.get(f"/api/v1/projects/{proj_id}", headers=headers_viewer)
    assert resp.status_code == 200
    assert resp.json()["code"] == "P01"

    # Tenant scoping check: other org user cannot see this project
    other_user = User(organization_id=other_org.id, email="other@test.com", full_name="Other User", status=UserStatus.ACTIVE)
    db_session.add(other_user)
    db_session.commit()
    ur_other = UserRole(user_id=other_user.id, role_id=role_viewer.id, is_active=True)
    db_session.add(ur_other)
    db_session.commit()

    resp = client.get(f"/api/v1/projects/{proj_id}", headers={"X-User-Id": str(other_user.id)})
    assert resp.status_code == 404

    # 7. Patch/Update Project
    # Try updating with incorrect row_version -> 409
    resp = client.patch(
        f"/api/v1/projects/{proj_id}",
        headers=headers_admin,
        json={"name": "New Name", "row_version": 999}
    )
    assert resp.status_code == 409

    # Update with correct row_version (version=1 initially) -> 200
    resp = client.patch(
        f"/api/v1/projects/{proj_id}",
        headers=headers_admin,
        json={"name": "New Name", "row_version": 1}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["row_version"] == 2

    # Verify audit event for ProjectUpdated
    audit_update = db_session.query(AuditEvent).filter(AuditEvent.event_name == "ProjectUpdated").first()
    assert audit_update is not None

    # 8. ProjectAssetLine Mutations
    # Create line -> 201
    resp = client.post(
        "/api/v1/projects/{}/asset-lines".format(proj_id),
        headers=headers_admin,
        json={
            "asset_name": "Asset 1",
            "quantity": 5.0,
            "unit_id": str(unit.id)
        }
    )
    assert resp.status_code == 201
    line_id = resp.json()["id"]

    # Verify audit event for ProjectAssetLineCreated
    audit_line = db_session.query(AuditEvent).filter(AuditEvent.event_name == "ProjectAssetLineCreated").first()
    assert audit_line is not None

    # List lines
    resp = client.get("/api/v1/projects/{}/asset-lines".format(proj_id), headers=headers_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Update line (row_version match) -> 200
    resp = client.patch(
        "/api/v1/projects/{}/asset-lines/{}".format(proj_id, line_id),
        headers=headers_admin,
        json={"quantity": 10.0, "row_version": 1}
    )
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 10.0

    # 9. ProjectFile Metadata Mutations (Metadata-only, no binary)
    resp = client.post(
        "/api/v1/projects/{}/files".format(proj_id),
        headers=headers_admin,
        json={
            "file_name": "inventory.xlsx",
            "file_category": "customer_excel",
            "file_size": 2048,
            "mime_type": "application/vnd.ms-excel",
            "storage_object_key": "raw/inv.xlsx",
            "checksum_sha256": "abcdef123"
        }
    )
    assert resp.status_code == 201
    file_id = resp.json()["id"]
    assert resp.json()["processing_status"] == "pending"

    # Verify audit event for ProjectFileUploaded
    audit_file = db_session.query(AuditEvent).filter(AuditEvent.event_name == "ProjectFileUploaded").first()
    assert audit_file is not None

    # List files
    resp = client.get("/api/v1/projects/{}/files".format(proj_id), headers=headers_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["id"] == file_id

    # 10. Archive project
    resp = client.post(f"/api/v1/projects/{proj_id}/archive", headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"

    # Verify audit event for ProjectArchived
    audit_arch = db_session.query(AuditEvent).filter(AuditEvent.event_name == "ProjectArchived").first()
    assert audit_arch is not None

    # 11. Cancel project
    resp = client.post(f"/api/v1/projects/{proj_id}/cancel", headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_openapi_loads_and_no_future_routes(client: TestClient) -> None:
    # Verify openapi.json contains projects paths
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "/api/v1/projects" in data["paths"]

    # Verify no Workbench or advanced workflow routes are implemented (returns 404)
    # E.g. QC submit route
    resp = client.post("/api/v1/workbench/submit")
    assert resp.status_code == 404

    # E.g. Document Intelligence/OCR route
    resp = client.post("/api/v1/ocr/import")
    assert resp.status_code == 404
