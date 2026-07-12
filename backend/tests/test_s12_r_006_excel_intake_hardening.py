"""
S12-R-006 Excel intake hardening tests — corrected for streaming API.
"""
import io
import zipfile

import openpyxl
import pytest
from fastapi.testclient import TestClient
from fastapi import UploadFile

from app.modules.excel_import.application.parse_workbook import parse_workbook, ParseError
from app.modules.excel_import.domain import ExcelImportLimits
from app.modules.project_master_data.models import (
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    ImportBatchStatus,
)


def _mk_file(filename: str, content: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content))


def _xlsx(sheet: str = "Sheet1", rows: list | None = None) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    if rows:
        for r in rows:
            ws.append([str(c) if c is not None else None for c in r])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


class TestFileBounds:
    def test_uppercase_xlsx(self):
        buf = _xlsx(rows=[["A"], ["v"]])
        staging, fname, sheet, cols = parse_workbook(_mk_file("test.XLSX", buf.read()), None)
        assert len(staging) == 1
        assert cols == 1

    def test_xls_rejected(self):
        with pytest.raises(ParseError) as exc:
            parse_workbook(_mk_file("bad.xls", b"not-excel"), None)
        assert exc.value.error_code == "unsupported_extension"

    def test_oversized(self):
        limits = ExcelImportLimits(max_upload_bytes=100)
        buf = _xlsx(rows=[["A"], ["v"]])
        with pytest.raises(ParseError) as exc:
            parse_workbook(_mk_file("test.xlsx", buf.read()), None, limits=limits)
        assert exc.value.error_code == "upload_too_large"


class TestZipSafety:
    def test_invalid(self):
        with pytest.raises(ParseError) as exc:
            parse_workbook(_mk_file("bad.xlsx", b"not-zip"), None)
        assert exc.value.error_code == "invalid_xlsx"

    def test_many_entries(self):
        limits = ExcelImportLimits(max_zip_entries=5)
        buf = _xlsx(rows=[["A"], ["v"]])
        with pytest.raises(ParseError) as exc:
            parse_workbook(_mk_file("test.xlsx", buf.read()), None, limits=limits)
        assert exc.value.error_code == "zip_entry_limit"

    def test_encrypted(self):
        buf = io.BytesIO()
        zf = zipfile.ZipFile(buf, "w")
        zf.writestr("[Content_Types].xml", "<xml></xml>")
        zf.writestr("xl/workbook.xml", "<xml></xml>")
        zf.setpassword(b"pass")
        zf.close()
        with pytest.raises(ParseError) as exc:
            parse_workbook(_mk_file("enc.xlsx", buf.getvalue()), None)
        assert exc.value.error_code in ("encrypted_archive", "invalid_xlsx")


class TestSheet:
    def test_missing_sheet(self):
        buf = _xlsx(sheet="Wrong", rows=[["A"], ["v"]])
        with pytest.raises(ParseError) as exc:
            parse_workbook(_mk_file("test.xlsx", buf.read()), "Missing")
        assert exc.value.error_code == "sheet_not_found"

    def test_empty_wb(self):
        buf = io.BytesIO()
        zf = zipfile.ZipFile(buf, "w")
        zf.writestr("[Content_Types].xml", "<xml></xml>")
        zf.writestr("xl/workbook.xml", "<xml></xml>")
        zf.close()
        with pytest.raises(ParseError) as exc:
            parse_workbook(_mk_file("empty.xlsx", buf.getvalue()), None)
        assert exc.value.error_code in ("invalid_xlsx",)


class TestRowLimits:
    def test_5000_ok(self):
        limits = ExcelImportLimits(max_data_rows=5000, max_physical_rows=5100)
        rows = [["H"]] + [[f"r{i}"] for i in range(5000)]
        buf = _xlsx(rows=rows)
        staging, _, _, _ = parse_workbook(_mk_file("test.xlsx", buf.read()), None, limits=limits)
        assert len(staging) == 5000

    def test_5001_reject(self):
        limits = ExcelImportLimits(max_data_rows=5000, max_physical_rows=5100)
        rows = [["H"]] + [[f"r{i}"] for i in range(5001)]
        buf = _xlsx(rows=rows)
        with pytest.raises(ParseError) as exc:
            parse_workbook(_mk_file("test.xlsx", buf.read()), None, limits=limits)
        assert exc.value.error_code == "data_row_limit"


class TestColumnLimits:
    def test_100_ok(self):
        limits = ExcelImportLimits(max_columns=100)
        h = [f"c{i}" for i in range(100)]
        buf = _xlsx(rows=[h, [str(i) for i in range(100)]])
        staging, _, _, cols = parse_workbook(_mk_file("test.xlsx", buf.read()), None, limits=limits)
        assert cols == 100
        assert len(staging) == 1

    def test_101_reject(self):
        limits = ExcelImportLimits(max_columns=100)
        h = [f"c{i}" for i in range(101)]
        buf = _xlsx(rows=[h, [str(i) for i in range(101)]])
        with pytest.raises(ParseError) as exc:
            parse_workbook(_mk_file("test.xlsx", buf.read()), None, limits=limits)
        assert exc.value.error_code == "column_limit"


class TestRawCells:
    def test_duplicates(self):
        buf = _xlsx(rows=[["A", "A"], ["1", "2"]])
        staging, _, _, _ = parse_workbook(_mk_file("test.xlsx", buf.read()), None)
        cells = staging[0]["raw_cells"]
        assert len(cells) == 2
        assert cells[0]["header"] == "A"
        assert cells[1]["header"] == "A"
        assert cells[0]["value"] == "1"
        assert cells[1]["value"] == "2"

    def test_blanks(self):
        buf = _xlsx(rows=[["A", "", "B"], ["1", "blank", "3"]])
        staging, _, _, _ = parse_workbook(_mk_file("test.xlsx", buf.read()), None)
        cells = staging[0]["raw_cells"]
        assert cells[1]["header"] == ""
        assert cells[1]["value"] == "blank"

    def test_positions(self):
        buf = _xlsx(rows=[["A", "B", "C"], ["x", "y", "z"]])
        staging, _, _, _ = parse_workbook(_mk_file("test.xlsx", buf.read()), None)
        c = staging[0]["raw_cells"]
        assert c[0]["column_index"] == 1
        assert c[0]["column_letter"] == "A"
        assert c[1]["column_index"] == 2
        assert c[1]["column_letter"] == "B"

    def test_extra_columns(self):
        buf = _xlsx(rows=[["A"], ["1", "2", "3"]])
        staging, _, _, _ = parse_workbook(_mk_file("test.xlsx", buf.read()), None)
        cells = staging[0]["raw_cells"]
        assert len(cells) == 3
        assert cells[2]["header"] == ""
        assert cells[2]["value"] == "3"


class TestFormula:
    def test_not_evaluated(self):
        buf = _xlsx(rows=[["A"], ["text", "=SUM(1+1)"]])
        staging, _, _, _ = parse_workbook(_mk_file("test.xlsx", buf.read()), None)
        val = staging[0]["raw_cells"][1]["value"]
        assert isinstance(val, str)
        assert val != "3"


class TestReupload:
    def test_preserved(self):
        from app.main import app
        from app.db import Base, get_db
        from app.modules.project_master_data.models import (
            OrganizationProfile, OrganizationStatus, User, UserStatus,
            Role, UserRole, Customer, CustomerStatus, Project, ProjectWorkflowStatus,
        )
        from sqlalchemy import create_engine as ce
        from sqlalchemy.pool import StaticPool
        engine = ce("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=engine)
        from sqlalchemy.orm import Session as S
        sess = S(bind=engine)
        try:
            o = OrganizationProfile(legal_name="T", organization_slug="t", status=OrganizationStatus.ACTIVE)
            sess.add(o)
            sess.commit()
            r = Role(code="e", display_name="E", permissions=["project:read","workbench:edit"])
            sess.add(r)
            sess.commit()
            u = User(organization_id=o.id, email="u@t.com", full_name="U", status=UserStatus.ACTIVE)
            sess.add(u)
            sess.commit()
            ur = UserRole(user_id=u.id, role_id=r.id, is_active=True)
            sess.add(ur)
            sess.commit()
            c = Customer(organization_id=o.id, legal_name="C", status=CustomerStatus.ACTIVE, created_by=u.id)
            sess.add(c)
            sess.commit()
            p = Project(organization_id=o.id, customer_id=c.id, code="P", name="P", status=ProjectWorkflowStatus.DRAFT, created_by=u.id)
            sess.add(p)
            sess.commit()
            b = ProjectAssetImportBatch(organization_id=o.id, project_id=p.id, source_filename="old.xlsx", status=ImportBatchStatus.PARSED, total_rows=3, created_by_user_id=u.id)
            sess.add(b)
            sess.commit()
            for i in range(3):
                sr = ProjectAssetImportStagingRow(organization_id=o.id, project_id=p.id, import_batch_id=b.id, source_row_number=i+1, raw_values={"cells":[]}, mapped_values={}, normalized_preview={}, validation_status="valid", proposed_asset_name=f"O{i}")
                sess.add(sr)
            sess.commit()
            pre = sess.query(ProjectAssetImportStagingRow).filter(ProjectAssetImportStagingRow.import_batch_id==b.id).count()
            assert pre > 0
            app.dependency_overrides[get_db] = lambda: sess
            cl = TestClient(app)
            resp = cl.post(f"/api/v1/projects/{p.id}/asset-imports/{b.id}/upload", files={"file": ("bad.xls", b"not-wb", "app/vnd.ms-excel")}, headers={"X-User-Id": str(u.id)})
            assert resp.status_code in (400, 413)
            post = sess.query(ProjectAssetImportStagingRow).filter(ProjectAssetImportStagingRow.import_batch_id==b.id).count()
            assert post == pre
        finally:
            app.dependency_overrides.clear()
            sess.close()
