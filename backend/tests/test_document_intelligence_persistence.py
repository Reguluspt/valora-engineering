import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DBAPIError

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, User, UserStatus, Role, UserRole, Project,
    ProjectWorkflowStatus, Customer, EvidenceFile, EvidenceSource, EvidenceSourceType,
    DocumentTemplate, DocumentTemplateStatus, TemplateVersion, TemplateVersionStatus,
    RenderJob, RenderJobStatus, GeneratedDocument, GeneratedDocumentStatus,
    ParsedDocument, ParsedDocumentStatus, ExtractedField, ExtractedFieldStatus,
    DocumentDiff, DocumentDiffType, DocumentDiffStatus, DocumentCorrection,
    DocumentCorrectionDecision, DocumentCorrectionStatus
)

@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    # Enable foreign keys in SQLite
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


@pytest.fixture
def client():
    # Placeholder for test client checks if needed
    pass


@pytest.fixture
def setup_basics(db_session: Session):
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    user = User(organization_id=org.id, email="admin@test.com", full_name="Admin User", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    customer = Customer(organization_id=org.id, legal_name="Cust 1", status="active", created_by=user.id)
    db_session.add(customer)
    db_session.commit()

    proj = Project(
        organization_id=org.id,
        code="PROJ-2026",
        name="Project 2026",
        status=ProjectWorkflowStatus.DRAFT,
        customer_id=customer.id,
        created_by=user.id
    )
    db_session.add(proj)
    db_session.commit()

    ev_file = EvidenceFile(
        filename="scanned_quote.pdf",
        mime_type="application/pdf",
        file_size=50000,
        object_key="evidence/scanned_quote.pdf",
        checksum="doc-hash-123",
        uploaded_by=user.id
    )
    db_session.add(ev_file)
    db_session.commit()

    # DocumentTemplate, Version, and GeneratedDocument
    t = DocumentTemplate(
        organization_id=org.id,
        document_type="report",
        code="T_DI",
        name="Diff template",
        created_by=user.id
    )
    db_session.add(t)
    db_session.commit()

    v = TemplateVersion(
        document_template_id=t.id,
        version_number=1,
        template_format="docx",
        status=TemplateVersionStatus.ACTIVE
    )
    db_session.add(v)
    db_session.commit()

    job = RenderJob(
        project_id=proj.id,
        template_version_id=v.id,
        render_mode="draft",
        output_formats=["docx"],
        data_snapshot={"key": "val"},
        data_snapshot_hash="hash123",
        status=RenderJobStatus.COMPLETED,
        created_by=user.id
    )
    db_session.add(job)
    db_session.commit()

    gen_doc = GeneratedDocument(
        project_id=proj.id,
        render_job_id=job.id,
        document_type="report",
        output_format="docx",
        filename="report.docx",
        storage_key="documents/report.docx",
        checksum_sha256="checksum",
        file_size_bytes=1024,
        template_version_id=v.id,
        data_snapshot_hash="hash123",
        status=GeneratedDocumentStatus.OFFICIAL
    )
    db_session.add(gen_doc)
    db_session.commit()

    return {
        "org_id": org.id,
        "user_id": user.id,
        "project_id": proj.id,
        "evidence_file_id": ev_file.id,
        "generated_document_id": gen_doc.id
    }


def test_parsed_document_and_extracted_fields(db_session: Session, setup_basics) -> None:
    # 1. Create ParsedDocument
    parsed = ParsedDocument(
        evidence_file_id=setup_basics["evidence_file_id"],
        document_type="supplier_quote",
        page_count=3,
        text_content_hash="contenthash123",
        parse_status=ParsedDocumentStatus.PARSED,
        confidence_score=0.9850
    )
    db_session.add(parsed)
    db_session.commit()

    assert parsed.parse_status == ParsedDocumentStatus.PARSED
    assert parsed.evidence_file.filename == "scanned_quote.pdf"

    # 2. Create ExtractedField
    field = ExtractedField(
        parsed_document_id=parsed.id,
        field_key="total_price",
        field_label="Total Price",
        extracted_value={"raw": "5,000,000 VND"},
        normalized_value={"amount": 5000000.0, "currency": "VND"},
        confidence_score=0.9920,
        source_page_number=1,
        status=ExtractedFieldStatus.CANDIDATE
    )
    db_session.add(field)
    db_session.commit()

    assert field.parsed_document.id == parsed.id
    assert field.extracted_value == {"raw": "5,000,000 VND"}


def test_document_diff_payload(db_session: Session, setup_basics) -> None:
    parsed = ParsedDocument(
        evidence_file_id=setup_basics["evidence_file_id"],
        document_type="supplier_quote",
        page_count=1,
        parse_status=ParsedDocumentStatus.PARSED
    )
    db_session.add(parsed)
    db_session.commit()

    diff = DocumentDiff(
        source_document_id=setup_basics["generated_document_id"],
        target_document_id=parsed.id,
        diff_type=DocumentDiffType.GENERATED_VS_EDITED,
        status=DocumentDiffStatus.REVIEW_READY,
        diff_payload={"text_changes": [{"diff_type": "deleted", "value": "Old title"}]}
    )
    db_session.add(diff)
    db_session.commit()

    assert diff.source_document.filename == "report.docx"
    assert diff.target_document.id == parsed.id
    assert diff.diff_payload["text_changes"][0]["value"] == "Old title"


def test_document_correction_and_isolation(db_session: Session, setup_basics) -> None:
    parsed = ParsedDocument(
        evidence_file_id=setup_basics["evidence_file_id"],
        document_type="supplier_quote",
        page_count=1,
        parse_status=ParsedDocumentStatus.PARSED
    )
    db_session.add(parsed)
    db_session.commit()

    correction = DocumentCorrection(
        parsed_document_id=parsed.id,
        target_type="extracted_field",
        target_id=uuid.uuid4(),
        affects_approved_data=False,
        correction_payload={"field_key": "total_price", "corrected_value": 5200000.0},
        decision=DocumentCorrectionDecision.ACCEPT,
        decided_by=setup_basics["user_id"],
        status=DocumentCorrectionStatus.DRAFT
    )
    db_session.add(correction)
    db_session.commit()

    assert correction.status == DocumentCorrectionStatus.DRAFT
    assert correction.decider.email == "admin@test.com"


def test_parent_deletion_restrict_on_parsed_document(db_session: Session, setup_basics) -> None:
    parsed = ParsedDocument(
        evidence_file_id=setup_basics["evidence_file_id"],
        document_type="supplier_quote",
        page_count=1,
        parse_status=ParsedDocumentStatus.PARSED
    )
    db_session.add(parsed)
    db_session.commit()

    # Attempting to delete the parent EvidenceFile must fail due to RESTRICT check
    ev_file = db_session.query(EvidenceFile).filter(EvidenceFile.id == setup_basics["evidence_file_id"]).one()
    db_session.delete(ev_file)
    with pytest.raises((IntegrityError, DBAPIError)):
        db_session.commit()
    db_session.rollback()
