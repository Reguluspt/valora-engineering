"""S12-R-006: final corrective re-audit tests."""
import io
import os
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
    ImportBatchStatus, ProjectAssetLine,
)
from app.modules.project_master_data.models import AuditEvent

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
        # Clean up database tables if using real DB
        if self.engine.url.drivername != 'sqlite':
            Base.metadata.drop_all(bind=self.engine)

# ── J-1 & R-1: request header enforcement ──────────────────────────────────
class TestRequestLimit(BaseExcelTest):
    def test_oversized_header(self):
        self._setup()
        try:
            content = _xlsx(rows=[["asset_name"]])
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", content, "app/vnd...xlsx")},
                headers={"X-User-Id": str(self.u.id), "Content-Length": "13000000"})
            assert resp.status_code == 413
            assert "kích thước" in resp.json()["detail"].lower()
        finally:
            self.teardown()

    def test_negative_header(self):
        self._setup()
        try:
            content = _xlsx(rows=[["asset_name"]])
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", content, "app/vnd...xlsx")},
                headers={"X-User-Id": str(self.u.id), "Content-Length": "-10"})
            assert resp.status_code == 400
        finally:
            self.teardown()

    def test_malformed_header(self):
        self._setup()
        try:
            content = _xlsx(rows=[["asset_name"]])
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", content, "app/vnd...xlsx")},
                headers={"X-User-Id": str(self.u.id), "Content-Length": "not-a-number"})
            assert resp.status_code == 400
        finally:
            self.teardown()

    def test_missing_header_accepted(self):
        self._setup()
        try:
            self.b.source_sheet_name = None
            self.sess.commit()
            content = _xlsx(rows=[["asset_name"], ["new1"]])
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", content, "app/vnd...xlsx")},
                headers={"X-User-Id": str(self.u.id)})
            assert resp.status_code == 200
        finally:
            self.teardown()

# ── J-2: lazy workbook lifecycle cleanups ───────────────────────────────────
class TestLazyCleanup:
    def test_cleanup_scenarios(self, monkeypatch):
        spool_closes = 0
        wb_closes = 0

        class SpySpool:
            def __init__(self, real):
                self.real = real
            def close(self):
                nonlocal spool_closes
                spool_closes += 1
                self.real.close()
            def __getattr__(self, name):
                return getattr(self.real, name)

        class SpyWorkbook:
            def __init__(self, real):
                self.real = real
            def close(self):
                nonlocal wb_closes
                wb_closes += 1
                self.real.close()
            def __getitem__(self, item):
                return self.real[item]
            def __getattr__(self, name):
                return getattr(self.real, name)

        import tempfile
        import openpyxl

        orig_spool = tempfile.SpooledTemporaryFile
        orig_load = openpyxl.load_workbook

        def mock_spool(*a, **kw):
            return SpySpool(orig_spool(*a, **kw))

        def mock_load(file_obj, *a, **kw):
            return SpyWorkbook(orig_load(file_obj, *a, **kw))

        monkeypatch.setattr(tempfile, "SpooledTemporaryFile", mock_spool)
        monkeypatch.setattr(openpyxl, "load_workbook", mock_load)

        # 1. Invalid ZIP
        spool_closes = 0
        with pytest.raises(ParseError):
            parse_workbook_lazy(FakeUpload("test.xlsx", b"invalid-zip"), None)
        assert spool_closes == 1

        # 2. Missing Sheet
        spool_closes = 0
        wb_closes = 0
        content = _xlsx(sheet="CorrectSheet")
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", content), "NonExistentSheet")
        assert exc.value.error_code == "sheet_not_found"
        assert spool_closes == 1
        assert wb_closes == 1

        # 3. Header failure (blank sheet)
        spool_closes = 0
        wb_closes = 0
        content = _xlsx(sheet="Sheet1", rows=[])
        with pytest.raises(ParseError) as exc:
            parse_workbook_lazy(FakeUpload("test.xlsx", content), "Sheet1")
        assert exc.value.error_code == "header_not_found"
        assert spool_closes == 1
        assert wb_closes == 1

        # 4. Normal Exhaustion
        spool_closes = 0
        wb_closes = 0
        content = _xlsx(sheet="Sheet1", rows=[["asset_name"], ["row1"]])
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), "Sheet1") as lazy:
            list(lazy)
        assert spool_closes == 1
        assert wb_closes == 1

        # 5. Early context exit
        spool_closes = 0
        wb_closes = 0
        content = _xlsx(sheet="Sheet1", rows=[["asset_name"], ["row1"], ["row2"]])
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), "Sheet1") as lazy:
            next(lazy)
        assert spool_closes == 1
        assert wb_closes == 1

        # 6. Iteration exception
        spool_closes = 0
        wb_closes = 0
        content = _xlsx(sheet="Sheet1", rows=[["asset_name"], ["row1"]])
        try:
            with parse_workbook_lazy(FakeUpload("test.xlsx", content), "Sheet1") as lazy:
                next(lazy)
                raise RuntimeError("Force exit")
        except RuntimeError:
            pass
        assert spool_closes == 1
        assert wb_closes == 1

# ── J-3: PostgreSQL concurrency test ────────────────────────────────────────
class TestPGConcurrency(BaseExcelTest):
    def test_concurrent_upload_serialization(self):
        pg = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
        if not pg or "postgres" not in pg:
            pytest.skip("PostgreSQL concurrency test requires CI with PostgreSQL service")

        self._setup(db_url=pg)
        try:
            # 1. Create a unique organization/project/batch for this test
            org2 = OrganizationProfile(legal_name="T2", organization_slug="t2", status=OrganizationStatus.ACTIVE)
            self.sess.add(org2)
            self.sess.commit()
            
            cust2 = Customer(organization_id=org2.id, legal_name="C2", status=CustomerStatus.ACTIVE, created_by=self.u.id)
            self.sess.add(cust2)
            self.sess.commit()
            
            p2 = Project(organization_id=org2.id, customer_id=cust2.id, code="P2", name="P2", status=ProjectWorkflowStatus.DRAFT, created_by=self.u.id)
            self.sess.add(p2)
            self.sess.commit()
            
            b2 = ProjectAssetImportBatch(organization_id=org2.id, project_id=p2.id, source_filename="b2.xlsx", source_sheet_name="Sheet1", status=ImportBatchStatus.PARSED, total_rows=0, created_by_user_id=self.u.id)
            self.sess.add(b2)
            self.sess.commit()

            import threading
            barrier = threading.Barrier(2)
            results = []
            exceptions = []

            def worker(worker_id):
                # Use separate database session
                sess_worker = self.SessionLocal()
                content = _xlsx(rows=[["asset_name"], [f"worker-{worker_id}"]])
                upload = FakeUpload("b2.xlsx", content)
                barrier.wait()
                try:
                    res = upload_excel_file_orchestrator(
                        db=sess_worker,
                        org_id=org2.id,
                        project_id=p2.id,
                        batch_id=b2.id,
                        file=upload,
                        request=None,
                        current_user=self.u,
                        correlation_id=f"corr-{worker_id}"
                    )
                    results.append((worker_id, "success", res.total_rows))
                except Exception as e:
                    exceptions.append(e)
                    results.append((worker_id, "failure", str(e)))
                finally:
                    sess_worker.close()

            t1 = threading.Thread(target=worker, args=(1,))
            t2 = threading.Thread(target=worker, args=(2,))
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            # Inspect outcomes
            assert len(results) == 2
            success_count = sum(1 for r in results if r[1] == "success")
            assert success_count >= 1

            # Fetch final state
            self.sess.refresh(b2)
            assert b2.status == ImportBatchStatus.PARSED
            assert b2.total_rows == 1

            stg_rows = self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=b2.id).all()
            assert len(stg_rows) == 1

            audits = self.sess.query(AuditEvent).filter(
                AuditEvent.organization_id == org2.id,
                AuditEvent.action == "ProjectAssetImportBatchUploaded"
            ).all()
            assert len(audits) >= 1

        finally:
            self.teardown()

# ── J-4: transaction failure tests ──────────────────────────────────────────
class TestTransactionFaults(BaseExcelTest):
    def test_staging_flush_failure(self, monkeypatch):
        self._setup()
        try:
            self.b.source_sheet_name = None
            self.sess.commit()

            fail_flush = False
            orig_flush = self.sess.flush
            def mock_flush(*a, **kw):
                nonlocal fail_flush
                if fail_flush:
                    fail_flush = False
                    raise RuntimeError("Staging flush failed")
                return orig_flush(*a, **kw)
            monkeypatch.setattr(self.sess, "flush", mock_flush)

            orig_add = self.sess.add
            def mock_add(instance, *a, **kw):
                nonlocal fail_flush
                if isinstance(instance, ProjectAssetImportStagingRow):
                    fail_flush = True
                return orig_add(instance, *a, **kw)
            monkeypatch.setattr(self.sess, "add", mock_add)

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

            # Verify original staging rows intact
            rows = self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=self.b.id).all()
            assert len(rows) == 3
            assert [r.id for r in rows] == self.seeded_staging_ids
        finally:
            self.teardown()

    def test_success_audit_event_failure(self, monkeypatch):
        self._setup()
        try:
            self.b.source_sheet_name = None
            self.sess.commit()

            def mock_audit(*a, **kw):
                raise RuntimeError("Audit failure")
            import app.modules.excel_import.application.replace_staging_rows as rs_mod
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

            # Verify original staging rows intact
            rows = self.sess.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=self.b.id).all()
            assert len(rows) == 3
            assert [r.id for r in rows] == self.seeded_staging_ids
        finally:
            self.teardown()

# ── J-5: ProjectAssetLine snapshot proof ────────────────────────────────────
class TestProjectAssetLineImmutability(BaseExcelTest):
    def test_line_immutable_on_failures(self):
        self._setup()
        try:
            before = self.sess.query(ProjectAssetLine).get(self.al_id)
            b_id = before.id
            b_name = before.asset_name
            b_qty = before.quantity
            b_ver = before.row_version

            # 1. Malformed XLSX
            resp = self.client.post(
                f"/api/v1/projects/{self.p.id}/asset-imports/{self.b.id}/upload",
                files={"file": ("test.xlsx", b"invalid-zip", "app/vnd...xlsx")},
                headers={"X-User-Id": str(self.u.id)})
            assert resp.status_code == 400

            # Verify line unchanged
            after = self.sess.query(ProjectAssetLine).get(self.al_id)
            assert after.id == b_id
            assert after.asset_name == b_name
            assert after.quantity == b_qty
            assert after.row_version == b_ver
        finally:
            self.teardown()

# ── J-6: resource proof (columns limit) ────────────────────────────────────
class TestColumnsLimit:
    def test_exact_100_columns_accepted(self):
        limits = ExcelImportLimits(max_columns=100)
        rows = [[f"col{i}" for i in range(100)], ["val" for _ in range(100)]]
        content = _xlsx(rows=rows)
        with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
            assert lazy.column_count == 100

    def test_101_columns_rejected(self):
        limits = ExcelImportLimits(max_columns=100)
        rows = [[f"col{i}" for i in range(101)], ["val" for _ in range(101)]]
        content = _xlsx(rows=rows)
        with pytest.raises(ParseError) as exc:
            with parse_workbook_lazy(FakeUpload("test.xlsx", content), None, limits=limits) as lazy:
                list(lazy)
        assert exc.value.error_code == "column_limit"
