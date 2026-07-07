import uuid
import pytest
from sqlalchemy import create_engine, exc, inspect, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus,
    User, UserStatus,
    TaxonomyNode, TaxonomyNodeLevel, TaxonomyStatus,
    AssetFamily, AssetFamilyStatus,
    CanonicalAsset, CanonicalAssetStatus,
    AssetVariant, AssetVariantStatus,
    Project, ProjectAssetLine, Customer
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
        Base.metadata.drop_all(bind=engine)


def test_project_asset_line_identity_nullable(db_session: Session) -> None:
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    user = User(organization_id=org.id, email="pal@test.com", full_name="User", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    customer = Customer(organization_id=org.id, legal_name="Cust 1", status="active", created_by=user.id)
    db_session.add(customer)
    db_session.commit()

    project = Project(organization_id=org.id, customer_id=customer.id, code="PRJ-1", name="Project 1", created_by=user.id)
    db_session.add(project)
    db_session.commit()

    # 1. ProjectAssetLine can exist without identity references
    line = ProjectAssetLine(
        project_id=project.id,
        asset_name="Standard Asset Line",
        quantity=1.0
    )
    db_session.add(line)
    db_session.commit()

    assert line.id is not None
    assert line.suggested_canonical_asset_id is None
    assert line.approved_canonical_asset_id is None


def test_project_asset_line_identity_relationships(db_session: Session) -> None:
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    user = User(organization_id=org.id, email="pal2@test.com", full_name="User", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    node = TaxonomyNode(
        level=TaxonomyNodeLevel.GROUP,
        code="GRP-TRANS",
        name_vi="Máy biến áp",
        status=TaxonomyStatus.ACTIVE,
        created_by=user.id
    )
    db_session.add(node)
    db_session.commit()

    family = AssetFamily(taxonomy_node_id=node.id, code="FAM-TRANS", name_vi="Biến áp lực", status=AssetFamilyStatus.ACTIVE)
    db_session.add(family)
    db_session.commit()

    asset = CanonicalAsset(
        asset_family_id=family.id,
        primary_taxonomy_node_id=node.id,
        standard_name="Máy biến áp ABB 110kV",
        status=CanonicalAssetStatus.ACTIVE
    )
    db_session.add(asset)
    db_session.commit()

    variant = AssetVariant(
        canonical_asset_id=asset.id,
        asset_family_id=family.id,
        code="ABB-110KV-V1",
        display_name="Phiên bản 1",
        status=AssetVariantStatus.ACTIVE
    )
    db_session.add(variant)
    db_session.commit()

    customer = Customer(organization_id=org.id, legal_name="Cust 1", status="active", created_by=user.id)
    db_session.add(customer)
    db_session.commit()

    project = Project(organization_id=org.id, customer_id=customer.id, code="PRJ-1", name="Project 1", created_by=user.id)
    db_session.add(project)
    db_session.commit()

    # 1. Assign suggested but keep approved empty
    line = ProjectAssetLine(
        project_id=project.id,
        asset_name="MBA ABB",
        quantity=1.0,
        suggested_taxonomy_node_id=node.id,
        suggested_canonical_asset_id=asset.id,
        suggested_asset_variant_id=variant.id
    )
    db_session.add(line)
    db_session.commit()

    assert line.suggested_canonical_asset_id == asset.id
    assert line.approved_canonical_asset_id is None
    assert line.suggested_canonical_asset.standard_name == "Máy biến áp ABB 110kV"
    assert line.suggested_asset_variant.code == "ABB-110KV-V1"

    # 2. Deleting CanonicalAsset should fail due to RESTRICT FK constraint
    db_session.delete(asset)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()
