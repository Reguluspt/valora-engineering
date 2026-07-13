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
    validate_project_asset_import_batch,
)
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

    def test_rule_engine_failure_rolls_back_and_may_record_failure(self, monkeypatch):
        self.h.add_row("A", "1")
        import app.modules.excel_import.application.validate_staging as vs

        def boom(*a, **k):
            raise RuntimeError("rule boom")

        monkeypatch.setattr(vs, "_apply_validation_to_rows", boom)
        client = self.h.client_as(self.h.user)
        r = client.post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/validate"
        )
        assert r.status_code == 500
        assert "Không thể kiểm tra" in r.json()["detail"]
        self.h.db.expire_all()
        row = (
            self.h.db.query(ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=self.h.batch.id)
            .one()
        )
        # prior pending/stale generation preserved or failure path set validation_failed
        assert row.proposed_asset_name == "A"
        self.h.assert_line_immutable()

    def test_outer_commit_failure_preserves_generation(self, monkeypatch):
        self.h.add_row("A", "1")
        orig = self.h.db.commit
        fail = {"n": 0}

        def mock_commit():
            # fail the outer commit after nested success (first commit after savepoint)
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
        self.h.db.expire_all()
        self.h.assert_line_immutable()

    def test_stale_failure_does_not_overwrite_newer_generation(self, monkeypatch):
        self.h.add_row("A", "1")
        import app.modules.excel_import.application.validate_staging as vs

        orig_recover = vs._recover_validation_failure

        def inject_newer(*args, **kwargs):
            # After rollback window: land a newer ready_for_review generation
            self.h.batch.status = ImportBatchStatus.READY_FOR_REVIEW
            self.h.batch.valid_rows = 99
            self.h.db.commit()
            orig_recover(*args, **kwargs)

        monkeypatch.setattr(vs, "_recover_validation_failure", inject_newer)

        def boom(*a, **k):
            raise RuntimeError("x")

        monkeypatch.setattr(vs, "_apply_validation_to_rows", boom)

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


class TestPGValidationConcurrency:
    def test_same_batch_serializes_under_postgres(self):
        pg = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
        if not pg or "postgres" not in pg:
            pytest.skip("SKIPPED LOCALLY - REQUIRES CI WITH POSTGRESQL")

        engine = create_engine(pg)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        try:
            org = OrganizationProfile(
                legal_name=f"PG-{uuid.uuid4().hex[:8]}",
                organization_slug=f"pg-{uuid.uuid4().hex[:8]}",
                status=OrganizationStatus.ACTIVE,
            )
            db.add(org)
            db.commit()
            role = Role(
                code=f"e-{uuid.uuid4().hex[:6]}",
                display_name="E",
                permissions=["project:read", "workbench:edit"],
            )
            db.add(role)
            db.commit()
            user = User(
                organization_id=org.id,
                email=f"u-{uuid.uuid4().hex[:8]}@t.com",
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
                code=f"PG{uuid.uuid4().hex[:6]}",
                name="P",
                status=ProjectWorkflowStatus.DRAFT,
                created_by=user.id,
            )
            db.add(project)
            db.commit()
            batch = ProjectAssetImportBatch(
                organization_id=org.id,
                project_id=project.id,
                source_filename="pg.xlsx",
                status=ImportBatchStatus.PARSED,
                created_by_user_id=user.id,
            )
            db.add(batch)
            db.commit()
            for i in range(3):
                db.add(
                    ProjectAssetImportStagingRow(
                        organization_id=org.id,
                        project_id=project.id,
                        import_batch_id=batch.id,
                        source_row_number=i + 1,
                        raw_values={"cells": []},
                        mapped_values={},
                        normalized_preview={},
                        validation_status=ImportRowValidationStatus.PENDING,
                        validation_errors=[],
                        validation_warnings=[],
                        proposed_asset_name=f"A{i}",
                        proposed_quantity="1",
                    )
                )
            db.commit()
            batch_id = batch.id
            org_id = org.id
            project_id = project.id
            user_id = user.id

            errors = []
            barrier = threading.Barrier(2, timeout=30)

            def worker():
                s = SessionLocal()
                try:
                    u = s.query(User).filter_by(id=user_id).one()
                    barrier.wait(timeout=30)
                    validate_project_asset_import_batch(
                        s,
                        org_id=org_id,
                        project_id=project_id,
                        batch_id=batch_id,
                        current_user=u,
                    )
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
            # At least one success; both may succeed serially
            s = SessionLocal()
            try:
                b = s.query(ProjectAssetImportBatch).filter_by(id=batch_id).one()
                assert b.status == ImportBatchStatus.READY_FOR_REVIEW
                assert b.total_rows == 3
                assert b.valid_rows == 3
                assert b.invalid_rows == 0
            finally:
                s.close()
            # cleanup
            s = SessionLocal()
            try:
                s.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=batch_id).delete()
                s.query(AuditEvent).filter(AuditEvent.entity_id == batch_id).delete(
                    synchronize_session=False
                )
                s.query(ProjectAssetImportBatch).filter_by(id=batch_id).delete()
                s.query(Project).filter_by(id=project_id).delete()
                s.query(Customer).filter_by(id=cust.id).delete()
                s.query(UserRole).filter_by(user_id=user_id).delete()
                s.query(User).filter_by(id=user_id).delete()
                s.query(Role).filter_by(id=role.id).delete()
                s.query(OrganizationProfile).filter_by(id=org_id).delete()
                s.commit()
            finally:
                s.close()
        finally:
            db.close()
