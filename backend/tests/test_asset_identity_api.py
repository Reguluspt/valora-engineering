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
            "asset_identity:asset:read",
            "asset_identity:variant:create",
            "asset_identity:variant:update",
            "asset_identity:variant:read",
            "asset_identity:alias:create",
            "asset_identity:alias:update",
            "asset_identity:alias:read"
        ]
    )
    role_viewer = Role(
        code="viewer",
        display_name="Viewer",
        permissions=[
            "asset_identity:asset:read",
            "asset_identity:variant:read",
            "asset_identity:alias:read"
        ]
    )
    role_empty = Role(code="empty", display_name="No Perms", permissions=[])
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
        "headers_unauth": {"X-User-Id": str(user_unauth.id)},
        "user_admin_id": user_admin.id,
        "taxonomy_node_id": node.id,
        "asset_family_id": fam.id
    }


def test_asset_identity_rbac_and_flow(client: TestClient, db_session: Session, setup_user_and_headers) -> None:
    headers_admin = setup_user_and_headers["headers_admin"]
    headers_viewer = setup_user_and_headers["headers_viewer"]
    headers_unauth = setup_user_and_headers["headers_unauth"]
    fam_id = setup_user_and_headers["asset_family_id"]
    node_id = setup_user_and_headers["taxonomy_node_id"]

    # 1. Deny by default check (Unauth)
    resp = client.post(
        "/api/v1/asset-identity/assets",
        headers=headers_unauth,
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
    alias_id = resp.json()["id"]
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

    # 7. Verify read endpoints (GET) RBAC deny-by-default for unauth
    resp = client.get("/api/v1/asset-identity/assets", headers=headers_unauth)
    assert resp.status_code == 403

    resp = client.get("/api/v1/asset-identity/assets/{}".format(asset_id), headers=headers_unauth)
    assert resp.status_code == 403

    resp = client.get("/api/v1/asset-identity/assets/{}/variants".format(asset_id), headers=headers_unauth)
    assert resp.status_code == 403

    resp = client.get("/api/v1/asset-identity/variants/{}".format(var_id), headers=headers_unauth)
    assert resp.status_code == 403

    resp = client.get("/api/v1/asset-identity/aliases", headers=headers_unauth)
    assert resp.status_code == 403

    resp = client.get("/api/v1/asset-identity/aliases/{}".format(alias_id), headers=headers_unauth)
    assert resp.status_code == 403

    # 8. Verify read endpoints success for viewer
    resp = client.get("/api/v1/asset-identity/assets", headers=headers_viewer)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.get("/api/v1/asset-identity/assets/{}".format(asset_id), headers=headers_viewer)
    assert resp.status_code == 200

    resp = client.get("/api/v1/asset-identity/assets/{}/variants".format(asset_id), headers=headers_viewer)
    assert resp.status_code == 200

    resp = client.get("/api/v1/asset-identity/variants/{}".format(var_id), headers=headers_viewer)
    assert resp.status_code == 200

    resp = client.get("/api/v1/asset-identity/aliases", headers=headers_viewer)
    assert resp.status_code == 200

    resp = client.get("/api/v1/asset-identity/aliases/{}".format(alias_id), headers=headers_viewer)
    assert resp.status_code == 200

    # 9. Verify update endpoints (PATCH) RBAC deny-by-default for viewer (read-only)
    resp = client.patch(
        "/api/v1/asset-identity/assets/{}".format(asset_id),
        headers=headers_viewer,
        json={"standard_name": "Updated Name By Viewer"}
    )
    assert resp.status_code == 403

    # 10. Verify PATCH update success for admin
    resp = client.patch(
        "/api/v1/asset-identity/assets/{}".format(asset_id),
        headers=headers_admin,
        json={"standard_name": "Updated Name By Admin"}
    )
    assert resp.status_code == 200
    assert resp.json()["standard_name"] == "Updated Name By Admin"

    audit_update = db_session.query(AuditEvent).filter(AuditEvent.event_name == "CANONICAL_ASSET_UPDATE").first()
    assert audit_update is not None


def test_canonical_asset_validation(client: TestClient, db_session: Session, setup_user_and_headers) -> None:
    headers_admin = setup_user_and_headers["headers_admin"]
    node_id = setup_user_and_headers["taxonomy_node_id"]

    # Test missing family ID
    resp = client.post(
        "/api/v1/asset-identity/assets",
        headers=headers_admin,
        json={
            "asset_family_id": str(uuid.uuid4()),
            "primary_taxonomy_node_id": str(node_id),
            "standard_name": "Valid Name"
        }
    )
    assert resp.status_code == 422


def test_asset_variant_boundary(client: TestClient, db_session: Session, setup_user_and_headers) -> None:
    headers_admin = setup_user_and_headers["headers_admin"]
    fam_id = setup_user_and_headers["asset_family_id"]
    node_id = setup_user_and_headers["taxonomy_node_id"]

    # Pre-create two canonical assets
    c1 = CanonicalAsset(asset_family_id=fam_id, primary_taxonomy_node_id=node_id, standard_name="Asset 1", status=CanonicalAssetStatus.ACTIVE)
    c2 = CanonicalAsset(asset_family_id=fam_id, primary_taxonomy_node_id=node_id, standard_name="Asset 2", status=CanonicalAssetStatus.ACTIVE)
    db_session.add_all([c1, c2])
    db_session.commit()

    # 1. Non-existent parent asset variant creation -> fail
    resp = client.post(
        "/api/v1/asset-identity/assets/{}/variants".format(uuid.uuid4()),
        headers=headers_admin,
        json={"asset_family_id": str(fam_id), "code": "VAR-CODE", "display_name": "Name"}
    )
    assert resp.status_code == 404

    # 2. Same code under different assets -> success
    resp = client.post(
        "/api/v1/asset-identity/assets/{}/variants".format(c1.id),
        headers=headers_admin,
        json={"asset_family_id": str(fam_id), "code": "VAR-SHARED-CODE", "display_name": "Variant for C1"}
    )
    assert resp.status_code == 201

    resp = client.post(
        "/api/v1/asset-identity/assets/{}/variants".format(c2.id),
        headers=headers_admin,
        json={"asset_family_id": str(fam_id), "code": "VAR-SHARED-CODE", "display_name": "Variant for C2"}
    )
    assert resp.status_code == 201


def test_asset_alias_scoping(client: TestClient, db_session: Session, setup_user_and_headers) -> None:
    headers_admin = setup_user_and_headers["headers_admin"]
    fam_id = setup_user_and_headers["asset_family_id"]
    node_id = setup_user_and_headers["taxonomy_node_id"]

    c1 = CanonicalAsset(asset_family_id=fam_id, primary_taxonomy_node_id=node_id, standard_name="Asset 1", status=CanonicalAssetStatus.ACTIVE)
    c2 = CanonicalAsset(asset_family_id=fam_id, primary_taxonomy_node_id=node_id, standard_name="Asset 2", status=CanonicalAssetStatus.ACTIVE)
    db_session.add_all([c1, c2])
    db_session.commit()

    v1 = AssetVariant(canonical_asset_id=c1.id, asset_family_id=fam_id, code="VAR-1", display_name="Variant 1", status=AssetVariantStatus.ACTIVE)
    db_session.add(v1)
    db_session.commit()

    # 1. Canonical scope + variant ID not None -> fail
    resp = client.post(
        "/api/v1/asset-identity/assets/{}/aliases".format(c1.id),
        headers=headers_admin,
        json={
            "alias_scope": "canonical",
            "asset_variant_id": str(v1.id),
            "raw_alias": "Raw 1"
        }
    )
    assert resp.status_code == 422

    # 2. Variant scope + variant ID from different canonical asset -> fail
    resp = client.post(
        "/api/v1/asset-identity/assets/{}/aliases".format(c2.id),
        headers=headers_admin,
        json={
            "alias_scope": "variant",
            "asset_variant_id": str(v1.id),
            "raw_alias": "Raw 2"
        }
    )
    assert resp.status_code == 422


def test_no_hard_delete_restrictions(client: TestClient, db_session: Session, setup_user_and_headers) -> None:
    # Asset identity endpoints do not provide delete endpoints (status deprecation only)
    resp = client.delete("/api/v1/asset-identity/assets")
    assert resp.status_code in [404, 405]


def test_openapi_schema_loads(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert "paths" in resp.json()


def test_no_candidate_or_merge_endpoints(client: TestClient) -> None:
    # Verify no candidate matching or merge endpoints are exposed yet
    resp = client.post("/api/v1/asset-identity/candidates/generate-bulk")
    assert resp.status_code == 404

    resp = client.post("/api/v1/asset-identity/assets/merge")
    assert resp.status_code in [404, 405]
