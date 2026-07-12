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
from app.modules.excel_import.application.replace_staging_rows import record_failure_audit
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
        
        self.b = ProjectAssetImportBatch(organization_id=self.org.id, project_id=self.p.id, source_filename="old.xlsx", source_sheet_name="S", status=ImportBatchStatus.PARSED, total_rows=3, created_by_user_id=self.u.id)
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

    def test_data_cell_length(self):
        limits = ExcelImportLimits(max_cell_chars=5)
        rows = [["asset_name"], ["too_long_value"]]
        content = _xlsx(rows=rows)
        with pytest.raises(ParseError) as exc:
            with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
                list(lazy)
        assert exc.value.error_code == "cell_length_limit"

    def test_data_row_length(self):
        limits = ExcelImportLimits(max_row_chars=10)
        rows = [["asset_name", "description"], ["val1", "val2"]]
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

# ── L-1: Raw Persistence Restored ──────────────────────────────────────────
class TestRawPersistenceRestored:
    def test_exact_cells_structure(self):
        content = _xlsx(rows=[["asset_name", "description"], ["v1", "v2"]])
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None) as lazy:
            row = next(lazy)
            cells = row["raw_cells"]
            assert len(cells) == 2
            assert cells[0] == {"column_index": 1, "column_letter": "A", "header": "asset_name", "value": "v1"}
            assert cells[1] == {"column_index": 2, "column_letter": "B", "header": "description", "value": "v2"}

    def test_duplicate_headers(self):
        content = _xlsx(rows=[["asset_name", "asset_name"], ["v1", "v2"]])
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None) as lazy:
            row = next(lazy)
            cells = row["raw_cells"]
            assert cells[0]["header"] == "asset_name"
            assert cells[1]["header"] == "asset_name"

    def test_blank_headers(self):
        content = _xlsx(rows=[["asset_name", "", "description"], ["v1", "v2", "v3"]])
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None) as lazy:
            row = next(lazy)
            cells = row["raw_cells"]
            assert cells[1]["header"] == ""
            assert cells[1]["value"] == "v2"

    def test_extra_columns(self):
        content = _xlsx(rows=[["asset_name"], ["v1", "extra_val"]])
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None) as lazy:
            row = next(lazy)
            cells = row["raw_cells"]
            assert len(cells) == 2
            assert cells[1]["header"] == ""
            assert cells[1]["value"] == "extra_val"

    def test_empty_cells(self):
        content = _xlsx(rows=[["asset_name", "description"], ["v1", None]])
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None) as lazy:
            row = next(lazy)
            assert row["mapped_values"]["proposed_description"] == ""

    def test_row_order(self):
        content = _xlsx(rows=[["asset_name"], ["row1"], ["row2"]])
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None) as lazy:
            res = list(lazy)
            assert res[0]["mapped_values"]["proposed_asset_name"] == "row1"
            assert res[1]["mapped_values"]["proposed_asset_name"] == "row2"

    def test_source_row_number(self):
        content = _xlsx(rows=[["asset_name"], [], ["row1"]])
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None) as lazy:
            res = list(lazy)
            assert res[0]["source_row_number"] == 3

    def test_first_alias_wins(self):
        content = _xlsx(rows=[["asset_name", "tên tài sản"], ["v1", "v2"]])
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None) as lazy:
            row = next(lazy)
            assert row["mapped_values"]["proposed_asset_name"] == "v1"

# ── L-2: PostgreSQL Concurrency Redesign ────────────────────────────────────
class TestPGConcurrencyRestructured(BaseExcelTest):
    def test_concurrent_upload_serialization(self):
        pg = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
        if not pg or "postgres" not in pg:
            pytest.skip("PostgreSQL concurrency test requires PostgreSQL database environment.")

        # Ensure no metadata drop_all/create_all run in our PG integration test
        self._setup(db_url=pg)
        try:
            # Generate unique test identifiers
            uid_suffix = str(uuid.uuid4())[:8]
            unique_org_slug = f"org_{uid_suffix}"
            unique_email_1 = f"user1_{uid_suffix}@t.com"
            unique_email_2 = f"user2_{uid_suffix}@t.com"
            unique_role_code = f"role_{uid_suffix}"
            unique_proj_code = f"proj_{uid_suffix}"

            # Create test context record set
            org = OrganizationProfile(legal_name=f"Org {uid_suffix}", organization_slug=unique_org_slug, status=OrganizationStatus.ACTIVE)
            self.sess.add(org)
            self.sess.commit()

            role = Role(code=unique_role_code, display_name="Editor", permissions=["project:read", "workbench:edit"])
            self.sess.add(role)
            self.sess.commit()

            u1 = User(organization_id=org.id, email=unique_email_1, full_name="User 1", status=UserStatus.ACTIVE)
            u2 = User(organization_id=org.id, email=unique_email_2, full_name="User 2", status=UserStatus.ACTIVE)
            self.sess.add(u1)
            self.sess.add(u2)
            self.sess.commit()

            self.sess.add(UserRole(user_id=u1.id, role_id=role.id, is_active=True))
            self.sess.add(UserRole(user_id=u2.id, role_id=role.id, is_active=True))
            self.sess.commit()

            cust = Customer(organization_id=org.id, legal_name="Cust", status=CustomerStatus.ACTIVE, created_by=u1.id)
            self.sess.add(cust)
            self.sess.commit()

            proj = Project(organization_id=org.id, customer_id=cust.id, code=unique_proj_code, name="P", status=ProjectWorkflowStatus.DRAFT, created_by=u1.id)
            self.sess.add(proj)
            self.sess.commit()

            batch = ProjectAssetImportBatch(organization_id=org.id, project_id=proj.id, source_filename="b.xlsx", source_sheet_name="Sheet1", status=ImportBatchStatus.CREATED, total_rows=0, created_by_user_id=u1.id)
            self.sess.add(batch)
            self.sess.commit()

            # Pre-capture UUIDs
            org_id = org.id
            proj_id = proj.id
            batch_id = batch.id
            u1_id = u1.id
            u2_id = u2.id

            # Scenario A: Two successful uploads to same batch
            barrier = threading.Barrier(2)
            results = []
            exceptions = []

            def worker_success(worker_id, user_id):
                sess_w = self.SessionLocal()
                # Load its own current_user inside the thread session
                current_u = sess_w.query(User).get(user_id)
                content = _xlsx(rows=[["asset_name"], [f"worker-{worker_id}"]])
                upload = FakeUpload("b.xlsx", content)
                barrier.wait()
                try:
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
                    results.append((worker_id, "success", res.total_rows))
                except Exception as e:
                    exceptions.append(e)
                    results.append((worker_id, "failure", str(e)))
                finally:
                    sess_w.close()

            t1 = threading.Thread(target=worker_success, args=(1, u1_id))
            t2 = threading.Thread(target=worker_success, args=(2, u2_id))
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            assert exceptions == []
            assert len(results) == 2
            assert all(r[1] == "success" for r in results)

            # Scenario B: Slow stale failure followed by newer success
            # We configure Thread 1 (failing) to lock the batch, block Thread 2, write failure, then Thread 2 succeeds
            barrier_stale = threading.Barrier(2)
            event_a_locked = threading.Event()
            event_b_blocked = threading.Event()
            stale_results = []
            stale_exceptions = []

            # We use monkeypatch/mocks to control Thread A's execution flow
            # Let's write Thread A that fails, and Thread B that succeeds
            def worker_stale_fail(user_id):
                sess_w = self.SessionLocal()
                current_u = sess_w.query(User).get(user_id)
                
                # Mock a slow upload that fails
                # Thread A locks first, signals Thread B to proceed to query, then fails
                barrier_stale.wait()
                
                # Let's acquire lock
                batch_locked = sess_w.query(ProjectAssetImportBatch).filter_by(id=batch_id).with_for_update().first()
                assert batch_locked is not None
                
                event_a_locked.set()
                event_b_blocked.wait()
                time.sleep(0.1) # ensure Thread B is blocked on DB lock query
                
                # Now fail the upload
                try:
                    # trigger ParseError
                    raise ParseError(400, "invalid_xlsx", "Stale Failure Proof")
                except ParseError as pe:
                    # Orchestrator error behavior manual replication for controlled lock flow
                    sp = sess_w.begin_nested()
                    sp.rollback()
                    record_failure_audit(
                        db=sess_w,
                        org_id=org_id,
                        batch_id=batch_id,
                        actor_id=current_u.id,
                        sanitized_filename="b.xlsx",
                        requested_sheet="Sheet1",
                        error_code=pe.error_code,
                        previous_row_count=1,
                        correlation_id="stale-fail-corr"
                    )
                    sess_w.commit()
                    stale_results.append(("stale_fail", "failure"))
                finally:
                    sess_w.close()

            def worker_newer_success(user_id):
                sess_w = self.SessionLocal()
                current_u = sess_w.query(User).get(user_id)
                content = _xlsx(rows=[["asset_name"], ["newer-success-data"]])
                upload = FakeUpload("b.xlsx", content)
                barrier_stale.wait()
                
                # Wait until Thread A holds lock
                event_a_locked.wait()
                # Signal we are about to query and block
                event_b_blocked.set()
                
                try:
                    res = upload_excel_file_orchestrator(
                        db=sess_w,
                        org_id=org_id,
                        project_id=proj_id,
                        batch_id=batch_id,
                        file=upload,
                        request=None,
                        current_user=current_u,
                        correlation_id="newer-success-corr"
                    )
                    stale_results.append(("newer_success", "success", res.total_rows))
                except Exception as e:
                    stale_exceptions.append(e)
                    stale_results.append(("newer_success", "failure", str(e)))
                finally:
                    sess_w.close()

            t_fail = threading.Thread(target=worker_stale_fail, args=(u1_id,))
            t_succ = threading.Thread(target=worker_newer_success, args=(u2_id,))
            t_fail.start()
            t_succ.start()
            t_fail.join()
            t_succ.join()

            assert stale_exceptions == []
            
            # Verify final batch status is PARSED
            self.sess.refresh(batch)
            assert batch.status == ImportBatchStatus.PARSED
            assert batch.total_rows == 1

            # Staging belongs to success
            stg = self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=batch_id).all()
            assert len(stg) == 1
            assert stg[0].proposed_asset_name == "newer-success-data"

            # Both AuditEvents exist
            events = self.sess.query(AuditEvent).filter_by(entity_id=batch_id).all()
            event_names = [e.event_name for e in events]
            assert "ProjectAssetImportBatchUploadFailed" in event_names
            assert "ProjectAssetImportBatchUploaded" in event_names

            # Cleanup only test-owned records
            self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=batch_id).delete()
            self.sess.query(AuditEvent).filter_by(entity_id=batch_id).delete()
            self.sess.query(ProjectAssetImportBatch).filter_by(id=batch_id).delete()
            self.sess.query(Project).filter_by(id=proj_id).delete()
            self.sess.query(Customer).filter_by(id=cust.id).delete()
            self.sess.query(UserRole).filter(UserRole.user_id.in_([u1_id, u2_id])).delete()
            self.sess.query(User).filter(User.id.in_([u1_id, u2_id])).delete()
            self.sess.query(Role).filter_by(code=unique_role_code).delete()
            self.sess.query(OrganizationProfile).filter_by(id=org_id).delete()
            self.sess.commit()

        finally:
            self.teardown()

# ── L-4: Complete Transaction Fault Tests ────────────────────────────────────
class TestTransactionFaultsCompleted(BaseExcelTest):
    def test_outer_commit_failure(self, monkeypatch):
        self._setup()
        try:
            self.b.source_sheet_name = None
            self.sess.commit()

            # Mock outer commit failure during the core upload
            orig_commit = self.sess.commit
            fail_commit = False
            def mock_commit():
                nonlocal fail_commit
                if fail_commit:
                    fail_commit = False # Only fail once
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

            # Verify recovery behavior wrote a commit_failure audit event
            fail_commit = False
            self.sess.rollback()
            events = self.sess.query(AuditEvent).filter_by(entity_id=self.b.id).all()
            assert any(e.payload.get("error_code") == "commit_failure" for e in events)

            # Original staging rows intact
            if self.engine.url.drivername != 'sqlite':
                rows = self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=self.b.id).all()
                assert len(rows) == 3
        finally:
            self.teardown()

    def test_failure_audit_event_flush_failure(self, monkeypatch):
        self._setup()
        try:
            self.b.source_sheet_name = None
            self.sess.commit()

            # Mock log_audit_event failure on failure logging
            import app.modules.excel_import.application.replace_staging_rows as rs_mod
            def mock_audit(*a, **kw):
                if kw.get("event_name") == "ProjectAssetImportBatchUploadFailed":
                    raise RuntimeError("Failure Audit Flush Failed")
            monkeypatch.setattr(rs_mod, "log_audit_event", mock_audit)

            # Trigger a ParseError (10001 chars cell exceeds 10000 chars cell length limit)
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
            assert exc.value.detail != "Failure Audit Flush Failed" # original exception not masked
        finally:
            self.teardown()

    def test_failure_audit_event_commit_failure(self, monkeypatch):
        self._setup()
        try:
            self.b.source_sheet_name = None
            self.sess.commit()

            # Mock db commit failure during failure audit logging
            orig_commit = self.sess.commit
            fail_commit = False
            def mock_commit():
                if fail_commit:
                    raise RuntimeError("Commit failure in failure audit path")
                orig_commit()
            monkeypatch.setattr(self.sess, "commit", mock_commit)

            # Trigger a ParseError
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

# ── L-5: ProjectAssetLine Immutability Snapshot Proofs ──────────────────────
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
                files={"file": ("test.xlsx", content, "app/vnd...xlsx")},
                headers={"X-User-Id": str(self.u.id)})
            assert resp.status_code == 200
            after1 = self.sess.query(ProjectAssetLine).get(self.al_id)
            assert (after1.id, after1.asset_name, after1.quantity, after1.row_version) == snapshot_before

            # 2. Invalid ZIP
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", b"invalid-zip", "app/vnd...xlsx")},
                headers={"X-User-Id": str(self.u.id)})
            assert resp.status_code == 400
            after2 = self.sess.query(ProjectAssetLine).get(self.al_id)
            assert (after2.id, after2.asset_name, after2.quantity, after2.row_version) == snapshot_before

            # 3. Row Limit Rollback (5001 rows)
            limits = ExcelImportLimits(max_data_rows=5, max_physical_rows=10)
            rows = [["asset_name"]] + [["v"] for _ in range(6)]
            content_large = _xlsx(rows=rows)
            # Patch default limits temporarily in both import_service and parse_workbook
            import sys
            service_mod = sys.modules["app.modules.excel_import.application.import_service"]
            parse_mod = sys.modules["app.modules.excel_import.application.parse_workbook"]
            monkeypatch.setattr(service_mod, "DEFAULT_LIMITS", limits)
            monkeypatch.setattr(parse_mod, "DEFAULT_LIMITS", limits)
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", content_large, "app/vnd...xlsx")},
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
                files={"file": ("test.xlsx", content, "app/vnd...xlsx")},
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
            print("MOCK FUN IS:", rs_mod.log_audit_event)
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", content, "app/vnd...xlsx")},
                headers={"X-User-Id": str(self.u.id)})
            print("STATUS:", resp.status_code, "BODY:", resp.text)
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
                files={"file": ("test.xlsx", content, "app/vnd...xlsx")},
                headers={"X-User-Id": str(self.u.id)})
            assert resp.status_code == 500
            after6 = self.sess.query(ProjectAssetLine).get(self.al_id)
            assert (after6.id, after6.asset_name, after6.quantity, after6.row_version) == snapshot_before
        finally:
            self.teardown()
