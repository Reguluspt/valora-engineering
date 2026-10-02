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
    _map_row,
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
    """V2 activation closes synthetic legacy entry; mapping rules remain unit-tested."""

    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()

    def assert_denial_preserved(self):
        self.h.assert_manual_immutable()
        assert self.h.db.query(ProjectAssetLine).count() == 1
        assert self.h.db.query(AuditEvent).filter(
            AuditEvent.event_name.in_((SUCCESS_EVENT, FAILURE_EVENT)),
        ).count() == 0
        assert self.h.batch.status == ImportBatchStatus.READY_FOR_REVIEW

    @pytest.mark.parametrize("payload", [{}, {"confirm": False}])
    def test_confirm_required(self, payload):
        self.h.add_row()
        response = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json=payload,
        )
        assert response.status_code == 400
        assert response.json()["detail"]["error_code"] == "apply_confirmation_required"
        self.assert_denial_preserved()

    @pytest.mark.parametrize("payload", [
        {"confirm": True},
        {"confirm": True, "contract_version": "s12-pr-004-v1"},
        {"confirm": True, "contract_version": CONTRACT_VERSION},
        {"confirm": True, "contract_version": CONTRACT_VERSION, "expected_case_version": "bad"},
        {"confirm": True, "contract_version": "unsupported", "expected_case_version": "a" * 64},
    ])
    def test_legacy_or_invalid_request_cannot_mutate(self, payload):
        row = self.h.add_row()
        before = (row.validation_status, row.proposed_asset_name, row.mapped_values)
        response = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json=payload,
        )
        assert response.status_code == 400
        assert response.json()["detail"]["error_code"] == "apply_contract_invalid"
        self.h.db.refresh(row)
        assert (row.validation_status, row.proposed_asset_name, row.mapped_values) == before
        self.assert_denial_preserved()

    def test_internal_legacy_entry_cannot_mutate(self):
        self.h.add_row()
        with pytest.raises(HTTPException) as denied:
            apply_project_asset_import_batch(
                self.h.db, org_id=self.h.org.id, project_id=self.h.project.id,
                batch_id=self.h.batch.id, current_user=self.h.user, confirm=True,
            )
        assert denied.value.status_code == 400
        assert denied.value.detail["error_code"] == "apply_contract_invalid"
        self.assert_denial_preserved()

    def test_not_draft(self):
        self.h.add_row()
        self.h.project.status = ProjectWorkflowStatus.SUBMITTED
        self.h.db.commit()
        response = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True, "contract_version": CONTRACT_VERSION,
                  "expected_case_version": "a" * 64},
        )
        assert response.status_code == 400
        assert response.json()["detail"]["error_code"] == "apply_project_not_draft"
        self.assert_denial_preserved()

    def test_safe_404(self):
        response = self.h.client().post(
            f"/api/v1/projects/{uuid.uuid4()}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True, "contract_version": CONTRACT_VERSION,
                  "expected_case_version": "a" * 64},
        )
        assert response.status_code == 404
        self.assert_denial_preserved()

    def test_batch_state_then_intake_prerequisite_denied(self):
        self.h.batch.status = ImportBatchStatus.PARSED
        self.h.db.commit()
        self.h.add_row()
        payload = {"confirm": True, "contract_version": CONTRACT_VERSION,
                   "expected_case_version": "a" * 64}
        url = f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply"
        response = self.h.client().post(url, json=payload)
        assert response.status_code == 409
        assert response.json()["detail"]["error_code"] == "apply_state_not_allowed"
        self.h.batch.status = ImportBatchStatus.READY_FOR_REVIEW
        self.h.db.commit()
        self.h.add_row(status=ImportRowValidationStatus.INVALID)
        response = self.h.client().post(url, json=payload)
        assert response.status_code == 409
        assert response.json()["detail"]["error_code"] == "apply_intake_required"
        self.assert_denial_preserved()

    def test_registered_mapping_and_forbidden_inputs(self):
        row = self.h.add_row(name="  A-asset  ", qty="", unit="cai", desc="  hello  ",
                             price="10.50", currency="vnd")
        fields = _map_row(self.h.db, row)
        assert fields == {
            "asset_name": "A-asset", "description": "hello", "quantity": Decimal("1.0000"),
            "unit_id": self.h.unit.id, "raw_price": Decimal("10.50"),
            "raw_price_currency_id": self.h.cur.id,
        }
        assert not {"appraised_unit_price", "review_status", "validation_status"} & fields.keys()
        self.assert_denial_preserved()

    @pytest.mark.parametrize("changes", [
        {"unit": "NOPE"}, {"unit": "OLD"}, {"currency": "XXX"}, {"currency": "₫"},
        {"qty": "1.00001"}, {"qty": "NaN"}, {"price": "1.001"},
    ])
    def test_invalid_registered_mapping_rejected(self, changes):
        row = self.h.add_row(**changes)
        with pytest.raises(ValueError):
            _map_row(self.h.db, row)
        self.assert_denial_preserved()

    def test_validate_rejects_historical_applied_batch(self):
        self.h.add_row()
        self.h.batch.status = ImportBatchStatus.APPLIED
        self.h.db.commit()
        with pytest.raises(HTTPException) as denied:
            validate_project_asset_import_batch(
                self.h.db, org_id=self.h.org.id, project_id=self.h.project.id,
                batch_id=self.h.batch.id, current_user=self.h.user,
            )
        assert denied.value.status_code == 409
        assert self.h.batch.status == ImportBatchStatus.APPLIED
        self.h.assert_manual_immutable()
        assert self.h.db.query(AuditEvent).count() == 0


def _pg_url():
    pg = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not pg or "postgres" not in pg:
        return None
    return pg


class TestPGApplyConcurrency:
    def test_pg_concurrent_naked_v1_requests_are_denied(self):
        pg = _pg_url()
        if not pg:
            pytest.fail("Guarded Apply concurrency certification requires PostgreSQL TEST_DATABASE_URL")

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
        assert results == []
        assert len(errors) == 2
        assert all(isinstance(error, HTTPException) and error.status_code == 400
                   and error.detail["error_code"] == "apply_contract_invalid" for error in errors)
        sess = SessionLocal()
        try:
            lines = (
                sess.query(ProjectAssetLine)
                .filter_by(source_import_batch_id=ids["batch"])
                .count()
            )
            assert lines == 0
            assert (
                sess.query(AuditEvent)
                .filter_by(entity_id=ids["batch"], event_name=SUCCESS_EVENT)
                .count()
                == 0
            )
            assert sess.query(AuditEvent).filter_by(
                entity_id=ids["batch"], event_name=FAILURE_EVENT,
            ).count() == 0
            assert sess.get(ProjectAssetImportBatch, ids["batch"]).status == ImportBatchStatus.READY_FOR_REVIEW
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
