"""S15-PR-003 DOCX Extraction Runtime and Table Role Candidates Service."""
from __future__ import annotations

import uuid
from typing import Any, Sequence
from sqlalchemy.orm import Session

from app.modules.excel_import.models import (
    DocxExtractedRow,
    DocxExtractedTable,
    TableRoleCandidate,
)


def classify_table_role(title: str | None, headers: Sequence[str]) -> TableRoleCandidate:
    """Classify extracted Word report table candidate role based on title and headers (ADR 0032)."""
    text_sample = ((title or "") + " " + " ".join(headers)).lower()

    if any(k in text_sample for k in ["thông số kỹ thuật", "đặc tính", "quy cách", "thông số"]):
        return TableRoleCandidate.TECHNICAL_SPECIFICATIONS
    elif any(k in text_sample for k in ["báo giá", "so sánh", "thị trường", "nhà cung cấp", "nhiều báo giá"]):
        return TableRoleCandidate.MARKET_COMPARISON
    elif any(k in text_sample for k in ["kết quả", "tổng hợp", "giá trị định giá", "kết luận"]):
        return TableRoleCandidate.FINAL_VALUATION_SUMMARY

    return TableRoleCandidate.UNKNOWN


def persist_docx_extracted_tables(
    db: Session,
    *,
    org_id: uuid.UUID,
    dossier_bundle_id: uuid.UUID,
    source_file_id: uuid.UUID,
    tables_data: Sequence[dict[str, Any]],
) -> list[DocxExtractedTable]:
    """Persist extracted Word report tables and rows into database."""
    saved_tables: list[DocxExtractedTable] = []

    for idx, tbl in enumerate(tables_data):
        title = tbl.get("raw_title")
        rows = tbl.get("rows", [])
        headers = rows[0] if rows else []

        role = classify_table_role(title, headers)

        ext_tbl = DocxExtractedTable(
            id=uuid.uuid4(),
            organization_id=org_id,
            dossier_bundle_id=dossier_bundle_id,
            source_file_id=source_file_id,
            table_index=idx,
            table_role_candidate=role.value,
            raw_title=title,
            row_count=len(rows),
            col_count=len(headers) if headers else 0,
        )
        db.add(ext_tbl)

        for r_idx, r_cells in enumerate(rows):
            ext_row = DocxExtractedRow(
                id=uuid.uuid4(),
                organization_id=org_id,
                extracted_table_id=ext_tbl.id,
                row_index=r_idx,
                cells_json=list(r_cells),
            )
            db.add(ext_row)

        saved_tables.append(ext_tbl)

    db.commit()
    for st in saved_tables:
        db.refresh(st)

    return saved_tables
