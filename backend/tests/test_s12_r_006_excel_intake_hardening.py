"""S12-R-006: complete restored and concurrency tests."""
import io
import os
import uuid
import zipfile
import threading
import time
import openpyxl
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db
from app.modules.excel_import.application.parse_workbook import (
    parse_workbook_lazy, ParseError
)
from app.modules.excel_import.application.import_service import upload_excel_file_orchestrator
from app.modules.excel_import.domain import ExcelImportLimits
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, User, UserStatus,
    Role, UserRole, Customer, CustomerStatus, Project, ProjectWorkflowStatus,
    ProjectAssetImportBatch, ProjectAssetImportStagingRow,
    ImportBatchStatus, ProjectAssetLine, AuditEvent
)

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

class BaseExcelTest:
    def _setup(self, db_url="sqlite:///:memory:"):
        if db_url == "sqlite:///:memory:":
            self.engine = create_engine(db_url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
        else:
            self.engine = create_engine(db_url)
        Base.metadata.create_all(bind=self.engine)
        
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.sess = self.SessionLocal()
        
        self.org = OrganizationProfile(legal_name="T", organization_slug="t", status=OrganizationStatus.ACTIVE)
        self.sess.add(self.org)
        self.sess.commit()
        
        self.role = Role(code="e", display_name="E", permissions=["project:read","workbench:edit"])
        self.sess.add(self.role)
        self.sess.commit()
        
        self.u = User(organization_id=self.org.id, email="u@t.com", full_name="U", status=UserStatus.ACTIVE)
        self.sess.add(self.u)
        self.sess.commit()
        
        self.ur = UserRole(user_id=self.u.id, role_id=self.role.id, is_active=True)
        self.sess.add(self.ur)
        self.sess.commit()
        
        self.cust = Customer(organization_id=self.org.id, legal_name="C", status=CustomerStatus.ACTIVE, created_by=self.u.id)
        self.sess.add(self.cust)
        self.sess.commit()
        
        self.p = Project(organization_id=self.org.id, customer_id=self.cust.id, code="P", name="P", status=ProjectWorkflowStatus.DRAFT, created_by=self.u.id)
        self.sess.add(self.p)
        self.sess.commit()
        
        self.b = ProjectAssetImportBatch(organization_id=self.org.id, project_id=self.p.id, source_filename="old.xlsx", source_sheet_name="Sheet1", status=ImportBatchStatus.PARSED, total_rows=3, created_by_user_id=self.u.id)
        self.sess.add(self.b)
        self.sess.commit()
        
        self.seeded_staging_ids = []
        for i in range(3):
            sr = ProjectAssetImportStagingRow(
                organization_id=self.org.id,
                project_id=self.p.id,
                import_batch_id=self.b.id,
                source_row_number=i+1,
                raw_values={"cells":[{"column_index": 1, "column_letter": "A", "header": "asset_name", "value": f"O{i}"}]},
                mapped_values={"proposed_asset_name": f"O{i}"},
                normalized_preview={},
                validation_status="valid",
                proposed_asset_name=f"O{i}"
            )
            self.sess.add(sr)
            self.sess.commit()
            self.seeded_staging_ids.append(sr.id)

        self.al = ProjectAssetLine(
            project_id=self.p.id,
            asset_name="Immutable Asset",
            quantity=10.0,
            row_version=1
        )
        self.sess.add(self.al)
        self.sess.commit()
        self.al_id = self.al.id

        app.dependency_overrides[get_db] = lambda: self.sess
        self.client = TestClient(app)

    def teardown(self):
        app.dependency_overrides.clear()
        self.sess.close()
        if self.engine.url.drivername != 'sqlite':
            # Clean only test-specific entries in real DB
            pass

# ── L-1: ZIP and XLSX Safety Restorations ──────────────────────────────────
class TestZipSafetyRestored:
    def test_invalid_zip(self):
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", b"invalid-zip-headers"), None)
        assert exc.value.error_code == "invalid_xlsx"

    def test_missing_content_types(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("xl/workbook.xml", "<xml></xml>")
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", buf.getvalue()), None)
        assert exc.value.error_code == "invalid_xlsx"

    def test_missing_workbook_xml(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<xml></xml>")
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", buf.getvalue()), None)
        assert exc.value.error_code == "invalid_xlsx"

    def test_zip_entry_limit(self):
        limits = ExcelImportLimits(max_zip_entries=2)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<xml></xml>")
            zf.writestr("xl/workbook.xml", "<xml></xml>")
            zf.writestr("xl/styles.xml", "<xml></xml>")
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", buf.getvalue()), None, limits=limits)
        assert exc.value.error_code == "zip_entry_limit"

    def test_uncompressed_expansion_limit(self):
        limits = ExcelImportLimits(max_uncompressed_zip_bytes=10)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "a" * 15)
            zf.writestr("xl/workbook.xml", "b" * 15)
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", buf.getvalue()), None, limits=limits)
        assert exc.value.error_code == "zip_expansion_limit"

    def test_encrypted_metadata(self, monkeypatch):
        orig_infolist = zipfile.ZipFile.infolist
        def mock_infolist(self):
            infos = orig_infolist(self)
            for info in infos:
                if info.filename == "xl/workbook.xml":
                    info.flag_bits = 1
            return infos
        monkeypatch.setattr(zipfile.ZipFile, "infolist", mock_infolist)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<xml></xml>")
            zf.writestr("xl/workbook.xml", "<xml></xml>")
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", buf.getvalue()), None)
        assert exc.value.error_code == "encrypted_archive"

    def test_vba_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<xml></xml>")
            zf.writestr("xl/workbook.xml", "<xml></xml>")
            zf.writestr("xl/vbaProject.bin", "vba-code")
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", buf.getvalue()), None)
        assert exc.value.error_code == "macro_not_allowed"

    def test_external_link_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<xml></xml>")
            zf.writestr("xl/workbook.xml", "<xml></xml>")
            zf.writestr("xl/externalLinks/sheet1.xml", "link")
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", buf.getvalue()), None)
        assert exc.value.error_code == "external_link_not_allowed"

    def test_dotdot_traversal(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<xml></xml>")
            zf.writestr("xl/workbook.xml", "<xml></xml>")
            zf.writestr("xl/../escaped.xml", "leak")
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", buf.getvalue()), None)
        assert exc.value.error_code == "unsafe_zip_path"

    def test_backslash_traversal(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<xml></xml>")
            zf.writestr("xl/workbook.xml", "<xml></xml>")
            zf.writestr("xl\\..\\escaped.xml", "leak")
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", buf.getvalue()), None)
        assert exc.value.error_code == "unsafe_zip_path"

    def test_absolute_path_traversal(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<xml></xml>")
            zf.writestr("xl/workbook.xml", "<xml></xml>")
            zf.writestr("/etc/passwd", "leak")
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", buf.getvalue()), None)
        assert exc.value.error_code == "unsafe_zip_path"

    def test_drive_path_traversal(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<xml></xml>")
            zf.writestr("xl/workbook.xml", "<xml></xml>")
            zf.writestr("C:xl/workbook.xml", "leak")
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", buf.getvalue()), None)
        assert exc.value.error_code == "unsafe_zip_path"

    def test_unc_path_traversal(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<xml></xml>")
            zf.writestr("xl/workbook.xml", "<xml></xml>")
            zf.writestr("//server/share/file", "leak")
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", buf.getvalue()), None)
        assert exc.value.error_code == "unsafe_zip_path"

    def test_nul_metadata_traversal(self, monkeypatch):
        orig_infolist = zipfile.ZipFile.infolist
        def mock_infolist(self):
            infos = orig_infolist(self)
            info = zipfile.ZipInfo()
            info.filename = "xl/\x00workbook.xml"
            infos.append(info)
            return infos
        monkeypatch.setattr(zipfile.ZipFile, "infolist", mock_infolist)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("[Content_Types].xml", "<xml></xml>")
            zf.writestr("xl/workbook.xml", "<xml></xml>")
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", buf.getvalue()), None)
        assert exc.value.error_code == "unsafe_zip_path"

    def test_valid_xlsx(self):
        content = _xlsx(rows=[["asset_name"], ["valid-data"]])
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None) as lazy:
            assert lazy.resolved_sheet == "Sheet1"

# ── L-1: Workbook Resource Limits Restored ───────────────────────────────
class TestWorkbookResourceLimitsRestored:
    def test_header_at_boundary(self):
        limits = ExcelImportLimits(max_header_search_rows=10)
        rows = [[] for _ in range(9)] + [["asset_name"], ["v1"]]
        content = _xlsx(rows=rows)
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
            assert lazy.resolved_sheet == "Sheet1"

    def test_header_beyond_boundary(self):
        limits = ExcelImportLimits(max_header_search_rows=10)
        rows = [[] for _ in range(10)] + [["asset_name"], ["v1"]]
        content = _xlsx(rows=rows)
        with pytest.raises(ParseError) as exc:
            with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
                list(lazy)
        assert exc.value.error_code == "header_not_found"

    def test_header_cell_length(self):
        limits = ExcelImportLimits(max_cell_chars=5)
        rows = [["asset_name_too_long"], ["v1"]]
        content = _xlsx(rows=rows)
        with pytest.raises(ParseError) as exc:
            with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
                list(lazy)
        assert exc.value.error_code == "cell_length_limit"

    def test_header_row_length(self):
        limits = ExcelImportLimits(max_row_chars=10)
        rows = [["col1", "col2", "col3"], ["v1", "v2", "v3"]]
        content = _xlsx(rows=rows)
        with pytest.raises(ParseError) as exc:
            with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
                list(lazy)
        assert exc.value.error_code == "row_length_limit"

    def test_upload_byte_limit(self):
        limits = ExcelImportLimits(max_upload_bytes=10)
        content = _xlsx(rows=[["asset_name"], ["v1"]])
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits)
        assert exc.value.error_code == "upload_too_large"

    def test_5000_accepted(self):
        limits = ExcelImportLimits(max_data_rows=5000, max_physical_rows=5100)
        rows = [["asset_name"]] + [["v"] for _ in range(5000)]
        content = _xlsx(rows=rows)
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
            assert len(list(lazy)) == 5000

    def test_5001_rejected(self):
        limits = ExcelImportLimits(max_data_rows=5000, max_physical_rows=5100)
        rows = [["asset_name"]] + [["v"] for _ in range(5001)]
        content = _xlsx(rows=rows)
        with pytest.raises(ParseError) as exc:
            with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
                list(lazy)
        assert exc.value.error_code == "data_row_limit"

    def test_physical_row_limit(self):
        limits = ExcelImportLimits(max_data_rows=5000, max_physical_rows=10)
        rows = [["asset_name"]] + [["v"] for _ in range(12)]
        content = _xlsx(rows=rows)
        with pytest.raises(ParseError) as exc:
            with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
                list(lazy)
        assert exc.value.error_code == "physical_row_limit"

    def test_cell_length_boundary_accepted(self):
        limits = ExcelImportLimits(max_cell_chars=10)
        rows = [["asset_name"], ["1234567890"]]
        content = _xlsx(rows=rows)
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
            res = list(lazy)
            assert len(res) == 1

    def test_cell_length_boundary_rejected(self):
        limits = ExcelImportLimits(max_cell_chars=10)
        rows = [["asset_name"], ["12345678901"]]
        content = _xlsx(rows=rows)
        with pytest.raises(ParseError) as exc:
            with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
                list(lazy)
        assert exc.value.error_code == "cell_length_limit"

    def test_row_length_boundary_accepted(self):
        limits = ExcelImportLimits(max_row_chars=15)
        rows = [["a", "b"], ["1234567890", "12345"]]
        content = _xlsx(rows=rows)
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
            res = list(lazy)
            assert len(res) == 1

    def test_row_length_boundary_rejected(self):
        limits = ExcelImportLimits(max_row_chars=15)
        rows = [["a", "b"], ["1234567890", "123456"]]
        content = _xlsx(rows=rows)
        with pytest.raises(ParseError) as exc:
            with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
                list(lazy)
        assert exc.value.error_code == "row_length_limit"

    def test_blank_rows_not_counted(self):
        rows = [["asset_name"], ["v1"], [], ["v2"]]
        content = _xlsx(rows=rows)
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None) as lazy:
            res = list(lazy)
            assert len(res) == 2
            assert res[0]["mapped_values"]["proposed_asset_name"] == "v1"
            assert res[1]["mapped_values"]["proposed_asset_name"] == "v2"

    def test_100_columns_accepted(self):
        limits = ExcelImportLimits(max_columns=100)
        header = [f"c{i}" for i in range(100)]
        rows = [header, ["v" for _ in range(100)]]
        content = _xlsx(rows=rows)
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
            assert lazy.column_count == 100

    def test_101_columns_rejected(self):
        limits = ExcelImportLimits(max_columns=100)
        header = [f"c{i}" for i in range(101)]
        rows = [header, ["v" for _ in range(101)]]
        content = _xlsx(rows=rows)
        with pytest.raises(ParseError) as exc:
            with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
                list(lazy)
        assert exc.value.error_code == "column_limit"

# ── N-7: Raw Persistence Integration ───────────────────────────────────────
class TestRawPersistenceRestored(BaseExcelTest):
    def test_db_raw_persistence_scenarios(self):
        self._setup()
        try:
            def run_upload(rows, filename="test.xlsx"):
                self.b.status = ImportBatchStatus.CREATED
                self.b.source_sheet_name = "Sheet1"
                self.sess.commit()
                self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=self.b.id).delete()
                self.sess.commit()
                
                content = _xlsx(rows=rows)
                file = FakeUpload(filename, content)
                upload_excel_file_orchestrator(
                    db=self.sess,
                    org_id=self.org.id,
                    project_id=self.p.id,
                    batch_id=self.b.id,
                    file=file,
                    request=None,
                    current_user=self.u
                )
                return self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=self.b.id).order_by(ProjectAssetImportStagingRow.source_row_number).all()

            # 1. Exact cells structure
            stg = run_upload([["asset_name", "description"], ["v1", "v2"]])
            assert len(stg) == 1
            cells = stg[0].raw_values["cells"]
            assert len(cells) == 2
            assert cells[0] == {"column_index": 1, "column_letter": "A", "header": "asset_name", "value": "v1"}
            assert cells[1] == {"column_index": 2, "column_letter": "B", "header": "description", "value": "v2"}

            # 2. Duplicate headers
            stg = run_upload([["asset_name", "asset_name"], ["v1", "v2"]])
            assert len(stg) == 1
            cells = stg[0].raw_values["cells"]
            assert cells[0]["header"] == "asset_name"
            assert cells[1]["header"] == "asset_name"

            # 3. Blank header
            stg = run_upload([["asset_name", "", "description"], ["v1", "v2", "v3"]])
            assert len(stg) == 1
            cells = stg[0].raw_values["cells"]
            assert cells[1]["header"] == ""
            assert cells[1]["value"] == "v2"

            # 4. Extra column
            stg = run_upload([["asset_name"], ["v1", "extra_val"]])
            assert len(stg) == 1
            cells = stg[0].raw_values["cells"]
            assert cells[1]["header"] == ""
            assert cells[1]["value"] == "extra_val"

            # 5. Empty cell
            stg = run_upload([["asset_name", "description"], ["v1", None]])
            assert len(stg) == 1
            assert stg[0].mapped_values["proposed_description"] == ""

            # 6. First alias wins
            stg = run_upload([["asset_name", "tên tài sản"], ["v1", "v2"]])
            assert len(stg) == 1
            assert stg[0].mapped_values["proposed_asset_name"] == "v1"

            # 7. Correct source row number and order
            stg = run_upload([["asset_name"], [], ["row1"], ["row2"]])
            assert len(stg) == 2
            assert stg[0].source_row_number == 3
            assert stg[0].mapped_values["proposed_asset_name"] == "row1"
            assert stg[1].source_row_number == 4
            assert stg[1].mapped_values["proposed_asset_name"] == "row2"
        finally:
            self.teardown()

# ── N-1, N-2, N-3: PostgreSQL Concurrency Integration ────────────────────────
class ControlledSlowFile:
    def __init__(self, invalid_bytes, read_event, block_event):
        self.invalid_bytes = invalid_bytes
        self.read_event = read_event
        self.block_event = block_event
        self.bytes_io = io.BytesIO(invalid_bytes)
        self.has_read = False

    def read(self, size=-1):
        if not self.has_read:
            self.has_read = True
            # Signal that worker A entered the orchestrator and holds the lock
            self.read_event.set()
            # Wait for main thread to allow worker A to proceed
            self.block_event.wait()
        return self.bytes_io.read(size)

class TestPGIsolatedConcurrencyRestored:
    def test_concurrent_upload_serialization(self):
        pg = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
        if not pg or "postgres" not in pg:
            pytest.skip("PostgreSQL concurrency test requires PostgreSQL database environment.")

        # Dedicated setup: NO create_all / drop_all!
        engine = create_engine(pg)
        SessionLocal = sessionmaker(bind=engine)
        sess = SessionLocal()

        # Track created entities for FK-safe cleanup
        created_org_id = None
        created_role_id = None
        created_u1_id = None
        created_u2_id = None
        created_ur_ids = []
        created_cust_id = None
        created_proj_id = None
        created_batch_id = None

        try:
            uid = str(uuid.uuid4())
            uid_s = uid[:8]

            # UUID-suffixed entities
            org = OrganizationProfile(
                legal_name=f"Org {uid}",
                organization_slug=f"org_{uid_s}",
                status=OrganizationStatus.ACTIVE
            )
            sess.add(org)
            sess.commit()
            created_org_id = org.id

            role = Role(
                code=f"role_{uid_s}",
                display_name=f"Role {uid_s}",
                permissions=["project:read", "workbench:edit"]
            )
            sess.add(role)
            sess.commit()
            created_role_id = role.id

            u1 = User(
                organization_id=org.id,
                email=f"u1_{uid_s}@valora.com",
                full_name=f"U1 {uid_s}",
                status=UserStatus.ACTIVE
            )
            u2 = User(
                organization_id=org.id,
                email=f"u2_{uid_s}@valora.com",
                full_name=f"U2 {uid_s}",
                status=UserStatus.ACTIVE
            )
            sess.add(u1)
            sess.add(u2)
            sess.commit()
            created_u1_id = u1.id
            created_u2_id = u2.id

            ur1 = UserRole(user_id=u1.id, role_id=role.id, is_active=True)
            ur2 = UserRole(user_id=u2.id, role_id=role.id, is_active=True)
            sess.add(ur1)
            sess.add(ur2)
            sess.commit()
            created_ur_ids = [ur1.id, ur2.id]

            cust = Customer(
                organization_id=org.id,
                legal_name=f"Cust {uid_s}",
                status=CustomerStatus.ACTIVE,
                created_by=u1.id
            )
            sess.add(cust)
            sess.commit()
            created_cust_id = cust.id

            proj = Project(
                organization_id=org.id,
                customer_id=cust.id,
                code=f"proj_{uid_s}",
                name=f"Proj {uid_s}",
                status=ProjectWorkflowStatus.DRAFT,
                created_by=u1.id
            )
            sess.add(proj)
            sess.commit()
            created_proj_id = proj.id

            batch = ProjectAssetImportBatch(
                organization_id=org.id,
                project_id=proj.id,
                source_filename=f"b_{uid_s}.xlsx",
                source_sheet_name="Sheet1",
                status=ImportBatchStatus.CREATED,
                total_rows=0,
                created_by_user_id=u1.id
            )
            sess.add(batch)
            sess.commit()
            created_batch_id = batch.id

            # Capture only IDs before starting workers
            org_id = org.id
            proj_id = proj.id
            batch_id = batch.id
            u1_id = u1.id
            u2_id = u2.id

            # ── Scenario A: Two Successful Uploads to same batch ─────────────────
            barrier = threading.Barrier(2)
            results = []
            exceptions = []

            def worker_success(worker_id, user_id, filename, row_vals):
                sess_w = SessionLocal()
                try:
                    current_u = sess_w.query(User).get(user_id)
                    content = _xlsx(rows=[["asset_name"]] + [[v] for v in row_vals])
                    upload = FakeUpload(filename, content)
                    barrier.wait(timeout=30)
                    res = upload_excel_file_orchestrator(
                        db=sess_w,
                        org_id=org_id,
                        project_id=proj_id,
                        batch_id=batch_id,
                        file=upload,
                        request=None,
                        current_user=current_u,
                        correlation_id=f"corr-success-{worker_id}"
                    )
                    results.append((worker_id, "success", res.total_rows, res.source_filename, set(row_vals)))
                except threading.BrokenBarrierError:
                    results.append((worker_id, "barrier_timeout"))
                except Exception as e:
                    exceptions.append(e)
                    results.append((worker_id, "failure", str(e), None))
                finally:
                    sess_w.close()

            t1 = threading.Thread(target=worker_success, args=(1, u1_id, f"w1_{uid_s}.xlsx", ["w1-row-a","w1-row-b","w1-row-c"]))
            t2 = threading.Thread(target=worker_success, args=(2, u2_id, f"w2_{uid_s}.xlsx", ["w2-row-a","w2-row-b","w2-row-c"]))
            t1.start()
            t2.start()
            t1.join(timeout=60)
            t2.join(timeout=60)
            assert not t1.is_alive()
            assert not t2.is_alive()

            assert exceptions == []
            assert len(results) == 2
            assert all(r[1] == "success" for r in results)

            sess.expire_all()
            final_batch = sess.query(ProjectAssetImportBatch).get(batch_id)
            assert final_batch.status == ImportBatchStatus.PARSED

            staging_rows = sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=batch_id).all()
            assert len(staging_rows) == 3
            row_vals = {r.proposed_asset_name for r in staging_rows}
            assert row_vals in ({"w1-row-a","w1-row-b","w1-row-c"}, {"w2-row-a","w2-row-b","w2-row-c"})
            if row_vals == {"w1-row-a","w1-row-b","w1-row-c"}:
                assert final_batch.source_filename == f"w1_{uid_s}.xlsx"
                assert final_batch.total_rows == 3
            else:
                assert final_batch.source_filename == f"w2_{uid_s}.xlsx"
                assert final_batch.total_rows == 3

            events = sess.query(AuditEvent).filter_by(entity_id=batch_id).all()
            success_events = [e for e in events if e.event_name == "ProjectAssetImportBatchUploaded"]
            assert len(success_events) == 2

            # ── Scenario B: Slow Stale Failure followed by newer Success ─────────
            # Reset batch for Scenario B
            final_batch.status = ImportBatchStatus.CREATED
            sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=batch_id).delete()
            sess.query(AuditEvent).filter_by(entity_id=batch_id).delete()
            sess.commit()

            read_event = threading.Event()
            block_event = threading.Event()
            stale_results = []
            stale_exceptions = []

            try:
                def worker_stale_fail():
                    sess_w = SessionLocal()
                    try:
                        current_u = sess_w.query(User).get(u1_id)
                        controlled_file = ControlledSlowFile(b"corrupt-zip-bytes", read_event, block_event)
                        upload = FakeUpload(f"b_stale_{uid_s}.xlsx", b"")
                        upload.file = controlled_file

                        upload_excel_file_orchestrator(
                            db=sess_w,
                            org_id=org_id,
                            project_id=proj_id,
                            batch_id=batch_id,
                            file=upload,
                            request=None,
                            current_user=current_u,
                            correlation_id=f"corr-stale-{uid_s}"
                        )
                        stale_results.append(("worker_stale", "success"))
                    except HTTPException as e:
                        stale_results.append(("worker_stale", "http_error", e.status_code))
                    except Exception as e:
                        stale_exceptions.append(e)
                        stale_results.append(("worker_stale", "unexpected_error", str(e)))
                    finally:
                        sess_w.close()
                        block_event.set()

                def worker_newer_success():
                    read_event.wait(timeout=30)
                    sess_w = SessionLocal()
                    try:
                        current_u = sess_w.query(User).get(u2_id)
                        content = _xlsx(rows=[["asset_name"], ["success-final-val"]])
                        upload = FakeUpload(f"b_success_{uid_s}.xlsx", content)

                        upload_excel_file_orchestrator(
                            db=sess_w,
                            org_id=org_id,
                            project_id=proj_id,
                            batch_id=batch_id,
                            file=upload,
                            request=None,
                            current_user=current_u,
                            correlation_id=f"corr-success-{uid_s}"
                        )
                        stale_results.append(("worker_success", "success"))
                    except Exception as e:
                        stale_exceptions.append(e)
                        stale_results.append(("worker_success", "failure", str(e)))
                    finally:
                        sess_w.close()
                        read_event.set()
                        block_event.set()

                t_fail = threading.Thread(target=worker_stale_fail)
                t_succ = threading.Thread(target=worker_newer_success)
                t_fail.start()
                t_succ.start()

                read_event.wait(timeout=10)
                time.sleep(0.2)
                block_event.set()

                t_fail.join(timeout=60)
                t_succ.join(timeout=60)
                assert not t_fail.is_alive()
                assert not t_succ.is_alive()

            finally:
                block_event.set()
                read_event.set()

            assert stale_exceptions == []
            # One HTTP 400 failure and one success
            assert ("worker_stale", "http_error", 400) in stale_results
            assert ("worker_success", "success") in stale_results

            # Assert final staging and batch belong exclusively to success worker B
            sess.expire_all()
            final_batch_b = sess.query(ProjectAssetImportBatch).get(batch_id)
            assert final_batch_b.status == ImportBatchStatus.PARSED
            assert final_batch_b.source_filename == f"b_success_{uid_s}.xlsx"

            stg_b = sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=batch_id).all()
            assert len(stg_b) == 1
            assert stg_b[0].proposed_asset_name == "success-final-val"

            # Assert real failure and success AuditEvents by event_name
            events_b = sess.query(AuditEvent).filter_by(entity_id=batch_id).all()
            event_names = [e.event_name for e in events_b]
            assert "ProjectAssetImportBatchUploadFailed" in event_names
            assert "ProjectAssetImportBatchUploaded" in event_names

        finally:
            # Clean only test-owned rows in FK-safe order
            if sess:
                try:
                    if created_batch_id:
                        sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=created_batch_id).delete()
                        sess.query(AuditEvent).filter_by(entity_id=created_batch_id).delete()
                        sess.query(ProjectAssetImportBatch).filter_by(id=created_batch_id).delete()
                    if created_proj_id:
                        sess.query(Project).filter_by(id=created_proj_id).delete()
                    if created_cust_id:
                        sess.query(Customer).filter_by(id=created_cust_id).delete()
                    if created_ur_ids:
                        sess.query(UserRole).filter(UserRole.id.in_(created_ur_ids)).delete()
                    if created_u1_id or created_u2_id:
                        ids = [i for i in [created_u1_id, created_u2_id] if i is not None]
                        sess.query(User).filter(User.id.in_(ids)).delete()
                    if created_role_id:
                        sess.query(Role).filter_by(id=created_role_id).delete()
                    if created_org_id:
                        sess.query(OrganizationProfile).filter_by(id=created_org_id).delete()
                    sess.commit()
                except Exception as cleanup_err:
                    print(f"Cleanup error: {cleanup_err}")
                finally:
                    sess.close()

# ── N-5: Unique Fault & Exception Verification Tests ─────────────────────────
class TestTransactionFaultsCompleted(BaseExcelTest):
    def test_staging_flush_failure(self, monkeypatch):
        self._setup()
        try:
            # Mock staging rows database insert/flush failure
            import app.modules.excel_import.application.import_service as service_mod
            def mock_replace(*args, **kwargs):
                raise RuntimeError("Staging DB Flush Failed")
            monkeypatch.setattr(service_mod, "replace_staging_rows", mock_replace)

            content = _xlsx(rows=[["asset_name"], ["new1"]])
            file = FakeUpload("test.xlsx", content)

            with pytest.raises(HTTPException) as exc:
                upload_excel_file_orchestrator(
                    db=self.sess,
                    org_id=self.org.id,
                    project_id=self.p.id,
                    batch_id=self.b.id,
                    file=file,
                    request=None,
                    current_user=self.u
                )
            assert exc.value.status_code == 500
            # Preserves original exception
            assert exc.value.detail == "Lỗi hệ thống khi xử lý tệp Excel."

            # Exact old staging IDs and values preserved
            rows = self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=self.b.id).order_by(ProjectAssetImportStagingRow.source_row_number).all()
            assert len(rows) == 3
            assert [r.id for r in rows] == self.seeded_staging_ids
            assert [r.proposed_asset_name for r in rows] == ["O0", "O1", "O2"]

            # Batch properties untouched
            self.sess.refresh(self.b)
            assert self.b.status == ImportBatchStatus.FAILED
            assert self.b.source_filename == "old.xlsx"
            assert self.b.source_sheet_name == "Sheet1"
            assert self.b.total_rows == 3
        finally:
            self.teardown()

    def test_success_audit_event_failure(self, monkeypatch):
        self._setup()
        try:
            # Mock success AuditEvent logging to fail (flush error)
            import app.modules.excel_import.application.replace_staging_rows as rs_mod
            def mock_audit(*args, **kwargs):
                if kwargs.get("event_name") == "ProjectAssetImportBatchUploaded":
                    raise RuntimeError("AuditEvent db flush failed")
            monkeypatch.setattr(rs_mod, "log_audit_event", mock_audit)

            content = _xlsx(rows=[["asset_name"], ["new1"]])
            file = FakeUpload("test.xlsx", content)

            with pytest.raises(HTTPException) as exc:
                upload_excel_file_orchestrator(
                    db=self.sess,
                    org_id=self.org.id,
                    project_id=self.p.id,
                    batch_id=self.b.id,
                    file=file,
                    request=None,
                    current_user=self.u
                )
            assert exc.value.status_code == 500

            # Staging preserved
            rows = self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=self.b.id).order_by(ProjectAssetImportStagingRow.source_row_number).all()
            assert len(rows) == 3
            assert [r.proposed_asset_name for r in rows] == ["O0", "O1", "O2"]

            # Batch properties untouched
            self.sess.refresh(self.b)
            assert self.b.status == ImportBatchStatus.FAILED
            assert self.b.source_filename == "old.xlsx"
        finally:
            self.teardown()

        def test_outer_commit_failure(self, monkeypatch):
            self._setup()
            try:
                # Mock outer db commit AND savepoint commit to both fail.
                orig_commit = self.sess.commit
                fail_commit = False
                def mock_commit():
                    nonlocal fail_commit
                    if fail_commit:
                        fail_commit = False
                        raise RuntimeError("Outer commit database failure")
                    orig_commit()
                monkeypatch.setattr(self.sess, "commit", mock_commit)

                content = _xlsx(rows=[["asset_name"], ["new1"]])
                file = FakeUpload("test.xlsx", content)

                fail_commit = True
                with pytest.raises(HTTPException) as exc:
                    upload_excel_file_orchestrator(
                        db=self.sess,
                        org_id=self.org.id,
                        project_id=self.p.id,
                        batch_id=self.b.id,
                        file=file,
                        request=None,
                        current_user=self.u
                    )
                assert exc.value.status_code == 500

                # Verify recovery sequence wrote a commit_failure audit event
                events = self.sess.query(AuditEvent).filter_by(entity_id=self.b.id).all()
                filtered = [e for e in events if e.event_name == "ProjectAssetImportBatchUploadFailed" and e.payload and e.payload.get("error_code") == "commit_failure"]
                assert len(filtered) == 1, f"Expected 1 commit_failure event, got {len(filtered)}"
                assert filtered[0].event_name == "ProjectAssetImportBatchUploadFailed"
                assert filtered[0].payload is not None
                assert filtered[0].payload["error_code"] == "commit_failure"

                # No success AuditEvent from the rolled-back attempt
                success = [e for e in events if e.event_name == "ProjectAssetImportBatchUploaded"]
                assert len(success) == 0

                # Old staging IDs and values preserved
                rows = self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=self.b.id).all()
                assert len(rows) == 3
                assert {r.proposed_asset_name for r in rows} == {"Old0", "Old1", "Old2"}

            finally:
                self.teardown()

    def test_outer_commit_failure_with_newer_concurrent_success(self, monkeypatch):
        self._setup()
        try:
            import sys
            service_mod = sys.modules["app.modules.excel_import.application.import_service"]
            
            # Mock outer commit to fail
            orig_commit = self.sess.commit
            fail_commit = False
            def mock_commit():
                nonlocal fail_commit
                if fail_commit:
                    fail_commit = False
                    raise RuntimeError("Outer commit database failure")
                orig_commit()
            monkeypatch.setattr(self.sess, "commit", mock_commit)

            # Concurrent success updates batch to PARSED during recovery rollback window
            orig_recover = service_mod._recover_commit_failure
            def mock_recover(*args, **kwargs):
                sess_c = self.SessionLocal()
                try:
                    batch_c = sess_c.query(ProjectAssetImportBatch).filter_by(id=self.b.id).first()
                    batch_c.status = ImportBatchStatus.PARSED
                    batch_c.source_filename = "newer_success.xlsx"
                    sess_c.commit()
                finally:
                    sess_c.close()
                # Run actual recovery, which should see changed fingerprint and abort
                orig_recover(*args, **kwargs)

            monkeypatch.setattr(service_mod, "_recover_commit_failure", mock_recover)

            content = _xlsx(rows=[["asset_name"], ["new1"]])
            file = FakeUpload("test.xlsx", content)

            fail_commit = True
            with pytest.raises(HTTPException) as exc:
                upload_excel_file_orchestrator(
                    db=self.sess,
                    org_id=self.org.id,
                    project_id=self.p.id,
                    batch_id=self.b.id,
                    file=file,
                    request=None,
                    current_user=self.u
                )
            assert exc.value.status_code == 500

            # Verify that final newer success state survives
            self.sess.rollback()
            self.sess.refresh(self.b)
            assert self.b.status == ImportBatchStatus.PARSED
            assert self.b.source_filename == "newer_success.xlsx"
        finally:
            self.teardown()

    def test_failure_audit_event_flush_failure(self, monkeypatch):
        self._setup()
        try:
            # Mock log_audit_event failure on failure logging
            import app.modules.excel_import.application.replace_staging_rows as rs_mod
            def mock_audit(*args, **kwargs):
                if kwargs.get("event_name") == "ProjectAssetImportBatchUploadFailed":
                    raise RuntimeError("Failure Audit Flush Failed")
            monkeypatch.setattr(rs_mod, "log_audit_event", mock_audit)

            # Trigger ParseError (cell value > limits)
            content = _xlsx(rows=[["asset_name"], ["v" * 10001]])
            file = FakeUpload("test.xlsx", content)

            with pytest.raises(HTTPException) as exc:
                upload_excel_file_orchestrator(
                    db=self.sess,
                    org_id=self.org.id,
                    project_id=self.p.id,
                    batch_id=self.b.id,
                    file=file,
                    request=None,
                    current_user=self.u
                )
            assert exc.value.status_code == 400
            # Original exception detail preserved, not masked by audit event failure
            assert exc.value.detail != "Failure Audit Flush Failed"
        finally:
            self.teardown()

    def test_failure_audit_event_commit_failure(self, monkeypatch):
        self._setup()
        try:
            # Mock db commit failure during failure audit logging
            orig_commit = self.sess.commit
            fail_commit = False
            def mock_commit():
                if fail_commit:
                    raise RuntimeError("Commit failure in failure audit path")
                orig_commit()
            monkeypatch.setattr(self.sess, "commit", mock_commit)

            # Trigger ParseError
            content = _xlsx(rows=[["asset_name"], ["v" * 10001]])
            file = FakeUpload("test.xlsx", content)

            fail_commit = True
            with pytest.raises(HTTPException) as exc:
                upload_excel_file_orchestrator(
                    db=self.sess,
                    org_id=self.org.id,
                    project_id=self.p.id,
                    batch_id=self.b.id,
                    file=file,
                    request=None,
                    current_user=self.u
                )
            assert exc.value.status_code == 400
        finally:
            self.teardown()

    def test_closed_savepoint_safety(self, monkeypatch):
        self._setup()
        try:
            import sys
            service_mod = sys.modules["app.modules.excel_import.application.import_service"]
            
            # Record status during execution
            class SavepointTracker:
                def __init__(self, sp):
                    self.sp = sp
                    self.rolled_back = False
                def rollback(self):
                    self.rolled_back = True
                    self.sp.rollback()
                def commit(self):
                    self.sp.commit()

            orig_nested = self.sess.begin_nested
            tracker = None
            def mock_nested():
                nonlocal tracker
                sp = orig_nested()
                tracker = SavepointTracker(sp)
                return tracker
            monkeypatch.setattr(self.sess, "begin_nested", mock_nested)

            # Trigger an orchestrator run that fails during openpyxl parsing (iterator failure)
            class FaultIterator:
                def __init__(self):
                    self.resolved_sheet = "Sheet1"
                    self.column_count = 1
                def __iter__(self): return self
                def __next__(self): raise ParseError(400, "invalid_xlsx", "Fault")
                def close(self): pass
                def __enter__(self): return self
                def __exit__(self, *a): pass

            monkeypatch.setattr(service_mod, "parse_workbook_lazy", lambda *a, **kw: FaultIterator())
            
            content = _xlsx(rows=[["asset_name"], ["v"]])
            file = FakeUpload("test.xlsx", content)

            with pytest.raises(HTTPException) as exc:
                upload_excel_file_orchestrator(
                    db=self.sess,
                    org_id=self.org.id,
                    project_id=self.p.id,
                    batch_id=self.b.id,
                    file=file,
                    request=None,
                    current_user=self.u
                )
            assert exc.value.status_code == 400
            # Verifies savepoint was rolled back and not committed
            assert tracker is not None
            assert tracker.rolled_back
        finally:
            self.teardown()

# ── N-5: ProjectAssetLine Immutability Snapshot Proofs ──────────────────────
class TestProjectAssetLineImmutabilityExpanded(BaseExcelTest):
    def test_line_immutable_snapshots(self, monkeypatch):
        self._setup()
        try:
            before = self.sess.query(ProjectAssetLine).get(self.al_id)
            snapshot_before = (before.id, before.asset_name, before.quantity, before.row_version)

            # 1. Successful Upload
            self.b.source_sheet_name = None
            self.sess.commit()
            content = _xlsx(rows=[["asset_name"], ["new1"]])
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers={"X-User-Id": str(self.u.id)})
            assert resp.status_code == 200
            after1 = self.sess.query(ProjectAssetLine).get(self.al_id)
            assert (after1.id, after1.asset_name, after1.quantity, after1.row_version) == snapshot_before

            # 2. Invalid ZIP
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", b"invalid-zip", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers={"X-User-Id": str(self.u.id)})
            assert resp.status_code == 400
            after2 = self.sess.query(ProjectAssetLine).get(self.al_id)
            assert (after2.id, after2.asset_name, after2.quantity, after2.row_version) == snapshot_before

            # 3. Row Limit Rollback (5001 rows)
            limits = ExcelImportLimits(max_data_rows=5, max_physical_rows=10)
            rows = [["asset_name"]] + [["v"] for _ in range(6)]
            content_large = _xlsx(rows=rows)
            import sys
            service_mod = sys.modules["app.modules.excel_import.application.import_service"]
            parse_mod = sys.modules["app.modules.excel_import.application.parse_workbook"]
            monkeypatch.setattr(service_mod, "DEFAULT_LIMITS", limits)
            monkeypatch.setattr(parse_mod, "DEFAULT_LIMITS", limits)
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", content_large, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers={"X-User-Id": str(self.u.id)})
            assert resp.status_code == 413
            after3 = self.sess.query(ProjectAssetLine).get(self.al_id)
            assert (after3.id, after3.asset_name, after3.quantity, after3.row_version) == snapshot_before

            # 4. Iterator Exception
            class ExceptionIterator:
                def __init__(self):
                    self.resolved_sheet = "Sheet1"
                    self.column_count = 1
                    self.closed = False
                def __iter__(self): return self
                def __next__(self): raise RuntimeError("Lazy Iterator Failure")
                def close(self): self.closed = True
                def __enter__(self): return self
                def __exit__(self, exc_type, exc_val, exc_tb): self.close()
            monkeypatch.setattr(service_mod, "parse_workbook_lazy", lambda *a, **kw: ExceptionIterator())
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers={"X-User-Id": str(self.u.id)})
            assert resp.status_code == 500
            after4 = self.sess.query(ProjectAssetLine).get(self.al_id)
            assert (after4.id, after4.asset_name, after4.quantity, after4.row_version) == snapshot_before

            # 5. Success Audit Failure
            monkeypatch.undo() # clean mocks
            import sys
            rs_mod = sys.modules["app.modules.excel_import.application.replace_staging_rows"]
            def mock_audit_fail(*a, **kw):
                raise RuntimeError("Success Audit log failure")
            monkeypatch.setattr(rs_mod, "log_audit_event", mock_audit_fail)
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers={"X-User-Id": str(self.u.id)})
            assert resp.status_code == 500
            after5 = self.sess.query(ProjectAssetLine).get(self.al_id)
            assert (after5.id, after5.asset_name, after5.quantity, after5.row_version) == snapshot_before

            # 6. Outer Commit Failure
            monkeypatch.undo()
            def mock_commit_fail():
                raise RuntimeError("Outer commit fail")
            monkeypatch.setattr(self.sess, "commit", mock_commit_fail)
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers={"X-User-Id": str(self.u.id)})
            assert resp.status_code == 500
            after6 = self.sess.query(ProjectAssetLine).get(self.al_id)
            assert (after6.id, after6.asset_name, after6.quantity, after6.row_version) == snapshot_before
        finally:
            self.teardown()

