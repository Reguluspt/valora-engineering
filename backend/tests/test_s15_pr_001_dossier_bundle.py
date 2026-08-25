"""S15-PR-001 unit tests for DossierBundle Aggregate and Source File Roles."""
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.db import Base
import app.modules.excel_import.models  # noqa: F401
from app.modules.document_engine_intelligence.application.dossier_bundle_service import create_paired_dossier_bundle


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


def test_create_paired_dossier_bundle_success(db_session: Session):
    """Verify that pairing an Excel workbook + Word report creates a valid DossierBundle."""
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    bundle_code = "HS-2026-VAL-001"

    files = [
        {
            "file_role": "excel_workbook",
            "file_name": "Bang_Tinh_Gia_PD001.xlsx",
            "file_size_bytes": 102400,
            "checksum_sha256": "a" * 64,
            "storage_object_key": "artifacts/2026/excel_001.xlsx",
        },
        {
            "file_role": "word_report",
            "file_name": "Bao_Cao_Dinh_Gia_PD001.docx",
            "file_size_bytes": 204800,
            "checksum_sha256": "b" * 64,
            "storage_object_key": "artifacts/2026/word_001.docx",
        },
    ]

    bundle, source_files = create_paired_dossier_bundle(
        db_session,
        actor_id=actor_id,
        org_id=org_id,
        bundle_code=bundle_code,
        files=files,
    )

    assert bundle.bundle_code == "HS-2026-VAL-001"
    assert bundle.status == "pending"
    assert len(source_files) == 2
    roles = {sf.file_role for sf in source_files}
    assert "excel_workbook" in roles
    assert "word_report" in roles


def test_missing_word_report_raises_http_400(db_session: Session):
    """Verify that missing Word report in paired dossier raises 400 Bad Request."""
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()

    files = [
        {
            "file_role": "excel_workbook",
            "file_name": "Bang_Tinh.xlsx",
            "file_size_bytes": 102400,
            "checksum_sha256": "a" * 64,
            "storage_object_key": "artifacts/2026/excel_001.xlsx",
        },
    ]

    with pytest.raises(HTTPException) as exc_info:
        create_paired_dossier_bundle(
            db_session,
            actor_id=actor_id,
            org_id=org_id,
            bundle_code="HS-2026-ERR",
            files=files,
        )
    assert exc_info.value.status_code == 400
