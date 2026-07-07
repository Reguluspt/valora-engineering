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


@pytest.fixture
def setup_user_and_headers(db_session: Session):
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

    return {
        "headers_admin": {"X-User-Id": str(user_admin.id)},
        "headers_viewer": {"X-User-Id": str(user_viewer.id)},
        "user_admin_id": user_admin.id
    }


def test_taxonomy_api_rbac_and_flow(client: TestClient, db_session: Session, setup_user_and_headers) -> None:
    headers_admin = setup_user_and_headers["headers_admin"]
    headers_viewer = setup_user_and_headers["headers_viewer"]

    # 1. Deny by default check
    resp = client.post(
        "/api/v1/taxonomy/nodes",
        headers=headers_viewer,
        json={"level": "domain", "code": "DOM-ELEC", "name_vi": "Thiết bị điện"}
    )
    assert resp.status_code == 403

    # 2. Create Domain Node successfully (Admin)
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
    assert audit.actor_user_id == setup_user_and_headers["user_admin_id"]

    # 3. Attempt to create CATEGORY under CATEGORY (violates Level order - DOMAIN -> CATEGORY)
    resp = client.post(
        "/api/v1/taxonomy/nodes",
        headers=headers_admin,
        json={"parent_id": dom_id, "level": "subcategory", "code": "SUB-INVALID", "name_vi": "Invalid Level Order"}
    )
    assert resp.status_code == 422

    # 4. Create CATEGORY correctly under DOMAIN
    resp = client.post(
        "/api/v1/taxonomy/nodes",
        headers=headers_admin,
        json={"parent_id": dom_id, "level": "category", "code": "CAT-DIST", "name_vi": "Phân phối"}
    )
    assert resp.status_code == 201
    cat_id = resp.json()["id"]

    # 5. Approve node (moves draft -> active)
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

    # 6. Create AssetFamily under active TaxonomyNode
    resp = client.post(
        "/api/v1/taxonomy/families",
        headers=headers_admin,
        json={"taxonomy_node_id": cat_id, "code": "FAM-CB", "name_vi": "Cầu dao"}
    )
    assert resp.status_code == 201
    fam_id = resp.json()["id"]

    # 7. Create AssetDNA draft
    resp = client.post(
        "/api/v1/taxonomy/dna",
        headers=headers_admin,
        json={"asset_family_id": fam_id, "version": 1, "name": "DNA Cầu dao v1"}
    )
    assert resp.status_code == 201
    dna_id = resp.json()["id"]

    # 8. Create AssetAttributeDefinition
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


def test_taxonomy_node_hierarchy_errors(client: TestClient, db_session: Session, setup_user_and_headers) -> None:
    headers_admin = setup_user_and_headers["headers_admin"]

    # 1. CATEGORY with no parent (422)
    resp = client.post(
        "/api/v1/taxonomy/nodes",
        headers=headers_admin,
        json={"level": "category", "code": "CAT-M", "name_vi": "Category"}
    )
    assert resp.status_code == 422

    # 2. DOMAIN with a parent (422)
    dom = TaxonomyNode(level=TaxonomyNodeLevel.DOMAIN, code="DOM-P", name_vi="Parent Domain", status=TaxonomyStatus.ACTIVE, created_by=setup_user_and_headers["user_admin_id"])
    db_session.add(dom)
    db_session.commit()

    resp = client.post(
        "/api/v1/taxonomy/nodes",
        headers=headers_admin,
        json={"parent_id": str(dom.id), "level": "domain", "code": "DOM-C", "name_vi": "Child Domain"}
    )
    assert resp.status_code == 422


def test_taxonomy_node_lifecycle(client: TestClient, db_session: Session, setup_user_and_headers) -> None:
    headers_admin = setup_user_and_headers["headers_admin"]

    resp = client.post(
        "/api/v1/taxonomy/nodes",
        headers=headers_admin,
        json={"level": "domain", "code": "DOM-L", "name_vi": "Lifecycle Node"}
    )
    node_id = resp.json()["id"]

    # 1. Submit review (draft -> pending_review)
    resp = client.post("/api/v1/taxonomy/nodes/{}/submit-review".format(node_id), headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_review"

    # Cannot submit review again
    resp = client.post("/api/v1/taxonomy/nodes/{}/submit-review".format(node_id), headers=headers_admin)
    assert resp.status_code == 400

    # 2. Approve (pending_review -> active)
    resp = client.post("/api/v1/taxonomy/nodes/{}/approve".format(node_id), headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    # 3. Deprecate (active -> deprecated)
    resp = client.post("/api/v1/taxonomy/nodes/{}/deprecate".format(node_id), headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["status"] == "deprecated"

    # Verify deprecation did not delete node from database (status-only check)
    node = db_session.query(TaxonomyNode).filter(TaxonomyNode.id == uuid.UUID(node_id)).first()
    assert node is not None
    assert node.status == TaxonomyStatus.DEPRECATED


def test_asset_family_errors(client: TestClient, db_session: Session, setup_user_and_headers) -> None:
    headers_admin = setup_user_and_headers["headers_admin"]

    dom = TaxonomyNode(level=TaxonomyNodeLevel.DOMAIN, code="DOM-F", name_vi="Domain F", status=TaxonomyStatus.ACTIVE, created_by=setup_user_and_headers["user_admin_id"])
    cat_draft = TaxonomyNode(parent_id=dom.id, level=TaxonomyNodeLevel.CATEGORY, code="CAT-DRAFT", name_vi="Draft Category", status=TaxonomyStatus.DRAFT, created_by=setup_user_and_headers["user_admin_id"])
    db_session.add_all([dom, cat_draft])
    db_session.commit()

    # Create family under draft taxonomy node (rejected/bad request)
    resp = client.post(
        "/api/v1/taxonomy/families",
        headers=headers_admin,
        json={"taxonomy_node_id": str(cat_draft.id), "code": "FAM-ERR", "name_vi": "Error"}
    )
    assert resp.status_code == 400


def test_asset_dna_uniqueness_and_activation(client: TestClient, db_session: Session, setup_user_and_headers) -> None:
    headers_admin = setup_user_and_headers["headers_admin"]

    dom = TaxonomyNode(level=TaxonomyNodeLevel.DOMAIN, code="DOM-DNA", name_vi="Domain", status=TaxonomyStatus.ACTIVE, created_by=setup_user_and_headers["user_admin_id"])
    db_session.add(dom)
    db_session.commit()

    fam = AssetFamily(taxonomy_node_id=dom.id, code="FAM-DNA", name_vi="Family", status=AssetFamilyStatus.ACTIVE)
    db_session.add(fam)
    db_session.commit()

    dna1 = AssetDNA(asset_family_id=fam.id, version=1, name="DNA 1", status=AssetDNAStatus.ACTIVE)
    dna2 = AssetDNA(asset_family_id=fam.id, version=2, name="DNA 2", status=AssetDNAStatus.DRAFT)
    db_session.add_all([dna1, dna2])
    db_session.commit()

    # Activating DNA 2 deactivates DNA 1
    resp = client.post("/api/v1/taxonomy/dna/{}/activate".format(dna2.id), headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    db_session.refresh(dna1)
    assert dna1.status == AssetDNAStatus.DEPRECATED


def test_attribute_definition_errors(client: TestClient, db_session: Session, setup_user_and_headers) -> None:
    headers_admin = setup_user_and_headers["headers_admin"]

    dom = TaxonomyNode(level=TaxonomyNodeLevel.DOMAIN, code="DOM-A", name_vi="Domain", status=TaxonomyStatus.ACTIVE, created_by=setup_user_and_headers["user_admin_id"])
    db_session.add(dom)
    db_session.commit()

    fam = AssetFamily(taxonomy_node_id=dom.id, code="FAM-A", name_vi="Family", status=AssetFamilyStatus.ACTIVE)
    db_session.add(fam)
    db_session.commit()

    dna = AssetDNA(asset_family_id=fam.id, version=1, name="DNA", status=AssetDNAStatus.DRAFT)
    db_session.add(dna)
    db_session.commit()

    # 1. Invalid key casing (should be rejected by Pydantic snake_case validation)
    resp = client.post(
        "/api/v1/taxonomy/attribute-definitions",
        headers=headers_admin,
        json={
            "asset_dna_id": str(dna.id),
            "key": "InvalidKeyCasing",
            "label_vi": "Label",
            "data_type": "string",
            "scope": "both"
        }
    )
    assert resp.status_code == 422

    # 2. Enum type missing enum_values
    resp = client.post(
        "/api/v1/taxonomy/attribute-definitions",
        headers=headers_admin,
        json={
            "asset_dna_id": str(dna.id),
            "key": "enum_attr",
            "label_vi": "Enum Label",
            "data_type": "enum",
            "scope": "both"
        }
    )
    assert resp.status_code == 422


def test_openapi_schema_loads(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert "paths" in resp.json()


def test_no_asset_identity_endpoints(client: TestClient) -> None:
    # Ensure asset identity endpoints are not exposed
    resp = client.post("/api/v1/asset-identity/candidates/generate-bulk")
    assert resp.status_code == 404
