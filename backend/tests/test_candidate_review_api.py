import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus,
    User, UserStatus, Role, UserRole, AuditEvent,
    TaxonomyNode, TaxonomyNodeLevel, TaxonomyStatus,
    AssetFamily, AssetFamilyStatus,
    Project, ProjectWorkflowStatus, ProjectAssetLine,
    IdentityCandidate, IdentityCandidateStatus,
    SimilarityScore,
    IdentityReviewItem, IdentityReviewStatus, IdentityDecisionLog, IdentityDecisionType
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


@pytest.fixture
def setup_data(db_session: Session):
    # 1. Seed Org, Users, Roles
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    role_admin = Role(
        code="admin",
        display_name="Admin",
        permissions=[
            "asset_identity:candidate:read",
            "asset_identity:candidate:update",
            "asset_identity:review:read",
            "asset_identity:review:update"
        ]
    )
    role_viewer = Role(
        code="viewer",
        display_name="Viewer",
        permissions=[
            "asset_identity:candidate:read",
            "asset_identity:review:read"
        ]
    )
    role_empty = Role(code="empty", display_name="Empty", permissions=[])
    db_session.add_all([role_admin, role_viewer, role_empty])
    db_session.commit()

    user_admin = User(organization_id=org.id, email="admin@test.com", full_name="Admin User", status=UserStatus.ACTIVE)
    user_viewer = User(organization_id=org.id, email="viewer@test.com", full_name="Viewer User", status=UserStatus.ACTIVE)
    user_unauth = User(organization_id=org.id, email="unauth@test.com", full_name="Unauth User", status=UserStatus.ACTIVE)
    db_session.add_all([user_admin, user_viewer, user_unauth])
    db_session.commit()

    db_session.add(UserRole(user_id=user_admin.id, role_id=role_admin.id, is_active=True))
    db_session.add(UserRole(user_id=user_viewer.id, role_id=role_viewer.id, is_active=True))
    db_session.add(UserRole(user_id=user_unauth.id, role_id=role_empty.id, is_active=True))
    db_session.commit()

    # 2. Seed Project & Asset Line
    proj = Project(
        organization_id=org.id,
        code="PROJ-01",
        name="Project 01",
        status=ProjectWorkflowStatus.DRAFT,
        customer_id=uuid.uuid4(),
        created_by=user_admin.id
    )
    db_session.add(proj)
    db_session.commit()

    line = ProjectAssetLine(
        project_id=proj.id,
        asset_name="ABB Transformer 110kV",
        quantity=5.0,
        description="ABB Transformer 110kV"
    )
    db_session.add(line)
    db_session.commit()

    # 3. Seed Candidate & Similarity Scores
    candidate = IdentityCandidate(
        project_asset_line_id=line.id,
        status=IdentityCandidateStatus.PENDING,
        confidence_score=0.95,
        match_method="deterministic"
    )
    db_session.add(candidate)
    db_session.commit()

    score = SimilarityScore(
        identity_candidate_id=candidate.id,
        component="model_code_match",
        score=0.98,
        metadata_info={"matched_string": "110kV"}
    )
    db_session.add(score)
    db_session.commit()

    # 4. Seed Review Item
    review_item = IdentityReviewItem(
        project_asset_line_id=line.id,
        identity_candidate_id=candidate.id,
        review_status=IdentityReviewStatus.PENDING
    )
    db_session.add(review_item)
    db_session.commit()

    return {
        "headers_admin": {"X-User-Id": str(user_admin.id)},
        "headers_viewer": {"X-User-Id": str(user_viewer.id)},
        "headers_unauth": {"X-User-Id": str(user_unauth.id)},
        "candidate_id": candidate.id,
        "review_item_id": review_item.id,
        "line_id": line.id
    }


def test_candidate_endpoints(client: TestClient, db_session: Session, setup_data) -> None:
    h_admin = setup_data["headers_admin"]
    h_viewer = setup_data["headers_viewer"]
    h_unauth = setup_data["headers_unauth"]
    cand_id = setup_data["candidate_id"]

    # 1. RBAC GET deny-by-default for unauth
    resp = client.get("/api/v1/asset-identity/candidates", headers=h_unauth)
    assert resp.status_code == 403

    # 2. RBAC GET list/get details for viewer
    resp = client.get("/api/v1/asset-identity/candidates", headers=h_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["confidence_score"] == 0.95
    # SimilarityScore included as nested read-only details
    assert len(resp.json()[0]["similarity_scores"]) == 1
    assert resp.json()[0]["similarity_scores"][0]["component"] == "model_code_match"

    resp = client.get("/api/v1/asset-identity/candidates/{}".format(cand_id), headers=h_viewer)
    assert resp.status_code == 200

    # 3. RBAC PATCH update status for viewer -> fail
    resp = client.patch(
        "/api/v1/asset-identity/candidates/{}".format(cand_id),
        headers=h_viewer,
        json={"status": "ignored"}
    )
    assert resp.status_code == 403

    # 4. PATCH update status for admin -> success
    resp = client.patch(
        "/api/v1/asset-identity/candidates/{}".format(cand_id),
        headers=h_admin,
        json={"status": "ignored"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"

    # Verify audit event logged
    audit = db_session.query(AuditEvent).filter(AuditEvent.event_name == "IDENTITY_CANDIDATE_UPDATE").first()
    assert audit is not None

    # 5. Stale row version check -> 409
    resp = client.patch(
        "/api/v1/asset-identity/candidates/{}".format(cand_id),
        headers=h_admin,
        json={"status": "pending", "row_version": 999}
    )
    assert resp.status_code == 409


def test_review_item_endpoints(client: TestClient, db_session: Session, setup_data) -> None:
    h_admin = setup_data["headers_admin"]
    h_viewer = setup_data["headers_viewer"]
    h_unauth = setup_data["headers_unauth"]
    review_id = setup_data["review_item_id"]
    line_id = setup_data["line_id"]

    # 1. RBAC GET deny-by-default for unauth
    resp = client.get("/api/v1/asset-identity/review-items", headers=h_unauth)
    assert resp.status_code == 403

    # 2. RBAC GET list/get details for viewer
    resp = client.get("/api/v1/asset-identity/review-items", headers=h_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.get("/api/v1/asset-identity/review-items/{}".format(review_id), headers=h_viewer)
    assert resp.status_code == 200

    # 3. RBAC PATCH metadata for viewer -> fail
    resp = client.patch(
        "/api/v1/asset-identity/review-items/{}".format(review_id),
        headers=h_viewer,
        json={"reviewer_note": "Stale Review Notes"}
    )
    assert resp.status_code == 403

    # 4. PATCH metadata for admin -> success
    resp = client.patch(
        "/api/v1/asset-identity/review-items/{}".format(review_id),
        headers=h_admin,
        json={"reviewer_note": "Looks good"}
    )
    assert resp.status_code == 200
    assert resp.json()["reviewer_note"] == "Looks good"

    # Verify audit event logged
    audit = db_session.query(AuditEvent).filter(AuditEvent.event_name == "IDENTITY_REVIEW_ITEM_UPDATE").first()
    assert audit is not None

    # 5. Resolve review outcome for admin -> success & creates append-only log & does not mutate project lines
    resp = client.post(
        "/api/v1/asset-identity/review-items/{}/resolve".format(review_id),
        headers=h_admin,
        json={
            "review_status": "reviewed",
            "reviewer_note": "Resolving candidate",
            "decision_type": "approve_candidate",
            "details": {"approved_name": "ABB Transformer"}
        }
    )
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "reviewed"

    # Verify Audit log resolution trigger
    audit_res = db_session.query(AuditEvent).filter(AuditEvent.event_name == "IDENTITY_REVIEW_ITEM_RESOLVE").first()
    assert audit_res is not None

    # Verify Decision Log appended
    dec_log = db_session.query(IdentityDecisionLog).filter(IdentityDecisionLog.project_asset_line_id == line_id).first()
    assert dec_log is not None
    assert dec_log.decision_type == "approve_candidate"

    # Verify ProjectAssetLine was not mutated by resolve
    line = db_session.query(ProjectAssetLine).filter(ProjectAssetLine.id == line_id).first()
    assert line.approved_canonical_asset_id is None
    assert line.approved_asset_variant_id is None


def test_forbidden_duplicate_and_merge_routes(client: TestClient) -> None:
    resp = client.get("/api/v1/asset-identity/duplicates")
    assert resp.status_code in [404, 405]

    resp = client.post("/api/v1/asset-identity/merge-decisions")
    assert resp.status_code in [404, 405]

    resp = client.post("/api/v1/asset-identity/candidates/generate-bulk")
    assert resp.status_code in [404, 405]
