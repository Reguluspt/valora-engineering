"""
S12-R-006 Excel intake hardening tests.
Tests for file bounds, ZIP safety, streaming limits, raw cell preservation,
and re-upload atomicity.
"""
import io
import struct
import os
import zipfile

import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.excel_import.application import parse_uploaded_workbook
from app.modules.excel_import.domain import ExcelImportLimits
from app.modules.project_master_data.models import (
    ProjectAssetLine,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    ImportBatchStatus,
)


# ── helpers ────────────────────────────────────────────────────────────────
def _make_upload_file(filename: str, content: bytes) -> "UploadFile":
    from fastapi import UploadFile
    return UploadFile(filename=filename, file=io.BytesIO(content))


def _make_xlsx(sheet_name: str = "Sheet1", rows: list[list] | None = None) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    if ws:
        ws.title = sheet_name
    if rows:
        for row in rows:
            ws.append([str(c) if c is not None else None for c in row])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ── B1: file/request bounds ────────────────────────────────────────────────
class TestFileBounds:
    def test_uppercase_xlsx_succeeds(self):
        buf = _make_xlsx(rows=[["A"], ["v"]])
        staged, headers, raw_cells, count, name = parse_uploaded_workbook(
            _make_upload_file("test.XLSX", buf.read()), source_sheet_name=None
        )
        assert count == 1

    def test_xls_rejected(self):
        with pytest.raises(Exception) as exc:
            parse_uploaded_workbook(
                _make_upload_file("bad.xls", b"not-excel"), source_sheet_name=None
            )
        assert "không được hỗ trợ" in str(exc.value.detail)

    def test_chunked_upload_exceeding_limit(self):
        limits = ExcelImportLimits(max_upload_bytes=100)
        large = b"x" * 101
        buf = _make_xlsx(rows=[["A"], ["v"]])
        content = buf.read()
        with pytest.raises(Exception) as exc:
            parse_uploaded_workbook(
                _make_upload_file("test.xlsx", content), source_sheet_name=None, limits=limits
            )
        assert "vượt quá" in str(exc.value.detail)


# ── B2: ZIP/XLSX safety ────────────────────────────────────────────────────
class TestZipSafety:
    def test_invalid_zip_rejected(self):
        with pytest.raises(Exception) as exc:
            parse_uploaded_workbook(
                _make_upload_file("bad.xlsx", b"not-a-zip"), source_sheet_name=None
            )
        assert "không hợp lệ" in str(exc.value.detail)

    def test_too_many_zip_entries(self):
        limits = ExcelImportLimits(max_zip_entries=5)
        buf = _make_xlsx(rows=[["A"], ["v"]])
        content = buf.read()
        with pytest.raises(Exception) as exc:
            parse_uploaded_workbook(
                _make_upload_file("test.xlsx", content), source_sheet_name=None, limits=limits
            )
        assert "quá nhiều" in str(exc.value.detail)

    def test_encrypted_zip_rejected(self):
        buf = io.BytesIO()
        zf = zipfile.ZipFile(buf, "w")
        zf.writestr("[Content_Types].xml", "<xml></xml>")
        zf.writestr("xl/workbook.xml", "<xml></xml>")
        zf.setpassword(b"pass")
        zf.close()
        with pytest.raises(Exception) as exc:
            parse_uploaded_workbook(
                _make_upload_file("enc.xlsx", buf.getvalue()), source_sheet_name=None
            )
        detail = str(exc.value.detail).lower()
        assert "mã hóa" in detail or "không thể đọc" in detail


# ── B3: sheet selection ────────────────────────────────────────────────────
class TestSheetSelection:
    def test_requested_sheet_not_found(self):
        buf = _make_xlsx(sheet_name="Wrong", rows=[["A"], ["v"]])
        with pytest.raises(Exception) as exc:
            parse_uploaded_workbook(
                _make_upload_file("test.xlsx", buf.read()), source_sheet_name="Missing"
            )
        assert "không tồn tại" in str(exc.value.detail)

    def test_empty_workbook_rejected(self):
        buf = io.BytesIO()
        zf = zipfile.ZipFile(buf, "w")
        zf.writestr("[Content_Types].xml", "<xml></xml>")
        zf.writestr("xl/workbook.xml", "<xml></xml>")
        zf.close()
        with pytest.raises(Exception) as exc:
            parse_uploaded_workbook(
                _make_upload_file("empty.xlsx", buf.getvalue()), source_sheet_name=None
            )
        detail = str(exc.value.detail).lower()
        assert any(w in detail for w in ["không chứa", "trống", "không thể đọc"])


# ── B4: row limits ─────────────────────────────────────────────────────────
class TestRowLimits:
    def test_5000_rows_accepted(self):
        limits = ExcelImportLimits(max_data_rows=5000, max_physical_rows=5100)
        rows = [["H"]] + [[f"r{i}"] for i in range(5000)]
        buf = _make_xlsx(rows=rows)
        _, _, _, count, _ = parse_uploaded_workbook(
            _make_upload_file("test.xlsx", buf.read()), source_sheet_name=None, limits=limits
        )
        assert count == 5000

    def test_5001_rows_rejected(self):
        limits = ExcelImportLimits(max_data_rows=5000, max_physical_rows=5100)
        rows = [["H"]] + [[f"r{i}"] for i in range(5001)]
        buf = _make_xlsx(rows=rows)
        with pytest.raises(Exception) as exc:
            parse_uploaded_workbook(
                _make_upload_file("test.xlsx", buf.read()), source_sheet_name=None, limits=limits
            )
        assert "5000" in str(exc.value.detail)


# ── B5: column limits ──────────────────────────────────────────────────────
class TestColumnLimits:
    def test_100_columns_accepted(self):
        limits = ExcelImportLimits(max_columns=100)
        header = [f"C{i}" for i in range(100)]
        buf = _make_xlsx(rows=[header, [str(i) for i in range(100)]])
        _, _, _, count, _ = parse_uploaded_workbook(
            _make_upload_file("test.xlsx", buf.read()), source_sheet_name=None, limits=limits
        )
        assert count == 1

    def test_101_columns_rejected(self):
        limits = ExcelImportLimits(max_columns=100)
        header = [f"C{i}" for i in range(101)]
        buf = _make_xlsx(rows=[header, [str(i) for i in range(101)]])
        with pytest.raises(Exception) as exc:
            parse_uploaded_workbook(
                _make_upload_file("test.xlsx", buf.read()), source_sheet_name=None, limits=limits
            )
        assert "cột" in str(exc.value.detail).lower()


# ── B6: raw cells preserve duplicates and blanks ───────────────────────────
class TestRawCells:
    def test_duplicate_headers_preserved(self):
        buf = _make_xlsx(rows=[["A", "A"], ["1", "2"]])
        _, _, raw_cells_list, _, _ = parse_uploaded_workbook(
            _make_upload_file("test.xlsx", buf.read()), source_sheet_name=None
        )
        cells = raw_cells_list[0]
        assert len(cells) == 2
        assert cells[0]["header"] == "A"
        assert cells[1]["header"] == "A"
        assert cells[0]["value"] == "1"
        assert cells[1]["value"] == "2"

    def test_blank_headers_preserved(self):
        buf = _make_xlsx(rows=[["A", "", "B"], ["1", "blank", "3"]])
        _, _, raw_cells_list, _, _ = parse_uploaded_workbook(
            _make_upload_file("test.xlsx", buf.read()), source_sheet_name=None
        )
        cells = raw_cells_list[0]
        assert cells[1]["header"] == ""
        assert cells[1]["value"] == "blank"


# ── B7: formula safety ─────────────────────────────────────────────────────
class TestFormulaSafety:
    def test_formula_not_evaluated(self):
        buf = _make_xlsx(rows=[["A"], ["text", "=SUM(1+1)"]])
        _, _, raw_cells_list, _, _ = parse_uploaded_workbook(
            _make_upload_file("test.xlsx", buf.read()), source_sheet_name=None
        )
        assert len(raw_cells_list) >= 1
        val = raw_cells_list[0][1]["value"]
        assert isinstance(val, str)
        assert val != "3"  # formula should never produce a computed value


# ── B8: re-upload preservation and atomicity ──────────────────────────────
class TestReuploadAtomicity:
    def test_staging_preserved_on_upload_failure(self):
        from app.main import app
        from app.db import Base, get_db
        from app.modules.project_master_data.models import (
            OrganizationProfile, OrganizationStatus, User, UserStatus,
            Role, UserRole, Customer, CustomerStatus, Project, ProjectWorkflowStatus,
        )
        engine = _create_test_engine()
        Base.metadata.create_all(bind=engine)
        sess = Session(bind=engine)
        try:
            org = _seed_org(sess)
            user = _seed_user(sess, org)
            proj = _seed_project(sess, org, user)
            batch = _seed_parsed_batch(sess, org, proj, user)
            batch_id = batch.id

            pre_count = sess.query(ProjectAssetImportStagingRow).filter(
                ProjectAssetImportStagingRow.import_batch_id == batch_id
            ).count()
            assert pre_count > 0

            app.dependency_overrides[get_db] = lambda: sess
            client = TestClient(app)

            resp = client.post(
                f"/api/v1/projects/{proj.id}/asset-imports/{batch.id}/upload",
                files={"file": ("bad.xls", b"not-a-workbook", "application/vnd.ms-excel")},
                headers={"X-User-Id": str(user.id)},
            )
            assert resp.status_code in (400, 413)

            post_count = sess.query(ProjectAssetImportStagingRow).filter(
                ProjectAssetImportStagingRow.import_batch_id == batch_id
            ).count()
            assert post_count == pre_count
        finally:
            app.dependency_overrides.clear()
            sess.close()


def _create_test_engine():
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    return create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def _seed_org(sess):
    from app.modules.project_master_data.models import OrganizationProfile, OrganizationStatus
    org = OrganizationProfile(legal_name="Test", organization_slug="test", status=OrganizationStatus.ACTIVE)
    sess.add(org)
    sess.commit()
    return org


def _seed_user(sess, org):
    from app.modules.project_master_data.models import User, UserStatus, Role, UserRole
    role = Role(code="editor", display_name="E", permissions=["project:read", "workbench:edit"])
    sess.add(role)
    sess.commit()
    user = User(organization_id=org.id, email="u@t.com", full_name="U", status=UserStatus.ACTIVE)
    sess.add(user)
    sess.commit()
    sess.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))
    sess.commit()
    return user


def _seed_project(sess, org, user):
    from app.modules.project_master_data.models import Customer, CustomerStatus, Project, ProjectWorkflowStatus
    c = Customer(organization_id=org.id, legal_name="Cust", status=CustomerStatus.ACTIVE, created_by=user.id)
    sess.add(c)
    sess.commit()
    p = Project(organization_id=org.id, customer_id=c.id, code="P", name="P", status=ProjectWorkflowStatus.DRAFT, created_by=user.id)
    sess.add(p)
    sess.commit()
    return p


def _seed_parsed_batch(sess, org, proj, user):
    from app.modules.project_master_data.models import ProjectAssetImportBatch, ProjectAssetImportStagingRow, ImportBatchStatus, ImportRowValidationStatus
    batch = ProjectAssetImportBatch(organization_id=org.id, project_id=proj.id, source_filename="old.xlsx", status=ImportBatchStatus.PARSED, total_rows=3, created_by_user_id=user.id)
    sess.add(batch)
    sess.commit()
    for i in range(3):
        sr = ProjectAssetImportStagingRow(organization_id=org.id, project_id=proj.id, import_batch_id=batch.id, source_row_number=i+1, raw_values={"cells": []}, mapped_values={}, normalized_preview={}, validation_status=ImportRowValidationStatus.VALID, proposed_asset_name=f"Old{i}")
        sess.add(sr)
    sess.commit()
    return batch
