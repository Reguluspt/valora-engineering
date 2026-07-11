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
    ProjectWorkflowStatus, Customer, EvidenceFile, GeneratedDocument, GeneratedDocumentStatus,
    UserActionLog, AuditEvent,
    DocumentTemplate, TemplateVersion, TemplateVersionStatus, RenderJob, RenderJobStatus
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
        code="intel_admin",
        display_name="Intelligence Admin",
        permissions=[
            "document_intelligence:read",
            "document_intelligence:parse:create",
            "document_intelligence:field:update",
            "document_intelligence:diff:create",
            "document_intelligence:correction:create",
            "document_intelligence:correction:review"
        ]
    )
    role_viewer = Role(
        code="intel_viewer",
        display_name="Intelligence Viewer",
        permissions=[
            "document_intelligence:read"
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

    ev_file = EvidenceFile(
        filename="scanned_quote.pdf",
        mime_type="application/pdf",
        file_size=50000,
        object_key="evidence/scanned_quote.pdf",
        checksum="doc-hash-123",
        uploaded_by=user_admin.id
    )
    db_session.add(ev_file)
    db_session.commit()

    # Create project
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

    # Create generated document
    t = DocumentTemplate(
        organization_id=org.id,
        document_type="report",
        code="T_INTEL",
        name="Intel Template",
        created_by=user_admin.id
    )
    db_session.add(t)
    db_session.commit()

    v = TemplateVersion(
        document_template_id=t.id,
        version_number=1,
        template_format="docx",
        status=TemplateVersionStatus.ACTIVE
    )
    db_session.add(v)
    db_session.commit()

    job = RenderJob(
        project_id=proj.id,
        template_version_id=v.id,
        render_mode="draft",
        output_formats=["docx"],
        data_snapshot={"key": "val"},
        data_snapshot_hash="hash123",
        status=RenderJobStatus.COMPLETED,
        created_by=user_admin.id
    )
    db_session.add(job)
    db_session.commit()

    gen_doc = GeneratedDocument(
        project_id=proj.id,
        render_job_id=job.id,
        document_type="report",
        output_format="docx",
        filename="report.docx",
        storage_key="documents/report.docx",
        checksum_sha256="checksum",
        file_size_bytes=1024,
        template_version_id=v.id,
        data_snapshot_hash="hash123",
        status=GeneratedDocumentStatus.OFFICIAL
    )
    db_session.add(gen_doc)
    db_session.commit()

    return {
        "org_id": org.id,
        "admin_id": user_admin.id,
        "viewer_id": user_viewer.id,
        "project_id": proj.id,
        "evidence_file_id": ev_file.id,
        "generated_document_id": gen_doc.id
    }


def test_health_passes(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_openapi_loads(client: TestClient) -> None:
    res = client.get("/openapi.json")
    assert res.status_code == 200
    openapi = res.json()
    assert "/api/v1/document-intelligence/parsed-documents" in openapi["paths"]


def test_deny_by_default_rbac(client: TestClient) -> None:
    # Attempting to list parsed documents without authorization header should return 401
    res = client.get("/api/v1/document-intelligence/parsed-documents")
    assert res.status_code == 401


def test_parsed_documents_and_extracted_fields(client: TestClient, setup_rbac_users) -> None:
    admin_headers = {"X-User-Id": str(setup_rbac_users["admin_id"])}
    viewer_headers = {"X-User-Id": str(setup_rbac_users["viewer_id"])}

    # 1. Create ParsedDocument (metadata only)
    payload = {
        "evidence_file_id": str(setup_rbac_users["evidence_file_id"]),
        "document_type": "supplier_quote",
        "page_count": 2,
        "text_content_hash": "hash123",
        "parse_status": "candidate",
        "confidence_score": 0.9500
    }
    res = client.post("/api/v1/document-intelligence/parsed-documents", json=payload, headers=admin_headers)
    assert res.status_code == 201
    doc = res.json()
    assert doc["parse_status"] == "candidate"
    doc_id = doc["id"]

    # 2. Get ParsedDocument
    res = client.get(f"/api/v1/document-intelligence/parsed-documents/{doc_id}", headers=viewer_headers)
    assert res.status_code == 200
    assert res.json()["confidence_score"] == 0.9500

    # 3. Patch ParsedDocument
    patch_payload = {
        "parse_status": "parsed",
        "expected_row_version": doc["row_version"]
    }
    res = client.patch(f"/api/v1/document-intelligence/parsed-documents/{doc_id}", json=patch_payload, headers=admin_headers)
    assert res.status_code == 200
    patched_doc = res.json()
    assert patched_doc["parse_status"] == "parsed"

    # 4. Create ExtractedField
    field_payload = {
        "field_key": "total_cost",
        "field_label": "Total Cost",
        "extracted_value": {"raw": "3000 USD"},
        "normalized_value": {"amount": 3000.0, "currency": "USD"},
        "confidence_score": 0.9900,
        "source_page_number": 1,
        "status": "candidate"
    }
    res = client.post(f"/api/v1/document-intelligence/parsed-documents/{doc_id}/fields", json=field_payload, headers=admin_headers)
    assert res.status_code == 201
    field = res.json()
    assert field["field_key"] == "total_cost"

    # 5. Patch ExtractedField
    field_patch = {
        "status": "accepted",
        "expected_row_version": field["row_version"]
    }
    res = client.patch(f"/api/v1/document-intelligence/fields/{field['id']}", json=field_patch, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "accepted"


def test_document_diff_endpoints(client: TestClient, setup_rbac_users) -> None:
    admin_headers = {"X-User-Id": str(setup_rbac_users["admin_id"])}

    # Create target parsed document
    parsed_payload = {
        "evidence_file_id": str(setup_rbac_users["evidence_file_id"]),
        "document_type": "quote",
        "page_count": 1,
        "parse_status": "parsed"
    }
    res = client.post("/api/v1/document-intelligence/parsed-documents", json=parsed_payload, headers=admin_headers)
    parsed_id = res.json()["id"]

    # Create Diff record
    diff_payload = {
        "source_document_id": str(setup_rbac_users["generated_document_id"]),
        "target_document_id": str(parsed_id),
        "diff_type": "generated_vs_edited",
        "status": "candidate",
        "diff_payload": {"changes": []}
    }
    res = client.post("/api/v1/document-intelligence/diffs", json=diff_payload, headers=admin_headers)
    assert res.status_code == 201
    diff = res.json()
    assert diff["diff_type"] == "generated_vs_edited"

    # Get Diff
    res = client.get(f"/api/v1/document-intelligence/diffs/{diff['id']}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "candidate"


def test_document_correction_and_review(client: TestClient, setup_rbac_users, db_session: Session) -> None:
    admin_headers = {"X-User-Id": str(setup_rbac_users["admin_id"])}

    # Create parsed document
    parsed_payload = {
        "evidence_file_id": str(setup_rbac_users["evidence_file_id"]),
        "document_type": "quote",
        "page_count": 1,
        "parse_status": "parsed"
    }
    res = client.post("/api/v1/document-intelligence/parsed-documents", json=parsed_payload, headers=admin_headers)
    parsed_id = res.json()["id"]

    # 1. Create Correction Draft
    corr_payload = {
        "target_type": "extracted_field",
        "target_id": str(uuid.uuid4()),
        "affects_approved_data": False,
        "correction_payload": {"value": 1500},
        "decision": "request_change",
        "decided_by": str(setup_rbac_users["admin_id"]),
        "status": "draft"
    }
    res = client.post(f"/api/v1/document-intelligence/parsed-documents/{parsed_id}/corrections", json=corr_payload, headers=admin_headers)
    assert res.status_code == 201
    corr = res.json()
    assert corr["status"] == "draft"

    # 2. Get Correction Detail
    res = client.get(f"/api/v1/document-intelligence/corrections/{corr['id']}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["affects_approved_data"] is False

    # 3. Review Correction
    review_payload = {
        "decision": "accept",
        "status": "reviewed",
        "expected_row_version": corr["row_version"]
    }
    res = client.post(f"/api/v1/document-intelligence/corrections/{corr['id']}/review", json=review_payload, headers=admin_headers)
    assert res.status_code == 200
    reviewed_corr = res.json()
    assert reviewed_corr["decision"] == "accept"
    assert reviewed_corr["status"] == "reviewed"

    # 4. Verify official project data was NOT mutated
    proj = db_session.query(Project).filter(Project.id == setup_rbac_users["project_id"]).one()
    assert proj.code == "PROJ-2026"  # Intact


def test_audit_logs_created(client: TestClient, setup_rbac_users, db_session: Session) -> None:
    admin_headers = {"X-User-Id": str(setup_rbac_users["admin_id"])}

    # Create ParsedDocument
    payload = {
        "evidence_file_id": str(setup_rbac_users["evidence_file_id"]),
        "document_type": "quote",
        "page_count": 1,
        "parse_status": "candidate"
    }
    res = client.post("/api/v1/document-intelligence/parsed-documents", json=payload, headers=admin_headers)
    assert res.status_code == 201
    doc_id = res.json()["id"]

    # Verify AuditEvent was logged
    audit_events = db_session.query(AuditEvent).filter(AuditEvent.entity_id == uuid.UUID(doc_id)).all()
    assert len(audit_events) > 0
    assert audit_events[0].event_name == "PARSED_DOCUMENT_CREATE"

    # Verify UserActionLog was logged
    action_logs = db_session.query(UserActionLog).filter(UserActionLog.target_id == uuid.UUID(doc_id)).all()
    assert len(action_logs) > 0
    assert action_logs[0].action_type == "create_parsed_document"
