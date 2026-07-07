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
    AssetFamily, AssetFamilyStatus, AssetDNA, AssetDNAStatus,
    AssetAttributeDefinition, AssetAttributeDataType, AssetAttributeScope
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


def test_taxonomy_api_rbac_and_flow(client: TestClient, db_session: Session) -> None:
    # 1. Seed org, users, and roles
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    role_admin = Role(
        code="admin",
        display_name="Admin",
        permissions=[
            "taxonomy:node:create",
            "taxonomy:node:update",
            "taxonomy:node:approve",
            "taxonomy:node:deprecate"
        ]
    )
    role_viewer = Role(
        code="viewer",
        display_name="Viewer",
        permissions=[]
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

    headers_admin = {"X-User-Id": str(user_admin.id)}
    headers_viewer = {"X-User-Id": str(user_viewer.id)}

    # 2. Deny by default check
    resp = client.post(
        "/api/v1/taxonomy/nodes",
        headers=headers_viewer,
        json={"level": "domain", "code": "DOM-ELEC", "name_vi": "Thiết bị điện"}
    )
    assert resp.status_code == 403

    # 3. Create Domain Node successfully (Admin)
    resp = client.post(
        "/api/v1/taxonomy/nodes",
        headers=headers_admin,
        json={"level": "domain", "code": "DOM-ELEC", "name_vi": "Thiết bị điện"}
    )
    assert resp.status_code == 201
    dom_id = resp.json()["id"]

    # Verify audit event logged
    audit = db_session.query(AuditEvent).filter(AuditEvent.event_name == "TAXONOMY_NODE_CREATE").first()
    assert audit is not None
    assert audit.actor_user_id == user_admin.id

    # 4. Attempt to create CATEGORY under CATEGORY (violates Level order - DOMAIN -> CATEGORY)
    resp = client.post(
        "/api/v1/taxonomy/nodes",
        headers=headers_admin,
        json={"parent_id": dom_id, "level": "subcategory", "code": "SUB-INVALID", "name_vi": "Invalid Level Order"}
    )
    assert resp.status_code == 422

    # 5. Create CATEGORY correctly under DOMAIN
    resp = client.post(
        "/api/v1/taxonomy/nodes",
        headers=headers_admin,
        json={"parent_id": dom_id, "level": "category", "code": "CAT-DIST", "name_vi": "Phân phối"}
    )
    assert resp.status_code == 201
    cat_id = resp.json()["id"]

    # 6. Approve node (moves draft -> active)
    resp = client.post(
        "/api/v1/taxonomy/nodes/{}/approve".format(dom_id),
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    resp = client.post(
        "/api/v1/taxonomy/nodes/{}/approve".format(cat_id),
        headers=headers_admin
    )
    assert resp.status_code == 200

    # 7. Create AssetFamily under active TaxonomyNode
    resp = client.post(
        "/api/v1/taxonomy/families",
        headers=headers_admin,
        json={"taxonomy_node_id": cat_id, "code": "FAM-CB", "name_vi": "Cầu dao"}
    )
    assert resp.status_code == 201
    fam_id = resp.json()["id"]

    # 8. Create AssetDNA draft
    resp = client.post(
        "/api/v1/taxonomy/dna",
        headers=headers_admin,
        json={"asset_family_id": fam_id, "version": 1, "name": "DNA Cầu dao v1"}
    )
    assert resp.status_code == 201
    dna_id = resp.json()["id"]

    # 9. Create AssetAttributeDefinition
    # Check constraint: variant-defining attributes cannot have canonical scope
    resp = client.post(
        "/api/v1/taxonomy/attribute-definitions",
        headers=headers_admin,
        json={
            "asset_dna_id": dna_id,
            "key": "rated_current",
            "label_vi": "Dòng định mức",
            "data_type": "number",
            "scope": "canonical",
            "is_variant_defining": True
        }
    )
    assert resp.status_code == 422 # VAL_TAX_DNA_002 scope mismatch

    # Correct creation
    resp = client.post(
        "/api/v1/taxonomy/attribute-definitions",
        headers=headers_admin,
        json={
            "asset_dna_id": dna_id,
            "key": "rated_current",
            "label_vi": "Dòng định mức",
            "data_type": "number",
            "scope": "variant",
            "is_variant_defining": True
        }
    )
    assert resp.status_code == 201

    # 10. Activate DNA & ensure active DNA uniqueness
    resp = client.post(
        "/api/v1/taxonomy/dna/{}/activate".format(dna_id),
        headers=headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


def test_no_asset_identity_endpoints(client: TestClient) -> None:
    # Ensure asset identity endpoints are not exposed
    resp = client.post("/api/v1/asset-identity/candidates/generate-bulk")
    assert resp.status_code == 404
