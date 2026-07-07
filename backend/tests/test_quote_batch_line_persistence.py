import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, exc, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus,
    User, UserStatus,
    TaxonomyNode, TaxonomyNodeLevel, TaxonomyStatus,
    AssetFamily, AssetFamilyStatus,
    CanonicalAsset, CanonicalAssetStatus,
    EvidenceFile, EvidenceFileStatus, EvidenceSensitivityLevel,
    QuoteBatch, QuoteBatchStatus, QuoteLine, QuoteLineStatus
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


def test_table_registration() -> None:
    tables = Base.metadata.tables
    assert "quote_batches" in tables
    assert "quote_lines" in tables


@pytest.fixture
def setup_seed_data(db_session: Session):
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    user = User(organization_id=org.id, email="curator@test.com", full_name="Curator User", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    tax = TaxonomyNode(
        level=TaxonomyNodeLevel.GROUP,
        code="TRANS",
        name_vi="Transformers",
        status=TaxonomyStatus.ACTIVE,
        created_by=user.id
    )
    db_session.add(tax)
    db_session.commit()

    family = AssetFamily(
        taxonomy_node_id=tax.id,
        code="TRANSFORMER",
        name_vi="Transformer Family",
        status=AssetFamilyStatus.ACTIVE
    )
    db_session.add(family)
    db_session.commit()

    canon = CanonicalAsset(
        asset_family_id=family.id,
        primary_taxonomy_node_id=tax.id,
        standard_name="ABB Transformer 110kV Standard",
        status=CanonicalAssetStatus.ACTIVE
    )
    db_session.add(canon)
    db_session.commit()

    ev_file = EvidenceFile(
        filename="quote.pdf",
        mime_type="application/pdf",
        file_size=10240,
        object_key="uploads/quote.pdf",
        checksum="quotehash",
        sensitivity_level=EvidenceSensitivityLevel.NORMAL,
        uploaded_by=user.id
    )
    db_session.add(ev_file)
    db_session.commit()

    return {
        "user_id": user.id,
        "canon_id": canon.id,
        "evidence_id": ev_file.id
    }


def test_quote_batch_and_line_persistence(db_session: Session, setup_seed_data) -> None:
    # 1. Create a candidate QuoteBatch
    batch = QuoteBatch(
        canonical_asset_id=setup_seed_data["canon_id"],
        created_by=setup_seed_data["user_id"],
        status=QuoteBatchStatus.CANDIDATE
    )
    db_session.add(batch)
    db_session.commit()

    # 2. Add multiple QuoteLines
    line1 = QuoteLine(
        quote_batch_id=batch.id,
        evidence_file_id=setup_seed_data["evidence_id"],
        supplier_name="ABB Vietnam",
        quoted_unit_price=54000.0,
        currency="USD",
        quantity=1.0,
        unit_of_measure="set",
        quote_label="ABB-110",
        quote_date=datetime.now(timezone.utc),
        status=QuoteLineStatus.ACTIVE
    )
    line2 = QuoteLine(
        quote_batch_id=batch.id,
        evidence_file_id=setup_seed_data["evidence_id"],
        supplier_name="Siemens Vietnam",
        quoted_unit_price=56500.0,
        currency="USD",
        quantity=1.0,
        unit_of_measure="set",
        quote_label="SVT-110",
        quote_date=datetime.now(timezone.utc),
        status=QuoteLineStatus.ACTIVE
    )
    db_session.add_all([line1, line2])
    db_session.commit()

    db_session.expire_all()
    q_batch = db_session.query(QuoteBatch).filter(QuoteBatch.id == batch.id).one()
    assert len(q_batch.quote_lines) == 2
    assert q_batch.quote_lines[0].supplier_name in ["ABB Vietnam", "Siemens Vietnam"]
    assert q_batch.quote_lines[0].quoted_unit_price > 0


def test_quote_batch_revision_chain(db_session: Session, setup_seed_data) -> None:
    # 1. Create original batch and approve it
    v1 = QuoteBatch(
        canonical_asset_id=setup_seed_data["canon_id"],
        created_by=setup_seed_data["user_id"],
        status=QuoteBatchStatus.ACTIVE,
        revision_number=1,
        approved_by=setup_seed_data["user_id"],
        approved_at=datetime.now(timezone.utc)
    )
    db_session.add(v1)
    db_session.commit()

    line_v1 = QuoteLine(
        quote_batch_id=v1.id,
        supplier_name="Vendor A",
        quoted_unit_price=1000.0,
        currency="USD",
        status=QuoteLineStatus.ACTIVE
    )
    db_session.add(line_v1)
    db_session.commit()

    # 2. To change pricing, create a revision (v2 draft) linking back to v1
    v2 = QuoteBatch(
        canonical_asset_id=setup_seed_data["canon_id"],
        created_by=setup_seed_data["user_id"],
        status=QuoteBatchStatus.DRAFT,
        revision_number=2,
        previous_quote_batch_id=v1.id
    )
    db_session.add(v2)
    db_session.commit()

    line_v2 = QuoteLine(
        quote_batch_id=v2.id,
        supplier_name="Vendor A",
        quoted_unit_price=1050.0,  # Revised price
        currency="USD",
        status=QuoteLineStatus.DRAFT
    )
    db_session.add(line_v2)
    db_session.commit()

    db_session.expire_all()
    q_v2 = db_session.query(QuoteBatch).filter(QuoteBatch.id == v2.id).one()
    assert q_v2.previous_quote_batch_id == v1.id
    assert q_v2.revision_number == 2
    assert q_v2.previous_quote_batch.status == QuoteBatchStatus.ACTIVE


def test_quote_line_deletion_restrict(db_session: Session, setup_seed_data) -> None:
    batch = QuoteBatch(
        canonical_asset_id=setup_seed_data["canon_id"],
        created_by=setup_seed_data["user_id"],
        status=QuoteBatchStatus.DRAFT
    )
    db_session.add(batch)
    db_session.commit()

    line = QuoteLine(
        quote_batch_id=batch.id,
        supplier_name="Vendor A",
        quoted_unit_price=100.0,
        currency="USD"
    )
    db_session.add(line)
    db_session.commit()

    # Attempting to delete QuoteBatch must fail due to RESTRICT on QuoteLine
    db_session.delete(batch)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_migration_chain() -> None:
    import importlib.util
    import os
    
    filepath = os.path.join(os.path.dirname(__file__), "../alembic/versions/a87a9b6da99c_create_quote_batch_line_tables.py")
    spec = importlib.util.spec_from_file_location("migration_a87a9b6da99c", filepath)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    
    assert migration.revision == "a87a9b6da99c"
    assert migration.down_revision == "a87a9b6da99b"
