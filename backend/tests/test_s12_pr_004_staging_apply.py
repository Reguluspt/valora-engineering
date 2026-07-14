"""S12-PR-004 Excel staging Apply command & provenance — behavioral proof."""
from __future__ import annotations

import os
import threading
import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db
from app.modules.excel_import.application.apply_staging import (
    CONTRACT_VERSION,
    FAILURE_EVENT,
    SUCCESS_EVENT,
    apply_project_asset_import_batch,
)
from app.modules.excel_import.application.validate_staging import (
    validate_project_asset_import_batch,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    Currency,
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


def _sqlite_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _sqlite_disable_isolation(dbapi_connection, connection_record):
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _sqlite_emit_begin(conn):
        conn.exec_driver_sql("BEGIN")

    Base.metadata.create_all(bind=engine)
    return engine


class ApplyHarness:
    def __init__(self):
        self.engine = _sqlite_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()
        self._seed()

    def _seed(self):
        self.org = OrganizationProfile(
            legal_name="Org", organization_slug=f"org-{uuid.uuid4().hex[:8]}", status=OrganizationStatus.ACTIVE
        )
        self.db.add(self.org)
        self.db.commit()
        self.role = Role(
            code=f"e-{uuid.uuid4().hex[:6]}",
            display_name="E",
            permissions=["project:read", "workbench:edit"],
        )
        self.db.add(self.role)
        self.db.commit()
        self.user = User(
            organization_id=self.org.id,
            email=f"u-{uuid.uuid4().hex[:6]}@t.com",
            full_name="U",
            status=UserStatus.ACTIVE,
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.add(UserRole(user_id=self.user.id, role_id=self.role.id, is_active=True))
        self.db.commit()
        self.cust = Customer(
            organization_id=self.org.id,
            legal_name="C",
            status=CustomerStatus.ACTIVE,
            created_by=self.user.id,
        )
        self.db.add(self.cust)
        self.db.commit()
        self.project = Project(
            organization_id=self.org.id,
            customer_id=self.cust.id,
            code=f"P{uuid.uuid4().hex[:6]}",
            name="P",
            status=ProjectWorkflowStatus.DRAFT,
            created_by=self.user.id,
        )
        self.db.add(self.project)
        self.db.commit()
        self.manual = ProjectAssetLine(
            project_id=self.project.id,
            asset_name="Manual",
            quantity=2.0,
            row_version=1,
        )
        self.db.add(self.manual)
        self.db.commit()
        self.manual_snap = {
            "id": self.manual.id,
            "asset_name": self.manual.asset_name,
            "quantity": self.manual.quantity,
            "row_version": self.manual.row_version,
            "source_import_batch_id": self.manual.source_import_batch_id,
            "source_staging_row_id": self.manual.source_staging_row_id,
        }
        self.unit = Unit(
            code="CAI", display_name="Cái", symbol="cái", status=ReferenceStatus.ACTIVE
        )
        self.unit_inactive = Unit(
            code="OLD", display_name="Old", symbol="old", status=ReferenceStatus.INACTIVE
        )
        self.cur = Currency(
            code="VND", display_name="Dong", symbol="₫", status=ReferenceStatus.ACTIVE
        )
        self.cur_inactive = Currency(
            code="XXX", display_name="Dead", symbol="x", status=ReferenceStatus.INACTIVE
        )
        self.db.add_all([self.unit, self.unit_inactive, self.cur, self.cur_inactive])
        self.db.commit()
        self.batch = ProjectAssetImportBatch(
            organization_id=self.org.id,
            project_id=self.project.id,
            source_filename="a.xlsx",
            source_sheet_name="Sheet1",
            status=ImportBatchStatus.READY_FOR_REVIEW,
            total_rows=0,
            valid_rows=0,
            invalid_rows=0,
            warning_rows=0,
            created_by_user_id=self.user.id,
        )
        self.db.add(self.batch)
        self.db.commit()

    def add_row(
        self,
        name="Asset",
        qty="1",
        *,
        unit="CAI",
        desc=None,
        price=None,
        currency=None,
        status=ImportRowValidationStatus.VALID,
        source_row_number=None,
    ):
        n = source_row_number or (
            self.db.query(ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=self.batch.id)
            .count()
            + 1
        )
        row = ProjectAssetImportStagingRow(
            organization_id=self.org.id,
            project_id=self.project.id,
            import_batch_id=self.batch.id,
            source_row_number=n,
            raw_values={"cells": []},
            mapped_values={},
            normalized_preview={},
            validation_status=status,
            validation_errors=[],
            validation_warnings=[],
            proposed_asset_name=name,
            proposed_description=desc,
            proposed_quantity=qty,
            proposed_unit=unit,
            proposed_raw_price=price,
            proposed_currency=currency,
            proposed_appraised_unit_price="999",
            proposed_review_status="accepted",
            proposed_validation_status="valid",
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        self._sync_counters()
        return row

    def _sync_counters(self):
        rows = (
            self.db.query(ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=self.batch.id)
            .all()
        )
        self.batch.total_rows = len(rows)
        self.batch.valid_rows = sum(
            1 for r in rows if r.validation_status == ImportRowValidationStatus.VALID
        )
        self.batch.invalid_rows = sum(
            1 for r in rows if r.validation_status == ImportRowValidationStatus.INVALID
        )
        self.batch.warning_rows = sum(
            1 for r in rows if r.validation_status == ImportRowValidationStatus.WARNING
        )
        self.db.commit()
        self.db.refresh(self.batch)

    def client(self):
        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        from app.core.rbac import get_current_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: self.user
        return TestClient(app)

    def assert_manual_immutable(self):
        self.db.expire_all()
        m = self.db.query(ProjectAssetLine).filter_by(id=self.manual_snap["id"]).one()
        assert m.asset_name == self.manual_snap["asset_name"]
        assert m.quantity == self.manual_snap["quantity"]
        assert m.row_version == self.manual_snap["row_version"]
        assert m.source_import_batch_id is None
        assert m.source_staging_row_id is None

    def close(self):
        app.dependency_overrides.clear()
        self.db.close()


class TestApplyApiAndEligibility:
    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()

    def test_confirm_required(self):
        self.h.add_row()
        c = self.h.client()
        url = f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply"
        r = c.post(url, json={})
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "apply_confirmation_required"
        r2 = c.post(url, json={"confirm": False})
        assert r2.status_code == 400
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
            == 0
        )

    def test_not_draft(self):
        self.h.add_row()
        self.h.project.status = ProjectWorkflowStatus.SUBMITTED
        self.h.db.commit()
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "apply_project_not_draft"

    def test_safe_404(self):
        self.h.add_row()
        r = self.h.client().post(
            f"/api/v1/projects/{uuid.uuid4()}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 404

    def test_batch_state_and_rows_not_ready(self):
        self.h.batch.status = ImportBatchStatus.PARSED
        self.h.db.commit()
        self.h.add_row()
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "apply_state_not_allowed"

        self.h.batch.status = ImportBatchStatus.READY_FOR_REVIEW
        self.h.db.commit()
        self.h.add_row(status=ImportRowValidationStatus.INVALID)
        r2 = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r2.status_code == 409
        assert r2.json()["detail"]["error_code"] == "apply_rows_not_ready"

    def test_success_mapping_lineage_order_and_audit(self):
        r2 = self.h.add_row(name="B-asset", qty="2", unit="Cái", source_row_number=2)
        r1 = self.h.add_row(
            name="  A-asset  ",
            qty="",
            unit="cai",
            desc="  hello  ",
            price="10.50",
            currency="vnd",
            source_row_number=1,
        )
        # force order: source_row 1 then 2
        self.h.db.refresh(r1)
        self.h.db.refresh(r2)
        res = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["status"] == "applied"
        assert body["created_count"] == 2
        assert [x["source_row_number"] for x in body["created_lines"]] == [1, 2]
        self.h.db.expire_all()
        self.h.db.refresh(self.h.batch)
        assert self.h.batch.status == ImportBatchStatus.APPLIED
        line1 = self.h.db.query(ProjectAssetLine).filter_by(
            id=uuid.UUID(str(body["created_lines"][0]["line_id"]))
        ).one()
        assert line1.asset_name == "A-asset"
        assert line1.description == "hello"
        assert Decimal(str(line1.quantity)) == Decimal("1.0000")
        assert line1.unit_id == self.h.unit.id
        assert Decimal(str(line1.raw_price)) == Decimal("10.50")
        assert line1.raw_price_currency_id == self.h.cur.id
        assert line1.review_status == "pending" or line1.review_status.value == "pending"
        assert (
            line1.validation_status == "unvalidated"
            or line1.validation_status.value == "unvalidated"
        )
        assert line1.source_import_batch_id == self.h.batch.id
        assert line1.source_staging_row_id is not None
        assert line1.row_version == 1
        # forbidden spreadsheet fields not applied
        assert line1.appraised_unit_price is None
        succ = (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=SUCCESS_EVENT)
            .all()
        )
        assert len(succ) == 1
        p = succ[0].payload
        assert p["contract_version"] == CONTRACT_VERSION
        assert set(p.keys()) == {
            "contract_version",
            "organization_id",
            "project_id",
            "batch_id",
            "source_status",
            "target_status",
            "total_rows",
            "created_count",
        }
        assert p["created_count"] == 2
        self.h.assert_manual_immutable()

    def test_reapply_409(self):
        self.h.add_row()
        url = f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply"
        assert self.h.client().post(url, json={"confirm": True}).status_code == 200
        r = self.h.client().post(url, json={"confirm": True})
        assert r.status_code == 409
        assert r.json()["detail"]["error_code"] == "apply_state_not_allowed"
        assert (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .count()
            == 1
        )
        assert (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=SUCCESS_EVENT)
            .count()
            == 1
        )

    def test_mapping_invalid_failure_audit(self):
        self.h.add_row(unit="NOPE")
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "apply_mapping_invalid"
        self.h.db.expire_all()
        self.h.db.refresh(self.h.batch)
        assert self.h.batch.status == ImportBatchStatus.READY_FOR_REVIEW
        fails = (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=FAILURE_EVENT)
            .all()
        )
        assert len(fails) == 1
        assert fails[0].payload["contract_version"] == CONTRACT_VERSION
        assert fails[0].payload["error_code"] == "apply_mapping_invalid"
        assert set(fails[0].payload.keys()) == {
            "contract_version",
            "organization_id",
            "project_id",
            "batch_id",
            "source_status",
            "error_code",
        }
        assert (
            self.h.db.query(ProjectAssetLine)
            .filter(ProjectAssetLine.source_import_batch_id == self.h.batch.id)
            .count()
            == 0
        )
        self.h.assert_manual_immutable()

    def test_currency_symbol_rejected(self):
        self.h.add_row(currency="₫")
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 400

    def test_decimal_reject_scale_and_nan(self):
        self.h.add_row(qty="1.00001")
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 400
        self.h.db.query(ProjectAssetImportStagingRow).delete()
        self.h.db.commit()
        self.h.add_row(qty="NaN")
        r2 = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r2.status_code == 400

    def test_outer_commit_failure_engine_audit(self, monkeypatch):
        self.h.add_row()
        orig = self.h.db.commit
        n = {"i": 0}

        def boom():
            n["i"] += 1
            if n["i"] == 1:
                raise RuntimeError("outer fail")
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
            .filter_by(entity_id=self.h.batch.id, event_name=FAILURE_EVENT)
            .count()
            == 1
        )
        self.h.assert_manual_immutable()

    def test_upload_validate_reject_applied(self):
        self.h.add_row()
        url = f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply"
        assert self.h.client().post(url, json={"confirm": True}).status_code == 200
        with pytest.raises(HTTPException) as exc:
            validate_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
            )
        assert exc.value.status_code == 409


def _pg_url():
    pg = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not pg or "postgres" not in pg:
        return None
    return pg


class TestPGApplyConcurrency:
    def test_pg_apply_vs_apply_exact_once(self):
        pg = _pg_url()
        if not pg:
            pytest.skip("SKIPPED LOCALLY - REQUIRES CI WITH POSTGRESQL")

        engine = create_engine(pg)
        SessionLocal = sessionmaker(bind=engine)
        s = SessionLocal()
        try:
            uid = uuid.uuid4().hex[:8]
            org = OrganizationProfile(
                legal_name=f"O{uid}", organization_slug=f"o{uid}", status=OrganizationStatus.ACTIVE
            )
            s.add(org)
            s.commit()
            role = Role(code=f"r{uid}", display_name="R", permissions=["workbench:edit", "project:read"])
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
            row = ProjectAssetImportStagingRow(
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
            s.add(row)
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

        barrier = threading.Barrier(2, timeout=30)
        results = []
        errors = []

        def worker():
            sess = SessionLocal()
            try:
                u = sess.query(User).filter_by(id=ids["user"]).one()
                barrier.wait(timeout=30)
                out = apply_project_asset_import_batch(
                    sess,
                    org_id=ids["org"],
                    project_id=ids["project"],
                    batch_id=ids["batch"],
                    current_user=u,
                    confirm=True,
                )
                results.append(out["created_count"])
            except Exception as e:
                errors.append(e)
            finally:
                sess.close()

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join(timeout=60)
        t2.join(timeout=60)
        assert not t1.is_alive() and not t2.is_alive()
        # one success, one conflict or both serialized to one success + one 409
        succ = [r for r in results]
        assert sum(succ) == 1 or (len(succ) == 1 and any(
            isinstance(e, HTTPException) and e.status_code == 409 for e in errors
        ))
        sess = SessionLocal()
        try:
            lines = (
                sess.query(ProjectAssetLine)
                .filter_by(source_import_batch_id=ids["batch"])
                .count()
            )
            assert lines == 1
            assert (
                sess.query(AuditEvent)
                .filter_by(entity_id=ids["batch"], event_name=SUCCESS_EVENT)
                .count()
                == 1
            )
        finally:
            sess.close()
            # cleanup
            s = SessionLocal()
            try:
                s.query(ProjectAssetLine).filter_by(source_import_batch_id=ids["batch"]).delete()
                s.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=ids["batch"]).delete()
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
