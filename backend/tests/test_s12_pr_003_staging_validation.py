"""S12-PR-003 Excel staging validation engine — behavioral proof."""
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
from app.modules.excel_import.domain.validation_rules import (
    evaluate_row,
    is_finite_decimal_text,
    validate_asset_name,
    validate_quantity,
)
from app.modules.excel_import.application.validate_staging import (
    FAILURE_EVENT,
    SUCCESS_EVENT,
    build_validation_fingerprint,
    validate_project_asset_import_batch,
)
from app.modules.excel_import.application.import_service import upload_excel_file_orchestrator
import io
import openpyxl
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
    Role,
    User,
    UserRole,
    UserStatus,
)


# ---------------------------------------------------------------------------
# Domain unit tests
# ---------------------------------------------------------------------------


class TestValidationRulesCatalog:
    def test_null_empty_whitespace_asset_name_invalid(self):
        for value in (None, "", "   ", "\t"):
            err = validate_asset_name(value)
            assert err is not None
            assert err["message_key"] == "excel.validation.asset_name_required"
            assert err["field"] == "proposed_asset_name"
            assert "bắt buộc" in err["message"]

    def test_non_empty_asset_name_valid_without_rewrite(self):
        assert validate_asset_name("  Máy xúc  ") is None
        assert validate_asset_name("PC200") is None

    def test_null_empty_whitespace_quantity_valid(self):
        for value in (None, "", "  ", "\n"):
            assert validate_quantity(value) is None

    def test_finite_decimal_signed_zero_scientific_valid(self):
        for value in ("1", "0", "-3.5", "+2", "1e3", "2.5E-1", "0.0"):
            assert is_finite_decimal_text(value.strip()) or is_finite_decimal_text(value)
            assert validate_quantity(value) is None
        # ensure Decimal accepts
        assert Decimal("1e3").is_finite()

    def test_malformed_nan_infinity_quantity_invalid(self):
        for value in ("abc", "12x", "NaN", "nan", "Infinity", "+Infinity", "-Infinity", "1,000"):
            err = validate_quantity(value)
            assert err is not None, value
            assert err["message_key"] == "excel.validation.quantity_invalid"

    def test_both_errors_deterministic_order(self):
        status, errors, warnings = evaluate_row("  ", "not-a-number")
        assert status == "invalid"
        assert warnings == []
        assert [e["message_key"] for e in errors] == [
            "excel.validation.asset_name_required",
            "excel.validation.quantity_invalid",
        ]

    def test_valid_row_empty_warnings(self):
        status, errors, warnings = evaluate_row("Asset", "10")
        assert status == "valid"
        assert errors == []
        assert warnings == []

    def test_no_year_missing_warning(self):
        _, _, warnings = evaluate_row("A", None)
        assert warnings == []
        assert all("year" not in str(w).lower() for w in warnings)


class TestFingerprintNullAwareness:
    """F-1: fingerprint preserves null vs string distinctions."""

    def setup_method(self):
        self.h = ValidationHarness()

    def teardown_method(self):
        self.h.close()

    def _fp_for(self, name, qty):
        self.h.db.query(ProjectAssetImportStagingRow).filter_by(
            import_batch_id=self.h.batch.id
        ).delete()
        self.h.db.commit()
        self.h.add_row(name, qty)
        self.h.db.refresh(self.h.batch)
        return build_validation_fingerprint(self.h.db, self.h.batch)

    def test_fingerprint_differs_null_vs_literal_none_asset_name(self):
        a = self._fp_for(None, "1")
        b = self._fp_for("None", "1")
        assert a["validation_inputs"] != b["validation_inputs"]
        assert a != b

    def test_fingerprint_differs_null_vs_literal_none_quantity(self):
        a = self._fp_for("A", None)
        b = self._fp_for("A", "None")
        assert a["validation_inputs"] != b["validation_inputs"]
        assert a != b

    def test_fingerprint_differs_empty_string_vs_null(self):
        a = self._fp_for("", "1")
        b = self._fp_for(None, "1")
        assert a["validation_inputs"][0][0] == ""
        assert b["validation_inputs"][0][0] is None
        assert a != b

    def test_fingerprint_identical_typed_inputs_same_generation(self):
        self.h.db.query(ProjectAssetImportStagingRow).filter_by(
            import_batch_id=self.h.batch.id
        ).delete()
        self.h.db.commit()
        self.h.add_row("A", "1")
        c1 = build_validation_fingerprint(self.h.db, self.h.batch)
        c2 = build_validation_fingerprint(self.h.db, self.h.batch)
        assert c1 == c2
        assert c1["validation_inputs"] == [("A", "1")]

    def test_fingerprint_row_order_deterministic_by_id(self):
        self.h.db.query(ProjectAssetImportStagingRow).filter_by(
            import_batch_id=self.h.batch.id
        ).delete()
        self.h.db.commit()
        self.h.add_row("B", "2")
        self.h.add_row("A", "1")
        fp = build_validation_fingerprint(self.h.db, self.h.batch)
        rows = (
            self.h.db.query(ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=self.h.batch.id)
            .order_by(ProjectAssetImportStagingRow.id)
            .all()
        )
        assert fp["staging_row_ids"] == [r.id for r in rows]
        assert fp["validation_inputs"] == [
            (r.proposed_asset_name, r.proposed_quantity) for r in rows
        ]


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


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


class ValidationHarness:
    def __init__(self, engine=None):
        self.engine = engine or _sqlite_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()
        self._seed()

    def _seed(self):
        self.org = OrganizationProfile(
            legal_name="Org", organization_slug="org-v", status=OrganizationStatus.ACTIVE
        )
        self.org2 = OrganizationProfile(
            legal_name="Org2", organization_slug="org-v2", status=OrganizationStatus.ACTIVE
        )
        self.db.add_all([self.org, self.org2])
        self.db.commit()

        self.role = Role(
            code="editor",
            display_name="Editor",
            permissions=["project:read", "workbench:edit"],
        )
        self.role_viewer = Role(
            code="viewer", display_name="Viewer", permissions=["project:read"]
        )
        self.db.add_all([self.role, self.role_viewer])
        self.db.commit()

        self.user = User(
            organization_id=self.org.id,
            email="e@o.com",
            full_name="E",
            status=UserStatus.ACTIVE,
        )
        self.viewer = User(
            organization_id=self.org.id,
            email="v@o.com",
            full_name="V",
            status=UserStatus.ACTIVE,
        )
        self.user2 = User(
            organization_id=self.org2.id,
            email="e2@o.com",
            full_name="E2",
            status=UserStatus.ACTIVE,
        )
        self.db.add_all([self.user, self.viewer, self.user2])
        self.db.commit()
        self.db.add_all(
            [
                UserRole(user_id=self.user.id, role_id=self.role.id, is_active=True),
                UserRole(user_id=self.viewer.id, role_id=self.role_viewer.id, is_active=True),
                UserRole(user_id=self.user2.id, role_id=self.role.id, is_active=True),
            ]
        )
        self.db.commit()

        self.cust = Customer(
            organization_id=self.org.id,
            legal_name="C",
            status=CustomerStatus.ACTIVE,
            created_by=self.user.id,
        )
        self.cust2 = Customer(
            organization_id=self.org2.id,
            legal_name="C2",
            status=CustomerStatus.ACTIVE,
            created_by=self.user2.id,
        )
        self.db.add_all([self.cust, self.cust2])
        self.db.commit()

        self.project = Project(
            organization_id=self.org.id,
            customer_id=self.cust.id,
            code="P1",
            name="P1",
            status=ProjectWorkflowStatus.DRAFT,
            created_by=self.user.id,
        )
        self.project2 = Project(
            organization_id=self.org2.id,
            customer_id=self.cust2.id,
            code="P2",
            name="P2",
            status=ProjectWorkflowStatus.DRAFT,
            created_by=self.user2.id,
        )
        self.db.add_all([self.project, self.project2])
        self.db.commit()

        self.line = ProjectAssetLine(
            project_id=self.project.id,
            asset_name="Official Immutable",
            quantity=1.0,
            row_version=1,
        )
        self.db.add(self.line)
        self.db.commit()
        self.line_snapshot = {
            "id": self.line.id,
            "asset_name": self.line.asset_name,
            "quantity": self.line.quantity,
            "row_version": self.line.row_version,
        }

        self.batch = ProjectAssetImportBatch(
            organization_id=self.org.id,
            project_id=self.project.id,
            source_filename="a.xlsx",
            source_sheet_name="Sheet1",
            status=ImportBatchStatus.PARSED,
            total_rows=0,
            created_by_user_id=self.user.id,
        )
        self.db.add(self.batch)
        self.db.commit()

    def add_row(
        self,
        name: str | None,
        qty: str | None,
        *,
        batch=None,
        source_row_number: int | None = None,
    ) -> ProjectAssetImportStagingRow:
        batch = batch or self.batch
        n = source_row_number or (
            self.db.query(ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=batch.id)
            .count()
            + 1
        )
        row = ProjectAssetImportStagingRow(
            organization_id=batch.organization_id,
            project_id=batch.project_id,
            import_batch_id=batch.id,
            source_row_number=n,
            raw_values={"cells": []},
            mapped_values={},
            normalized_preview={},
            validation_status=ImportRowValidationStatus.PENDING,
            validation_errors=[{"field": "old", "message_key": "stale", "message": "old"}],
            validation_warnings=[{"field": "year", "message_key": "excel.validation.year_missing"}],
            proposed_asset_name=name,
            proposed_quantity=qty,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def client_as(self, user: User) -> TestClient:
        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        from app.core.rbac import get_current_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    def close(self):
        app.dependency_overrides.clear()
        self.db.close()

    def assert_line_immutable(self):
        self.db.expire_all()
        line = self.db.query(ProjectAssetLine).filter_by(id=self.line_snapshot["id"]).one()
        assert line.asset_name == self.line_snapshot["asset_name"]
        assert line.quantity == self.line_snapshot["quantity"]
        assert line.row_version == self.line_snapshot["row_version"]
        assert self.db.query(ProjectAssetLine).count() == 1


# ---------------------------------------------------------------------------
# Application / API tests
# ---------------------------------------------------------------------------


class TestValidationApiAndScope:
    def setup_method(self):
        self.h = ValidationHarness()

    def teardown_method(self):
        self.h.close()

    def test_workbench_edit_required_viewer_forbidden(self):
        self.h.add_row("A", "1")
        client = self.h.client_as(self.h.viewer)
        r = client.post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/validate"
        )
        assert r.status_code in (401, 403)

    def test_cross_tenant_project_safe_404(self):
        self.h.add_row("A", "1")
        client = self.h.client_as(self.h.user2)
        r = client.post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/validate"
        )
        assert r.status_code == 404

    def test_wrong_project_batch_safe_404(self):
        other_batch = ProjectAssetImportBatch(
            organization_id=self.h.org.id,
            project_id=self.h.project.id,
            source_filename="x.xlsx",
            status=ImportBatchStatus.PARSED,
            created_by_user_id=self.h.user.id,
        )
        self.h.db.add(other_batch)
        self.h.db.commit()
        # batch for project2 under org2
        b2 = ProjectAssetImportBatch(
            organization_id=self.h.org2.id,
            project_id=self.h.project2.id,
            source_filename="y.xlsx",
            status=ImportBatchStatus.PARSED,
            created_by_user_id=self.h.user2.id,
        )
        self.h.db.add(b2)
        self.h.db.commit()
        client = self.h.client_as(self.h.user)
        r = client.post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{b2.id}/validate"
        )
        assert r.status_code == 404

    def test_no_body_required_and_response_shape(self):
        self.h.add_row("Máy", "2")
        client = self.h.client_as(self.h.user)
        r = client.post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/validate"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ready_for_review"
        assert body["total_rows"] == 1
        assert body["valid_rows"] == 1
        assert body["invalid_rows"] == 0
        assert body["warning_rows"] == 0
        assert "id" in body and "project_id" in body

    def test_allowed_source_states_accepted(self):
        for st in (
            ImportBatchStatus.PARSED,
            ImportBatchStatus.VALIDATION_FAILED,
            ImportBatchStatus.READY_FOR_REVIEW,
        ):
            self.h.db.query(ProjectAssetImportStagingRow).delete()
            self.h.db.commit()
            self.h.batch.status = st
            self.h.db.commit()
            self.h.add_row("OK", "1")
            client = self.h.client_as(self.h.user)
            r = client.post(
                f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/validate"
            )
            assert r.status_code == 200, st
            assert r.json()["status"] == "ready_for_review"

    def test_disallowed_states_409_zero_mutation_zero_audit(self):
        self.h.add_row("A", "1")
        for st in (
            ImportBatchStatus.CREATED,
            ImportBatchStatus.PARSING,
            ImportBatchStatus.FAILED,
            ImportBatchStatus.APPLIED,
        ):
            self.h.batch.status = st
            self.h.db.commit()
            before_audits = self.h.db.query(AuditEvent).count()
            row = (
                self.h.db.query(ProjectAssetImportStagingRow)
                .filter_by(import_batch_id=self.h.batch.id)
                .first()
            )
            old_status = row.validation_status
            client = self.h.client_as(self.h.user)
            r = client.post(
                f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/validate"
            )
            assert r.status_code == 409, st
            assert "trạng thái" in r.json()["detail"]
            self.h.db.expire_all()
            self.h.db.refresh(self.h.batch)
            assert self.h.batch.status == st
            row2 = (
                self.h.db.query(ProjectAssetImportStagingRow)
                .filter_by(import_batch_id=self.h.batch.id)
                .first()
            )
            assert row2.validation_status == old_status
            assert self.h.db.query(AuditEvent).count() == before_audits


class TestValidationStateCountersRerun:
    def setup_method(self):
        self.h = ValidationHarness()

    def teardown_method(self):
        self.h.close()

    def test_mixed_rows_exact_counters_and_ready_for_review(self):
        self.h.add_row("Good", "1")
        self.h.add_row(None, "2")
        self.h.add_row("Also", "bad")
        client = self.h.client_as(self.h.user)
        r = client.post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/validate"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ready_for_review"
        assert body["total_rows"] == 3
        assert body["valid_rows"] == 1
        assert body["invalid_rows"] == 2
        assert body["warning_rows"] == 0
        self.h.db.expire_all()
        rows = (
            self.h.db.query(ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=self.h.batch.id)
            .order_by(ProjectAssetImportStagingRow.source_row_number)
            .all()
        )
        assert rows[0].validation_status == ImportRowValidationStatus.VALID
        assert rows[1].validation_status == ImportRowValidationStatus.INVALID
        assert rows[2].validation_status == ImportRowValidationStatus.INVALID
        assert rows[0].validation_warnings == []
        # stale prior errors replaced
        assert not any(e.get("message_key") == "stale" for e in rows[0].validation_errors)
        assert not any(
            w.get("message_key") == "excel.validation.year_missing"
            for w in rows[0].validation_warnings
        )
        # proposed values unchanged
        assert rows[0].proposed_asset_name == "Good"
        assert rows[2].proposed_quantity == "bad"
        self.h.assert_line_immutable()

    def test_zero_row_batch_ready_for_review_all_zero_counters(self):
        client = self.h.client_as(self.h.user)
        r = client.post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/validate"
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ready_for_review"
        assert body["total_rows"] == 0
        assert body["valid_rows"] == body["invalid_rows"] == body["warning_rows"] == 0

    def test_rerun_replaces_and_idempotent(self):
        self.h.add_row("A", "1")
        client = self.h.client_as(self.h.user)
        url = f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/validate"
        r1 = client.post(url).json()
        r2 = client.post(url).json()
        assert r1["status"] == r2["status"] == "ready_for_review"
        assert r1["valid_rows"] == r2["valid_rows"] == 1
        events = (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=SUCCESS_EVENT)
            .count()
        )
        assert events == 2

    def test_invalid_to_valid_and_valid_to_invalid_on_rerun(self):
        row = self.h.add_row(None, "1")
        client = self.h.client_as(self.h.user)
        url = f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/validate"
        assert client.post(url).json()["invalid_rows"] == 1
        row.proposed_asset_name = "Fixed"
        self.h.db.commit()
        assert client.post(url).json()["valid_rows"] == 1
        row.proposed_asset_name = ""
        self.h.db.commit()
        assert client.post(url).json()["invalid_rows"] == 1


class TestValidationTransactionsAudits:
    def setup_method(self):
        self.h = ValidationHarness()

    def teardown_method(self):
        self.h.close()

    def _snapshot(self):
        self.h.db.expire_all()
        self.h.db.refresh(self.h.batch)
        rows = (
            self.h.db.query(ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=self.h.batch.id)
            .order_by(ProjectAssetImportStagingRow.id)
            .all()
        )
        return {
            "status": self.h.batch.status,
            "total_rows": self.h.batch.total_rows,
            "valid_rows": self.h.batch.valid_rows,
            "invalid_rows": self.h.batch.invalid_rows,
            "warning_rows": self.h.batch.warning_rows,
            "row_ids": [r.id for r in rows],
            "proposed": [(r.proposed_asset_name, r.proposed_quantity) for r in rows],
            "val_status": [r.validation_status for r in rows],
            "val_errors": [list(r.validation_errors or []) for r in rows],
            "val_warnings": [list(r.validation_warnings or []) for r in rows],
            "success_ids": [
                e.id
                for e in self.h.db.query(AuditEvent)
                .filter_by(entity_id=self.h.batch.id, event_name=SUCCESS_EVENT)
                .order_by(AuditEvent.created_at)
                .all()
            ],
            "failure_ids": [
                e.id
                for e in self.h.db.query(AuditEvent)
                .filter_by(entity_id=self.h.batch.id, event_name=FAILURE_EVENT)
                .order_by(AuditEvent.created_at)
                .all()
            ],
        }

    def _assert_generation(self, snap):
        cur = self._snapshot()
        for k in (
            "status",
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "warning_rows",
            "row_ids",
            "proposed",
            "val_status",
            "val_errors",
            "val_warnings",
        ):
            assert cur[k] == snap[k], k
        self.h.assert_line_immutable()

    def test_success_audit_payload_safe_and_complete(self):
        self.h.add_row("A", "1")
        client = self.h.client_as(self.h.user)
        client.post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/validate"
        )
        ev = (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=SUCCESS_EVENT)
            .order_by(AuditEvent.created_at.desc())
            .first()
        )
        assert ev is not None
        assert ev.command_name == "ValidateProjectAssetImportBatch"
        p = ev.payload
        for k in (
            "rule_set_version",
            "organization_id",
            "project_id",
            "batch_id",
            "source_status",
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "warning_rows",
        ):
            assert k in p
        assert p["rule_set_version"] == "s12-pr-003-v1"
        assert p["source_status"] == "parsed"
        assert "raw_values" not in p
        assert "stack" not in str(p).lower()

    def test_rule_evaluation_failure_records_exact_failure_audit(self, monkeypatch):
        self.h.add_row("A", "1")
        snap = self._snapshot()
        import app.modules.excel_import.application.validate_staging as vs

        monkeypatch.setattr(
            vs,
            "_apply_validation_to_rows",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("rule boom")),
        )
        client = self.h.client_as(self.h.user)
        r = client.post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/validate"
        )
        assert r.status_code == 500
        assert r.json()["detail"] == "Không thể kiểm tra dữ liệu Excel. Vui lòng thử lại."
        self.h.db.expire_all()
        self.h.db.refresh(self.h.batch)
        # fingerprint matched: engine failure marks validation_failed + one failure audit
        assert self.h.batch.status == ImportBatchStatus.VALIDATION_FAILED
        fails = (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=FAILURE_EVENT)
            .all()
        )
        assert len(fails) == 1
        p = fails[0].payload
        assert p["error_code"] == "validation_engine_failed"
        assert p["rule_set_version"] == "s12-pr-003-v1"
        assert set(p.keys()) >= {
            "rule_set_version",
            "organization_id",
            "project_id",
            "batch_id",
            "source_status",
            "error_code",
        }
        assert "raw_values" not in p
        # staging generation preserved except batch status/failure audit
        rows = (
            self.h.db.query(ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=self.h.batch.id)
            .order_by(ProjectAssetImportStagingRow.id)
            .all()
        )
        assert [r.id for r in rows] == snap["row_ids"]
        assert [(r.proposed_asset_name, r.proposed_quantity) for r in rows] == snap["proposed"]
        assert [r.validation_status for r in rows] == snap["val_status"]
        assert self.h.db.query(AuditEvent).filter_by(
            entity_id=self.h.batch.id, event_name=SUCCESS_EVENT
        ).count() == 0
        self.h.assert_line_immutable()

    def test_flush_failure_after_audit_preserves_generation(self, monkeypatch):
        self.h.add_row("A", "1")
        snap = self._snapshot()
        import app.modules.excel_import.application.validate_staging as vs

        orig_audit = vs._record_success_audit

        def boom_after_audit(*a, **k):
            orig_audit(*a, **k)
            raise RuntimeError("flush-equivalent fail after audit")

        monkeypatch.setattr(vs, "_record_success_audit", boom_after_audit)
        with pytest.raises(HTTPException) as exc:
            validate_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
            )
        assert exc.value.status_code == 500
        assert "Không thể kiểm tra" in str(exc.value.detail)
        self.h.db.expire_all()
        rows = (
            self.h.db.query(ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=self.h.batch.id)
            .order_by(ProjectAssetImportStagingRow.id)
            .all()
        )
        assert [r.id for r in rows] == snap["row_ids"]
        assert [(r.proposed_asset_name, r.proposed_quantity) for r in rows] == snap["proposed"]
        assert [r.validation_status for r in rows] == snap["val_status"]
        # matched fingerprint → validation_failed + one failure audit
        self.h.db.refresh(self.h.batch)
        assert self.h.batch.status == ImportBatchStatus.VALIDATION_FAILED
        assert (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=FAILURE_EVENT)
            .count()
            == 1
        )
        self.h.assert_line_immutable()

    def test_savepoint_commit_failure_preserves_generation(self, monkeypatch):
        self.h.add_row("A", "1")
        snap = self._snapshot()

        class FakeSP:
            def commit(self):
                raise RuntimeError("savepoint release fail")

            def rollback(self):
                return None

        monkeypatch.setattr(self.h.db, "begin_nested", lambda: FakeSP())
        with pytest.raises(HTTPException) as exc:
            validate_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
            )
        assert exc.value.status_code == 500
        self.h.db.expire_all()
        rows = (
            self.h.db.query(ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=self.h.batch.id)
            .order_by(ProjectAssetImportStagingRow.id)
            .all()
        )
        assert [r.id for r in rows] == snap["row_ids"]
        assert [(r.proposed_asset_name, r.proposed_quantity) for r in rows] == snap["proposed"]
        self.h.assert_line_immutable()

    def test_outer_commit_failure_exact_failure_audit(self, monkeypatch):
        self.h.add_row("A", "1")
        snap = self._snapshot()
        orig = self.h.db.commit
        fail = {"n": 0}

        def mock_commit():
            fail["n"] += 1
            if fail["n"] == 1:
                raise RuntimeError("outer commit fail")
            return orig()

        monkeypatch.setattr(self.h.db, "commit", mock_commit)
        with pytest.raises(HTTPException) as exc:
            validate_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
            )
        assert exc.value.status_code == 500
        assert "Không thể kiểm tra" in str(exc.value.detail)
        self.h.db.expire_all()
        self.h.db.refresh(self.h.batch)
        # After outer commit fail + recover with matching fingerprint
        assert self.h.batch.status == ImportBatchStatus.VALIDATION_FAILED
        fails = (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=FAILURE_EVENT)
            .all()
        )
        assert len(fails) == 1
        assert fails[0].payload["error_code"] == "validation_engine_failed"
        rows = (
            self.h.db.query(ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=self.h.batch.id)
            .order_by(ProjectAssetImportStagingRow.id)
            .all()
        )
        assert [r.id for r in rows] == snap["row_ids"]
        assert [(r.proposed_asset_name, r.proposed_quantity) for r in rows] == snap["proposed"]
        assert self.h.db.query(AuditEvent).filter_by(
            entity_id=self.h.batch.id, event_name=SUCCESS_EVENT
        ).count() == 0
        self.h.assert_line_immutable()

    def test_failure_audit_persistence_failure_preserves_pre_attempt(self, monkeypatch):
        self.h.add_row("A", "1")
        snap = self._snapshot()
        import app.modules.excel_import.application.validate_staging as vs

        monkeypatch.setattr(
            vs,
            "_apply_validation_to_rows",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("rule boom")),
        )
        monkeypatch.setattr(
            vs,
            "_record_failure_audit",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("audit fail")),
        )
        with pytest.raises(HTTPException) as exc:
            validate_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
            )
        assert exc.value.status_code == 500
        self.h.db.expire_all()
        self.h.db.refresh(self.h.batch)
        # recover also fails audit write → rollback; pre-attempt generation preserved
        assert self.h.batch.status == snap["status"]
        assert self.h.db.query(AuditEvent).filter_by(
            entity_id=self.h.batch.id, event_name=FAILURE_EVENT
        ).count() == 0
        rows = (
            self.h.db.query(ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=self.h.batch.id)
            .order_by(ProjectAssetImportStagingRow.id)
            .all()
        )
        assert [r.id for r in rows] == snap["row_ids"]
        assert [(r.proposed_asset_name, r.proposed_quantity) for r in rows] == snap["proposed"]
        assert [r.validation_status for r in rows] == snap["val_status"]
        self.h.assert_line_immutable()

    def test_stale_failure_does_not_overwrite_newer_generation(self, monkeypatch):
        self.h.add_row("A", "1")
        import app.modules.excel_import.application.validate_staging as vs

        orig_recover = vs._recover_validation_failure

        def inject_newer(*args, **kwargs):
            self.h.batch.status = ImportBatchStatus.READY_FOR_REVIEW
            self.h.batch.valid_rows = 99
            self.h.batch.total_rows = 1
            self.h.batch.invalid_rows = 0
            self.h.batch.warning_rows = 0
            self.h.db.commit()
            orig_recover(*args, **kwargs)

        monkeypatch.setattr(vs, "_recover_validation_failure", inject_newer)
        monkeypatch.setattr(
            vs,
            "_apply_validation_to_rows",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")),
        )

        with pytest.raises(HTTPException):
            validate_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
            )
        self.h.db.expire_all()
        self.h.db.refresh(self.h.batch)
        assert self.h.batch.status == ImportBatchStatus.READY_FOR_REVIEW
        assert self.h.batch.valid_rows == 99
        fails = (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=FAILURE_EVENT)
            .count()
        )
        assert fails == 0
        self.h.assert_line_immutable()


class TestProjectAssetLineImmutabilityOnValidation:
    def setup_method(self):
        self.h = ValidationHarness()

    def teardown_method(self):
        self.h.close()

    def test_immutable_on_success_and_business_invalid(self):
        self.h.add_row("Good", "1")
        self.h.add_row(None, "x")
        client = self.h.client_as(self.h.user)
        assert (
            client.post(
                f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/validate"
            ).status_code
            == 200
        )
        self.h.assert_line_immutable()


def _pg_url():
    pg = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not pg or "postgres" not in pg:
        return None
    return pg


def _xlsx(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    for r in rows:
        ws.append([str(c) if c is not None else None for c in r])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


class FakeUpload:
    def __init__(self, filename, content):
        self.filename = filename
        self.file = io.BytesIO(content)
        self.size = len(content)


class _PGSeed:
    """Shared PostgreSQL seed/cleanup for concurrency matrix."""

    def __init__(self, SessionLocal):
        self.SessionLocal = SessionLocal
        self.db = SessionLocal()
        self.ids = {}

    def seed(self, with_line=True):
        db = self.db
        uid = uuid.uuid4().hex[:8]
        org = OrganizationProfile(
            legal_name=f"PG-{uid}",
            organization_slug=f"pg-{uid}",
            status=OrganizationStatus.ACTIVE,
        )
        db.add(org)
        db.commit()
        role = Role(
            code=f"e-{uid}",
            display_name="E",
            permissions=["project:read", "workbench:edit"],
        )
        db.add(role)
        db.commit()
        user = User(
            organization_id=org.id,
            email=f"u-{uid}@t.com",
            full_name="U",
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.commit()
        db.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))
        db.commit()
        cust = Customer(
            organization_id=org.id,
            legal_name="C",
            status=CustomerStatus.ACTIVE,
            created_by=user.id,
        )
        db.add(cust)
        db.commit()
        project = Project(
            organization_id=org.id,
            customer_id=cust.id,
            code=f"PG{uid[:6]}",
            name="P",
            status=ProjectWorkflowStatus.DRAFT,
            created_by=user.id,
        )
        db.add(project)
        db.commit()
        line = None
        if with_line:
            line = ProjectAssetLine(
                project_id=project.id,
                asset_name="Official",
                quantity=1.0,
                row_version=1,
            )
            db.add(line)
            db.commit()
        batch = ProjectAssetImportBatch(
            organization_id=org.id,
            project_id=project.id,
            source_filename="pg.xlsx",
            source_sheet_name="Sheet1",
            status=ImportBatchStatus.PARSED,
            created_by_user_id=user.id,
        )
        db.add(batch)
        db.commit()
        self.ids = {
            "org": org.id,
            "role": role.id,
            "user": user.id,
            "cust": cust.id,
            "project": project.id,
            "batch": batch.id,
            "line": line.id if line else None,
            "line_name": line.asset_name if line else None,
            "line_qty": line.quantity if line else None,
            "line_ver": line.row_version if line else None,
        }
        return self.ids

    def add_rows(self, specs):
        db = self.db
        bid = self.ids["batch"]
        for i, (name, qty) in enumerate(specs):
            db.add(
                ProjectAssetImportStagingRow(
                    organization_id=self.ids["org"],
                    project_id=self.ids["project"],
                    import_batch_id=bid,
                    source_row_number=i + 1,
                    raw_values={"cells": []},
                    mapped_values={},
                    normalized_preview={},
                    validation_status=ImportRowValidationStatus.PENDING,
                    validation_errors=[],
                    validation_warnings=[],
                    proposed_asset_name=name,
                    proposed_quantity=qty,
                )
            )
        db.commit()

    def assert_line(self):
        if not self.ids.get("line"):
            return
        s = self.SessionLocal()
        try:
            line = s.query(ProjectAssetLine).filter_by(id=self.ids["line"]).one()
            assert line.asset_name == self.ids["line_name"]
            assert line.quantity == self.ids["line_qty"]
            assert line.row_version == self.ids["line_ver"]
        finally:
            s.close()

    def cleanup(self):
        s = self.SessionLocal()
        try:
            bid = self.ids["batch"]
            s.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=bid).delete()
            s.query(AuditEvent).filter(AuditEvent.entity_id == bid).delete(
                synchronize_session=False
            )
            s.query(ProjectAssetImportBatch).filter_by(id=bid).delete()
            if self.ids.get("line"):
                s.query(ProjectAssetLine).filter_by(id=self.ids["line"]).delete()
            s.query(Project).filter_by(id=self.ids["project"]).delete()
            s.query(Customer).filter_by(id=self.ids["cust"]).delete()
            s.query(UserRole).filter_by(user_id=self.ids["user"]).delete()
            s.query(User).filter_by(id=self.ids["user"]).delete()
            s.query(Role).filter_by(id=self.ids["role"]).delete()
            s.query(OrganizationProfile).filter_by(id=self.ids["org"]).delete()
            s.commit()
        finally:
            s.close()
            self.db.close()


class TestPGValidationConcurrency:
    """PostgreSQL concurrency matrix PG-A..PG-D (skip without PG)."""

    def test_pg_a_two_validations_same_batch_both_succeed(self):
        pg = _pg_url()
        if not pg:
            pytest.skip("SKIPPED LOCALLY - REQUIRES CI WITH POSTGRESQL")

        engine = create_engine(pg)
        SessionLocal = sessionmaker(bind=engine)
        seed = _PGSeed(SessionLocal)
        try:
            ids = seed.seed()
            seed.add_rows([("A0", "1"), ("A1", "1"), ("A2", "1")])
            results = []
            errors = []
            barrier = threading.Barrier(2, timeout=30)

            def worker():
                s = SessionLocal()
                try:
                    u = s.query(User).filter_by(id=ids["user"]).one()
                    barrier.wait(timeout=30)
                    out = validate_project_asset_import_batch(
                        s,
                        org_id=ids["org"],
                        project_id=ids["project"],
                        batch_id=ids["batch"],
                        current_user=u,
                    )
                    results.append(out.status)
                except Exception as e:
                    errors.append(e)
                finally:
                    s.close()

            t1 = threading.Thread(target=worker)
            t2 = threading.Thread(target=worker)
            t1.start()
            t2.start()
            t1.join(timeout=60)
            t2.join(timeout=60)
            assert not t1.is_alive() and not t2.is_alive()
            assert errors == []
            assert len(results) == 2
            assert all(
                (r == ImportBatchStatus.READY_FOR_REVIEW or r == "ready_for_review")
                for r in results
            )
            s = SessionLocal()
            try:
                b = s.query(ProjectAssetImportBatch).filter_by(id=ids["batch"]).one()
                assert b.status == ImportBatchStatus.READY_FOR_REVIEW
                assert b.total_rows == 3
                assert b.valid_rows == 3
                assert b.invalid_rows == 0
                assert b.warning_rows == 0
                rows = (
                    s.query(ProjectAssetImportStagingRow)
                    .filter_by(import_batch_id=ids["batch"])
                    .order_by(ProjectAssetImportStagingRow.id)
                    .all()
                )
                assert len(rows) == 3
                for row in rows:
                    assert row.validation_status == ImportRowValidationStatus.VALID
                    assert row.validation_errors == []
                    assert row.validation_warnings == []
                succ = (
                    s.query(AuditEvent)
                    .filter_by(entity_id=ids["batch"], event_name=SUCCESS_EVENT)
                    .count()
                )
                fail = (
                    s.query(AuditEvent)
                    .filter_by(entity_id=ids["batch"], event_name=FAILURE_EVENT)
                    .count()
                )
                assert succ == 2
                assert fail == 0
            finally:
                s.close()
            seed.assert_line()
        finally:
            seed.cleanup()

    def test_pg_b_upload_then_validation_serial_orders(self):
        pg = _pg_url()
        if not pg:
            pytest.skip("SKIPPED LOCALLY - REQUIRES CI WITH POSTGRESQL")

        engine = create_engine(pg)
        SessionLocal = sessionmaker(bind=engine)

        def run_order(upload_first: bool):
            seed = _PGSeed(SessionLocal)
            try:
                ids = seed.seed()
                seed.add_rows([("Old", "1")])
                lock_held = threading.Event()
                release = threading.Event()
                done = []
                errors = []

                def upload_worker():
                    s = SessionLocal()
                    try:
                        u = s.query(User).filter_by(id=ids["user"]).one()
                        if not upload_first:
                            lock_held.wait(timeout=30)
                        content = _xlsx([["asset_name", "quantity"], ["NewU", "9"]])
                        # Hold path: begin lock via validate or upload using orchestrator
                        if upload_first:
                            # acquire by starting upload after signaling via nested mock is hard;
                            # use FOR UPDATE in thread then call upload
                            b = (
                                s.query(ProjectAssetImportBatch)
                                .filter_by(id=ids["batch"])
                                .with_for_update()
                                .first()
                            )
                            assert b is not None
                            lock_held.set()
                            release.wait(timeout=30)
                            s.rollback()  # release advisory hold then real upload
                        upload_excel_file_orchestrator(
                            s,
                            org_id=ids["org"],
                            project_id=ids["project"],
                            batch_id=ids["batch"],
                            file=FakeUpload("n.xlsx", content),
                            request=None,
                            current_user=u,
                        )
                        done.append("upload")
                    except Exception as e:
                        errors.append(("upload", e))
                    finally:
                        s.close()

                def validate_worker():
                    s = SessionLocal()
                    try:
                        u = s.query(User).filter_by(id=ids["user"]).one()
                        if upload_first:
                            lock_held.wait(timeout=30)
                            # wait for upload hold then release so upload proceeds
                            release.set()
                        else:
                            b = (
                                s.query(ProjectAssetImportBatch)
                                .filter_by(id=ids["batch"])
                                .with_for_update()
                                .first()
                            )
                            assert b is not None
                            lock_held.set()
                            release.wait(timeout=30)
                            s.rollback()
                        validate_project_asset_import_batch(
                            s,
                            org_id=ids["org"],
                            project_id=ids["project"],
                            batch_id=ids["batch"],
                            current_user=u,
                        )
                        done.append("validate")
                    except Exception as e:
                        errors.append(("validate", e))
                    finally:
                        s.close()

                if upload_first:
                    t1 = threading.Thread(target=upload_worker)
                    t2 = threading.Thread(target=validate_worker)
                else:
                    t1 = threading.Thread(target=validate_worker)
                    t2 = threading.Thread(target=upload_worker)
                t1.start()
                t2.start()
                t1.join(timeout=90)
                t2.join(timeout=90)
                assert not t1.is_alive() and not t2.is_alive()
                assert errors == [], errors
                assert set(done) == {"upload", "validate"}
                s = SessionLocal()
                try:
                    b = s.query(ProjectAssetImportBatch).filter_by(id=ids["batch"]).one()
                    rows = (
                        s.query(ProjectAssetImportStagingRow)
                        .filter_by(import_batch_id=ids["batch"])
                        .order_by(ProjectAssetImportStagingRow.id)
                        .all()
                    )
                    if upload_first:
                        # final: validate after upload → ready_for_review on NewU
                        assert b.status == ImportBatchStatus.READY_FOR_REVIEW
                        assert b.total_rows == 1
                        assert rows[0].proposed_asset_name == "NewU"
                        assert rows[0].validation_status == ImportRowValidationStatus.VALID
                    else:
                        # final: upload after validation → parsed pending generation
                        assert b.status == ImportBatchStatus.PARSED
                        assert rows[0].proposed_asset_name == "NewU"
                        assert rows[0].validation_status == ImportRowValidationStatus.PENDING
                finally:
                    s.close()
                seed.assert_line()
            finally:
                seed.cleanup()

        run_order(upload_first=True)
        run_order(upload_first=False)

    def test_pg_c_stale_validation_failure_vs_newer_success(self):
        pg = _pg_url()
        if not pg:
            pytest.skip("SKIPPED LOCALLY - REQUIRES CI WITH POSTGRESQL")

        engine = create_engine(pg)
        SessionLocal = sessionmaker(bind=engine)
        seed = _PGSeed(SessionLocal)
        try:
            ids = seed.seed()
            seed.add_rows([("A", "1")])
            entered = threading.Event()
            release = threading.Event()
            errors = []

            import app.modules.excel_import.application.validate_staging as vs

            orig_recover = vs._recover_validation_failure

            def gated_recover(*a, **k):
                entered.set()
                release.wait(timeout=30)
                return orig_recover(*a, **k)

            # Patch in worker only via module global
            def stale_worker():
                s = SessionLocal()
                try:
                    # force rule failure after lock
                    real_apply = vs._apply_validation_to_rows

                    def boom(*a, **k):
                        raise RuntimeError("stale boom")

                    vs._apply_validation_to_rows = boom
                    vs._recover_validation_failure = gated_recover
                    u = s.query(User).filter_by(id=ids["user"]).one()
                    try:
                        validate_project_asset_import_batch(
                            s,
                            org_id=ids["org"],
                            project_id=ids["project"],
                            batch_id=ids["batch"],
                            current_user=u,
                        )
                    except HTTPException:
                        pass
                    finally:
                        vs._apply_validation_to_rows = real_apply
                        vs._recover_validation_failure = orig_recover
                except Exception as e:
                    errors.append(e)
                finally:
                    s.close()

            t = threading.Thread(target=stale_worker)
            t.start()
            assert entered.wait(timeout=30)
            # newer success on separate session
            s2 = SessionLocal()
            try:
                u = s2.query(User).filter_by(id=ids["user"]).one()
                content = _xlsx([["asset_name", "quantity"], ["Newer", "5"]])
                upload_excel_file_orchestrator(
                    s2,
                    org_id=ids["org"],
                    project_id=ids["project"],
                    batch_id=ids["batch"],
                    file=FakeUpload("newer.xlsx", content),
                    request=None,
                    current_user=u,
                )
            finally:
                s2.close()
            release.set()
            t.join(timeout=60)
            assert not t.is_alive()
            assert errors == []
            s = SessionLocal()
            try:
                b = s.query(ProjectAssetImportBatch).filter_by(id=ids["batch"]).one()
                assert b.status == ImportBatchStatus.PARSED
                assert b.source_filename == "newer.xlsx"
                rows = (
                    s.query(ProjectAssetImportStagingRow)
                    .filter_by(import_batch_id=ids["batch"])
                    .all()
                )
                assert len(rows) == 1
                assert rows[0].proposed_asset_name == "Newer"
                assert rows[0].validation_status == ImportRowValidationStatus.PENDING
                fail = (
                    s.query(AuditEvent)
                    .filter_by(entity_id=ids["batch"], event_name=FAILURE_EVENT)
                    .count()
                )
                assert fail == 0
                up = (
                    s.query(AuditEvent)
                    .filter_by(
                        entity_id=ids["batch"],
                        event_name="ProjectAssetImportBatchUploaded",
                    )
                    .count()
                )
                assert up >= 1
            finally:
                s.close()
            seed.assert_line()
        finally:
            seed.cleanup()

    def test_pg_d_different_batches_independent(self):
        pg = _pg_url()
        if not pg:
            pytest.skip("SKIPPED LOCALLY - REQUIRES CI WITH POSTGRESQL")

        engine = create_engine(pg)
        SessionLocal = sessionmaker(bind=engine)
        seed_a = _PGSeed(SessionLocal)
        seed_b = _PGSeed(SessionLocal)
        try:
            ids_a = seed_a.seed()
            seed_a.add_rows([("AA", "1")])
            ids_b = seed_b.seed()
            seed_b.add_rows([("BB", "2")])
            held = threading.Event()
            release = threading.Event()
            b_done = threading.Event()
            errors = []

            def hold_a():
                s = SessionLocal()
                try:
                    b = (
                        s.query(ProjectAssetImportBatch)
                        .filter_by(id=ids_a["batch"])
                        .with_for_update()
                        .first()
                    )
                    assert b is not None
                    held.set()
                    release.wait(timeout=30)
                    u = s.query(User).filter_by(id=ids_a["user"]).one()
                    # release lock then validate
                    s.rollback()
                    validate_project_asset_import_batch(
                        s,
                        org_id=ids_a["org"],
                        project_id=ids_a["project"],
                        batch_id=ids_a["batch"],
                        current_user=u,
                    )
                except Exception as e:
                    errors.append(e)
                finally:
                    s.close()

            def validate_b():
                s = SessionLocal()
                try:
                    held.wait(timeout=30)
                    u = s.query(User).filter_by(id=ids_b["user"]).one()
                    validate_project_asset_import_batch(
                        s,
                        org_id=ids_b["org"],
                        project_id=ids_b["project"],
                        batch_id=ids_b["batch"],
                        current_user=u,
                    )
                    b_done.set()
                except Exception as e:
                    errors.append(e)
                finally:
                    s.close()

            t_a = threading.Thread(target=hold_a)
            t_b = threading.Thread(target=validate_b)
            t_a.start()
            t_b.start()
            assert b_done.wait(timeout=30), "batch B should complete while A still holds lock"
            release.set()
            t_a.join(timeout=60)
            t_b.join(timeout=60)
            assert not t_a.is_alive() and not t_b.is_alive()
            assert errors == []
            s = SessionLocal()
            try:
                ba = s.query(ProjectAssetImportBatch).filter_by(id=ids_a["batch"]).one()
                bb = s.query(ProjectAssetImportBatch).filter_by(id=ids_b["batch"]).one()
                assert ba.status == ImportBatchStatus.READY_FOR_REVIEW
                assert bb.status == ImportBatchStatus.READY_FOR_REVIEW
                assert ba.valid_rows == 1 and bb.valid_rows == 1
                # no cross contamination of audits
                for bid in (ids_a["batch"], ids_b["batch"]):
                    assert (
                        s.query(AuditEvent)
                        .filter_by(entity_id=bid, event_name=SUCCESS_EVENT)
                        .count()
                        == 1
                    )
            finally:
                s.close()
            seed_a.assert_line()
            seed_b.assert_line()
        finally:
            seed_a.cleanup()
            seed_b.cleanup()
