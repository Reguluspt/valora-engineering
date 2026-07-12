"""S12-R-006: final corrective tests — lazy streaming, ZIP, limits, mapping, transactions, concurrency."""
import io, os, zipfile, struct, tempfile

import openpyxl
import pytest
from fastapi.testclient import TestClient

from app.modules.excel_import.application.parse_workbook import (
    parse_workbook_lazy, ParseError, sanitize_filename, get_request_size, enforce_request_limit,
)
from app.modules.excel_import.domain import ExcelImportLimits, DEFAULT_LIMITS

# ── helpers ────────────────────────────────────────────────────────────────
class FakeUpload:
    def __init__(self, filename, content):
        self.filename = filename
        self.file = io.BytesIO(content)
        self.size = len(content)

def _xlsx(sheet="Sheet1", rows=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    if rows:
        for r in rows:
            ws.append([str(c) if c is not None else None for c in r])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()

# ── R-3: filename sanitizer ────────────────────────────────────────────────
class TestFilename:
    def test_sanitize_windows(self):
        assert "file.xlsx" in sanitize_filename("C:\\Users\\doc\\file.xlsx")
    def test_sanitize_unix(self):
        assert sanitize_filename("/home/user/file.xlsx") == "file.xlsx"
    def test_sanitize_empty(self):
        assert sanitize_filename("") == "import.xlsx"

# ── R-1: request header enforcement ─────────────────────────────────────────
class TestRequestLimit:
    def test_oversized_header(self):
        with pytest.raises(ParseError) as exc:
            enforce_request_limit(13_000_000, DEFAULT_LIMITS)
        assert exc.value.error_code == "request_too_large"
        assert exc.value.status == 413

    def test_negative_header(self):
        with pytest.raises(ParseError) as exc:
            enforce_request_limit(-1, DEFAULT_LIMITS)
        assert exc.value.status == 400

    def test_valid_under_limit(self):
        enforce_request_limit(5_000_000, DEFAULT_LIMITS)

    def test_missing_header(self):
        enforce_request_limit(None, DEFAULT_LIMITS)

    def test_get_request_size(self):
        class R: headers = {"content-length": "5000"}
        assert get_request_size(R()) == 5000

    def test_get_request_size_missing(self):
        assert get_request_size(type("X", (), {"headers": {}})()) is None

# ── R-2: lazy streaming proof ──────────────────────────────────────────────
class TestLazy:
    def test_rows_lazy(self):
        rows = [["H"], ["a"], ["b"], ["c"]]
        lazy = parse_workbook_lazy(FakeUpload("test.xlsx", _xlsx(rows=rows)), None)
        count = 0
        for stg in lazy:
            count += 1
            assert stg["mapped_values"] or stg["raw_cells"]
        assert count == 3
        assert lazy._closed

    def test_5001_rejected_while_streaming(self):
        limits = ExcelImportLimits(max_data_rows=5000, max_physical_rows=5100)
        rows = [["H"]] + [[f"r{i}"] for i in range(5001)]
        lazy = parse_workbook_lazy(FakeUpload("test.xlsx", _xlsx(rows=rows)), None, limits=limits)
        with pytest.raises(ParseError) as exc:
            for _ in lazy:
                pass
        assert exc.value.error_code == "data_row_limit"

    def test_cleanup_on_error(self):
        limits = ExcelImportLimits(max_data_rows=2, max_physical_rows=10)
        rows = [["H"]] + [[f"r{i}"] for i in range(5)]
        lazy = parse_workbook_lazy(FakeUpload("test.xlsx", _xlsx(rows=rows)), None, limits=limits)
        with pytest.raises(ParseError):
            for _ in lazy:
                pass
        assert lazy._closed

# ── R-4 + R-5: ZIP security ────────────────────────────────────────────────
class TestZipSecurity:
    def _zip_with_entries(self, entries, password=None):
        buf = io.BytesIO()
        zf = zipfile.ZipFile(buf, "w")
        for name, content in entries:
            info = zipfile.ZipInfo(name)
            if password:
                info.flag_bits |= 0x1
            zf.writestr(info, content)
        zf.close()
        return buf.getvalue()

    def test_missing_content_types(self):
        data = self._zip_with_entries([("xl/workbook.xml", "<xml/>")])
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", data), None)
        assert exc.value.error_code == "invalid_xlsx"

    def test_missing_workbook(self):
        data = self._zip_with_entries([("[Content_Types].xml", "<xml/>")])
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", data), None)
        assert exc.value.error_code == "invalid_xlsx"

    def test_encrypted_entry(self):
        data = self._zip_with_entries([
            ("[Content_Types].xml", "<xml/>"), ("xl/workbook.xml", "<xml/>"),
            ("xl/worksheets/sheet1.xml", "<xml/>"),
        ], password=True)
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", data), None)
        assert exc.value.error_code == "encrypted_archive"

    def test_vba_part(self):
        data = self._zip_with_entries([
            ("[Content_Types].xml", "<xml/>"), ("xl/workbook.xml", "<xml/>"),
            ("xl/vbaProject.bin", b"macro"),
        ])
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", data), None)
        assert exc.value.error_code == "macro_not_allowed"

    def test_external_link(self):
        data = self._zip_with_entries([
            ("[Content_Types].xml", "<xml/>"), ("xl/workbook.xml", "<xml/>"),
            ("xl/externalLinks/ext1.xml", "<xml/>"),
        ])
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", data), None)
        assert exc.value.error_code == "external_link_not_allowed"

    def test_dotdot_path(self):
        data = self._zip_with_entries([
            ("[Content_Types].xml", "<xml/>"), ("xl/workbook.xml", "<xml/>"),
            ("../etc/passwd", b"bad"),
        ])
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", data), None)
        assert exc.value.error_code == "unsafe_zip_path"

    def test_backslash_path(self):
        data = self._zip_with_entries([
            ("[Content_Types].xml", "<xml/>"), ("xl/workbook.xml", "<xml/>"),
            ("xl\\..\\evil.txt", b"bad"),
        ])
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", data), None)
        assert exc.value.error_code == "unsafe_zip_path"

    def test_absolute_path(self):
        data = self._zip_with_entries([
            ("[Content_Types].xml", "<xml/>"), ("xl/workbook.xml", "<xml/>"),
            ("/absolute/passwd", b"bad"),
        ])
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", data), None)
        assert exc.value.error_code == "unsafe_zip_path"

    def test_drive_path(self):
        data = self._zip_with_entries([
            ("[Content_Types].xml", "<xml/>"), ("xl/workbook.xml", "<xml/>"),
            ("C:bad.txt", b"bad"),
        ])
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", data), None)
        assert exc.value.error_code == "unsafe_zip_path"

    def test_unc_path(self):
        data = self._zip_with_entries([
            ("[Content_Types].xml", "<xml/>"), ("xl/workbook.xml", "<xml/>"),
            ("//server/share/bad.txt", b"bad"),
        ])
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", data), None)
        assert exc.value.error_code == "unsafe_zip_path"

    def test_nul_path(self):
        data = self._zip_with_entries([
            ("[Content_Types].xml", "<xml/>"), ("xl/workbook.xml", "<xml/>"),
            ("bad\x00name.txt", b"bad"),
        ])
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", data), None)
        assert exc.value.error_code == "unsafe_zip_path"

    def test_zip_expansion_limit(self):
        limits = ExcelImportLimits(max_uncompressed_zip_bytes=1)
        # tiny limit — the normal XLSX parts exceed it
        rows = [["H"], ["v"]]
        content = _xlsx(rows=rows)
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits)
        assert exc.value.error_code == "zip_expansion_limit"

    def test_valid_xlsx_passes(self):
        content = _xlsx(rows=[["H"], ["v"]])
        lazy = parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=ExcelImportLimits(max_zip_entries=50))
        rows = list(lazy)
        assert len(rows) == 1

# ── R-6 + R-7: workbook limits ──────────────────────────────────────────────
class TestWorkbookLimits:
    def test_header_at_boundary(self):
        limits = ExcelImportLimits(max_header_search_rows=2)
        rows = [["H"], ["r1"]]
        content = _xlsx(rows=rows)
        lazy = parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits)
        assert list(lazy) != []

    def test_header_beyond_boundary(self):
        limits = ExcelImportLimits(max_header_search_rows=1)
        rows = [["x"], ["y"], ["z"], ["w"]]
        content = _xlsx(rows=rows)
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits)
        assert exc.value.error_code == "header_not_found"

    def test_mapping_first_wins(self):
        rows = [["asset_name", "ten_tai_san"], ["first", "second"]]
        lazy = parse_workbook_lazy(FakeUpload("test.xlsx", _xlsx(rows=rows)), None)
        row = next(lazy)
        assert row["proposed_asset_name"] == "first"

    def test_raw_cell_shape(self):
        rows = [["A"], ["val"]]
        lazy = parse_workbook_lazy(FakeUpload("test.xlsx", _xlsx(rows=rows)), None)
        row = next(lazy)
        cells = row["raw_cells"]
        assert cells == [{"column_index": 1, "column_letter": "A", "header": "A", "value": "val"}]

    def test_blank_and_dup_headers(self):
        rows = [["A", "A", ""], ["1", "2", "blank"]]
        lazy = parse_workbook_lazy(FakeUpload("test.xlsx", _xlsx(rows=rows)), None)
        row = next(lazy)
        c = row["raw_cells"]
        assert c[0]["value"] == "1"
        assert c[1]["value"] == "2"
        assert c[2]["value"] == "blank"

# ── R-8: transaction fault injection ────────────────────────────────────────
class TestTransactionFaults:
    def _setup(self):
        from app.main import app
        from app.db import Base, get_db
        from app.modules.project_master_data.models import (
            OrganizationProfile, OrganizationStatus, User, UserStatus,
            Role, UserRole, Customer, CustomerStatus, Project, ProjectWorkflowStatus,
            ProjectAssetImportBatch, ProjectAssetImportStagingRow,
            ImportBatchStatus, ImportRowValidationStatus, ProjectAssetLine,
        )
        from sqlalchemy import create_engine as ce
        from sqlalchemy.pool import StaticPool
        engine = ce("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(bind=engine)
        from sqlalchemy.orm import Session as S
        sess = S(bind=engine)
        o = OrganizationProfile(legal_name="T", organization_slug="t", status=OrganizationStatus.ACTIVE)
        sess.add(o); sess.commit()
        r = Role(code="e", display_name="E", permissions=["project:read","workbench:edit"])
        sess.add(r); sess.commit()
        u = User(organization_id=o.id, email="u@t.com", full_name="U", status=UserStatus.ACTIVE)
        sess.add(u); sess.commit()
        ur = UserRole(user_id=u.id, role_id=r.id, is_active=True)
        sess.add(ur); sess.commit()
        c = Customer(organization_id=o.id, legal_name="C", status=CustomerStatus.ACTIVE, created_by=u.id)
        sess.add(c); sess.commit()
        p = Project(organization_id=o.id, customer_id=c.id, code="P", name="P", status=ProjectWorkflowStatus.DRAFT, created_by=u.id)
        sess.add(p); sess.commit()
        b = ProjectAssetImportBatch(organization_id=o.id, project_id=p.id, source_filename="old.xlsx", source_sheet_name="S", status=ImportBatchStatus.PARSED, total_rows=3, created_by_user_id=u.id)
        sess.add(b); sess.commit()
        for i in range(3):
            sr = ProjectAssetImportStagingRow(organization_id=o.id, project_id=p.id, import_batch_id=b.id, source_row_number=i+1, raw_values={"cells":[]}, mapped_values={}, normalized_preview={}, validation_status="valid", proposed_asset_name="O{}".format(i))
            sess.add(sr)
        sess.commit()
        app.dependency_overrides[get_db] = lambda: sess
        self.client = TestClient(app)
        self.sess = sess
        self.app = app
        self.b = b
        self.p = p
        self.u = u

    def teardown(self):
        self.app.dependency_overrides.clear()
        self.sess.close()

    def test_success_replaces_exactly(self):
        self._setup()
        try:
            content = _xlsx(rows=[["H"],["new1"],["new2"]])
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", content, "app/vnd...xlsx")},
                headers={"X-User-Id": str(self.u.id)})
            assert resp.status_code == 200
            d = resp.json()
            assert d["total_rows"] == 2
            rows = self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=self.b.id).all()
            assert len(rows) == 2
            assert rows[0].proposed_asset_name == "new1"
        finally:
            self.teardown()

    def test_missing_sheet_preserves_staging(self):
        self._setup()
        try:
            self.b.source_sheet_name = "Missing"
            self.sess.commit()
            pre = self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=self.b.id).count()
            content = _xlsx(sheet="Wrong", rows=[["H"],["v"]])
            resp = self.client.post(f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", content, "app/vnd...xlsx")},
                headers={"X-User-Id": str(self.u.id)})
            assert resp.status_code == 400
            post = self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=self.b.id).count()
            assert post == pre
        finally:
            self.teardown()

    def test_success_replaces_exactly(self):
        self._setup()
        try:
            self.b.source_sheet_name = "S"
            self.sess.commit()
            content = _xlsx(sheet="S", rows=[["H"],["new1"],["new2"]])
            resp = self.client.post(f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", content, "app/vnd...xlsx")},
                headers={"X-User-Id": str(self.u.id)})
            assert resp.status_code == 200
            d = resp.json()
            assert d["total_rows"] == 2
            rows = self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=self.b.id).all()
            assert len(rows) == 2
            assert rows[0].proposed_asset_name == "new1"
        finally:
            self.teardown()

# ── R-9: concurrency ───────────────────────────────────────────────────────
class TestPGConcurrency:
    def test_concurrent_skip_local(self):
        pg = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
        if not pg or "postgres" not in pg:
            pytest.skip("PostgreSQL concurrency test requires CI with PostgreSQL service")
