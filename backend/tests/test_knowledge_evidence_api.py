import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, User, UserStatus, Role, UserRole, AuditEvent,
    EvidenceSource, EvidenceSourceType, EvidenceFile, EvidenceFileStatus, EvidenceSensitivityLevel,
    EvidenceLink, EvidenceAccessLog, EvidenceAccessType,
    TechnicalSpecification, TechnicalSpecificationVersion, TechnicalSpecificationVersionStatus,
    QuoteBatch, QuoteBatchStatus, QuoteLine, QuoteLineStatus,
    AppraisedPriceDecision, AppraisedPriceDecisionStatus,
    KnowledgeQueueItem, KnowledgeQueueItemStatus,
    KnowledgeConflict, KnowledgeConflictStatus, KnowledgeConflictSeverity
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
        code="admin",
        display_name="Admin",
        permissions=[
            "knowledge:read",
            "knowledge:create",
            "knowledge:update",
            "knowledge:approve",
            "knowledge:cleanup",
            "evidence:file:create",
            "evidence:file:update",
            "evidence:file:download_sensitive",
            "evidence:link:create",
            "evidence:link:delete",
            "evidence:source:update",
            "evidence:cleanup"
        ]
    )
    role_viewer = Role(
        code="viewer",
        display_name="Viewer",
        permissions=[
            "knowledge:read"
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

    return {
        "admin_id": str(user_admin.id),
        "viewer_id": str(user_viewer.id),
        "org_id": org.id
    }


def test_openapi_and_health(client: TestClient) -> None:
    # 1. Health check passes
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    # 2. OpenAPI schemas load
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    openapi = resp.json()
    assert "paths" in openapi
    assert "/api/v1/evidence/sources" in openapi["paths"]
    assert "/api/v1/knowledge/technical-specifications" in openapi["paths"]


def test_evidence_source_api(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    # Seed source
    src = EvidenceSource(name="Vendor Portal", source_type=EvidenceSourceType.SUPPLIER, description="Portal A")
    db_session.add(src)
    db_session.commit()

    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    # GET sources (viewer has access)
    resp = client.get("/api/v1/evidence/sources", headers=headers_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # GET source by id
    resp = client.get(f"/api/v1/evidence/sources/{src.id}", headers=headers_viewer)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Vendor Portal"

    # PATCH source (viewer Denied)
    resp = client.patch(f"/api/v1/evidence/sources/{src.id}", json={"name": "New Name"}, headers=headers_viewer)
    assert resp.status_code == 403

    # PATCH source (admin Allowed)
    resp = client.patch(f"/api/v1/evidence/sources/{src.id}", json={"name": "Updated Portal"}, headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Portal"

    # Verify AuditEvent created
    audit = db_session.query(AuditEvent).filter(AuditEvent.event_name == "EVIDENCE_SOURCE_UPDATE").first()
    assert audit is not None
    assert audit.entity_id == src.id


def test_evidence_file_api(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    
    ev_file = EvidenceFile(
        filename="datasheet.pdf",
        mime_type="application/pdf",
        file_size=1024,
        object_key="uploads/datasheet.pdf",
        checksum="hash1",
        sensitivity_level=EvidenceSensitivityLevel.NORMAL,
        status=EvidenceFileStatus.ACTIVE,
        uploaded_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add(ev_file)
    db_session.commit()

    # GET file
    resp = client.get(f"/api/v1/evidence/files/{ev_file.id}", headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["filename"] == "datasheet.pdf"

    # PATCH metadata (optimistic lock mismatch)
    resp = client.patch(
        f"/api/v1/evidence/files/{ev_file.id}",
        json={"description": "Updated", "expected_row_version": 99},
        headers=headers_admin
    )
    assert resp.status_code == 409
    assert "VAL_KNOW_CONFLICT_001" in resp.json()["detail"]

    # PATCH metadata (optimistic lock success)
    resp = client.patch(
        f"/api/v1/evidence/files/{ev_file.id}",
        json={"description": "Updated description", "expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["row_version"] == 2


def test_evidence_links_create_and_soft_unlink(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}

    ev_file = EvidenceFile(
        filename="datasheet.pdf",
        mime_type="application/pdf",
        file_size=1024,
        object_key="uploads/datasheet.pdf",
        checksum="hash1",
        sensitivity_level=EvidenceSensitivityLevel.NORMAL,
        status=EvidenceFileStatus.ACTIVE,
        uploaded_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add(ev_file)
    db_session.commit()

    # POST link
    target_id = uuid.uuid4()
    resp = client.post(
        "/api/v1/evidence/links",
        json={"evidence_file_id": str(ev_file.id), "target_type": "technical_spec", "target_id": str(target_id)},
        headers=headers_admin
    )
    assert resp.status_code == 201
    link_id = resp.json()["id"]

    # DELETE link (soft unlink)
    resp = client.delete(f"/api/v1/evidence/links/{link_id}?reason=cleanup", headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["is_deleted"] is True

    # Assert underlying file is not affected
    db_session.expire_all()
    assert db_session.query(EvidenceFile).filter(EvidenceFile.id == ev_file.id).count() == 1


def test_technical_specifications_api(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}

    spec = TechnicalSpecification(created_by=uuid.UUID(setup_rbac_users["admin_id"]))
    db_session.add(spec)
    db_session.commit()

    # Create active and draft versions
    v_active = TechnicalSpecificationVersion(
        technical_specification_id=spec.id,
        version_number=1,
        attribute_values={"power": "110kV"},
        status=TechnicalSpecificationVersionStatus.ACTIVE,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    v_draft = TechnicalSpecificationVersion(
        technical_specification_id=spec.id,
        version_number=2,
        attribute_values={"power": "220kV"},
        status=TechnicalSpecificationVersionStatus.DRAFT,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add_all([v_active, v_draft])
    db_session.commit()

    # GET list
    resp = client.get("/api/v1/knowledge/technical-specifications", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # PATCH active version (rejected with 422)
    resp = client.patch(
        f"/api/v1/knowledge/technical-specifications/versions/{v_active.id}",
        json={"attribute_values": {"power": "changed"}, "expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 422
    assert "VAL_KNOW_PATCH_001" in resp.json()["detail"]

    # PATCH draft version (success)
    resp = client.patch(
        f"/api/v1/knowledge/technical-specifications/versions/{v_draft.id}",
        json={"attribute_values": {"power": "changed"}, "expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["attribute_values"] == {"power": "changed"}


def test_quote_batch_revise(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}

    batch = QuoteBatch(
        created_by=uuid.UUID(setup_rbac_users["admin_id"]),
        status=QuoteBatchStatus.ACTIVE,
        revision_number=1
    )
    db_session.add(batch)
    db_session.commit()

    # POST revise (creates new draft version)
    resp = client.post(f"/api/v1/knowledge/quote-batches/{batch.id}/revise", headers=headers_admin)
    assert resp.status_code == 201
    revised = resp.json()
    assert revised["previous_quote_batch_id"] == str(batch.id)
    assert revised["revision_number"] == 2
    assert revised["status"] == "draft"


def test_appraised_price_decisions(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}

    dec_active = AppraisedPriceDecision(
        final_unit_price=50000.0,
        currency="USD",
        rationale="Approved catalog entry",
        status=AppraisedPriceDecisionStatus.ACTIVE,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    dec_draft = AppraisedPriceDecision(
        final_unit_price=45000.0,
        currency="USD",
        rationale="Draft pricing entry",
        status=AppraisedPriceDecisionStatus.DRAFT,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add_all([dec_active, dec_draft])
    db_session.commit()

    # PATCH active decision -> reject
    resp = client.patch(
        f"/api/v1/knowledge/appraised-price-decisions/{dec_active.id}",
        json={"final_unit_price": 55000.0, "expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 422
    assert "VAL_KNOW_PATCH_001" in resp.json()["detail"]

    # PATCH draft decision -> success
    resp = client.patch(
        f"/api/v1/knowledge/appraised-price-decisions/{dec_draft.id}",
        json={"final_unit_price": 47000.0, "expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["final_unit_price"] == 47000.0


def test_queue_workflow(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}

    item = KnowledgeQueueItem(
        target_type="technical_specification_version",
        target_id=uuid.uuid4(),
        status=KnowledgeQueueItemStatus.PENDING,
        confidence_score=0.7500
    )
    db_session.add(item)
    db_session.commit()

    # Claim
    resp = client.post(f"/api/v1/knowledge/queue/{item.id}/claim?expected_row_version=1", headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["status"] == "claimed"
    assert resp.json()["claimed_by"] == setup_rbac_users["admin_id"]

    # Release
    resp = client.post(f"/api/v1/knowledge/queue/{item.id}/release?expected_row_version=2", headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    assert resp.json()["claimed_by"] is None

    # Review
    resp = client.post(f"/api/v1/knowledge/queue/{item.id}/review?status_choice=completed&expected_row_version=3", headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


def test_conflicts_api(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}

    conflict = KnowledgeConflict(
        target_type="quote_batch",
        target_id=uuid.uuid4(),
        conflict_type="quote_price_variance",
        severity=KnowledgeConflictSeverity.WARNING,
        status=KnowledgeConflictStatus.OPEN,
        calculated_value=25.0,
        threshold_value=20.0
    )
    db_session.add(conflict)
    db_session.commit()

    # GET conflicts
    resp = client.get("/api/v1/knowledge/conflicts", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # POST resolve
    resp = client.post(
        f"/api/v1/knowledge/conflicts/{conflict.id}/resolve?resolution_notes=Resolved+via+renegotiation&expected_row_version=1",
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
    assert resp.json()["resolution_notes"] == "Resolved via renegotiation"
