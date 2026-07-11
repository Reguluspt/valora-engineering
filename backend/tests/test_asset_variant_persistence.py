import pytest
from sqlalchemy import create_engine, exc, event
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
    AssetVariant,
    AssetVariantStatus,
    AssetVariantAttributeValue,
    AttributeValueSource,
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
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


def test_asset_variant_persistence(db_session: Session) -> None:
    # 1. Seed dependencies
    org = OrganizationProfile(
        legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id, email="variant@test.com", full_name="User", status=UserStatus.ACTIVE
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

    asset = CanonicalAsset(
        asset_family_id=family.id,
        primary_taxonomy_node_id=node.id,
        standard_name="Máy biến áp ABB 110kV",
        status=CanonicalAssetStatus.ACTIVE,
    )
    db_session.add(asset)
    db_session.commit()

    # 2. Create Asset Variant
    variant = AssetVariant(
        asset_family_id=family.id,
        canonical_asset_id=asset.id,
        code="VAR-ABB-110KV-10MVA",
        display_name="Máy biến áp ABB 110kV 10MVA",
        status=AssetVariantStatus.ACTIVE,
    )
    db_session.add(variant)
    db_session.commit()

    assert variant.id is not None
    assert variant.asset_family_id == family.id
    assert variant.canonical_asset_id == asset.id

    # 3. Test uniqueness constraint on code within the same Canonical Asset (should fail)
    dup = AssetVariant(
        asset_family_id=family.id,
        canonical_asset_id=asset.id,
        code="VAR-ABB-110KV-10MVA",
        display_name="Duplicate Code",
        status=AssetVariantStatus.DRAFT,
    )
    db_session.add(dup)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Allowed: same code but on a different canonical asset
    asset2 = CanonicalAsset(
        asset_family_id=family.id,
        primary_taxonomy_node_id=node.id,
        standard_name="Máy biến áp ABB 110kV 2",
        status=CanonicalAssetStatus.ACTIVE,
    )
    db_session.add(asset2)
    db_session.commit()

    variant_diff_canonical = AssetVariant(
        asset_family_id=family.id,
        canonical_asset_id=asset2.id,
        code="VAR-ABB-110KV-10MVA",
        display_name="Same Code Diff Canonical",
        status=AssetVariantStatus.ACTIVE,
    )
    db_session.add(variant_diff_canonical)
    db_session.commit()

    # 4. Add Attribute Definitions and Values
    dna = AssetDNA(
        asset_family_id=family.id, version=1, name="DNA Transformer", status=AssetDNAStatus.ACTIVE
    )
    db_session.add(dna)
    db_session.commit()

    attr_def = AssetAttributeDefinition(
        asset_dna_id=dna.id,
        key="capacity_mva",
        label_vi="Dung lượng (MVA)",
        data_type=AssetAttributeDataType.NUMBER,
        scope=AssetAttributeScope.VARIANT,
    )
    db_session.add(attr_def)
    db_session.commit()

    val = AssetVariantAttributeValue(
        asset_variant_id=variant.id,
        attribute_definition_id=attr_def.id,
        value_number=10.0,
        source=AttributeValueSource.MANUAL,
        confidence_score=1.0,
    )
    db_session.add(val)
    db_session.commit()

    assert val.id is not None
    assert val.asset_variant_id == variant.id
    assert val.attribute_definition_id == attr_def.id
    assert len(variant.attributes) == 1
    assert variant.attributes[0].value_number == 10.0


def test_parent_deletion_restricted(db_session: Session) -> None:
    org = OrganizationProfile(
        legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id, email="del@test.com", full_name="User", status=UserStatus.ACTIVE
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

    asset = CanonicalAsset(
        asset_family_id=family.id,
        primary_taxonomy_node_id=node.id,
        standard_name="Máy biến áp ABB 110kV",
        status=CanonicalAssetStatus.ACTIVE,
    )
    db_session.add(asset)
    db_session.commit()

    variant = AssetVariant(
        asset_family_id=family.id,
        canonical_asset_id=asset.id,
        code="VAR-ABB-110KV-10MVA",
        display_name="Máy biến áp ABB 110kV 10MVA",
        status=AssetVariantStatus.ACTIVE,
    )
    db_session.add(variant)
    db_session.commit()

    # Attempt to delete canonical asset parent (should fail due to RESTRICT ondelete constraint)
    db_session.delete(asset)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Attempt to delete asset family parent (should fail due to RESTRICT ondelete constraint)
    db_session.delete(family)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()
