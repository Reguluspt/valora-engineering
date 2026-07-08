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


def test_rbac_deny_by_default(client: TestClient, setup_rbac_users) -> None:
    # 1. No auth headers -> 401 Unauthorized
    resp = client.get("/api/v1/evidence/sources")
    assert resp.status_code == 401

    # 2. Viewer lacks update permission -> 403 Forbidden
    headers_viewer = {"X-User-Id": setup_rbac_users["viewer_id"]}
    resp = client.patch(
        f"/api/v1/evidence/sources/{uuid.uuid4()}",
        json={"name": "New"},
        headers=headers_viewer
    )
    assert resp.status_code == 403


def test_evidence_file_immutability(client: TestClient, db_session: Session, setup_rbac_users) -> None:
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

    # PATCH immutable parameters should be ignored by the Pydantic schemas
    resp = client.patch(
        f"/api/v1/evidence/files/{ev_file.id}",
        json={
            "description": "New description",
            "filename": "hacked.exe",
            "object_key": "hacked_key",
            "checksum": "hacked_checksum",
            "file_size": 999999,
            "expected_row_version": 1
        },
        headers=headers_admin
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["filename"] == "datasheet.pdf"
    assert res_data["object_key"] == "uploads/datasheet.pdf"
    assert res_data["checksum"] == "hash1"
    assert res_data["file_size"] == 1024


def test_concurrency_failures_returning_409(client: TestClient, db_session: Session, setup_rbac_users) -> None:
    headers_admin = {"X-User-Id": setup_rbac_users["admin_id"]}

    # 1. TechnicalSpecificationVersion Stale version check
    spec = TechnicalSpecification(created_by=uuid.UUID(setup_rbac_users["admin_id"]))
    db_session.add(spec)
    db_session.commit()

    v_draft = TechnicalSpecificationVersion(
        technical_specification_id=spec.id,
        version_number=1,
        attribute_values={"power": "110kV"},
        status=TechnicalSpecificationVersionStatus.DRAFT,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add(v_draft)
    db_session.commit()

    resp = client.patch(
        f"/api/v1/knowledge/technical-specifications/versions/{v_draft.id}",
        json={"attribute_values": {"power": "stale"}, "expected_row_version": 0},
        headers=headers_admin
    )
    assert resp.status_code == 409

    # 2. QuoteBatch Stale version check
    batch = QuoteBatch(
        created_by=uuid.UUID(setup_rbac_users["admin_id"]),
        status=QuoteBatchStatus.DRAFT,
        revision_number=1
    )
    db_session.add(batch)
    db_session.commit()

    resp = client.patch(
        f"/api/v1/knowledge/quote-batches/{batch.id}",
        json={"override_blocking_conflict_reason": "stale reason", "expected_row_version": 0},
        headers=headers_admin
    )
    assert resp.status_code == 409

    # 3. AppraisedPriceDecision Stale version check
    dec = AppraisedPriceDecision(
        final_unit_price=45000.0,
        currency="USD",
        rationale="Draft pricing entry",
        status=AppraisedPriceDecisionStatus.DRAFT,
        created_by=uuid.UUID(setup_rbac_users["admin_id"])
    )
    db_session.add(dec)
    db_session.commit()

    resp = client.patch(
        f"/api/v1/knowledge/appraised-price-decisions/{dec.id}",
        json={"final_unit_price": 48000.0, "expected_row_version": 0},
        headers=headers_admin
    )
    assert resp.status_code == 409

    # 4. KnowledgeQueueItem Stale claim check
    item = KnowledgeQueueItem(
        target_type="technical_specification_version",
        target_id=uuid.uuid4(),
        status=KnowledgeQueueItemStatus.PENDING,
        confidence_score=0.7500
    )
    db_session.add(item)
    db_session.commit()

    resp = client.post(
        f"/api/v1/knowledge/queue/{item.id}/claim?expected_row_version=0",
        headers=headers_admin
    )
    assert resp.status_code == 409

    # 5. KnowledgeConflict Stale resolve check
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

    resp = client.post(
        f"/api/v1/knowledge/conflicts/{conflict.id}/resolve?resolution_notes=stale&expected_row_version=0",
        headers=headers_admin
    )
    assert resp.status_code == 409


def test_forbidden_sprint_boundaries(client: TestClient) -> None:
    # Verify that unimplemented routes or forbidden byte streaming upload/download return 404 Not Found
    resp = client.get("/api/v1/evidence/download")
    assert resp.status_code == 404

    resp = client.post("/api/v1/evidence/upload")
    assert resp.status_code == 404
