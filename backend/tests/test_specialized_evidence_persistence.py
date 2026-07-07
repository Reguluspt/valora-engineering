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
    EvidenceFile, EvidenceFileStatus, EvidenceSensitivityLevel,
    SupplierQuoteEvidence, CatalogueEvidence, InternetEvidence, ImageEvidence, EmailEvidence,
    EvidenceExtractionResult, EvidenceExtractionStatus,
    EvidenceReviewDecision, EvidenceReviewDecisionStatus
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


def test_table_registration() -> None:
    tables = Base.metadata.tables
    # Check specialized tables registered
    assert "supplier_quote_evidences" in tables
    assert "catalogue_evidences" in tables
    assert "internet_evidences" in tables
    assert "image_evidences" in tables
    assert "email_evidences" in tables
    assert "evidence_extraction_results" in tables
    assert "evidence_review_decisions" in tables

    # Confirm knowledge tables are NOT present
    forbidden_tables = [
        "technical_specifications",
        "technical_specification_versions",
        "quote_batches",
        "quote_lines",
        "market_quotes",
        "appraised_price_decisions",
        "knowledge_versions",
        "knowledge_lineages",
        "knowledge_queue_items",
        "knowledge_conflicts",
        "knowledge_confidence"
    ]
    for table in forbidden_tables:
        assert table not in tables


@pytest.fixture
def setup_uploader(db_session: Session):
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()
    user = User(organization_id=org.id, email="uploader@test.com", full_name="Uploader User", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()
    return user


def create_mock_evidence_file(db_session: Session, user: User, filename: str) -> EvidenceFile:
    ev_file = EvidenceFile(
        filename=filename,
        mime_type="application/octet-stream",
        file_size=100,
        object_key=f"uploads/{filename}",
        checksum="dummyhash",
        sensitivity_level=EvidenceSensitivityLevel.NORMAL,
        uploaded_by=user.id
    )
    db_session.add(ev_file)
    db_session.commit()
    return ev_file


def test_supplier_quote_evidence(db_session: Session, setup_uploader) -> None:
    f = create_mock_evidence_file(db_session, setup_uploader, "supplier_quote.pdf")
    quote = SupplierQuoteEvidence(
        evidence_file_id=f.id,
        supplier_name="ABB Vietnam",
        quote_number="Q-2026-001",
        quote_date=datetime.now(timezone.utc),
        total_amount=54000.50,
        currency="USD"
    )
    db_session.add(quote)
    db_session.commit()

    db_session.expire_all()
    q_quote = db_session.query(SupplierQuoteEvidence).filter(SupplierQuoteEvidence.id == quote.id).one()
    assert q_quote.supplier_name == "ABB Vietnam"
    assert q_quote.quote_number == "Q-2026-001"
    assert q_quote.total_amount == 54000.50
    assert q_quote.currency == "USD"
    assert q_quote.evidence_file_id == f.id


def test_catalogue_evidence(db_session: Session, setup_uploader) -> None:
    f = create_mock_evidence_file(db_session, setup_uploader, "catalogue.pdf")
    cat = CatalogueEvidence(
        evidence_file_id=f.id,
        manufacturer_name="Schneider Electric",
        catalogue_name="LV Switchboards Catalogue 2026",
        page_number="P-124",
        product_code="MVS-1600"
    )
    db_session.add(cat)
    db_session.commit()

    db_session.expire_all()
    q_cat = db_session.query(CatalogueEvidence).filter(CatalogueEvidence.id == cat.id).one()
    assert q_cat.manufacturer_name == "Schneider Electric"
    assert q_cat.catalogue_name == "LV Switchboards Catalogue 2026"
    assert q_cat.page_number == "P-124"
    assert q_cat.product_code == "MVS-1600"


def test_internet_evidence(db_session: Session, setup_uploader) -> None:
    f = create_mock_evidence_file(db_session, setup_uploader, "web_capture.html")
    net = InternetEvidence(
        evidence_file_id=f.id,
        url="https://mpec.com.vn/product/123",
        captured_at=datetime.now(timezone.utc),
        site_name="MPEC Product Catalog"
    )
    db_session.add(net)
    db_session.commit()

    db_session.expire_all()
    q_net = db_session.query(InternetEvidence).filter(InternetEvidence.id == net.id).one()
    assert q_net.url == "https://mpec.com.vn/product/123"
    assert q_net.site_name == "MPEC Product Catalog"


def test_image_evidence(db_session: Session, setup_uploader) -> None:
    f = create_mock_evidence_file(db_session, setup_uploader, "nameplate.jpg")
    img = ImageEvidence(
        evidence_file_id=f.id,
        resolution="4032x3024",
        captured_at=datetime.now(timezone.utc),
        camera_metadata={"make": "Apple", "model": "iPhone 15 Pro"}
    )
    db_session.add(img)
    db_session.commit()

    db_session.expire_all()
    q_img = db_session.query(ImageEvidence).filter(ImageEvidence.id == img.id).one()
    assert q_img.resolution == "4032x3024"
    assert q_img.camera_metadata == {"make": "Apple", "model": "iPhone 15 Pro"}


def test_email_evidence(db_session: Session, setup_uploader) -> None:
    f = create_mock_evidence_file(db_session, setup_uploader, "email_export.eml")
    email = EmailEvidence(
        evidence_file_id=f.id,
        sender="sales@abb.com",
        recipient="purchasing@valora.com",
        subject="FW: Pricing Quote 110kV Transformer",
        sent_at=datetime.now(timezone.utc)
    )
    db_session.add(email)
    db_session.commit()

    db_session.expire_all()
    q_email = db_session.query(EmailEvidence).filter(EmailEvidence.id == email.id).one()
    assert q_email.sender == "sales@abb.com"
    assert q_email.recipient == "purchasing@valora.com"
    assert q_email.subject == "FW: Pricing Quote 110kV Transformer"


def test_evidence_extraction_result(db_session: Session, setup_uploader) -> None:
    f = create_mock_evidence_file(db_session, setup_uploader, "parse_target.pdf")
    ext = EvidenceExtractionResult(
        evidence_file_id=f.id,
        status=EvidenceExtractionStatus.COMPLETED,
        confidence_score=0.9400,
        extracted_payload={"model": "ABB-110", "price": 54000.0}
    )
    db_session.add(ext)
    db_session.commit()

    db_session.expire_all()
    q_ext = db_session.query(EvidenceExtractionResult).filter(EvidenceExtractionResult.id == ext.id).one()
    assert q_ext.status == EvidenceExtractionStatus.COMPLETED
    assert q_ext.confidence_score == 0.9400
    assert q_ext.extracted_payload == {"model": "ABB-110", "price": 54000.0}
    assert q_ext.row_version == 1


def test_evidence_review_decision(db_session: Session, setup_uploader) -> None:
    f = create_mock_evidence_file(db_session, setup_uploader, "review_target.pdf")
    dec = EvidenceReviewDecision(
        evidence_file_id=f.id,
        status=EvidenceReviewDecisionStatus.ACCEPTED,
        reviewer_id=setup_uploader.id,
        reviewed_at=datetime.now(timezone.utc),
        review_notes="Valid quote matching technical limits."
    )
    db_session.add(dec)
    db_session.commit()

    db_session.expire_all()
    q_dec = db_session.query(EvidenceReviewDecision).filter(EvidenceReviewDecision.id == dec.id).one()
    assert q_dec.status == EvidenceReviewDecisionStatus.ACCEPTED
    assert q_dec.reviewer_id == setup_uploader.id
    assert q_dec.review_notes == "Valid quote matching technical limits."
    assert q_dec.row_version == 1


def test_specialized_evidence_deletion_restrict(db_session: Session, setup_uploader) -> None:
    f = create_mock_evidence_file(db_session, setup_uploader, "restrict.pdf")
    quote = SupplierQuoteEvidence(
        evidence_file_id=f.id,
        supplier_name="Siemens"
    )
    db_session.add(quote)
    db_session.commit()

    # Attempting to delete EvidenceFile must fail due to foreign key RESTRICT on supplier_quote_evidences
    db_session.delete(f)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_migration_chain() -> None:
    import importlib.util
    import os
    
    filepath = os.path.join(os.path.dirname(__file__), "../alembic/versions/a87a9b6da99a_create_specialized_evidence_tables.py")
    spec = importlib.util.spec_from_file_location("migration_a87a9b6da99a", filepath)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    
    assert migration.revision == "a87a9b6da99a"
    assert migration.down_revision == "a87a9b6da999"
