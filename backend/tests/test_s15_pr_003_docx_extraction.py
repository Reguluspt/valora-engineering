"""S15-PR-003 unit tests for DOCX Extraction Runtime and Table Role Candidates."""
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
import app.modules.excel_import.models  # noqa: F401
from app.modules.excel_import.models import TableRoleCandidate
from app.modules.document_engine_intelligence.application.docx_extraction_service import (
    classify_table_role,
    persist_docx_extracted_tables,
)


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


def test_classify_table_role():
    """Verify table role classification heuristics."""
    assert classify_table_role("Bảng thông số kỹ thuật thiết bị", ["STT", "Tên thiết bị", "Quy cách"]) == TableRoleCandidate.TECHNICAL_SPECIFICATIONS
    assert classify_table_role("Bảng so sánh báo giá thị trường", ["STT", "Nhà cung cấp", "Đơn giá"]) == TableRoleCandidate.MARKET_COMPARISON
    assert classify_table_role("Bảng tổng hợp kết quả định giá", ["Hạng mục", "Giá trị"]) == TableRoleCandidate.FINAL_VALUATION_SUMMARY


def test_persist_docx_extracted_tables(db_session: Session):
    """Verify persisting extracted Word tables and rows."""
    org_id = uuid.uuid4()
    bundle_id = uuid.uuid4()
    file_id = uuid.uuid4()

    tables_data = [
        {
            "raw_title": "Bảng thông số kỹ thuật tài sản PD-001",
            "rows": [["STT", "Tên thiết bị", "Công suất"], ["1", "Máy biến áp ABB 110kV", "63MVA"]],
        },
        {
            "raw_title": "Bảng tổng hợp kết quả định giá",
            "rows": [["Hạng mục", "Giá trị VNĐ"], ["Tổng giá trị tài sản", "15000000000"]],
        },
    ]

    saved = persist_docx_extracted_tables(
        db_session,
        org_id=org_id,
        dossier_bundle_id=bundle_id,
        source_file_id=file_id,
        tables_data=tables_data,
    )

    assert len(saved) == 2
    assert saved[0].table_role_candidate == TableRoleCandidate.TECHNICAL_SPECIFICATIONS.value
    assert saved[1].table_role_candidate == TableRoleCandidate.FINAL_VALUATION_SUMMARY.value
