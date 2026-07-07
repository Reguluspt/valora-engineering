import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus,
    User, UserStatus, Role, UserRole, AuditEvent,
    TaxonomyNode, TaxonomyNodeLevel, TaxonomyStatus,
    AssetFamily, AssetFamilyStatus,
    CanonicalAsset, CanonicalAssetStatus,
    AssetVariant, AssetVariantStatus,
    AssetAlias, AssetAliasStatus
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
def setup_user_and_headers(db_session: Session):
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    role_admin = Role(
        code="admin",
        display_name="Admin",
        permissions=[
            "asset_identity:asset:create",
            "asset_identity:asset:update",
            "asset_identity:variant:create",
            "asset_identity:variant:update",
            "asset_identity:alias:create",
            "asset_identity:alias:update"
        ]
    )
    role_viewer = Role(code="viewer", display_name="Viewer", permissions=[])
    db_session.add_all([role_admin, role_viewer])
    db_session.commit()

    user_admin = User(organization_id=org.id, email="admin@test.com", full_name="Admin User", status=UserStatus.ACTIVE)
    user_viewer = User(organization_id=org.id, email="viewer@test.com", full_name="Viewer User", status=UserStatus.ACTIVE)
    db_session.add_all([user_admin, user_viewer])
    db_session.commit()

    db_session.add(UserRole(user_id=user_admin.id, role_id=role_admin.id, is_active=True))
    db_session.add(UserRole(user_id=user_viewer.id, role_id=role_viewer.id, is_active=True))
    db_session.commit()

    # Pre-seed Taxonomy
    node = TaxonomyNode(level=TaxonomyNodeLevel.GROUP, code="GRP-T", name_vi="Group T", status=TaxonomyStatus.ACTIVE, created_by=user_admin.id)
    db_session.add(node)
    db_session.commit()

    fam = AssetFamily(taxonomy_node_id=node.id, code="FAM-T", name_vi="Family T", status=AssetFamilyStatus.ACTIVE)
    db_session.add(fam)
    db_session.commit()

    return {
        "headers_admin": {"X-User-Id": str(user_admin.id)},
        "headers_viewer": {"X-User-Id": str(user_viewer.id)},
        "user_admin_id": user_admin.id,
        "taxonomy_node_id": node.id,
        "asset_family_id": fam.id
    }


def test_asset_identity_rbac_and_flow(client: TestClient, db_session: Session, setup_user_and_headers) -> None:
    headers_admin = setup_user_and_headers["headers_admin"]
    headers_viewer = setup_user_and_headers["headers_viewer"]
    fam_id = setup_user_and_headers["asset_family_id"]
    node_id = setup_user_and_headers["taxonomy_node_id"]

    # 1. Deny by default check
    resp = client.post(
        "/api/v1/asset-identity/assets",
        headers=headers_viewer,
        json={
            "asset_family_id": str(fam_id),
            "primary_taxonomy_node_id": str(node_id),
            "standard_name": "ABB Transformer 110kV"
        }
    )
    assert resp.status_code == 403

    # 2. Create Canonical Asset successfully (Admin)
    resp = client.post(
        "/api/v1/asset-identity/assets",
        headers=headers_admin,
        json={
            "asset_family_id": str(fam_id),
            "primary_taxonomy_node_id": str(node_id),
            "standard_name": "ABB Transformer 110kV"
        }
    )
    assert resp.status_code == 201
    asset_id = resp.json()["id"]

    # Verify audit event logged
    audit = db_session.query(AuditEvent).filter(AuditEvent.event_name == "CANONICAL_ASSET_CREATE").first()
    assert audit is not None

    # 3. Create Variant successfully
    resp = client.post(
        "/api/v1/asset-identity/assets/{}/variants".format(asset_id),
        headers=headers_admin,
        json={
            "asset_family_id": str(fam_id),
            "code": "VAR-ABB-10MVA",
            "display_name": "ABB Transformer 10MVA"
        }
    )
    assert resp.status_code == 201
    var_id = resp.json()["id"]

    # 4. Check Variant Uniqueness (same code under same asset -> fail)
    resp = client.post(
        "/api/v1/asset-identity/assets/{}/variants".format(asset_id),
        headers=headers_admin,
        json={
            "asset_family_id": str(fam_id),
            "code": "VAR-ABB-10MVA",
            "display_name": "ABB Transformer 10MVA Duplicate"
        }
    )
    assert resp.status_code == 409

    # 5. Create Alias (Canonical Scope)
    resp = client.post(
        "/api/v1/asset-identity/assets/{}/aliases".format(asset_id),
        headers=headers_admin,
        json={
            "alias_scope": "canonical",
            "raw_alias": "MBA ABB 110kV"
        }
    )
    assert resp.status_code == 201
    assert resp.json()["normalized_alias"] == "mba abb 110kv"

    # 6. Create Alias (Variant Scope) with missing variant ID -> fail
    resp = client.post(
        "/api/v1/asset-identity/assets/{}/aliases".format(asset_id),
        headers=headers_admin,
        json={
            "alias_scope": "variant",
            "raw_alias": "MBA ABB 10MVA"
        }
    )
    assert resp.status_code == 422


def test_no_candidate_or_merge_endpoints(client: TestClient) -> None:
    # Verify no candidate matching or merge endpoints are exposed yet
    resp = client.post("/api/v1/asset-identity/candidates/generate-bulk")
    assert resp.status_code == 404

    resp = client.post("/api/v1/asset-identity/assets/merge")
    assert resp.status_code in [404, 405]
