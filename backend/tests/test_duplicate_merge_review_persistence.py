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
    Project, ProjectAssetLine, Customer,
    DuplicateCandidate, DuplicateCandidateStatus,
    MergeDecision, MergeDecisionStatus,
    IdentityCandidate, IdentityCandidateStatus,
    IdentityReviewItem, IdentityReviewStatus,
    IdentityDecisionLog, IdentityDecisionType
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


def test_duplicate_candidate_constraints(db_session: Session) -> None:
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    user = User(organization_id=org.id, email="dup@test.com", full_name="User", status=UserStatus.ACTIVE)
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

    asset1 = CanonicalAsset(asset_family_id=family.id, primary_taxonomy_node_id=node.id, standard_name="Asset 1", status=CanonicalAssetStatus.ACTIVE)
    asset2 = CanonicalAsset(asset_family_id=family.id, primary_taxonomy_node_id=node.id, standard_name="Asset 2", status=CanonicalAssetStatus.ACTIVE)
    db_session.add_all([asset1, asset2])
    db_session.commit()

    # 1. Create duplicate candidate (valid)
    cand = DuplicateCandidate(
        source_asset_id=asset1.id,
        target_asset_id=asset2.id,
        confidence_score=0.91,
        status=DuplicateCandidateStatus.PENDING
    )
    db_session.add(cand)
    db_session.commit()

    assert cand.id is not None
    assert cand.source_asset_id == asset1.id

    # 2. CheckConstraint: source != target (should fail)
    invalid = DuplicateCandidate(
        source_asset_id=asset1.id,
        target_asset_id=asset1.id,
        confidence_score=1.00,
        status=DuplicateCandidateStatus.PENDING
    )
    db_session.add(invalid)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_merge_decision_constraints(db_session: Session) -> None:
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    user = User(organization_id=org.id, email="merge@test.com", full_name="User", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    node = TaxonomyNode(level=TaxonomyNodeLevel.GROUP, code="GRP-M", name_vi="M", status=TaxonomyStatus.ACTIVE, created_by=user.id)
    db_session.add(node)
    db_session.commit()

    family = AssetFamily(taxonomy_node_id=node.id, code="FAM-M", name_vi="M", status=AssetFamilyStatus.ACTIVE)
    db_session.add(family)
    db_session.commit()

    asset1 = CanonicalAsset(asset_family_id=family.id, primary_taxonomy_node_id=node.id, standard_name="Asset 1", status=CanonicalAssetStatus.ACTIVE)
    asset2 = CanonicalAsset(asset_family_id=family.id, primary_taxonomy_node_id=node.id, standard_name="Asset 2", status=CanonicalAssetStatus.ACTIVE)
    db_session.add_all([asset1, asset2])
    db_session.commit()

    # 1. Create merge decision (valid)
    dec = MergeDecision(
        source_asset_id=asset1.id,
        target_asset_id=asset2.id,
        status=MergeDecisionStatus.PROPOSED,
        reason="Duplicates"
    )
    db_session.add(dec)
    db_session.commit()

    assert dec.id is not None

    # 2. CheckConstraint: source != target (should fail)
    invalid = MergeDecision(
        source_asset_id=asset1.id,
        target_asset_id=asset1.id,
        status=MergeDecisionStatus.PROPOSED
    )
    db_session.add(invalid)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_identity_review_and_decision_logs(db_session: Session) -> None:
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    user = User(organization_id=org.id, email="rev@test.com", full_name="User", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    customer = Customer(organization_id=org.id, legal_name="Cust 1", status="active", created_by=user.id)
    db_session.add(customer)
    db_session.commit()

    project = Project(organization_id=org.id, customer_id=customer.id, code="PRJ-1", name="Project 1", created_by=user.id)
    db_session.add(project)
    db_session.commit()

    line = ProjectAssetLine(project_id=project.id, asset_name="MBA ABB", quantity=1.0)
    db_session.add(line)
    db_session.commit()

    # 1. Create Review Item
    review = IdentityReviewItem(
        project_asset_line_id=line.id,
        review_status=IdentityReviewStatus.PENDING
    )
    db_session.add(review)
    db_session.commit()

    assert review.id is not None
    assert review.review_status == IdentityReviewStatus.PENDING

    # 2. Create Decision Log
    log = IdentityDecisionLog(
        project_asset_line_id=line.id,
        decision_type=IdentityDecisionType.CREATE_NEW,
        actor_user_id=user.id,
        details={"reason": "No candidate found"}
    )
    db_session.add(log)
    db_session.commit()

    assert log.id is not None
    assert log.decision_type == IdentityDecisionType.CREATE_NEW
