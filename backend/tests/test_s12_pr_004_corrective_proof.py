"""S12-PR-004 corrective proof: C-1..C-7 regressions."""
from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.modules.excel_import.application.apply_staging import (
    FAILURE_EVENT,
    SUCCESS_EVENT,
    apply_project_asset_import_batch,
)
from app.modules.excel_import.application.validate_staging import (
    validate_project_asset_import_batch,
)
from app.modules.excel_import.application.import_service import upload_excel_file_orchestrator
from app.modules.project_master_data.models import (
    AuditEvent,
    Customer,
    CustomerStatus,
    ImportBatchStatus,
    ImportRowValidationStatus,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    ProjectAssetLine,
    ProjectWorkflowStatus,
    ReferenceStatus,
    Role,
    Unit,
    User,
    UserRole,
    UserStatus,
)
from tests.test_s12_pr_004_staging_apply import ApplyHarness


class TestC1PostCommitBoundary:
    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()

    def test_success_response_without_post_commit_refresh(self, monkeypatch):
        self.h.add_row(name="X")
        calls = {"refresh": 0, "query_after": 0}
        orig_refresh = self.h.db.refresh

        def track_refresh(*a, **k):
            calls["refresh"] += 1
            return orig_refresh(*a, **k)

        monkeypatch.setattr(self.h.db, "refresh", track_refresh)
        out = apply_project_asset_import_batch(
            self.h.db,
            org_id=self.h.org.id,
            project_id=self.h.project.id,
            batch_id=self.h.batch.id,
            current_user=self.h.user,
            confirm=True,
        )
        assert out["status"] == "applied"
        assert out["created_count"] == 1
        assert isinstance(out["created_lines"][0]["line_id"], uuid.UUID)
        assert calls["refresh"] == 0
        assert (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=SUCCESS_EVENT)
            .count()
            == 1
        )

    def test_outer_commit_failure_not_success(self, monkeypatch):
        self.h.add_row()
        orig = self.h.db.commit
        n = {"i": 0}

        def boom():
            n["i"] += 1
            if n["i"] == 1:
                raise RuntimeError("outer commit fail")
            return orig()

        monkeypatch.setattr(self.h.db, "commit", boom)
        with pytest.raises(HTTPException) as exc:
            apply_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
                confirm=True,
            )
        assert exc.value.status_code == 500
        self.h.db.expire_all()
        self.h.db.refresh(self.h.batch)
        assert self.h.batch.status == ImportBatchStatus.READY_FOR_REVIEW
        assert (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=SUCCESS_EVENT)
            .count()
            == 0
        )
        assert (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=FAILURE_EVENT)
            .count()
            == 1
        )
        assert (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .count()
            == 0
        )


class TestC2StagingForUpdate:
    def test_source_contains_staging_for_update(self):
        src = Path("app/modules/excel_import/application/apply_staging.py").read_text(
            encoding="utf-8"
        )
        assert "ProjectAssetImportStagingRow" in src
        assert ".with_for_update()" in src
        # ordered then locked
        assert "source_row_number" in src
        idx_order = src.find("ProjectAssetImportStagingRow.source_row_number")
        idx_fu = src.find(".with_for_update()", idx_order)
        assert idx_order != -1 and idx_fu != -1 and idx_fu > idx_order


class TestC5MappingExhaustive:
    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()

    def _apply(self):
        return self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )

    @pytest.mark.parametrize(
        "name,ok",
        [
            ("  Máy  ", True),
            ("", False),
            ("   ", False),
            ("A" * 255, True),
            ("A" * 256, False),
        ],
    )
    def test_asset_name_bounds(self, name, ok):
        self.h.add_row(name=name if name.strip() or name == "" else name)
        # blank after trim
        if name == "   ":
            self.h.db.query(ProjectAssetImportStagingRow).update(
                {"proposed_asset_name": "   "}
            )
            self.h.db.commit()
        r = self._apply()
        assert (r.status_code == 200) is ok

    @pytest.mark.parametrize(
        "desc,expect_null,ok",
        [
            ("  hi  ", False, True),
            ("", True, True),
            ("   ", True, True),
            ("D" * 5000, False, True),
            ("D" * 5001, False, False),
        ],
    )
    def test_description_bounds(self, desc, expect_null, ok):
        self.h.add_row(name="N", desc=desc)
        r = self._apply()
        if not ok:
            assert r.status_code == 400
            return
        assert r.status_code == 200
        line = (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .one()
        )
        if expect_null:
            assert line.description is None
        else:
            assert line.description == desc.strip()

    @pytest.mark.parametrize(
        "qty,ok",
        [
            (None, True),
            ("", True),
            ("0", True),
            ("1.0000", True),
            ("1.00001", False),
            ("1e3", True),
            ("NaN", False),
            ("Infinity", False),
            ("-1", False),
            ("1" + "0" * 11, False),  # 12 integer digits
            ("12345678901", True),  # 11 integer
        ],
    )
    def test_quantity_bounds(self, qty, ok):
        self.h.add_row(name="N", qty=qty)
        r = self._apply()
        assert (r.status_code == 200) is ok, (qty, r.text)

    def test_unit_priority_code_over_display(self):
        # display name matches another unit's display; code match wins for CAI
        u2 = Unit(
            code="ZZ",
            display_name="CAI",
            symbol="z",
            status=ReferenceStatus.ACTIVE,
        )
        self.h.db.add(u2)
        self.h.db.commit()
        self.h.add_row(name="N", unit="cai")
        r = self._apply()
        assert r.status_code == 200
        line = (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .one()
        )
        assert line.unit_id == self.h.unit.id

    def test_unit_inactive_unknown_ambiguous_symbol(self):
        self.h.add_row(name="N", unit="OLD")
        assert self._apply().status_code == 400
        self.h.db.query(ProjectAssetImportStagingRow).delete()
        self.h.db.commit()
        self.h.add_row(name="N", unit="unknown")
        assert self._apply().status_code == 400
        # ambiguous symbol
        self.h.db.query(ProjectAssetImportStagingRow).delete()
        self.h.db.commit()
        self.h.db.add(
            Unit(
                code="S1",
                display_name="S1",
                symbol="dup",
                status=ReferenceStatus.ACTIVE,
            )
        )
        self.h.db.add(
            Unit(
                code="S2",
                display_name="S2",
                symbol="dup",
                status=ReferenceStatus.ACTIVE,
            )
        )
        self.h.db.commit()
        self.h.add_row(name="N", unit="dup")
        assert self._apply().status_code == 400

    def test_currency_symbol_and_inactive(self):
        self.h.add_row(name="N", currency="₫")
        assert self._apply().status_code == 400
        self.h.db.query(ProjectAssetImportStagingRow).delete()
        self.h.db.commit()
        self.h.add_row(name="N", currency="XXX")
        assert self._apply().status_code == 400

    def test_exclusions_and_duplicate_names(self):
        self.h.add_row(name="Same", source_row_number=2)
        self.h.add_row(name="Same", source_row_number=1)
        r = self._apply()
        assert r.status_code == 200
        assert r.json()["created_count"] == 2
        assert [x["source_row_number"] for x in r.json()["created_lines"]] == [1, 2]
        lines = (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .all()
        )
        for line in lines:
            assert line.appraised_unit_price is None
            assert line.row_version == 1


class TestC4FaultInjection:
    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()

    def test_mapping_fail_after_partial_savepoint(self):
        self.h.add_row(name="Good", unit="CAI", source_row_number=1)
        self.h.add_row(name="Bad", unit="NOPE", source_row_number=2)
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 400
        self.h.db.expire_all()
        self.h.db.refresh(self.h.batch)
        assert self.h.batch.status == ImportBatchStatus.READY_FOR_REVIEW
        assert (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .count()
            == 0
        )
        assert (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=FAILURE_EVENT)
            .count()
            == 1
        )
        assert (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=SUCCESS_EVENT)
            .count()
            == 0
        )
        self.h.assert_manual_immutable()

    def test_savepoint_commit_failure(self, monkeypatch):
        self.h.add_row()
        real = self.h.db.begin_nested

        class Boom:
            def __init__(self, sp):
                self._sp = sp

            def commit(self):
                raise RuntimeError("sp fail")

            def rollback(self):
                return self._sp.rollback()

        monkeypatch.setattr(self.h.db, "begin_nested", lambda: Boom(real()))
        with pytest.raises(HTTPException) as exc:
            apply_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
                confirm=True,
            )
        assert exc.value.status_code == 500
        self.h.db.expire_all()
        self.h.db.refresh(self.h.batch)
        assert self.h.batch.status == ImportBatchStatus.READY_FOR_REVIEW
        assert (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=FAILURE_EVENT)
            .count()
            == 1
        )

    def test_failure_audit_persist_failure(self, monkeypatch):
        import app.modules.excel_import.application.apply_staging as ap

        self.h.add_row(unit="NOPE")
        orig = ap._record_failure_audit

        def stage_then_boom(*a, **k):
            orig(*a, **k)
            raise RuntimeError("fail audit persist")

        monkeypatch.setattr(ap, "_record_failure_audit", stage_then_boom)
        with pytest.raises(HTTPException):
            apply_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
                confirm=True,
            )
        self.h.db.expire_all()
        self.h.db.refresh(self.h.batch)
        # recovery rolled back partial failure audit
        assert self.h.batch.status == ImportBatchStatus.READY_FOR_REVIEW
        assert (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=FAILURE_EVENT)
            .count()
            == 0
        )

    def test_stale_failure_after_newer_apply(self, monkeypatch):
        import app.modules.excel_import.application.apply_staging as ap

        self.h.add_row()
        orig = ap._recover_apply_failure
        newer = {}

        def inject(*a, **k):
            self.h.batch.status = ImportBatchStatus.APPLIED
            self.h.db.commit()
            newer["status"] = "applied"
            return orig(*a, **k)

        monkeypatch.setattr(ap, "_recover_apply_failure", inject)
        monkeypatch.setattr(
            ap,
            "_map_row",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")),
        )
        with pytest.raises(HTTPException):
            apply_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
                confirm=True,
            )
        self.h.db.expire_all()
        self.h.db.refresh(self.h.batch)
        assert self.h.batch.status == ImportBatchStatus.APPLIED
        assert (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=FAILURE_EVENT)
            .count()
            == 0
        )


class TestC6LifecycleAndMigration:
    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()

    def test_upload_rejects_applied(self):
        self.h.add_row()
        assert (
            self.h.client()
            .post(
                f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
                json={"confirm": True},
            )
            .status_code
            == 200
        )
        before = self.h.db.query(AuditEvent).count()
        with pytest.raises(HTTPException) as exc:
            upload_excel_file_orchestrator(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                file=type(
                    "F",
                    (),
                    {
                        "filename": "x.xlsx",
                        "file": __import__("io").BytesIO(b"not-xlsx"),
                        "size": 8,
                    },
                )(),
                request=None,
                current_user=self.h.user,
            )
        assert exc.value.status_code == 409
        assert self.h.db.query(AuditEvent).count() == before
        self.h.db.refresh(self.h.batch)
        assert self.h.batch.status == ImportBatchStatus.APPLIED

    def test_validate_rejects_applied(self):
        self.h.add_row()
        assert (
            self.h.client()
            .post(
                f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
                json={"confirm": True},
            )
            .status_code
            == 200
        )
        before = self.h.db.query(AuditEvent).count()
        with pytest.raises(HTTPException) as exc:
            validate_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
            )
        assert exc.value.status_code == 409
        assert self.h.db.query(AuditEvent).count() == before

    def test_lineage_unique_and_manual_null(self):
        self.h.add_row()
        self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        line = (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .one()
        )
        assert line.source_staging_row_id is not None
        # manual remains null lineage
        self.h.assert_manual_immutable()
        # uniqueness: second line with same staging id fails
        dup = ProjectAssetLine(
            project_id=self.h.project.id,
            asset_name="Dup",
            quantity=1,
            source_import_batch_id=self.h.batch.id,
            source_staging_row_id=line.source_staging_row_id,
        )
        self.h.db.add(dup)
        with pytest.raises(Exception):
            self.h.db.commit()
        self.h.db.rollback()

    def test_alembic_single_head(self):
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        cfg = Config("alembic.ini")
        heads = ScriptDirectory.from_config(cfg).get_heads()
        assert heads == ["e1f2a3b4c5d6"]


def _pg_url():
    pg = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not pg or "postgres" not in pg:
        return None
    return pg


def _wait_lock(engine, pid, timeout=30.0):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        with engine.connect() as conn:
            last = conn.execute(
                text(
                    "SELECT wait_event_type, wait_event, state "
                    "FROM pg_stat_activity WHERE pid = :pid"
                ),
                {"pid": pid},
            ).first()
            if last is not None and last[0] == "Lock":
                return last
        time.sleep(0.05)
    raise AssertionError(f"pid {pid} never Lock-waited; last={last}")


class TestPGApplyMatrixCorrective:
    """C-3 multi-session matrix; skip without PostgreSQL."""

    def test_pg_apply_vs_apply(self):
        pg = _pg_url()
        if not pg:
            pytest.skip("SKIPPED LOCALLY - REQUIRES CI WITH POSTGRESQL")
        # reuse existing test pattern via import
        from tests.test_s12_pr_004_staging_apply import TestPGApplyConcurrency

        TestPGApplyConcurrency().test_pg_apply_vs_apply_exact_once()

    def test_pg_apply_holds_then_validate_waits(self):
        pg = _pg_url()
        if not pg:
            pytest.skip("SKIPPED LOCALLY - REQUIRES CI WITH POSTGRESQL")

        engine = create_engine(pg)
        SessionLocal = sessionmaker(bind=engine)
        s = SessionLocal()
        ids = {}
        try:
            uid = uuid.uuid4().hex[:8]
            org = OrganizationProfile(
                legal_name=f"O{uid}",
                organization_slug=f"o{uid}",
                status=OrganizationStatus.ACTIVE,
            )
            s.add(org)
            s.commit()
            role = Role(
                code=f"r{uid}",
                display_name="R",
                permissions=["workbench:edit", "project:read"],
            )
            s.add(role)
            s.commit()
            user = User(
                organization_id=org.id,
                email=f"u{uid}@t.com",
                full_name="U",
                status=UserStatus.ACTIVE,
            )
            s.add(user)
            s.commit()
            s.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))
            s.commit()
            cust = Customer(
                organization_id=org.id,
                legal_name="C",
                status=CustomerStatus.ACTIVE,
                created_by=user.id,
            )
            s.add(cust)
            s.commit()
            project = Project(
                organization_id=org.id,
                customer_id=cust.id,
                code=f"C{uid[:6]}",
                name="P",
                status=ProjectWorkflowStatus.DRAFT,
                created_by=user.id,
            )
            s.add(project)
            s.commit()
            batch = ProjectAssetImportBatch(
                organization_id=org.id,
                project_id=project.id,
                source_filename="x.xlsx",
                source_sheet_name="Sheet1",
                status=ImportBatchStatus.READY_FOR_REVIEW,
                total_rows=1,
                valid_rows=1,
                invalid_rows=0,
                warning_rows=0,
                created_by_user_id=user.id,
            )
            s.add(batch)
            s.commit()
            s.add(
                ProjectAssetImportStagingRow(
                    organization_id=org.id,
                    project_id=project.id,
                    import_batch_id=batch.id,
                    source_row_number=1,
                    raw_values={},
                    mapped_values={},
                    normalized_preview={},
                    validation_status=ImportRowValidationStatus.VALID,
                    validation_errors=[],
                    validation_warnings=[],
                    proposed_asset_name="PG",
                    proposed_quantity="1",
                )
            )
            s.commit()
            ids = {
                "org": org.id,
                "project": project.id,
                "batch": batch.id,
                "user": user.id,
                "role": role.id,
                "cust": cust.id,
            }
        finally:
            s.close()

        import app.modules.excel_import.application.apply_staging as ap

        hold = threading.Event()
        release = threading.Event()
        errors = []
        val_pid = []
        orig_fp = ap.build_apply_fingerprint

        def gated_fp(db, **kw):
            hold.set()
            assert release.wait(timeout=30)
            return orig_fp(db, **kw)

        ap.build_apply_fingerprint = gated_fp
        try:

            def apply_worker():
                sess = SessionLocal()
                try:
                    u = sess.query(User).filter_by(id=ids["user"]).one()
                    apply_project_asset_import_batch(
                        sess,
                        org_id=ids["org"],
                        project_id=ids["project"],
                        batch_id=ids["batch"],
                        current_user=u,
                        confirm=True,
                    )
                except Exception as e:
                    errors.append(("apply", e))
                finally:
                    sess.close()

            def validate_worker():
                sess = SessionLocal()
                try:
                    assert hold.wait(timeout=30)
                    val_pid.append(
                        sess.execute(text("SELECT pg_backend_pid()")).scalar()
                    )
                    u = sess.query(User).filter_by(id=ids["user"]).one()
                    validate_project_asset_import_batch(
                        sess,
                        org_id=ids["org"],
                        project_id=ids["project"],
                        batch_id=ids["batch"],
                        current_user=u,
                    )
                except Exception as e:
                    errors.append(("validate", e))
                finally:
                    sess.close()

            t_a = threading.Thread(target=apply_worker)
            t_a.start()
            assert hold.wait(timeout=30)
            t_v = threading.Thread(target=validate_worker)
            t_v.start()
            deadline = time.monotonic() + 30
            while not val_pid and time.monotonic() < deadline:
                time.sleep(0.02)
            assert val_pid, "validate pid not published"
            _wait_lock(engine, val_pid[0])
            release.set()
            t_a.join(timeout=90)
            t_v.join(timeout=90)
            assert not t_a.is_alive() and not t_v.is_alive()
            # apply succeeded; validate should 409 applied
            assert not any(e[0] == "apply" for e in errors)
            assert any(
                e[0] == "validate"
                and isinstance(e[1], HTTPException)
                and e[1].status_code == 409
                for e in errors
            )
            sess = SessionLocal()
            try:
                b = sess.query(ProjectAssetImportBatch).filter_by(id=ids["batch"]).one()
                assert b.status == ImportBatchStatus.APPLIED
                assert (
                    sess.query(ProjectAssetLine)
                    .filter_by(source_import_batch_id=ids["batch"])
                    .count()
                    == 1
                )
            finally:
                sess.close()
        finally:
            ap.build_apply_fingerprint = orig_fp
            s = SessionLocal()
            try:
                s.query(ProjectAssetLine).filter_by(
                    source_import_batch_id=ids["batch"]
                ).delete()
                s.query(ProjectAssetImportStagingRow).filter_by(
                    import_batch_id=ids["batch"]
                ).delete()
                s.query(AuditEvent).filter(AuditEvent.entity_id == ids["batch"]).delete(
                    synchronize_session=False
                )
                s.query(ProjectAssetImportBatch).filter_by(id=ids["batch"]).delete()
                s.query(Project).filter_by(id=ids["project"]).delete()
                s.query(Customer).filter_by(id=ids["cust"]).delete()
                s.query(UserRole).filter_by(user_id=ids["user"]).delete()
                s.query(User).filter_by(id=ids["user"]).delete()
                s.query(Role).filter_by(id=ids["role"]).delete()
                s.query(OrganizationProfile).filter_by(id=ids["org"]).delete()
                s.commit()
            finally:
                s.close()
