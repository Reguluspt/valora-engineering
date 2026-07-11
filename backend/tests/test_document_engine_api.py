import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, User, UserStatus, Role, UserRole, Project,
    ProjectWorkflowStatus, Customer, DocumentTemplate, TemplateVersion, TemplateVersionStatus, GeneratedDocument,
    UserActionLog, AuditEvent
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
        code="document_admin",
        display_name="Document Admin",
        permissions=[
            "document_engine:read",
            "document_engine:template:create",
            "document_engine:template:update",
            "document_engine:template:deprecate",
            "document_engine:render:create",
            "document_engine:package:create",
            "document_engine:package:update"
        ]
    )
    role_viewer = Role(
        code="document_viewer",
        display_name="Document Viewer",
        permissions=[
            "document_engine:read"
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

    customer = Customer(organization_id=org.id, legal_name="Cust 1", status="active", created_by=user_admin.id)
    db_session.add(customer)
    db_session.commit()

    proj = Project(
        organization_id=org.id,
        code="PROJ-2026",
        name="Project 2026",
        status=ProjectWorkflowStatus.DRAFT,
        customer_id=customer.id,
        created_by=user_admin.id
    )
    db_session.add(proj)
    db_session.commit()

    return {
        "org_id": org.id,
        "admin_id": user_admin.id,
        "viewer_id": user_viewer.id,
        "project_id": proj.id
    }


def test_health_passes(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_openapi_loads(client: TestClient) -> None:
    res = client.get("/openapi.json")
    assert res.status_code == 200
    openapi = res.json()
    assert "/api/v1/document-engine/templates" in openapi["paths"]


def test_deny_by_default_rbac(client: TestClient) -> None:
    # Attempting to call list templates without authorization header should return 401
    res = client.get("/api/v1/document-engine/templates")
    assert res.status_code == 401

    # Invalid user ID header should return 401
    res = client.get("/api/v1/document-engine/templates", headers={"X-User-Id": "not-a-uuid"})
    assert res.status_code == 401


def test_document_template_endpoints(client: TestClient, setup_rbac_users) -> None:
    admin_headers = {"X-User-Id": str(setup_rbac_users["admin_id"])}
    viewer_headers = {"X-User-Id": str(setup_rbac_users["viewer_id"])}

    # 1. Create Template with Admin
    payload = {
        "organization_id": str(setup_rbac_users["org_id"]),
        "document_type": "qc_report",
        "code": "QC-T1",
        "name": "Quality Control Template",
        "description": "A template for QC reports",
        "status": "draft"
    }
    res = client.post("/api/v1/document-engine/templates", json=payload, headers=admin_headers)
    assert res.status_code == 201
    template = res.json()
    template_id = template["id"]
    assert template["code"] == "QC-T1"
    assert template["row_version"] == 1

    # 2. Deny Create Template with Viewer
    res = client.post("/api/v1/document-engine/templates", json=payload, headers=viewer_headers)
    assert res.status_code == 403

    # 3. List Templates with Viewer
    res = client.get("/api/v1/document-engine/templates", headers=viewer_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # 4. Get Template with Viewer
    res = client.get(f"/api/v1/document-engine/templates/{template_id}", headers=viewer_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Quality Control Template"

    # 5. Update Template with Admin
    update_payload = {
        "name": "QC Template Updated",
        "expected_row_version": 1
    }
    res = client.patch(f"/api/v1/document-engine/templates/{template_id}", json=update_payload, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "QC Template Updated"

    # 6. Verify row_version stale update returns 409 Conflict
    stale_payload = {
        "name": "Should Fail",
        "expected_row_version": 1  # Should be 2 now
    }
    res = client.patch(f"/api/v1/document-engine/templates/{template_id}", json=stale_payload, headers=admin_headers)
    assert res.status_code == 409


def test_template_version_uniqueness_and_deprecation(client: TestClient, setup_rbac_users, db_session: Session) -> None:
    admin_headers = {"X-User-Id": str(setup_rbac_users["admin_id"])}

    # Create template
    tpl = DocumentTemplate(
        organization_id=setup_rbac_users["org_id"],
        document_type="qc_report",
        code="VER-T1",
        name="Version Test Template",
        created_by=setup_rbac_users["admin_id"]
    )
    db_session.add(tpl)
    db_session.commit()

    # 1. Create Version 1
    v1_payload = {
        "version_number": 1,
        "template_format": "docx",
        "status": "draft"
    }
    res = client.post(f"/api/v1/document-engine/templates/{tpl.id}/versions", json=v1_payload, headers=admin_headers)
    assert res.status_code == 201
    v1 = res.json()
    assert v1["version_number"] == 1

    # 2. Prevent Duplicate Version Number
    res = client.post(f"/api/v1/document-engine/templates/{tpl.id}/versions", json=v1_payload, headers=admin_headers)
    assert res.status_code == 400

    # 3. Deprecate Version
    deprecate_payload = {
        "deprecation_reason": "Outdated standard",
        "expected_row_version": v1["row_version"]
    }
    res = client.post(f"/api/v1/document-engine/template-versions/{v1['id']}/deprecate", json=deprecate_payload, headers=admin_headers)
    assert res.status_code == 200
    deprecated_v = res.json()
    assert deprecated_v["status"] == "deprecated"
    assert deprecated_v["deprecation_reason"] == "Outdated standard"

    # 4. Verify historical versions are not deleted
    db_version = db_session.query(TemplateVersion).filter(TemplateVersion.id == uuid.UUID(v1["id"])).first()
    assert db_version is not None
    assert db_version.status == TemplateVersionStatus.DEPRECATED


def test_placeholder_bindings_and_expressions(client: TestClient, setup_rbac_users, db_session: Session) -> None:
    admin_headers = {"X-User-Id": str(setup_rbac_users["admin_id"])}

    tpl = DocumentTemplate(
        organization_id=setup_rbac_users["org_id"],
        document_type="report",
        code="PL-T1",
        name="Placeholders Template",
        created_by=setup_rbac_users["admin_id"]
    )
    db_session.add(tpl)
    db_session.commit()

    ver = TemplateVersion(
        document_template_id=tpl.id,
        version_number=1,
        template_format="docx",
        status=TemplateVersionStatus.ACTIVE
    )
    db_session.add(ver)
    db_session.commit()

    # 1. Create Placeholder
    pl_payload = {
        "placeholder_key": "customer.name",
        "label_vi": "Tên Khách Hàng",
        "data_type": "scalar",
        "source_context": "project",
        "source_path": "$.customer.legal_name"
    }
    res = client.post(f"/api/v1/document-engine/template-versions/{ver.id}/placeholders", json=pl_payload, headers=admin_headers)
    assert res.status_code == 201
    placeholder = res.json()
    assert placeholder["placeholder_key"] == "customer.name"

    # 2. Get list of Placeholders
    res = client.get(f"/api/v1/document-engine/template-versions/{ver.id}/placeholders", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1

    # 3. Create Binding
    bind_payload = {
        "template_placeholder_id": placeholder["id"],
        "binding_path": "$.customer.legal_name",
        "binding_type": "direct",
        "fallback_value": {"val": "Unknown"}
    }
    res = client.post(f"/api/v1/document-engine/template-versions/{ver.id}/bindings", json=bind_payload, headers=admin_headers)
    assert res.status_code == 201
    assert res.json()["binding_path"] == "$.customer.legal_name"

    # 4. Create Computed Expression (does not execute)
    expr_payload = {
        "placeholder_key": "tax.amount",
        "expression_type": "valora_expr",
        "inputs": {"subtotal": "$.project.fee_amount"},
        "expression": "subtotal * 0.1",
        "output_data_type": "currency"
    }
    res = client.post(f"/api/v1/document-engine/template-versions/{ver.id}/computed-expressions", json=expr_payload, headers=admin_headers)
    assert res.status_code == 201
    assert res.json()["expression"] == "subtotal * 0.1"


def test_mock_render_jobs_and_packages(client: TestClient, setup_rbac_users, db_session: Session) -> None:
    admin_headers = {"X-User-Id": str(setup_rbac_users["admin_id"])}

    tpl = DocumentTemplate(
        organization_id=setup_rbac_users["org_id"],
        document_type="contract",
        code="REND-T1",
        name="Contract Template",
        created_by=setup_rbac_users["admin_id"]
    )
    db_session.add(tpl)
    db_session.commit()

    ver = TemplateVersion(
        document_template_id=tpl.id,
        version_number=1,
        template_format="docx",
        status=TemplateVersionStatus.ACTIVE
    )
    db_session.add(ver)
    db_session.commit()

    # 1. Create Mock Render Job
    render_payload = {
        "project_id": str(setup_rbac_users["project_id"]),
        "template_version_id": str(ver.id),
        "render_mode": "official",
        "output_formats": ["docx", "pdf"],
        "data_snapshot": {"project_name": "Project 2026", "fee": 5000}
    }
    res = client.post("/api/v1/document-engine/render-jobs", json=render_payload, headers=admin_headers)
    assert res.status_code == 201
    job = res.json()
    assert job["status"] == "completed"
    assert job["data_snapshot"] == {"project_name": "Project 2026", "fee": 5000}
    assert job["data_snapshot_hash"] != ""

    # Verify GeneratedDocument records were created synchronously
    docs = db_session.query(GeneratedDocument).filter(GeneratedDocument.render_job_id == uuid.UUID(job["id"])).all()
    assert len(docs) == 2
    doc_id = docs[0].id

    # 2. Get GeneratedDocument Metadata
    res = client.get(f"/api/v1/document-engine/generated-documents/{doc_id}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["checksum_sha256"] == job["data_snapshot_hash"]

    # 3. Create Document Package
    pkg_payload = {
        "project_id": str(setup_rbac_users["project_id"]),
        "package_type": "qc",
        "name": "S5 Package",
        "status": "draft"
    }
    res = client.post("/api/v1/document-engine/packages", json=pkg_payload, headers=admin_headers)
    assert res.status_code == 201
    pkg = res.json()

    # 4. Add Package Item
    item_payload = {
        "generated_document_id": str(doc_id),
        "sort_order": 1
    }
    res = client.post(f"/api/v1/document-engine/packages/{pkg['id']}/items", json=item_payload, headers=admin_headers)
    assert res.status_code == 201
    assert res.json()["sort_order"] == 1


def test_audit_logs_created(client: TestClient, setup_rbac_users, db_session: Session) -> None:
    admin_headers = {"X-User-Id": str(setup_rbac_users["admin_id"])}

    # Trigger Template Creation
    payload = {
        "organization_id": str(setup_rbac_users["org_id"]),
        "document_type": "report",
        "code": "AUDIT-T1",
        "name": "Audit Test Template",
        "status": "draft"
    }
    res = client.post("/api/v1/document-engine/templates", json=payload, headers=admin_headers)
    assert res.status_code == 201
    tpl_id = res.json()["id"]

    # Verify AuditEvent was logged
    audit_events = db_session.query(AuditEvent).filter(AuditEvent.entity_id == uuid.UUID(tpl_id)).all()
    assert len(audit_events) > 0
    assert audit_events[0].event_name == "DOCUMENT_TEMPLATE_CREATE"

    # Verify UserActionLog was logged
    action_logs = db_session.query(UserActionLog).filter(UserActionLog.target_id == uuid.UUID(tpl_id)).all()
    assert len(action_logs) > 0
    assert action_logs[0].action_type == "create_template"
