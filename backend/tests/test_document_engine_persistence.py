import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DBAPIError

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, User, UserStatus, Role, UserRole, Project,
    ProjectWorkflowStatus, Customer, EvidenceFile, EvidenceSource, EvidenceSourceType,
    DocumentTemplate, DocumentTemplateStatus, TemplateVersion, TemplateVersionStatus,
    TemplatePlaceholder, PlaceholderDataType, PlaceholderSourceContext, PlaceholderBinding,
    PlaceholderBindingType, ComputedPlaceholderExpression, ComputedExpressionType,
    ComputedExpressionStatus, RenderJob, RenderJobStatus, GeneratedDocument,
    GeneratedDocumentStatus, DocumentPackage, DocumentPackageType, DocumentPackageStatus,
    DocumentPackageItem
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

    # Evidence Source & File
    source = EvidenceSource(name="Ext Source", source_type=EvidenceSourceType.SUPPLIER)
    db_session.add(source)
    db_session.commit()

    ev_file = EvidenceFile(
        filename="template.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_size=1024,
        object_key="templates/template.docx",
        checksum="abc",
        uploaded_by=user.id
    )
    db_session.add(ev_file)
    db_session.commit()

    return {
        "org_id": org.id,
        "user_id": user.id,
        "project_id": proj.id,
        "evidence_file_id": ev_file.id
    }


def test_document_template_code_uniqueness(db_session: Session, setup_basics) -> None:
    # 1. Create first template
    t1 = DocumentTemplate(
        organization_id=setup_basics["org_id"],
        document_type="report",
        code="T1",
        name="Template One",
        created_by=setup_basics["user_id"]
    )
    db_session.add(t1)
    db_session.commit()

    # 2. Attempt duplicate code
    t2 = DocumentTemplate(
        organization_id=setup_basics["org_id"],
        document_type="report",
        code="T1",
        name="Template Two",
        created_by=setup_basics["user_id"]
    )
    db_session.add(t2)
    with pytest.raises((IntegrityError, DBAPIError)):
        db_session.commit()
    db_session.rollback()


def test_template_version_relationships_and_uniqueness(db_session: Session, setup_basics) -> None:
    t = DocumentTemplate(
        organization_id=setup_basics["org_id"],
        document_type="report",
        code="T_VERS",
        name="Template Version Test",
        created_by=setup_basics["user_id"]
    )
    db_session.add(t)
    db_session.commit()

    # Create version 1
    v1 = TemplateVersion(
        document_template_id=t.id,
        version_number=1,
        source_file_id=setup_basics["evidence_file_id"],
        template_format="docx",
        status=TemplateVersionStatus.ACTIVE
    )
    db_session.add(v1)
    db_session.commit()

    assert v1.document_template.name == "Template Version Test"

    # Verify version number uniqueness per template
    v2 = TemplateVersion(
        document_template_id=t.id,
        version_number=1,
        source_file_id=setup_basics["evidence_file_id"],
        template_format="docx",
        status=TemplateVersionStatus.DRAFT
    )
    db_session.add(v2)
    with pytest.raises((IntegrityError, DBAPIError)):
        db_session.commit()
    db_session.rollback()


def test_computed_placeholder_expressions_payload(db_session: Session, setup_basics) -> None:
    expr = ComputedPlaceholderExpression(
        placeholder_key="project.total_fee",
        expression_type=ComputedExpressionType.VALORA_EXPR,
        inputs={"fee": "$.project.fee_amount"},
        expression="fee * 1.1",
        output_data_type=PlaceholderDataType.CURRENCY,
        status=ComputedExpressionStatus.ACTIVE,
        created_by=setup_basics["user_id"]
    )
    db_session.add(expr)
    db_session.commit()

    assert expr.expression == "fee * 1.1"
    assert expr.inputs == {"fee": "$.project.fee_amount"}


def test_template_placeholders_and_bindings(db_session: Session, setup_basics) -> None:
    t = DocumentTemplate(
        organization_id=setup_basics["org_id"],
        document_type="report",
        code="T_PL",
        name="Placeholder Test",
        created_by=setup_basics["user_id"]
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

    p = TemplatePlaceholder(
        template_version_id=v.id,
        placeholder_key="cust_name",
        label_vi="Tên khách hàng",
        data_type=PlaceholderDataType.SCALAR,
        source_context=PlaceholderSourceContext.PROJECT,
        source_path="$.customer.legal_name",
        is_required=True
    )
    db_session.add(p)
    db_session.commit()

    assert p.template_version.id == v.id

    b = PlaceholderBinding(
        template_version_id=v.id,
        template_placeholder_id=p.id,
        binding_path="$.customer.legal_name",
        binding_type=PlaceholderBindingType.DIRECT,
        is_required=True
    )
    db_session.add(b)
    db_session.commit()

    assert b.template_placeholder.placeholder_key == "cust_name"


def test_render_job_and_generated_documents(db_session: Session, setup_basics) -> None:
    t = DocumentTemplate(
        organization_id=setup_basics["org_id"],
        document_type="report",
        code="T_REND",
        name="Render Test",
        created_by=setup_basics["user_id"]
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
        project_id=setup_basics["project_id"],
        template_version_id=v.id,
        render_mode="draft",
        output_formats=["docx", "pdf"],
        data_snapshot={"project_name": "Project 2026"},
        data_snapshot_hash="hash123",
        status=RenderJobStatus.QUEUED,
        created_by=setup_basics["user_id"]
    )
    db_session.add(job)
    db_session.commit()

    assert job.status == RenderJobStatus.QUEUED
    assert job.data_snapshot == {"project_name": "Project 2026"}

    # GeneratedDocument
    doc = GeneratedDocument(
        project_id=setup_basics["project_id"],
        render_job_id=job.id,
        document_type="report",
        output_format="docx",
        filename="report.docx",
        storage_key="documents/report.docx",
        checksum_sha256="doc-hash",
        file_size_bytes=50000,
        template_version_id=v.id,
        data_snapshot_hash="hash123",
        status=GeneratedDocumentStatus.DRAFT
    )
    db_session.add(doc)
    db_session.commit()

    assert doc.render_job.id == job.id


def test_document_packages_and_items(db_session: Session, setup_basics) -> None:
    t = DocumentTemplate(
        organization_id=setup_basics["org_id"],
        document_type="report",
        code="T_PKG",
        name="Package Test",
        created_by=setup_basics["user_id"]
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
        project_id=setup_basics["project_id"],
        template_version_id=v.id,
        render_mode="draft",
        output_formats=["docx"],
        data_snapshot={"key": "val"},
        data_snapshot_hash="hash123",
        status=RenderJobStatus.COMPLETED,
        created_by=setup_basics["user_id"]
    )
    db_session.add(job)
    db_session.commit()

    doc = GeneratedDocument(
        project_id=setup_basics["project_id"],
        render_job_id=job.id,
        document_type="report",
        output_format="docx",
        filename="report.docx",
        storage_key="documents/report.docx",
        checksum_sha256="doc-hash",
        file_size_bytes=1000,
        template_version_id=v.id,
        data_snapshot_hash="hash123",
        status=GeneratedDocumentStatus.OFFICIAL
    )
    db_session.add(doc)
    db_session.commit()

    pkg = DocumentPackage(
        project_id=setup_basics["project_id"],
        package_type=DocumentPackageType.QC,
        name="QC Package",
        status=DocumentPackageStatus.DRAFT,
        created_by=setup_basics["user_id"]
    )
    db_session.add(pkg)
    db_session.commit()

    item = DocumentPackageItem(
        document_package_id=pkg.id,
        generated_document_id=doc.id,
        sort_order=1
    )
    db_session.add(item)
    db_session.commit()

    assert item.document_package.name == "QC Package"
    assert item.generated_document.filename == "report.docx"


def test_parent_deletion_restrict_on_generated_documents(db_session: Session, setup_basics) -> None:
    t = DocumentTemplate(
        organization_id=setup_basics["org_id"],
        document_type="report",
        code="T_DEL",
        name="Delete Constraint Test",
        created_by=setup_basics["user_id"]
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
        project_id=setup_basics["project_id"],
        template_version_id=v.id,
        render_mode="draft",
        output_formats=["docx"],
        data_snapshot={"key": "val"},
        data_snapshot_hash="hash123",
        status=RenderJobStatus.COMPLETED,
        created_by=setup_basics["user_id"]
    )
    db_session.add(job)
    db_session.commit()

    doc = GeneratedDocument(
        project_id=setup_basics["project_id"],
        render_job_id=job.id,
        document_type="report",
        output_format="docx",
        filename="report.docx",
        storage_key="documents/report.docx",
        checksum_sha256="doc-hash",
        file_size_bytes=1000,
        template_version_id=v.id,
        data_snapshot_hash="hash123",
        status=GeneratedDocumentStatus.OFFICIAL
    )
    db_session.add(doc)
    db_session.commit()

    # Attempting to delete TemplateVersion 'v' should fail due to RESTRICT ondelete foreign key constraint
    db_session.delete(v)
    with pytest.raises((IntegrityError, DBAPIError)):
        db_session.commit()
    db_session.rollback()


def test_document_intelligence_not_implemented() -> None:
    # Verify no Document Intelligence classes are registered yet in the metadata
    mapper_classes = [mapper.class_.__name__ for mapper in Base.registry.mappers]
    for forbidden in ["ParsedDocument", "ExtractedField", "DocumentDiff", "DocumentCorrection"]:
        assert forbidden not in mapper_classes
