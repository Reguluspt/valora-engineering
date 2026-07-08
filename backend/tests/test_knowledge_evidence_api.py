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
    src = EvidenceSource(name="Vendor Portal", source_type=EvidenceSourceType.SUPPLIER, description="Portal A")
    db_session.add(src)
    db_session.commit()

    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}

    # GET /api/v1/evidence/sources
    resp = client.get("/api/v1/evidence/sources", headers=headers_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # GET /api/v1/evidence/sources/{source_id}
    resp = client.get(f"/api/v1/evidence/sources/{src.id}", headers=headers_viewer)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Vendor Portal"

    # PATCH /api/v1/evidence/sources/{source_id}
    resp = client.patch(f"/api/v1/evidence/sources/{src.id}", json={"name": "Updated Portal"}, headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Portal"


def test_evidence_file_api_crud_and_delete(client: TestClient, db_session: Session, setup_rbac_users) -> None:
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

    # GET /api/v1/evidence/files/{evidence_file_id}
    resp = client.get(f"/api/v1/evidence/files/{ev_file.id}", headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["filename"] == "datasheet.pdf"

    # PATCH /api/v1/evidence/files/{evidence_file_id}
    resp = client.patch(
        f"/api/v1/evidence/files/{ev_file.id}",
        json={"description": "Updated description", "expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 200

    # DELETE /api/v1/evidence/files/{evidence_file_id} (soft-delete/archive)
    resp = client.delete(f"/api/v1/evidence/files/{ev_file.id}", headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


def test_evidence_links_endpoints(client: TestClient, db_session: Session, setup_rbac_users) -> None:
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

    # POST /api/v1/evidence/links
    target_id = uuid.uuid4()
    resp = client.post(
        "/api/v1/evidence/links",
        json={"evidence_file_id": str(ev_file.id), "target_type": "technical_spec", "target_id": str(target_id)},
        headers=headers_admin
    )
    assert resp.status_code == 201
    link_id = resp.json()["id"]

    # GET /api/v1/evidence/links
    resp = client.get("/api/v1/evidence/links", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # DELETE /api/v1/evidence/links/{link_id} (soft-unlink)
    resp = client.delete(f"/api/v1/evidence/links/{link_id}?reason=cleanup", headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["is_deleted"] is True


def test_evidence_access_logs(client: TestClient, db_session: Session, setup_rbac_users) -> None:
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

    log = EvidenceAccessLog(
        evidence_file_id=ev_file.id,
        accessed_by=uuid.UUID(setup_rbac_users["admin_id"]),
        access_type=EvidenceAccessType.DOWNLOAD,
        access_reason="Audit test review"
    )
    db_session.add(log)
    db_session.commit()

    # GET /api/v1/evidence/access-logs
    resp = client.get("/api/v1/evidence/access-logs", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_technical_specifications_endpoints(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}

    spec = TechnicalSpecification(created_by=uuid.UUID(setup_rbac_users["admin_id"]))
    db_session.add(spec)
    db_session.commit()

    v_draft = TechnicalSpecificationVersion(
        technical_specification_id=spec.id,
        version_number=1,
        attribute_values={"power": "220kV"},
        status=TechnicalSpecificationVersionStatus.DRAFT,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add(v_draft)
    db_session.commit()

    # GET /api/v1/knowledge/technical-specifications
    resp = client.get("/api/v1/knowledge/technical-specifications", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # GET /api/v1/knowledge/technical-specifications/{id}
    resp = client.get(f"/api/v1/knowledge/technical-specifications/{spec.id}", headers=headers_admin)
    assert resp.status_code == 200

    # PATCH /api/v1/knowledge/technical-specifications/versions/{version_id}
    resp = client.patch(
        f"/api/v1/knowledge/technical-specifications/versions/{v_draft.id}",
        json={"attribute_values": {"power": "changed"}, "expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["attribute_values"] == {"power": "changed"}


def test_quote_batches_endpoints(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}

    batch = QuoteBatch(
        created_by=uuid.UUID(setup_rbac_users["admin_id"]),
        status=QuoteBatchStatus.DRAFT,
        revision_number=1
    )
    db_session.add(batch)
    db_session.commit()

    # GET /api/v1/knowledge/quote-batches
    resp = client.get("/api/v1/knowledge/quote-batches", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # GET /api/v1/knowledge/quote-batches/{quote_batch_id}
    resp = client.get(f"/api/v1/knowledge/quote-batches/{batch.id}", headers=headers_admin)
    assert resp.status_code == 200

    # PATCH /api/v1/knowledge/quote-batches/{quote_batch_id}
    resp = client.patch(
        f"/api/v1/knowledge/quote-batches/{batch.id}",
        json={"override_blocking_conflict_reason": "Approved exception", "expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 200

    # POST /api/v1/knowledge/quote-batches/{quote_batch_id}/revise
    # First make batch active to revision
    batch.status = QuoteBatchStatus.ACTIVE
    db_session.commit()
    resp = client.post(f"/api/v1/knowledge/quote-batches/{batch.id}/revise", headers=headers_admin)
    assert resp.status_code == 201


def test_appraised_price_decisions_endpoints(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}

    dec_draft = AppraisedPriceDecision(
        final_unit_price=45000.0,
        currency="USD",
        rationale="Draft pricing entry",
        status=AppraisedPriceDecisionStatus.DRAFT,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add(dec_draft)
    db_session.commit()

    # GET /api/v1/knowledge/appraised-price-decisions
    resp = client.get("/api/v1/knowledge/appraised-price-decisions", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # GET /api/v1/knowledge/appraised-price-decisions/{decision_id}
    resp = client.get(f"/api/v1/knowledge/appraised-price-decisions/{dec_draft.id}", headers=headers_admin)
    assert resp.status_code == 200

    # PATCH /api/v1/knowledge/appraised-price-decisions/{decision_id}
    resp = client.patch(
        f"/api/v1/knowledge/appraised-price-decisions/{dec_draft.id}",
        json={"final_unit_price": 47000.0, "expected_row_version": 1},
        headers=headers_admin
    )
    assert resp.status_code == 200


def test_knowledge_queue_endpoints(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}

    item = KnowledgeQueueItem(
        target_type="technical_specification_version",
        target_id=uuid.uuid4(),
        status=KnowledgeQueueItemStatus.PENDING,
        confidence_score=0.7500
    )
    db_session.add(item)
    db_session.commit()

    # GET /api/v1/knowledge/queue
    resp = client.get("/api/v1/knowledge/queue", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # GET /api/v1/knowledge/queue/{queue_item_id}
    resp = client.get(f"/api/v1/knowledge/queue/{item.id}", headers=headers_admin)
    assert resp.status_code == 200

    # POST /api/v1/knowledge/queue/{queue_item_id}/claim
    resp = client.post(f"/api/v1/knowledge/queue/{item.id}/claim?expected_row_version=1", headers=headers_admin)
    assert resp.status_code == 200

    # POST /api/v1/knowledge/queue/{queue_item_id}/release
    resp = client.post(f"/api/v1/knowledge/queue/{item.id}/release?expected_row_version=2", headers=headers_admin)
    assert resp.status_code == 200

    # POST /api/v1/knowledge/queue/{queue_item_id}/review
    resp = client.post(f"/api/v1/knowledge/queue/{item.id}/review?status_choice=completed&expected_row_version=3", headers=headers_admin)
    assert resp.status_code == 200


def test_conflicts_endpoints(client: TestClient, db_session: Session, setup_rbac_users) -> None:
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

    # GET /api/v1/knowledge/conflicts
    resp = client.get("/api/v1/knowledge/conflicts", headers=headers_admin)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # GET /api/v1/knowledge/conflicts/{conflict_id}
    resp = client.get(f"/api/v1/knowledge/conflicts/{conflict.id}", headers=headers_admin)
    assert resp.status_code == 200

    # POST /api/v1/knowledge/conflicts/{conflict_id}/resolve
    resp = client.post(
        f"/api/v1/knowledge/conflicts/{conflict.id}/resolve?resolution_notes=Resolved&expected_row_version=1",
        headers=headers_admin
    )
    assert resp.status_code == 200
