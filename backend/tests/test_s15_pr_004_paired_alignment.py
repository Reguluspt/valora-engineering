"""S15-PR-004 unit tests for Paired Alignment Engine and Historical Bootstrap."""
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
import app.modules.excel_import.models  # noqa: F401
from app.modules.excel_import.models import AlignmentStatus, DocxExtractedTable, TableRoleCandidate
from app.modules.document_engine_intelligence.application.dossier_bundle_service import create_paired_dossier_bundle
from app.modules.document_engine_intelligence.application.paired_alignment_service import align_paired_dossier_bundle


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_paired_alignment_success(db_session: Session):
    """Verify that complete paired dossier (Excel + Word) aligns successfully (ADR 0032)."""
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()

    files = [
        {
            "file_role": "excel_workbook",
            "file_name": "Bang_Tinh.xlsx",
            "file_size_bytes": 1000,
            "checksum_sha256": "a" * 64,
            "storage_object_key": "key1",
        },
        {
            "file_role": "word_report",
            "file_name": "Bao_Cao.docx",
            "file_size_bytes": 2000,
            "checksum_sha256": "b" * 64,
            "storage_object_key": "key2",
        },
    ]

    bundle, source_files = create_paired_dossier_bundle(
        db_session,
        actor_id=actor_id,
        org_id=org_id,
        bundle_code="HS-ALIGN-001",
        files=files,
    )

    # Add extracted Word table
    tbl = DocxExtractedTable(
        id=uuid.uuid4(),
        organization_id=org_id,
        dossier_bundle_id=bundle.id,
        source_file_id=source_files[1].id,
        table_index=0,
        table_role_candidate=TableRoleCandidate.TECHNICAL_SPECIFICATIONS.value,
        raw_title="Bảng thông số kỹ thuật PD-001",
        row_count=49,
        col_count=5,
    )
    db_session.add(tbl)
    db_session.commit()

    alignment = align_paired_dossier_bundle(db_session, org_id=org_id, dossier_bundle_id=bundle.id)

    assert alignment.alignment_status == AlignmentStatus.ALIGNED.value
    assert float(alignment.confidence_score) >= 0.85
    assert alignment.tech_rows_matched == 49


def test_alignment_idempotency(db_session: Session):
    """Verify that re-running paired alignment is idempotent and updates existing record."""
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()

    files = [
        {
            "file_role": "excel_workbook",
            "file_name": "Bang_Tinh.xlsx",
            "file_size_bytes": 1000,
            "checksum_sha256": "a" * 64,
            "storage_object_key": "key1",
        },
        {
            "file_role": "word_report",
            "file_name": "Bao_Cao.docx",
            "file_size_bytes": 2000,
            "checksum_sha256": "b" * 64,
            "storage_object_key": "key2",
        },
    ]

    bundle, _ = create_paired_dossier_bundle(
        db_session,
        actor_id=actor_id,
        org_id=org_id,
        bundle_code="HS-ALIGN-002",
        files=files,
    )

    align1 = align_paired_dossier_bundle(db_session, org_id=org_id, dossier_bundle_id=bundle.id)
    align2 = align_paired_dossier_bundle(db_session, org_id=org_id, dossier_bundle_id=bundle.id)

    assert align1.id == align2.id
