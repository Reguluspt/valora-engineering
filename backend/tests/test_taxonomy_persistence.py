import uuid
import pytest
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserStatus,
    TaxonomyNode,
    TaxonomyNodeLevel,
    TaxonomyStatus,
    AssetFamily,
    AssetFamilyStatus,
    AssetDNA,
    AssetDNAStatus,
    AssetAttributeDefinition,
    AssetAttributeDataType,
    AssetAttributeScope,
    TaxonomyChangeRequest,
    TaxonomyChangeRequestStatus,
    Unit,
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_taxonomy_node_hierarchy(db_session: Session) -> None:
    # Seed creator user
    org = OrganizationProfile(
        legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id, email="tax@test.com", full_name="Tax User", status=UserStatus.ACTIVE
    )
    db_session.add(user)
    db_session.commit()

    # 1. Create root node
    root = TaxonomyNode(
        level=TaxonomyNodeLevel.DOMAIN,
        code="DOM-EQ",
        name_vi="Thiết bị",
        status=TaxonomyStatus.ACTIVE,
        created_by=user.id,
    )
    db_session.add(root)
    db_session.commit()

    assert root.parent_id is None

    # 2. Create child node
    child = TaxonomyNode(
        parent_id=root.id,
        level=TaxonomyNodeLevel.CATEGORY,
        code="CAT-PUMP",
        name_vi="Máy bơm",
        status=TaxonomyStatus.ACTIVE,
        created_by=user.id,
    )
    db_session.add(child)
    db_session.commit()

    assert child.parent_id == root.id
    assert len(root.children) == 1
    assert root.children[0].id == child.id

    # 3. Test uniqueness constraint on code
    dup = TaxonomyNode(
        level=TaxonomyNodeLevel.DOMAIN,
        code="DOM-EQ",
        name_vi="Duplicate",
        status=TaxonomyStatus.DRAFT,
        created_by=user.id,
    )
    db_session.add(dup)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_asset_family_and_dna_schemas(db_session: Session) -> None:
    org = OrganizationProfile(
        legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id,
        email="tax2@test.com",
        full_name="Tax User",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()

    node = TaxonomyNode(
        level=TaxonomyNodeLevel.GROUP,
        code="GRP-PUMP",
        name_vi="Bơm ly tâm",
        status=TaxonomyStatus.ACTIVE,
        created_by=user.id,
    )
    db_session.add(node)
    db_session.commit()

    unit = Unit(code="pcs", display_name="Pieces")
    db_session.add(unit)
    db_session.commit()

    # 1. Create family
    family = AssetFamily(
        taxonomy_node_id=node.id,
        code="FAM-PUMP-01",
        name_vi="Bơm ly tâm trục đứng",
        default_unit_id=unit.id,
        status=AssetFamilyStatus.ACTIVE,
    )
    db_session.add(family)
    db_session.commit()

    assert family.taxonomy_node_id == node.id
    assert family.default_unit_id == unit.id

    # 2. Create DNA templates
    dna1 = AssetDNA(
        asset_family_id=family.id, version=1, name="DNA Standard", status=AssetDNAStatus.ACTIVE
    )
    db_session.add(dna1)
    db_session.commit()

    # Attempt to create another ACTIVE DNA version in the same family (should fail uq index)
    dna2 = AssetDNA(
        asset_family_id=family.id, version=2, name="DNA New Version", status=AssetDNAStatus.ACTIVE
    )
    db_session.add(dna2)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Allowed to create DRAFT DNA version 2
    dna2.status = AssetDNAStatus.DRAFT
    db_session.add(dna2)
    db_session.commit()

    assert len(family.dna_schemas) == 2


def test_asset_attribute_definitions(db_session: Session) -> None:
    org = OrganizationProfile(
        legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    db_session.commit()

    node = TaxonomyNode(
        level=TaxonomyNodeLevel.GROUP,
        code="GRP-MOTOR",
        name_vi="Động cơ điện",
        status=TaxonomyStatus.ACTIVE,
        created_by=uuid.uuid4(),  # Mock ID
    )
    db_session.add(node)
    db_session.commit()

    family = AssetFamily(
        taxonomy_node_id=node.id,
        code="FAM-MOTOR",
        name_vi="Động cơ",
        status=AssetFamilyStatus.ACTIVE,
    )
    db_session.add(family)
    db_session.commit()

    dna = AssetDNA(
        asset_family_id=family.id, version=1, name="DNA Motor", status=AssetDNAStatus.ACTIVE
    )
    db_session.add(dna)
    db_session.commit()

    # 1. Create attribute definition
    attr = AssetAttributeDefinition(
        asset_dna_id=dna.id,
        key="power_kw",
        label_vi="Công suất (kW)",
        data_type=AssetAttributeDataType.NUMBER,
        scope=AssetAttributeScope.VARIANT,
        is_required=True,
        is_variant_defining=True,
    )
    db_session.add(attr)
    db_session.commit()

    assert attr.asset_dna_id == dna.id
    assert attr.key == "power_kw"
    assert attr.scope == AssetAttributeScope.VARIANT

    # 2. Attempt duplicate key in same DNA schema
    dup = AssetAttributeDefinition(
        asset_dna_id=dna.id,
        key="power_kw",
        label_vi="Duplicate",
        data_type=AssetAttributeDataType.STRING,
    )
    db_session.add(dup)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_taxonomy_change_request(db_session: Session) -> None:
    org = OrganizationProfile(
        legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id, email="u@test.com", full_name="User", status=UserStatus.ACTIVE
    )
    db_session.add(user)
    db_session.commit()

    # Create proposal request
    req = TaxonomyChangeRequest(
        organization_id=org.id,
        change_type="create_node",
        node_level="subcategory",
        code="PROP-SUB",
        name_vi="Proposed Subcategory",
        status=TaxonomyChangeRequestStatus.PENDING,
        created_by=user.id,
    )
    db_session.add(req)
    db_session.commit()

    assert req.organization_id == org.id
    assert req.status == TaxonomyChangeRequestStatus.PENDING
    assert req.created_by == user.id
