from datetime import datetime, timezone
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
    CanonicalAsset,
    CanonicalAssetStatus,
    QuoteBatch,
    QuoteBatchStatus,
    AppraisedPriceDecision,
    AppraisedPriceDecisionStatus,
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


def test_table_registration() -> None:
    tables = Base.metadata.tables
    assert "appraised_price_decisions" in tables


@pytest.fixture
def setup_seed_data(db_session: Session):
    org = OrganizationProfile(
        legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id,
        email="curator@test.com",
        full_name="Curator User",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()

    tax = TaxonomyNode(
        level=TaxonomyNodeLevel.GROUP,
        code="TRANS",
        name_vi="Transformers",
        status=TaxonomyStatus.ACTIVE,
        created_by=user.id,
    )
    db_session.add(tax)
    db_session.commit()

    family = AssetFamily(
        taxonomy_node_id=tax.id,
        code="TRANSFORMER",
        name_vi="Transformer Family",
        status=AssetFamilyStatus.ACTIVE,
    )
    db_session.add(family)
    db_session.commit()

    canon = CanonicalAsset(
        asset_family_id=family.id,
        primary_taxonomy_node_id=tax.id,
        standard_name="ABB Transformer 110kV Standard",
        status=CanonicalAssetStatus.ACTIVE,
    )
    db_session.add(canon)
    db_session.commit()

    batch = QuoteBatch(
        canonical_asset_id=canon.id, created_by=user.id, status=QuoteBatchStatus.ACTIVE
    )
    db_session.add(batch)
    db_session.commit()

    return {"user_id": user.id, "canon_id": canon.id, "batch_id": batch.id}


def test_appraised_price_decision_persistence(db_session: Session, setup_seed_data) -> None:
    # Create professional catalog price decision standard
    decision = AppraisedPriceDecision(
        canonical_asset_id=setup_seed_data["canon_id"],
        quote_batch_id=setup_seed_data["batch_id"],
        final_unit_price=55000.0,
        currency="USD",
        rationale="Median price from competitive active vendor quotes.",
        status=AppraisedPriceDecisionStatus.ACTIVE,
        created_by=setup_seed_data["user_id"],
        approved_by=setup_seed_data["user_id"],
        approved_at=datetime.now(timezone.utc),
    )
    db_session.add(decision)
    db_session.commit()

    db_session.expire_all()
    q_dec = (
        db_session.query(AppraisedPriceDecision)
        .filter(AppraisedPriceDecision.id == decision.id)
        .one()
    )
    assert q_dec.final_unit_price == 55000.0
    assert q_dec.currency == "USD"
    assert q_dec.rationale == "Median price from competitive active vendor quotes."
    assert q_dec.status == AppraisedPriceDecisionStatus.ACTIVE
    assert q_dec.quote_batch_id == setup_seed_data["batch_id"]


def test_appraised_price_decision_immutability(db_session: Session, setup_seed_data) -> None:
    decision = AppraisedPriceDecision(
        canonical_asset_id=setup_seed_data["canon_id"],
        quote_batch_id=setup_seed_data["batch_id"],
        final_unit_price=55000.0,
        currency="USD",
        rationale="Median price",
        status=AppraisedPriceDecisionStatus.ACTIVE,
        created_by=setup_seed_data["user_id"],
    )
    db_session.add(decision)
    db_session.commit()

    # QuoteBatch deletion is blocked due to RESTRICT foreign key constraint on appraised_price_decisions
    batch = db_session.query(QuoteBatch).filter(QuoteBatch.id == setup_seed_data["batch_id"]).one()
    db_session.delete(batch)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_migration_chain() -> None:
    import importlib.util
    import os

    filepath = os.path.join(
        os.path.dirname(__file__),
        "../alembic/versions/a87a9b6da99d_create_appraised_price_decisions.py",
    )
    spec = importlib.util.spec_from_file_location("migration_a87a9b6da99d", filepath)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "a87a9b6da99d"
    assert migration.down_revision == "a87a9b6da99c"
