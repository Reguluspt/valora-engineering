import pytest
from sqlalchemy import create_engine
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
    CanonicalAsset,
    CanonicalAssetStatus,
    CanonicalAssetMaturity,
    CanonicalAssetAttributeValue,
    AttributeValueSource,
    Brand,
    Manufacturer,
    Country,
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


def test_canonical_asset_persistence(db_session: Session) -> None:
    # 1. Seed dependencies
    org = OrganizationProfile(
        legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id, email="asset@test.com", full_name="User", status=UserStatus.ACTIVE
    )
    db_session.add(user)
    db_session.commit()

    node = TaxonomyNode(
        level=TaxonomyNodeLevel.GROUP,
        code="GRP-TRANS",
        name_vi="Máy biến áp",
        status=TaxonomyStatus.ACTIVE,
        created_by=user.id,
    )
    db_session.add(node)
    db_session.commit()

    family = AssetFamily(
        taxonomy_node_id=node.id,
        code="FAM-TRANS",
        name_vi="Biến áp lực",
        status=AssetFamilyStatus.ACTIVE,
    )
    db_session.add(family)
    db_session.commit()

    brand = Brand(name="ABB")
    mfg = Manufacturer(legal_name="ABB Ltd", country_id=None)
    country = Country(iso2="CH", iso3="CHE", name_vi="Thụy Sĩ")
    db_session.add_all([brand, mfg, country])
    db_session.commit()

    # 2. Create Canonical Asset
    asset = CanonicalAsset(
        asset_family_id=family.id,
        primary_taxonomy_node_id=node.id,
        standard_name="Máy biến áp ABB 110kV",
        short_name="Biến áp ABB",
        brand_id=brand.id,
        manufacturer_id=mfg.id,
        country_id=country.id,
        model_code="ABB-110KV-01",
        maturity_level=CanonicalAssetMaturity.REVIEWED,
        status=CanonicalAssetStatus.ACTIVE,
    )
    db_session.add(asset)
    db_session.commit()

    assert asset.id is not None
    assert asset.asset_family_id == family.id
    assert asset.brand_id == brand.id
    assert asset.manufacturer_id == mfg.id
    assert asset.country_id == country.id

    # 3. Add Attribute Definitions and Values
    dna = AssetDNA(
        asset_family_id=family.id, version=1, name="DNA Transformer", status=AssetDNAStatus.ACTIVE
    )
    db_session.add(dna)
    db_session.commit()

    attr_def = AssetAttributeDefinition(
        asset_dna_id=dna.id,
        key="cooling_type",
        label_vi="Phương thức làm mát",
        data_type=AssetAttributeDataType.STRING,
        scope=AssetAttributeScope.CANONICAL,
    )
    db_session.add(attr_def)
    db_session.commit()

    val = CanonicalAssetAttributeValue(
        canonical_asset_id=asset.id,
        attribute_definition_id=attr_def.id,
        value_string="ONAN",
        source=AttributeValueSource.MANUAL,
        confidence_score=1.0,
    )
    db_session.add(val)
    db_session.commit()

    assert val.id is not None
    assert val.canonical_asset_id == asset.id
    assert val.attribute_definition_id == attr_def.id
    assert len(asset.attributes) == 1
    assert asset.attributes[0].value_string == "ONAN"
