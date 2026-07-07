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
    IdentityReviewItem, IdentityReviewStatus, IdentityDecisionLog, IdentityDecisionType,
    CanonicalAsset, CanonicalAssetStatus, CanonicalAssetMaturity, AssetVariant, AssetVariantStatus
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

    # 2. Seed Taxonomy & Assets
    tax_node = TaxonomyNode(
        level=TaxonomyNodeLevel.GROUP,
        code="TRANS",
        name_vi="Transformers",
        status=TaxonomyStatus.ACTIVE,
        created_by=user_admin.id
    )
    db_session.add(tax_node)
    db_session.commit()

    family = AssetFamily(
        taxonomy_node_id=tax_node.id,
        code="TRANSFORMER",
        name_vi="Transformer Family",
        status=AssetFamilyStatus.ACTIVE
    )
    db_session.add(family)
    db_session.commit()

    canon_asset = CanonicalAsset(
        asset_family_id=family.id,
        primary_taxonomy_node_id=tax_node.id,
        standard_name="ABB Transformer 110kV Standard",
        maturity_level=CanonicalAssetMaturity.DRAFT,
        status=CanonicalAssetStatus.DRAFT
    )
    db_session.add(canon_asset)
    db_session.commit()

    variant = AssetVariant(
        canonical_asset_id=canon_asset.id,
        asset_family_id=family.id,
        code="ABB-110KV-VAR",
        display_name="ABB 110kV Variant",
        status=AssetVariantStatus.DRAFT
    )
    db_session.add(variant)
    db_session.commit()

    # 3. Seed Project & Asset Line
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

    # 4. Seed Candidate & Similarity Scores
    candidate = IdentityCandidate(
        project_asset_line_id=line.id,
        proposed_canonical_asset_id=canon_asset.id,
        proposed_asset_variant_id=variant.id,
        proposed_taxonomy_node_id=tax_node.id,
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

    # 5. Seed Review Item
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
        "line_id": line.id,
        "canon_asset_id": canon_asset.id,
        "variant_id": variant.id,
        "score_id": score.id
    }


def test_rbac_deny_by_default(client: TestClient, setup_data) -> None:
    cand_id = setup_data["candidate_id"]
    review_id = setup_data["review_item_id"]
    h_unauth = setup_data["headers_unauth"]

    # 1. Unauthenticated (no user headers) -> 401 Unauthorized
    assert client.get("/api/v1/asset-identity/candidates").status_code == 401
    assert client.get(f"/api/v1/asset-identity/candidates/{cand_id}").status_code == 401
    assert client.patch(f"/api/v1/asset-identity/candidates/{cand_id}", json={"status": "ignored"}).status_code == 401

    assert client.get("/api/v1/asset-identity/review-items").status_code == 401
    assert client.get(f"/api/v1/asset-identity/review-items/{review_id}").status_code == 401
    assert client.patch(f"/api/v1/asset-identity/review-items/{review_id}", json={"reviewer_note": "No"}).status_code == 401
    assert client.post(f"/api/v1/asset-identity/review-items/{review_id}/resolve", json={"review_status": "reviewed"}).status_code == 401

    # 2. Authenticated but unauthorized (headers present but no permissions) -> 403 Forbidden
    assert client.get("/api/v1/asset-identity/candidates", headers=h_unauth).status_code == 403
    assert client.get(f"/api/v1/asset-identity/candidates/{cand_id}", headers=h_unauth).status_code == 403
    assert client.patch(f"/api/v1/asset-identity/candidates/{cand_id}", headers=h_unauth, json={"status": "ignored"}).status_code == 403

    assert client.get("/api/v1/asset-identity/review-items", headers=h_unauth).status_code == 403
    assert client.get(f"/api/v1/asset-identity/review-items/{review_id}", headers=h_unauth).status_code == 403
    assert client.patch(f"/api/v1/asset-identity/review-items/{review_id}", headers=h_unauth, json={"reviewer_note": "No"}).status_code == 403
    assert client.post(f"/api/v1/asset-identity/review-items/{review_id}/resolve", headers=h_unauth, json={"review_status": "reviewed"}).status_code == 403


def test_viewer_role_read_only(client: TestClient, setup_data) -> None:
    cand_id = setup_data["candidate_id"]
    review_id = setup_data["review_item_id"]
    h_viewer = setup_data["headers_viewer"]

    # Allowed reads
    assert client.get("/api/v1/asset-identity/candidates", headers=h_viewer).status_code == 200
    assert client.get(f"/api/v1/asset-identity/candidates/{cand_id}", headers=h_viewer).status_code == 200
    assert client.get("/api/v1/asset-identity/review-items", headers=h_viewer).status_code == 200
    assert client.get(f"/api/v1/asset-identity/review-items/{review_id}", headers=h_viewer).status_code == 200

    # Denied mutations
    assert client.patch(f"/api/v1/asset-identity/candidates/{cand_id}", headers=h_viewer, json={"status": "ignored"}).status_code == 403
    assert client.patch(f"/api/v1/asset-identity/review-items/{review_id}", headers=h_viewer, json={"reviewer_note": "Note"}).status_code == 403
    assert client.post(f"/api/v1/asset-identity/review-items/{review_id}/resolve", headers=h_viewer, json={"review_status": "reviewed"}).status_code == 403


def test_candidate_patch_validation(client: TestClient, db_session: Session, setup_data) -> None:
    cand_id = setup_data["candidate_id"]
    h_admin = setup_data["headers_admin"]
    line_id = setup_data["line_id"]

    # 1. Invalid status value rejected
    resp = client.patch(f"/api/v1/asset-identity/candidates/{cand_id}", headers=h_admin, json={"status": "invalid_status"})
    assert resp.status_code == 422

    # 2. Stale row version rejected (409)
    resp = client.patch(f"/api/v1/asset-identity/candidates/{cand_id}", headers=h_admin, json={"status": "ignored", "row_version": 999})
    assert resp.status_code == 409

    # 3. Extra fields are ignored (status / row_version only allowed)
    resp = client.patch(
        f"/api/v1/asset-identity/candidates/{cand_id}",
        headers=h_admin,
        json={
            "status": "ignored",
            "confidence_score": 0.1,
            "match_method": "hacked"
        }
    )
    assert resp.status_code == 200
    db_session.expire_all()
    cand = db_session.query(IdentityCandidate).filter(IdentityCandidate.id == cand_id).one()
    assert cand.status == "ignored"
    # Ensure they are not modified
    assert float(cand.confidence_score) == 0.95
    assert cand.match_method == "deterministic"

    # 4. Does not create or update SimilarityScore
    scores = db_session.query(SimilarityScore).filter(SimilarityScore.identity_candidate_id == cand_id).all()
    assert len(scores) == 1
    assert float(scores[0].score) == 0.98

    # 5. Does not mutate ProjectAssetLine identity fields
    line = db_session.query(ProjectAssetLine).filter(ProjectAssetLine.id == line_id).one()
    assert line.approved_canonical_asset_id is None
    assert line.suggested_canonical_asset_id is None


def test_candidate_detail_read_only_similarity_scores(client: TestClient, db_session: Session, setup_data) -> None:
    cand_id = setup_data["candidate_id"]
    h_viewer = setup_data["headers_viewer"]

    # Fetch candidate
    resp = client.get(f"/api/v1/asset-identity/candidates/{cand_id}", headers=h_viewer)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["similarity_scores"]) == 1
    assert data["similarity_scores"][0]["component"] == "model_code_match"
    assert data["similarity_scores"][0]["score"] == 0.98

    # Verify score value in database is not changed and matches expectations (no score recomputation)
    db_score = db_session.query(SimilarityScore).filter(SimilarityScore.identity_candidate_id == cand_id).one()
    assert float(db_score.score) == 0.98


def test_review_item_patch_validation(client: TestClient, db_session: Session, setup_data) -> None:
    review_id = setup_data["review_item_id"]
    h_admin = setup_data["headers_admin"]
    line_id = setup_data["line_id"]

    # 1. Stale row version rejected (409)
    resp = client.patch(f"/api/v1/asset-identity/review-items/{review_id}", headers=h_admin, json={"reviewer_note": "stale", "row_version": 999})
    assert resp.status_code == 409

    # 2. Extra fields are ignored
    resp = client.patch(
        f"/api/v1/asset-identity/review-items/{review_id}",
        headers=h_admin,
        json={
            "reviewer_note": "Valid Note",
            "reviewed_by": str(uuid.uuid4())
        }
    )
    assert resp.status_code == 200
    db_session.expire_all()
    item = db_session.query(IdentityReviewItem).filter(IdentityReviewItem.id == review_id).one()
    assert item.reviewer_note == "Valid Note"
    assert item.reviewed_by is None

    # 3. Does not mutate ProjectAssetLine fields
    line = db_session.query(ProjectAssetLine).filter(ProjectAssetLine.id == line_id).one()
    assert line.approved_canonical_asset_id is None


def test_review_item_resolve_verification(client: TestClient, db_session: Session, setup_data) -> None:
    review_id = setup_data["review_item_id"]
    h_admin = setup_data["headers_admin"]
    line_id = setup_data["line_id"]
    canon_asset_id = setup_data["canon_asset_id"]
    variant_id = setup_data["variant_id"]

    # 1. Resolve queue item
    resp = client.post(
        f"/api/v1/asset-identity/review-items/{review_id}/resolve",
        headers=h_admin,
        json={
            "review_status": "reviewed",
            "reviewer_note": "Resolved and Approved",
            "decision_type": "approve_candidate",
            "details": {"approved_name": "ABB Standard"}
        }
    )
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "reviewed"

    # 2. Verify decision log appended
    dec_log = db_session.query(IdentityDecisionLog).filter(IdentityDecisionLog.project_asset_line_id == line_id).all()
    assert len(dec_log) == 1
    assert dec_log[0].decision_type == "approve_candidate"
    assert dec_log[0].details == {"approved_name": "ABB Standard"}

    # 3. Verify audit event logged
    audit = db_session.query(AuditEvent).filter(AuditEvent.event_name == "IDENTITY_REVIEW_ITEM_RESOLVE").first()
    assert audit is not None
    assert audit.entity_id == review_id

    # 4. Verify ProjectAssetLine was not mutated by resolve (suggested/approved identity fields remain null/unmutated)
    line = db_session.query(ProjectAssetLine).filter(ProjectAssetLine.id == line_id).one()
    assert line.approved_canonical_asset_id is None
    assert line.suggested_canonical_asset_id is None

    # 5. Verify CanonicalAsset and AssetVariant are not activated automatically (status remains DRAFT)
    canon_asset = db_session.query(CanonicalAsset).filter(CanonicalAsset.id == canon_asset_id).one()
    assert canon_asset.status == CanonicalAssetStatus.DRAFT

    variant = db_session.query(AssetVariant).filter(AssetVariant.id == variant_id).one()
    assert variant.status == AssetVariantStatus.DRAFT


def test_identity_decision_log_is_append_only(client: TestClient) -> None:
    # Direct mutations must return 404
    assert client.post("/api/v1/asset-identity/decision-logs").status_code == 404
    assert client.patch("/api/v1/asset-identity/decision-logs/some-uuid").status_code == 404
    assert client.put("/api/v1/asset-identity/decision-logs/some-uuid").status_code == 404
    assert client.delete("/api/v1/asset-identity/decision-logs/some-uuid").status_code == 404


def test_forbidden_routes(client: TestClient) -> None:
    # Unimplemented paths must return exactly 404 Not Found (not 405 Method Not Allowed)
    # 404 is because the path itself is not registered on the router.
    assert client.get("/api/v1/asset-identity/duplicates").status_code == 404
    assert client.post("/api/v1/asset-identity/duplicates").status_code == 404

    assert client.get("/api/v1/asset-identity/merge-decisions").status_code == 404
    assert client.post("/api/v1/asset-identity/merge-decisions").status_code == 404

    # For /api/v1/asset-identity/assets/merge, POST returns 405 due to routing overlap with /api/v1/asset-identity/assets/{asset_id}
    assert client.post("/api/v1/asset-identity/assets/merge").status_code == 405

    # For /candidates/batch-approve and generate-bulk, POST returns 405 due to routing overlap with /candidates/{candidate_id}
    assert client.post("/api/v1/asset-identity/candidates/batch-approve").status_code == 405
    assert client.post("/api/v1/asset-identity/candidates/generate-bulk").status_code == 405


def test_openapi_schema_loads(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "openapi" in schema
    assert "paths" in schema
