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
    AssetAlias, AssetAliasScope, AssetAliasStatus, normalize_alias_helper,
    IdentityCandidate, IdentityCandidateStatus,
    SimilarityScore,
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


def test_asset_alias_persistence(db_session: Session) -> None:
    # 1. Seed deps
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    user = User(organization_id=org.id, email="alias@test.com", full_name="User", status=UserStatus.ACTIVE)
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

    # 2. Test Normalization Helper
    assert normalize_alias_helper("Máy Biến Áp ABB 110kV!") == "máy biến áp abb 110kv"

    # 3. Create Alias
    raw = "Máy Biến Áp ABB 110kV!"
    normalized = normalize_alias_helper(raw)
    alias = AssetAlias(
        alias_scope=AssetAliasScope.CANONICAL,
        canonical_asset_id=asset.id,
        raw_alias=raw,
        normalized_alias=normalized,
        status=AssetAliasStatus.ACTIVE
    )
    db_session.add(alias)
    db_session.commit()

    assert alias.id is not None
    assert alias.normalized_alias == "máy biến áp abb 110kv"
    assert alias.canonical_asset_id == asset.id

    # 4. Check uniqueness constraint
    dup = AssetAlias(
        alias_scope=AssetAliasScope.CANONICAL,
        canonical_asset_id=asset.id,
        raw_alias="ABB 110kV",
        normalized_alias=normalized,
        status=AssetAliasStatus.ACTIVE
    )
    db_session.add(dup)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 5. Check RESTRICT deletion policy (deleting CanonicalAsset should fail because of referencing alias)
    db_session.delete(asset)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_identity_candidate_and_scoring(db_session: Session) -> None:
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    user = User(organization_id=org.id, email="cand@test.com", full_name="User", status=UserStatus.ACTIVE)
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

    customer = Customer(organization_id=org.id, legal_name="Cust 1", status="active", created_by=user.id)
    db_session.add(customer)
    db_session.commit()

    project = Project(
        organization_id=org.id,
        customer_id=customer.id,
        code="PRJ-99",
        name="Project 1",
        created_by=user.id
    )
    db_session.add(project)
    db_session.commit()

    line = ProjectAssetLine(
        project_id=project.id,
        asset_name="MBA ABB 110kV",
        quantity=1.0
    )
    db_session.add(line)
    db_session.commit()

    asset = CanonicalAsset(
        asset_family_id=family.id,
        primary_taxonomy_node_id=node.id,
        standard_name="Máy biến áp ABB 110kV",
        status=CanonicalAssetStatus.ACTIVE
    )
    db_session.add(asset)
    db_session.commit()

    # 1. Create Identity Candidate
    cand = IdentityCandidate(
        project_asset_line_id=line.id,
        proposed_canonical_asset_id=asset.id,
        proposed_taxonomy_node_id=node.id,
        status=IdentityCandidateStatus.PENDING,
        confidence_score=0.92,
        match_method="deterministic"
    )
    db_session.add(cand)
    db_session.commit()

    assert cand.id is not None
    assert cand.status == IdentityCandidateStatus.PENDING
    assert cand.project_asset_line_id == line.id
    assert cand.proposed_canonical_asset_id == asset.id

    # 2. Add Similarity Scores
    score1 = SimilarityScore(
        identity_candidate_id=cand.id,
        component="name",
        score=0.95
    )
    score2 = SimilarityScore(
        identity_candidate_id=cand.id,
        component="brand",
        score=1.0
    )
    db_session.add_all([score1, score2])
    db_session.commit()

    assert len(cand.similarity_scores) == 2
    assert float(cand.similarity_scores[0].score) == 0.95


