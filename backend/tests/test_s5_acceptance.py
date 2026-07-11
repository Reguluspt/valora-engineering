import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
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
    Project,
    ProjectWorkflowStatus,
    Customer,
    EvidenceFile,
    GeneratedDocument,
    UserActionLog,
    AuditEvent,
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
def setup_s5_rbac(db_session: Session):
    org = OrganizationProfile(
        legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    db_session.commit()

    role_admin = Role(
        code="s5_admin",
        display_name="S5 Admin",
        permissions=[
            "document_engine:read",
            "document_engine:template:create",
            "document_engine:template:update",
            "document_engine:template:deprecate",
            "document_engine:render:create",
            "document_engine:package:create",
            "document_engine:package:update",
            "document_intelligence:read",
            "document_intelligence:parse:create",
            "document_intelligence:field:update",
            "document_intelligence:diff:create",
            "document_intelligence:correction:create",
            "document_intelligence:correction:review",
        ],
    )
    role_viewer = Role(
        code="s5_viewer",
        display_name="S5 Viewer",
        permissions=["document_engine:read", "document_intelligence:read"],
    )
    db_session.add_all([role_admin, role_viewer])
    db_session.commit()

    user_admin = User(
        organization_id=org.id,
        email="admin@test.com",
        full_name="Admin User",
        status=UserStatus.ACTIVE,
    )
    user_viewer = User(
        organization_id=org.id,
        email="viewer@test.com",
        full_name="Viewer User",
        status=UserStatus.ACTIVE,
    )
    db_session.add_all([user_admin, user_viewer])
    db_session.commit()

    db_session.add(UserRole(user_id=user_admin.id, role_id=role_admin.id, is_active=True))
    db_session.add(UserRole(user_id=user_viewer.id, role_id=role_viewer.id, is_active=True))
    db_session.commit()

    ev_file = EvidenceFile(
        filename="scanned_proposal.pdf",
        mime_type="application/pdf",
        file_size=120000,
        object_key="evidence/scanned_proposal.pdf",
        checksum="checksum-proposal",
        uploaded_by=user_admin.id,
    )
    db_session.add(ev_file)
    db_session.commit()

    customer = Customer(
        organization_id=org.id, legal_name="Cust S5", status="active", created_by=user_admin.id
    )
    db_session.add(customer)
    db_session.commit()

    proj = Project(
        organization_id=org.id,
        code="PROJ-S5",
        name="Project S5 Acceptance",
        status=ProjectWorkflowStatus.DRAFT,
        customer_id=customer.id,
        created_by=user_admin.id,
    )
    db_session.add(proj)
    db_session.commit()

    return {
        "org_id": org.id,
        "admin_id": user_admin.id,
        "viewer_id": user_viewer.id,
        "project_id": proj.id,
        "evidence_file_id": ev_file.id,
    }


def test_s5_comprehensive_e2e_flow(client: TestClient, setup_s5_rbac, db_session: Session) -> None:
    admin_headers = {"X-User-Id": str(setup_s5_rbac["admin_id"])}
    viewer_headers = {"X-User-Id": str(setup_s5_rbac["viewer_id"])}

    # Phase 1: Document Template & Version Registry
    tpl_payload = {
        "organization_id": str(setup_s5_rbac["org_id"]),
        "document_type": "contract",
        "code": "S5-TPL-01",
        "name": "Sprint 5 Contract Template",
        "status": "draft",
    }
    res = client.post("/api/v1/document-engine/templates", json=tpl_payload, headers=admin_headers)
    assert res.status_code == 201
    template_id = res.json()["id"]

    v1_payload = {"version_number": 1, "template_format": "docx", "status": "draft"}
    res = client.post(
        f"/api/v1/document-engine/templates/{template_id}/versions",
        json=v1_payload,
        headers=admin_headers,
    )
    assert res.status_code == 201
    version_id = res.json()["id"]

    # Phase 2: Placeholders, Bindings & Computed Expressions
    pl_payload = {
        "placeholder_key": "project.fee",
        "label_vi": "Phí Dự Án",
        "data_type": "currency",
        "source_context": "project",
        "source_path": "$.project.fee_amount",
    }
    res = client.post(
        f"/api/v1/document-engine/template-versions/{version_id}/placeholders",
        json=pl_payload,
        headers=admin_headers,
    )
    assert res.status_code == 201
    placeholder_id = res.json()["id"]

    bind_payload = {
        "template_placeholder_id": placeholder_id,
        "binding_path": "$.project.fee_amount",
        "binding_type": "direct",
        "fallback_value": {"val": 0.0},
    }
    res = client.post(
        f"/api/v1/document-engine/template-versions/{version_id}/bindings",
        json=bind_payload,
        headers=admin_headers,
    )
    assert res.status_code == 201

    expr_payload = {
        "placeholder_key": "project.vat",
        "expression_type": "valora_expr",
        "inputs": {"fee": "$.project.fee_amount"},
        "expression": "fee * 0.1",
        "output_data_type": "currency",
    }
    res = client.post(
        f"/api/v1/document-engine/template-versions/{version_id}/computed-expressions",
        json=expr_payload,
        headers=admin_headers,
    )
    assert res.status_code == 201

    # Phase 3: Mock Rendering & Generated Document Metadata
    render_payload = {
        "project_id": str(setup_s5_rbac["project_id"]),
        "template_version_id": version_id,
        "render_mode": "official",
        "output_formats": ["docx"],
        "data_snapshot": {"project_name": "Project S5 Acceptance", "fee_amount": 10000.0},
    }
    res = client.post(
        "/api/v1/document-engine/render-jobs", json=render_payload, headers=admin_headers
    )
    assert res.status_code == 201
    job_id = res.json()["id"]

    # Verify mock generated document exists
    docs = (
        db_session.query(GeneratedDocument)
        .filter(GeneratedDocument.render_job_id == uuid.UUID(job_id))
        .all()
    )
    assert len(docs) == 1
    doc_id = docs[0].id

    # Add to package
    pkg_payload = {
        "project_id": str(setup_s5_rbac["project_id"]),
        "package_type": "client_delivery",
        "name": "S5 Delivery Package",
        "status": "draft",
    }
    res = client.post("/api/v1/document-engine/packages", json=pkg_payload, headers=admin_headers)
    assert res.status_code == 201
    pkg_id = res.json()["id"]

    item_payload = {"generated_document_id": str(doc_id), "sort_order": 1}
    res = client.post(
        f"/api/v1/document-engine/packages/{pkg_id}/items", json=item_payload, headers=admin_headers
    )
    assert res.status_code == 201

    # Phase 4: Parsed Document, Diffing, and Corrections (Drafts-only)
    parsed_payload = {
        "evidence_file_id": str(setup_s5_rbac["evidence_file_id"]),
        "document_type": "contract",
        "page_count": 1,
        "text_content_hash": "txhash123",
        "parse_status": "parsed",
    }
    res = client.post(
        "/api/v1/document-intelligence/parsed-documents", json=parsed_payload, headers=admin_headers
    )
    assert res.status_code == 201
    parsed_id = res.json()["id"]

    diff_payload = {
        "source_document_id": str(doc_id),
        "target_document_id": parsed_id,
        "diff_type": "generated_vs_edited",
        "status": "candidate",
        "diff_payload": {"text_diffs": []},
    }
    res = client.post(
        "/api/v1/document-intelligence/diffs", json=diff_payload, headers=admin_headers
    )
    assert res.status_code == 201

    corr_payload = {
        "target_type": "extracted_field",
        "target_id": str(uuid.uuid4()),
        "affects_approved_data": False,
        "correction_payload": {"corrected_value": 11000.0},
        "decision": "request_change",
        "decided_by": str(setup_s5_rbac["admin_id"]),
        "status": "draft",
    }
    res = client.post(
        f"/api/v1/document-intelligence/parsed-documents/{parsed_id}/corrections",
        json=corr_payload,
        headers=admin_headers,
    )
    assert res.status_code == 201
    corr_id = res.json()["id"]

    # Review correction
    review_payload = {
        "decision": "accept",
        "status": "reviewed",
        "expected_row_version": res.json()["row_version"],
    }
    res = client.post(
        f"/api/v1/document-intelligence/corrections/{corr_id}/review",
        json=review_payload,
        headers=admin_headers,
    )
    assert res.status_code == 200

    # Phase 5: Confirm official data was not mutated
    proj = db_session.query(Project).filter(Project.id == setup_s5_rbac["project_id"]).one()
    assert proj.code == "PROJ-S5"  # Intact

    # Confirm audit trail logged
    tpl_audit = (
        db_session.query(AuditEvent).filter(AuditEvent.entity_id == uuid.UUID(template_id)).first()
    )
    assert tpl_audit is not None
    assert tpl_audit.event_name == "DOCUMENT_TEMPLATE_CREATE"

    tpl_action = (
        db_session.query(UserActionLog)
        .filter(UserActionLog.target_id == uuid.UUID(template_id))
        .first()
    )
    assert tpl_action is not None
    assert tpl_action.action_type == "create_template"
