"""S12-PR-004 proof-matrix integrity: M-1..M-5 executable evidence."""
from __future__ import annotations

import io
import os
import threading
import time
import uuid
from decimal import Decimal

import openpyxl
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.api.projects import archive_project
from app.modules.excel_import.application.apply_staging import (
    COMMAND_NAME,
    CONTRACT_VERSION,
    ERR_NOT_DRAFT,
    ERR_STATE,
    FAILURE_EVENT,
    SUCCESS_EVENT,
    VALIDATION_SUCCESS_EVENT,
    apply_project_asset_import_batch,
)
from app.modules.excel_import.application.import_service import (
    upload_excel_file_orchestrator,
)
from app.modules.excel_import.application.validate_staging import (
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
    ReferenceStatus,
    Role,
    Unit,
    User,
    UserRole,
    UserStatus,
)
from tests.test_s12_pr_004_acceptance_closure import official_line_snapshot
from tests.test_s12_pr_004_staging_apply import ApplyHarness


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

PG_NODE_IDS = (
    "pg_apply_vs_apply_lock_wait",
    "pg_upload_holds_apply_waits",
    "pg_apply_holds_upload_waits",
    "pg_validate_holds_apply_waits",
    "pg_apply_holds_validate_waits",
    "pg_workflow_holds_apply_waits",
    "pg_apply_holds_workflow_waits",
)

APPLY_SUCCESS_PAYLOAD_KEYS = frozenset(
    {
        "contract_version",
        "organization_id",
        "project_id",
        "batch_id",
        "source_status",
        "target_status",
        "total_rows",
        "created_count",
    }
)
APPLY_FAILURE_PAYLOAD_KEYS = frozenset(
    {
        "contract_version",
        "organization_id",
        "project_id",
        "batch_id",
        "source_status",
        "error_code",
    }
)


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
    raise AssertionError(f"pid={pid} never Lock-waited; last={last}")


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


class SlowUpload:
    """Real UploadFile-like object that blocks first read so upload holds locks."""

    def __init__(self, filename, content, entered, release):
        self.filename = filename
        self._bio = io.BytesIO(content)
        self.size = len(content)
        self.entered = entered
        self.release = release
        self._once = False
        self.file = self

    def read(self, size=-1):
        if not self._once:
            self._once = True
            self.entered.set()
            assert self.release.wait(timeout=30)
        return self._bio.read(size)


def audit_tuples(db, entity_id):
    """Ordered audit evidence tuples (name, command, entity, actor, org, corr, payload_keys)."""
    rows = (
        db.query(AuditEvent)
        .filter(AuditEvent.entity_id == entity_id)
        .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
        .all()
    )
    out = []
    for e in rows:
        keys = frozenset((e.payload or {}).keys())
        out.append(
            (
                e.event_name,
                e.command_name,
                e.entity_type,
                e.actor_user_id,
                e.organization_id,
                e.correlation_id,
                keys,
            )
        )
    return out


def assert_apply_success_audit(db, batch_id, *, actor_id, org_id, project_id):
    rows = (
        db.query(AuditEvent)
        .filter_by(entity_id=batch_id, event_name=SUCCESS_EVENT)
        .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
        .all()
    )
    assert len(rows) == 1
    e = rows[0]
    assert e.command_name == COMMAND_NAME
    assert e.entity_type == "ProjectAssetImportBatch"
    assert e.actor_user_id == actor_id
    assert e.organization_id == org_id
    payload = e.payload or {}
    assert frozenset(payload.keys()) == APPLY_SUCCESS_PAYLOAD_KEYS
    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["organization_id"] == str(org_id)
    assert payload["project_id"] == str(project_id)
    assert payload["batch_id"] == str(batch_id)
    assert payload["target_status"] == ImportBatchStatus.APPLIED.value
    return e


def assert_no_failure_audit(db, batch_id):
    assert (
        db.query(AuditEvent)
        .filter_by(entity_id=batch_id, event_name=FAILURE_EVENT)
        .count()
        == 0
    )


def assert_apply_success_count(db, batch_id, n=1):
    assert (
        db.query(AuditEvent)
        .filter_by(entity_id=batch_id, event_name=SUCCESS_EVENT)
        .count()
        == n
    )


def assert_apply_failure_count(db, batch_id, n=0):
    assert (
        db.query(AuditEvent)
        .filter_by(entity_id=batch_id, event_name=FAILURE_EVENT)
        .count()
        == n
    )


def _http_error_code(exc) -> str | None:
    if not isinstance(exc, HTTPException):
        return None
    detail = exc.detail
    if isinstance(detail, dict):
        return detail.get("error_code")
    return None


def _assert_http_error(errors, role, *, status, error_code=None):
    """Exactly one error for role with exact HTTP status and optional domain code."""
    role_errors = [e for e in errors if e[0] == role]
    assert len(role_errors) == 1, f"expected one {role!r} error, got {errors!r}"
    other = [e for e in errors if e[0] != role]
    assert other == [], f"unexpected errors outside {role!r}: {other!r}"
    exc = role_errors[0][1]
    assert isinstance(exc, HTTPException), exc
    assert exc.status_code == status, (exc.status_code, exc.detail)
    if error_code is not None:
        assert _http_error_code(exc) == error_code, exc.detail


def _assert_results_exact(results, expected):
    assert sorted(results) == sorted(expected), results


def _assert_holder_no_error(errors, role):
    assert not any(e[0] == role for e in errors), errors


def _assert_imported_lineage(db, ids, *, count=1):
    lines = (
        db.query(ProjectAssetLine)
        .filter_by(source_import_batch_id=ids["batch"])
        .order_by(ProjectAssetLine.id.asc())
        .all()
    )
    assert len(lines) == count
    if count == 1:
        assert lines[0].source_staging_row_id == ids["staging"]
        assert lines[0].source_import_batch_id == ids["batch"]
    return lines


def _assert_manual_immutable(db, seed):
    m = db.query(ProjectAssetLine).filter_by(id=seed.ids["manual"]).one()
    assert official_line_snapshot(m) == seed.manual_snap


def _assert_batch_generation(
    db,
    ids,
    *,
    status,
    filename="x.xlsx",
    sheet="Sheet1",
    total_rows=1,
    valid_rows=1,
    invalid_rows=0,
    warning_rows=0,
):
    b = db.query(ProjectAssetImportBatch).filter_by(id=ids["batch"]).one()
    assert b.status == status
    assert b.source_filename == filename
    assert b.source_sheet_name == sheet
    assert b.total_rows == total_rows
    assert b.valid_rows == valid_rows
    assert b.invalid_rows == invalid_rows
    assert b.warning_rows == warning_rows
    return b


# Expected outcome matrix (ADR 0029 lock order + production contracts; not soft dual-state):
# 1 apply vs apply: holder ok; waiter 409/apply_state_not_allowed; 1 imported line; 1 success audit
# 2 upload holds apply: upload ok; apply 409/apply_state_not_allowed; 0 imported; 0 apply audits
# 3 apply holds upload: apply ok; upload 409; applied generation x.xlsx; 1 line; 1 success audit
# 4 validate holds apply: both ok; applied; validation-success audit before apply-success
# 5 apply holds validate: apply ok; validate 409; applied; 1 line; 1 success audit
# 6 workflow holds apply: archive ok; apply 400/apply_project_not_draft; ready_for_review; 0 lines
# 7 apply holds workflow: both ok; archived+applied; apply success before ProjectArchived


# ---------------------------------------------------------------------------
# M-5 — mapping assertions (SQLite)
# ---------------------------------------------------------------------------


class TestM5MappingAssertions:
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
        "price,expect",
        [
            (None, None),
            ("", None),
            ("0", Decimal("0")),
            ("0.00", Decimal("0.00")),
            ("1.12", Decimal("1.12")),
            ("1.10", Decimal("1.10")),
            ("1234567890123", Decimal("1234567890123")),
            ("1e2", Decimal("100")),
            ("1.23e1", Decimal("12.3")),
        ],
    )
    def test_raw_price_exact_decimal(self, price, expect):
        pre = official_line_snapshot(self.h.manual)
        self.h.add_row(name="N", price=price)
        r = self._apply()
        assert r.status_code == 200, r.text
        line = (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .one()
        )
        if expect is None:
            assert line.raw_price is None
        else:
            assert Decimal(str(line.raw_price)) == expect
        self.h.db.expire_all()
        assert (
            official_line_snapshot(
                self.h.db.query(ProjectAssetLine).filter_by(id=pre["id"]).one()
            )
            == pre
        )

    @pytest.mark.parametrize(
        "price",
        ["1.123", "1e20", "1.23e-1", "-1", "NaN", "Infinity", "-Infinity"],
    )
    def test_raw_price_reject_no_rounding(self, price):
        pre = official_line_snapshot(self.h.manual)
        self.h.add_row(name="N", price=price)
        r = self._apply()
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "apply_mapping_invalid"
        assert (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .count()
            == 0
        )
        self.h.db.expire_all()
        assert (
            official_line_snapshot(
                self.h.db.query(ProjectAssetLine).filter_by(id=pre["id"]).one()
            )
            == pre
        )

    @pytest.mark.parametrize(
        "qty,expect",
        [
            (None, Decimal("1.0000")),
            ("", Decimal("1.0000")),
            ("0", Decimal("0")),
            ("1.1234", Decimal("1.1234")),
            ("1e3", Decimal("1000")),
            ("1.5e1", Decimal("15")),
        ],
    )
    def test_quantity_exact_decimal(self, qty, expect):
        pre = official_line_snapshot(self.h.manual)
        self.h.add_row(name="N", qty=qty)
        r = self._apply()
        assert r.status_code == 200, r.text
        line = (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .one()
        )
        assert Decimal(str(line.quantity)) == expect
        self.h.db.expire_all()
        assert (
            official_line_snapshot(
                self.h.db.query(ProjectAssetLine).filter_by(id=pre["id"]).one()
            )
            == pre
        )

    @pytest.mark.parametrize(
        "qty",
        ["1.12345", "1e20", "1.23e-5", "-1", "NaN", "Infinity"],
    )
    def test_quantity_reject(self, qty):
        pre = official_line_snapshot(self.h.manual)
        self.h.add_row(name="N", qty=qty)
        assert self._apply().status_code == 400
        self.h.db.expire_all()
        assert (
            official_line_snapshot(
                self.h.db.query(ProjectAssetLine).filter_by(id=pre["id"]).one()
            )
            == pre
        )

    def test_accent_preserved_exact_match_only(self):
        pre = official_line_snapshot(self.h.manual)
        # Dedicated unit: accented display that is not reachable via unaccented code
        accented = Unit(
            code="ACC1",
            display_name="Mét",
            symbol="m²",
            status=ReferenceStatus.ACTIVE,
        )
        self.h.db.add(accented)
        self.h.db.commit()
        self.h.add_row(name="Máy bơm", unit="Mét")
        r = self._apply()
        assert r.status_code == 200
        line = (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .one()
        )
        assert line.asset_name == "Máy bơm"
        assert line.unit_id == accented.id

        def _reset_ready():
            self.h.db.query(ProjectAssetImportStagingRow).delete()
            self.h.db.query(ProjectAssetLine).filter_by(
                source_import_batch_id=self.h.batch.id
            ).delete()
            self.h.db.commit()
            self.h.batch.status = ImportBatchStatus.READY_FOR_REVIEW
            self.h.batch.total_rows = 0
            self.h.batch.valid_rows = 0
            self.h.db.commit()

        # Accent-folded near-match (Met vs Mét) must not match
        _reset_ready()
        self.h.add_row(name="N2", unit="Met")
        assert self._apply().status_code == 400
        # Substring near-match
        _reset_ready()
        self.h.add_row(name="N3", unit="Mé")
        assert self._apply().status_code == 400
        # Fuzzy spacing/punctuation near-match
        _reset_ready()
        self.h.add_row(name="N4", unit="M e t")
        assert self._apply().status_code == 400
        self.h.db.expire_all()
        assert (
            official_line_snapshot(
                self.h.db.query(ProjectAssetLine).filter_by(id=pre["id"]).one()
            )
            == pre
        )

    def test_forbidden_inputs_explicit_defaults(self):
        pre = official_line_snapshot(self.h.manual)
        self.h.add_row(name="N")
        row = (
            self.h.db.query(ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=self.h.batch.id)
            .one()
        )
        row.proposed_appraised_unit_price = "99999.99"
        row.proposed_review_status = "accepted"
        row.proposed_validation_status = "valid"
        row.raw_values = {"cells": [{"value": "SECRET"}], "evil": True}
        row.mapped_values = {"unregistered": "x", "appraised_unit_price": "1"}
        self.h.db.commit()
        r = self._apply()
        assert r.status_code == 200
        line = (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .one()
        )
        assert line.appraised_unit_price is None
        assert (
            line.review_status == "pending"
            or getattr(line.review_status, "value", None) == "pending"
        )
        assert (
            line.validation_status == "unvalidated"
            or getattr(line.validation_status, "value", None) == "unvalidated"
        )
        assert line.asset_name == "N"
        self.h.db.expire_all()
        assert (
            official_line_snapshot(
                self.h.db.query(ProjectAssetLine).filter_by(id=pre["id"]).one()
            )
            == pre
        )
        assert_apply_success_audit(
            self.h.db,
            self.h.batch.id,
            actor_id=self.h.user.id,
            org_id=self.h.org.id,
            project_id=self.h.project.id,
        )


# ---------------------------------------------------------------------------
# M-3 — real stale-generation recovery
# ---------------------------------------------------------------------------


class TestM3StaleGenerationRecovery:
    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()

    def _snapshot_generation(self):
        self.h.db.expire_all()
        b = self.h.db.query(ProjectAssetImportBatch).filter_by(id=self.h.batch.id).one()
        rows = (
            self.h.db.query(ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=b.id)
            .order_by(
                ProjectAssetImportStagingRow.source_row_number,
                ProjectAssetImportStagingRow.id,
            )
            .all()
        )
        audits = (
            self.h.db.query(AuditEvent)
            .filter(AuditEvent.entity_id == b.id)
            .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
            .all()
        )
        lines = (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=b.id)
            .order_by(ProjectAssetLine.id)
            .all()
        )
        return {
            "project_status": (
                self.h.project.status.value
                if hasattr(self.h.project.status, "value")
                else self.h.project.status
            ),
            "batch_status": b.status.value if hasattr(b.status, "value") else b.status,
            "source_filename": b.source_filename,
            "source_sheet_name": b.source_sheet_name,
            "total_rows": b.total_rows,
            "valid_rows": b.valid_rows,
            "invalid_rows": b.invalid_rows,
            "warning_rows": b.warning_rows,
            "staging": [
                (
                    r.id,
                    r.source_row_number,
                    r.proposed_asset_name,
                    r.proposed_quantity,
                    r.validation_status.value
                    if hasattr(r.validation_status, "value")
                    else r.validation_status,
                    list(r.validation_errors or []),
                    list(r.validation_warnings or []),
                )
                for r in rows
            ],
            "audit_ids": [(a.id, a.event_name) for a in audits],
            "success_ids": [a.id for a in audits if a.event_name == SUCCESS_EVENT],
            "failure_ids": [a.id for a in audits if a.event_name == FAILURE_EVENT],
            "upload_ids": [
                a.id
                for a in audits
                if a.event_name == "ProjectAssetImportBatchUploaded"
            ],
            "validation_ids": [
                a.id
                for a in audits
                if a.event_name == "ProjectAssetImportBatchValidationSucceeded"
            ],
            "lines": [
                (
                    ln.id,
                    ln.asset_name,
                    ln.source_import_batch_id,
                    ln.source_staging_row_id,
                )
                for ln in lines
            ],
        }

    def test_stale_after_newer_upload(self, monkeypatch):
        import app.modules.excel_import.application.apply_staging as ap

        pre_manual = official_line_snapshot(self.h.manual)
        self.h.add_row(name="Old", qty="1")
        newer = {}
        orig = ap._recover_apply_failure

        def inject(*a, **k):
            content = _xlsx([["asset_name", "quantity"], ["Uploaded", "7"]])
            upload_excel_file_orchestrator(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                file=FakeUpload("newer.xlsx", content),
                request=None,
                current_user=self.h.user,
            )
            # re-validate so counters/validation outputs are complete generation
            validate_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
            )
            newer.update(self._snapshot_generation())
            return orig(*a, **k)

        monkeypatch.setattr(ap, "_recover_apply_failure", inject)
        monkeypatch.setattr(
            ap,
            "_map_row",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("force fail")),
        )
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
        final = self._snapshot_generation()
        assert newer, "newer generation must be captured"
        for k in newer:
            assert final[k] == newer[k], k
        assert final["source_filename"] == "newer.xlsx"
        assert final["failure_ids"] == []
        assert len(final["success_ids"]) == 0
        assert (
            official_line_snapshot(
                self.h.db.query(ProjectAssetLine).filter_by(id=pre_manual["id"]).one()
            )
            == pre_manual
        )

    def test_stale_after_newer_validation(self, monkeypatch):
        import app.modules.excel_import.application.apply_staging as ap

        pre_manual = official_line_snapshot(self.h.manual)
        self.h.add_row(name="Old", qty="1")
        # seed upload audit for fingerprint completeness
        from app.core.audit import log_audit_event

        log_audit_event(
            db=self.h.db,
            event_name="ProjectAssetImportBatchUploaded",
            entity_type="ProjectAssetImportBatch",
            entity_id=self.h.batch.id,
            organization_id=self.h.org.id,
            actor_user_id=self.h.user.id,
            command_name="UploadProjectAssetImportBatch",
            payload={"contract_version": "seed"},
        )
        self.h.db.commit()
        newer = {}
        orig = ap._recover_apply_failure

        def inject(*a, **k):
            # mutate proposed values then re-validate (complete validation generation)
            row = (
                self.h.db.query(ProjectAssetImportStagingRow)
                .filter_by(import_batch_id=self.h.batch.id)
                .one()
            )
            row.proposed_asset_name = "Validated"
            row.proposed_quantity = "9"
            self.h.db.commit()
            validate_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
            )
            newer.update(self._snapshot_generation())
            return orig(*a, **k)

        monkeypatch.setattr(ap, "_recover_apply_failure", inject)
        monkeypatch.setattr(
            ap,
            "_map_row",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("force fail")),
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
        final = self._snapshot_generation()
        assert newer
        for k in newer:
            assert final[k] == newer[k], k
        assert any(t[2] == "Validated" for t in final["staging"])
        assert final["failure_ids"] == []
        assert len(final["validation_ids"]) >= 1
        assert (
            official_line_snapshot(
                self.h.db.query(ProjectAssetLine).filter_by(id=pre_manual["id"]).one()
            )
            == pre_manual
        )

    def test_stale_after_newer_apply(self, monkeypatch):
        import app.modules.excel_import.application.apply_staging as ap

        pre_manual = official_line_snapshot(self.h.manual)
        self.h.add_row(name="ApplyMe", qty="2", unit="CAI")
        newer = {}
        real_map = ap._map_row
        real_recover = ap._recover_apply_failure

        def boom_map(*a, **k):
            raise RuntimeError("force fail")

        def inject(*a, **k):
            # StaticPool shares one connection: complete newer Apply on the same session.
            monkeypatch.setattr(ap, "_map_row", real_map)
            apply_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
                confirm=True,
            )
            newer.update(self._snapshot_generation())
            return real_recover(*a, **k)

        monkeypatch.setattr(ap, "_map_row", boom_map)
        monkeypatch.setattr(ap, "_recover_apply_failure", inject)
        with pytest.raises(HTTPException):
            apply_project_asset_import_batch(
                self.h.db,
                org_id=self.h.org.id,
                project_id=self.h.project.id,
                batch_id=self.h.batch.id,
                current_user=self.h.user,
                confirm=True,
            )
        final = self._snapshot_generation()
        assert newer
        for k in newer:
            assert final[k] == newer[k], k
        assert final["batch_status"] == ImportBatchStatus.APPLIED.value
        assert len(final["lines"]) == 1
        assert final["lines"][0][1] == "ApplyMe"
        assert final["lines"][0][2] == self.h.batch.id
        assert final["lines"][0][3] is not None
        assert len(final["success_ids"]) == 1
        assert final["failure_ids"] == []
        assert (
            official_line_snapshot(
                self.h.db.query(ProjectAssetLine).filter_by(id=pre_manual["id"]).one()
            )
            == pre_manual
        )


# ---------------------------------------------------------------------------
# M-4 — precondition rejections use full snapshot
# ---------------------------------------------------------------------------


class TestM4PreconditionSnapshots:
    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()

    def test_confirm_required_preserves_manual(self):
        pre = official_line_snapshot(self.h.manual)
        self.h.add_row()
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": False},
        )
        assert r.status_code == 400
        self.h.db.expire_all()
        assert (
            official_line_snapshot(
                self.h.db.query(ProjectAssetLine).filter_by(id=pre["id"]).one()
            )
            == pre
        )

    def test_not_draft_preserves_manual(self):
        pre = official_line_snapshot(self.h.manual)
        self.h.project.status = ProjectWorkflowStatus.SUBMITTED
        self.h.db.commit()
        self.h.add_row()
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 400
        self.h.db.expire_all()
        assert (
            official_line_snapshot(
                self.h.db.query(ProjectAssetLine).filter_by(id=pre["id"]).one()
            )
            == pre
        )


# ---------------------------------------------------------------------------
# M-2 — executable migration proof (PostgreSQL throwaway database)
# ---------------------------------------------------------------------------

LINEAGE_PARENT_REV = "db5977424e7b"
LINEAGE_HEAD_REV = "e1f2a3b4c5d6"
LINEAGE_COL_BATCH = "source_import_batch_id"
LINEAGE_COL_STAGING = "source_staging_row_id"


def _make_url(pg_url: str):
    from sqlalchemy.engine.url import make_url

    return make_url(pg_url)


def _point_alembic_settings_at(pg_url: str) -> dict:
    """Alembic env.py reads get_settings().database_url (POSTGRES_* env)."""
    from app.core.config import get_settings

    u = _make_url(pg_url)
    keys = {
        "POSTGRES_HOST": u.host or "localhost",
        "POSTGRES_PORT": str(u.port or 5432),
        "POSTGRES_DB": u.database,
        "POSTGRES_USER": u.username or "valora",
        "POSTGRES_PASSWORD": u.password or "",
    }
    prev = {k: os.environ.get(k) for k in keys}
    for k, v in keys.items():
        os.environ[k] = "" if v is None else str(v)
    get_settings.cache_clear()
    return prev


def _restore_env(prev: dict) -> None:
    from app.core.config import get_settings

    for k, v in prev.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    get_settings.cache_clear()


def _assert_no_lineage_artifacts(engine) -> None:
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("project_asset_lines")}
    assert LINEAGE_COL_BATCH not in cols
    assert LINEAGE_COL_STAGING not in cols
    fks = insp.get_foreign_keys("project_asset_lines")
    for fk in fks:
        constrained = fk.get("constrained_columns") or []
        assert LINEAGE_COL_BATCH not in constrained
        assert LINEAGE_COL_STAGING not in constrained
    for idx in insp.get_indexes("project_asset_lines"):
        col_names = idx.get("column_names") or []
        assert LINEAGE_COL_BATCH not in col_names
        assert LINEAGE_COL_STAGING not in col_names


def _assert_lineage_artifacts_at_head(engine) -> None:
    insp = inspect(engine)
    cols = {c["name"]: c for c in insp.get_columns("project_asset_lines")}
    assert LINEAGE_COL_BATCH in cols
    assert LINEAGE_COL_STAGING in cols
    assert cols[LINEAGE_COL_BATCH]["nullable"] is True
    assert cols[LINEAGE_COL_STAGING]["nullable"] is True

    fks = insp.get_foreign_keys("project_asset_lines")
    batch_fk = [
        f
        for f in fks
        if LINEAGE_COL_BATCH in (f.get("constrained_columns") or [])
    ]
    staging_fk = [
        f
        for f in fks
        if LINEAGE_COL_STAGING in (f.get("constrained_columns") or [])
    ]
    assert batch_fk, fks
    assert staging_fk, fks
    for fk in batch_fk + staging_fk:
        opts = fk.get("options") or {}
        ondelete = (opts.get("ondelete") or fk.get("ondelete") or "").upper()
        assert ondelete == "RESTRICT", fk

    idxs = insp.get_indexes("project_asset_lines")
    staging_idx = [
        i
        for i in idxs
        if LINEAGE_COL_STAGING in (i.get("column_names") or [])
    ]
    assert any(i.get("unique") for i in staging_idx), idxs
    batch_idx = [
        i for i in idxs if LINEAGE_COL_BATCH in (i.get("column_names") or [])
    ]
    assert batch_idx, idxs


def _run_lineage_dml_proof(engine) -> None:
    SessionLocal = sessionmaker(bind=engine)
    s = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        org = OrganizationProfile(
            legal_name=f"M2{uid}",
            organization_slug=f"m2{uid}",
            status=OrganizationStatus.ACTIVE,
        )
        s.add(org)
        s.commit()
        role = Role(
            code=f"m2{uid}",
            display_name="R",
            permissions=["workbench:edit"],
        )
        s.add(role)
        s.commit()
        user = User(
            organization_id=org.id,
            email=f"m2{uid}@t.com",
            full_name="U",
            status=UserStatus.ACTIVE,
        )
        s.add(user)
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
            code=f"M2{uid[:6]}",
            name="P",
            status=ProjectWorkflowStatus.DRAFT,
            created_by=user.id,
        )
        s.add(project)
        s.commit()
        batch = ProjectAssetImportBatch(
            organization_id=org.id,
            project_id=project.id,
            source_filename="m.xlsx",
            source_sheet_name="Sheet1",
            status=ImportBatchStatus.APPLIED,
            total_rows=1,
            valid_rows=1,
            invalid_rows=0,
            warning_rows=0,
            created_by_user_id=user.id,
        )
        s.add(batch)
        s.commit()
        staging = ProjectAssetImportStagingRow(
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
            proposed_asset_name="L",
            proposed_quantity="1",
        )
        s.add(staging)
        s.commit()
        line = ProjectAssetLine(
            project_id=project.id,
            asset_name="Imported",
            quantity=1,
            source_import_batch_id=batch.id,
            source_staging_row_id=staging.id,
        )
        manual = ProjectAssetLine(
            project_id=project.id,
            asset_name="Manual",
            quantity=1,
            source_import_batch_id=None,
            source_staging_row_id=None,
        )
        s.add_all([line, manual])
        s.commit()
        s.refresh(manual)
        assert manual.source_import_batch_id is None
        assert manual.source_staging_row_id is None

        with pytest.raises(Exception):
            s.query(ProjectAssetImportBatch).filter_by(id=batch.id).delete()
            s.commit()
        s.rollback()

        with pytest.raises(Exception):
            s.query(ProjectAssetImportStagingRow).filter_by(id=staging.id).delete()
            s.commit()
        s.rollback()

        dup = ProjectAssetLine(
            project_id=project.id,
            asset_name="Dup",
            quantity=1,
            source_import_batch_id=batch.id,
            source_staging_row_id=staging.id,
        )
        s.add(dup)
        with pytest.raises(Exception):
            s.commit()
        s.rollback()
    finally:
        s.close()


class TestM2ExecutableMigration:
    def test_lineage_migration_upgrade_downgrade_restrict_unique(self):
        """Real Alembic upgrade/downgrade on a throwaway PostgreSQL database.

        Cycle:
          CREATE DATABASE
          → alembic upgrade parent
          → assert no lineage artifacts
          → alembic upgrade head
          → inspect + DML RESTRICT/unique
          → alembic downgrade parent
          → assert lineage removed
          → alembic upgrade head
          → assert lineage restored
          → DROP DATABASE
        """
        pg = _pg_url()
        if not pg:
            pytest.skip(
                "SKIPPED LOCALLY - REQUIRES CI WITH POSTGRESQL "
                "(m2_lineage_migration_upgrade_downgrade)"
            )

        from alembic import command
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        base = _make_url(pg)
        db_name = f"s12pr004_m2_{uuid.uuid4().hex[:12]}"
        admin_url = base.set(database="postgres")
        isolated_url = base.set(database=db_name)
        isolated_url_str = isolated_url.render_as_string(hide_password=False)

        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        isolated_engine = None
        created = False
        prev_env: dict = {}
        try:
            try:
                with admin_engine.connect() as conn:
                    conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                created = True
            except Exception as exc:
                pytest.fail(
                    "BLOCKER: cannot CREATE throwaway PostgreSQL database for "
                    f"isolated Alembic proof (db={db_name!r}): {exc!r}. "
                    "Do not fall back to shared/public inspect or schema-only "
                    "placeholder proofs."
                )

            prev_env = _point_alembic_settings_at(isolated_url_str)
            cfg = Config("alembic.ini")
            script = ScriptDirectory.from_config(cfg)
            assert script.get_heads() == [LINEAGE_HEAD_REV]
            rev = script.get_revision(LINEAGE_HEAD_REV)
            assert rev.down_revision == LINEAGE_PARENT_REV

            # 1) upgrade to parent (lineage columns must not exist)
            command.upgrade(cfg, LINEAGE_PARENT_REV)
            isolated_engine = create_engine(isolated_url_str)
            _assert_no_lineage_artifacts(isolated_engine)

            # 2) upgrade to head + inspect lineage
            command.upgrade(cfg, LINEAGE_HEAD_REV)
            isolated_engine.dispose()
            isolated_engine = create_engine(isolated_url_str)
            _assert_lineage_artifacts_at_head(isolated_engine)

            # 3) DML RESTRICT + unique + null manual lineage
            _run_lineage_dml_proof(isolated_engine)
            isolated_engine.dispose()
            isolated_engine = None

            # 4) downgrade to parent → lineage artifacts gone
            command.downgrade(cfg, LINEAGE_PARENT_REV)
            isolated_engine = create_engine(isolated_url_str)
            _assert_no_lineage_artifacts(isolated_engine)
            isolated_engine.dispose()
            isolated_engine = None

            # 5) upgrade head again → artifacts restored
            command.upgrade(cfg, LINEAGE_HEAD_REV)
            isolated_engine = create_engine(isolated_url_str)
            _assert_lineage_artifacts_at_head(isolated_engine)

            assert ScriptDirectory.from_config(cfg).get_heads() == [LINEAGE_HEAD_REV]
        finally:
            if isolated_engine is not None:
                isolated_engine.dispose()
            _restore_env(prev_env)
            if created:
                try:
                    with admin_engine.connect() as conn:
                        conn.execute(
                            text(
                                "SELECT pg_terminate_backend(pid) "
                                "FROM pg_stat_activity "
                                "WHERE datname = :db AND pid <> pg_backend_pid()"
                            ),
                            {"db": db_name},
                        )
                        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
                except Exception:
                    pass
            admin_engine.dispose()


# ---------------------------------------------------------------------------
# M-1 — seven real PostgreSQL nodes
# ---------------------------------------------------------------------------


class _PGMatrixSeed:
    def __init__(self, SessionLocal):
        self.SessionLocal = SessionLocal
        self.db = SessionLocal()
        self.ids = {}
        self.manual_snap = None

    def seed(self, *, perms=None):
        db = self.db
        uid = uuid.uuid4().hex[:8]
        perms = perms or [
            "workbench:edit",
            "project:read",
            "project:update",
            "project:archive",
        ]
        org = OrganizationProfile(
            legal_name=f"PM{uid}",
            organization_slug=f"pm{uid}",
            status=OrganizationStatus.ACTIVE,
        )
        db.add(org)
        db.commit()
        role = Role(code=f"r{uid}", display_name="R", permissions=perms)
        db.add(role)
        db.commit()
        user = User(
            organization_id=org.id,
            email=f"u{uid}@t.com",
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
            code=f"P{uid[:6]}",
            name="P",
            status=ProjectWorkflowStatus.DRAFT,
            created_by=user.id,
        )
        db.add(project)
        db.commit()
        manual = ProjectAssetLine(
            project_id=project.id,
            asset_name="Manual",
            quantity=2.0,
            row_version=1,
        )
        db.add(manual)
        db.commit()
        self.manual_snap = official_line_snapshot(manual)
        unit = Unit(
            code=f"U{uid[:4]}",
            display_name="Unit",
            symbol=f"s{uid[:3]}",
            status=ReferenceStatus.ACTIVE,
        )
        db.add(unit)
        db.commit()
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
        db.add(batch)
        db.commit()
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
            proposed_unit=unit.code,
        )
        db.add(row)
        db.commit()
        self.ids = {
            "org": org.id,
            "role": role.id,
            "user": user.id,
            "cust": cust.id,
            "project": project.id,
            "batch": batch.id,
            "manual": manual.id,
            "unit": unit.id,
            "staging": row.id,
        }
        return self.ids

    def cleanup(self):
        s = self.SessionLocal()
        try:
            ids = self.ids
            if not ids:
                return
            s.query(ProjectAssetLine).filter(
                ProjectAssetLine.project_id == ids["project"]
            ).delete(synchronize_session=False)
            s.query(ProjectAssetImportStagingRow).filter_by(
                import_batch_id=ids["batch"]
            ).delete(synchronize_session=False)
            s.query(AuditEvent).filter(
                AuditEvent.entity_id.in_([ids["batch"], ids["project"]])
            ).delete(synchronize_session=False)
            s.query(ProjectAssetImportBatch).filter_by(id=ids["batch"]).delete(
                synchronize_session=False
            )
            s.query(Unit).filter_by(id=ids["unit"]).delete(synchronize_session=False)
            s.query(Project).filter_by(id=ids["project"]).delete(
                synchronize_session=False
            )
            s.query(Customer).filter_by(id=ids["cust"]).delete(
                synchronize_session=False
            )
            s.query(UserRole).filter_by(user_id=ids["user"]).delete(
                synchronize_session=False
            )
            s.query(User).filter_by(id=ids["user"]).delete(synchronize_session=False)
            s.query(Role).filter_by(id=ids["role"]).delete(synchronize_session=False)
            s.query(OrganizationProfile).filter_by(id=ids["org"]).delete(
                synchronize_session=False
            )
            s.commit()
        except Exception:
            s.rollback()
        finally:
            s.close()
            self.db.close()


def _run_node_apply_vs_apply(engine, SessionLocal):
    seed = _PGMatrixSeed(SessionLocal)
    ids = seed.seed()
    results = []
    errors = []
    import app.modules.excel_import.application.apply_staging as ap

    orig_fp = ap.build_apply_fingerprint
    hold = threading.Event()
    release = threading.Event()
    waiter_pid = []

    def gated_fp(db, **kw):
        hold.set()
        assert release.wait(timeout=30)
        return orig_fp(db, **kw)

    ap.build_apply_fingerprint = gated_fp
    try:

        def holder():
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
                results.append(("h", "ok"))
            except Exception as e:
                errors.append(("h", e))
            finally:
                sess.close()

        def waiter():
            sess = SessionLocal()
            try:
                assert hold.wait(timeout=30)
                waiter_pid.append(
                    sess.execute(text("SELECT pg_backend_pid()")).scalar()
                )
                u = sess.query(User).filter_by(id=ids["user"]).one()
                apply_project_asset_import_batch(
                    sess,
                    org_id=ids["org"],
                    project_id=ids["project"],
                    batch_id=ids["batch"],
                    current_user=u,
                    confirm=True,
                )
                results.append(("w", "ok"))
            except Exception as e:
                errors.append(("w", e))
            finally:
                sess.close()

        t1 = threading.Thread(target=holder)
        t1.start()
        assert hold.wait(timeout=30)
        t2 = threading.Thread(target=waiter)
        t2.start()
        deadline = time.monotonic() + 30
        while not waiter_pid and time.monotonic() < deadline:
            time.sleep(0.02)
        assert waiter_pid, "waiter never published pg_backend_pid"
        _wait_lock(engine, waiter_pid[0])
        release.set()
        t1.join(timeout=90)
        t2.join(timeout=90)
        assert not t1.is_alive() and not t2.is_alive()
        assert results == [("h", "ok")], results
        _assert_http_error(
            errors, "w", status=409, error_code=ERR_STATE
        )
        s = SessionLocal()
        try:
            p = s.query(Project).filter_by(id=ids["project"]).one()
            assert p.status == ProjectWorkflowStatus.DRAFT
            _assert_batch_generation(
                s, ids, status=ImportBatchStatus.APPLIED
            )
            _assert_imported_lineage(s, ids, count=1)
            assert_apply_success_audit(
                s,
                ids["batch"],
                actor_id=ids["user"],
                org_id=ids["org"],
                project_id=ids["project"],
            )
            assert_apply_failure_count(s, ids["batch"], 0)
            _assert_manual_immutable(s, seed)
        finally:
            s.close()
    finally:
        ap.build_apply_fingerprint = orig_fp
        seed.cleanup()


def _run_node_upload_holds_apply_waits(engine, SessionLocal):
    seed = _PGMatrixSeed(SessionLocal)
    ids = seed.seed()
    entered = threading.Event()
    release = threading.Event()
    waiter_pid = []
    errors = []
    results = []
    content = _xlsx([["asset_name", "quantity"], ["NewU", "3"]])
    try:

        def holder():
            sess = SessionLocal()
            try:
                u = sess.query(User).filter_by(id=ids["user"]).one()
                upload_excel_file_orchestrator(
                    sess,
                    org_id=ids["org"],
                    project_id=ids["project"],
                    batch_id=ids["batch"],
                    file=SlowUpload("up.xlsx", content, entered, release),
                    request=None,
                    current_user=u,
                )
                results.append("upload_ok")
            except Exception as e:
                errors.append(("upload", e))
            finally:
                sess.close()

        def waiter():
            sess = SessionLocal()
            try:
                assert entered.wait(timeout=30)
                waiter_pid.append(
                    sess.execute(text("SELECT pg_backend_pid()")).scalar()
                )
                u = sess.query(User).filter_by(id=ids["user"]).one()
                apply_project_asset_import_batch(
                    sess,
                    org_id=ids["org"],
                    project_id=ids["project"],
                    batch_id=ids["batch"],
                    current_user=u,
                    confirm=True,
                )
                results.append("apply_ok")
            except Exception as e:
                errors.append(("apply", e))
            finally:
                sess.close()

        t1 = threading.Thread(target=holder)
        t1.start()
        assert entered.wait(timeout=30)
        t2 = threading.Thread(target=waiter)
        t2.start()
        deadline = time.monotonic() + 30
        while not waiter_pid and time.monotonic() < deadline:
            time.sleep(0.02)
        assert waiter_pid, "apply waiter never published pid"
        _wait_lock(engine, waiter_pid[0])
        release.set()
        t1.join(timeout=90)
        t2.join(timeout=90)
        assert not t1.is_alive() and not t2.is_alive()
        # Upload replaces generation → batch leaves ready_for_review; Apply rejects state.
        _assert_results_exact(results, ["upload_ok"])
        _assert_http_error(errors, "apply", status=409, error_code=ERR_STATE)
        s = SessionLocal()
        try:
            p = s.query(Project).filter_by(id=ids["project"]).one()
            assert p.status == ProjectWorkflowStatus.DRAFT
            b = s.query(ProjectAssetImportBatch).filter_by(id=ids["batch"]).one()
            assert b.source_filename == "up.xlsx"
            assert b.source_sheet_name == "Sheet1"
            assert b.status != ImportBatchStatus.APPLIED
            assert b.status != ImportBatchStatus.READY_FOR_REVIEW
            assert (
                s.query(ProjectAssetLine)
                .filter_by(source_import_batch_id=ids["batch"])
                .count()
                == 0
            )
            assert_apply_success_count(s, ids["batch"], 0)
            assert_apply_failure_count(s, ids["batch"], 0)
            _assert_manual_immutable(s, seed)
        finally:
            s.close()
    finally:
        seed.cleanup()


def _run_node_apply_holds_upload_waits(engine, SessionLocal):
    seed = _PGMatrixSeed(SessionLocal)
    ids = seed.seed()
    import app.modules.excel_import.application.apply_staging as ap

    hold = threading.Event()
    release = threading.Event()
    waiter_pid = []
    errors = []
    results = []
    orig_fp = ap.build_apply_fingerprint
    content = _xlsx([["asset_name", "quantity"], ["X", "1"]])

    def gated_fp(db, **kw):
        hold.set()
        assert release.wait(timeout=30)
        return orig_fp(db, **kw)

    ap.build_apply_fingerprint = gated_fp
    try:

        def holder():
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
                results.append("apply_ok")
            except Exception as e:
                errors.append(("apply", e))
            finally:
                sess.close()

        def waiter():
            sess = SessionLocal()
            try:
                assert hold.wait(timeout=30)
                waiter_pid.append(
                    sess.execute(text("SELECT pg_backend_pid()")).scalar()
                )
                u = sess.query(User).filter_by(id=ids["user"]).one()
                upload_excel_file_orchestrator(
                    sess,
                    org_id=ids["org"],
                    project_id=ids["project"],
                    batch_id=ids["batch"],
                    file=FakeUpload("late.xlsx", content),
                    request=None,
                    current_user=u,
                )
                results.append("upload_ok")
            except Exception as e:
                errors.append(("upload", e))
            finally:
                sess.close()

        t1 = threading.Thread(target=holder)
        t1.start()
        assert hold.wait(timeout=30)
        t2 = threading.Thread(target=waiter)
        t2.start()
        deadline = time.monotonic() + 30
        while not waiter_pid and time.monotonic() < deadline:
            time.sleep(0.02)
        assert waiter_pid, "upload waiter never published pid"
        _wait_lock(engine, waiter_pid[0])
        release.set()
        t1.join(timeout=90)
        t2.join(timeout=90)
        assert not t1.is_alive() and not t2.is_alive()
        _assert_results_exact(results, ["apply_ok"])
        _assert_http_error(errors, "upload", status=409)
        s = SessionLocal()
        try:
            p = s.query(Project).filter_by(id=ids["project"]).one()
            assert p.status == ProjectWorkflowStatus.DRAFT
            _assert_batch_generation(
                s,
                ids,
                status=ImportBatchStatus.APPLIED,
                filename="x.xlsx",
                sheet="Sheet1",
            )
            _assert_imported_lineage(s, ids, count=1)
            assert_apply_success_audit(
                s,
                ids["batch"],
                actor_id=ids["user"],
                org_id=ids["org"],
                project_id=ids["project"],
            )
            assert_apply_failure_count(s, ids["batch"], 0)
            _assert_manual_immutable(s, seed)
        finally:
            s.close()
    finally:
        ap.build_apply_fingerprint = orig_fp
        seed.cleanup()


def _run_node_validate_holds_apply_waits(engine, SessionLocal):
    seed = _PGMatrixSeed(SessionLocal)
    ids = seed.seed()
    import app.modules.excel_import.application.validate_staging as vs

    hold = threading.Event()
    release = threading.Event()
    waiter_pid = []
    errors = []
    results = []
    orig_fp = vs.build_validation_fingerprint

    def gated_fp(db, batch):
        hold.set()
        assert release.wait(timeout=30)
        return orig_fp(db, batch)

    vs.build_validation_fingerprint = gated_fp
    try:

        def holder():
            sess = SessionLocal()
            try:
                u = sess.query(User).filter_by(id=ids["user"]).one()
                validate_project_asset_import_batch(
                    sess,
                    org_id=ids["org"],
                    project_id=ids["project"],
                    batch_id=ids["batch"],
                    current_user=u,
                )
                results.append("validate_ok")
            except Exception as e:
                errors.append(("validate", e))
            finally:
                sess.close()

        def waiter():
            sess = SessionLocal()
            try:
                assert hold.wait(timeout=30)
                waiter_pid.append(
                    sess.execute(text("SELECT pg_backend_pid()")).scalar()
                )
                u = sess.query(User).filter_by(id=ids["user"]).one()
                apply_project_asset_import_batch(
                    sess,
                    org_id=ids["org"],
                    project_id=ids["project"],
                    batch_id=ids["batch"],
                    current_user=u,
                    confirm=True,
                )
                results.append("apply_ok")
            except Exception as e:
                errors.append(("apply", e))
            finally:
                sess.close()

        t1 = threading.Thread(target=holder)
        t1.start()
        assert hold.wait(timeout=30)
        t2 = threading.Thread(target=waiter)
        t2.start()
        deadline = time.monotonic() + 30
        while not waiter_pid and time.monotonic() < deadline:
            time.sleep(0.02)
        assert waiter_pid, "apply waiter never published pid"
        _wait_lock(engine, waiter_pid[0])
        release.set()
        t1.join(timeout=90)
        t2.join(timeout=90)
        assert not t1.is_alive() and not t2.is_alive()
        _assert_results_exact(results, ["validate_ok", "apply_ok"])
        assert errors == [], errors
        s = SessionLocal()
        try:
            p = s.query(Project).filter_by(id=ids["project"]).one()
            assert p.status == ProjectWorkflowStatus.DRAFT
            _assert_batch_generation(s, ids, status=ImportBatchStatus.APPLIED)
            _assert_imported_lineage(s, ids, count=1)
            assert_apply_success_audit(
                s,
                ids["batch"],
                actor_id=ids["user"],
                org_id=ids["org"],
                project_id=ids["project"],
            )
            assert_apply_failure_count(s, ids["batch"], 0)
            val_rows = (
                s.query(AuditEvent)
                .filter_by(
                    entity_id=ids["batch"], event_name=VALIDATION_SUCCESS_EVENT
                )
                .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
                .all()
            )
            apply_rows = (
                s.query(AuditEvent)
                .filter_by(entity_id=ids["batch"], event_name=SUCCESS_EVENT)
                .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
                .all()
            )
            assert len(val_rows) >= 1
            assert len(apply_rows) == 1
            # validation-success audit must precede apply-success (commit order)
            assert (
                val_rows[-1].created_at,
                str(val_rows[-1].id),
            ) < (
                apply_rows[0].created_at,
                str(apply_rows[0].id),
            )
            _assert_manual_immutable(s, seed)
        finally:
            s.close()
    finally:
        vs.build_validation_fingerprint = orig_fp
        seed.cleanup()


def _run_node_apply_holds_validate_waits(engine, SessionLocal):
    seed = _PGMatrixSeed(SessionLocal)
    ids = seed.seed()
    import app.modules.excel_import.application.apply_staging as ap

    hold = threading.Event()
    release = threading.Event()
    waiter_pid = []
    errors = []
    results = []
    orig_fp = ap.build_apply_fingerprint

    def gated_fp(db, **kw):
        hold.set()
        assert release.wait(timeout=30)
        return orig_fp(db, **kw)

    ap.build_apply_fingerprint = gated_fp
    try:

        def holder():
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
                results.append("apply_ok")
            except Exception as e:
                errors.append(("apply", e))
            finally:
                sess.close()

        def waiter():
            sess = SessionLocal()
            try:
                assert hold.wait(timeout=30)
                waiter_pid.append(
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
                results.append("validate_ok")
            except Exception as e:
                errors.append(("validate", e))
            finally:
                sess.close()

        t1 = threading.Thread(target=holder)
        t1.start()
        assert hold.wait(timeout=30)
        t2 = threading.Thread(target=waiter)
        t2.start()
        deadline = time.monotonic() + 30
        while not waiter_pid and time.monotonic() < deadline:
            time.sleep(0.02)
        assert waiter_pid, "validate waiter never published pid"
        _wait_lock(engine, waiter_pid[0])
        release.set()
        t1.join(timeout=90)
        t2.join(timeout=90)
        assert not t1.is_alive() and not t2.is_alive()
        _assert_results_exact(results, ["apply_ok"])
        _assert_http_error(errors, "validate", status=409)
        s = SessionLocal()
        try:
            p = s.query(Project).filter_by(id=ids["project"]).one()
            assert p.status == ProjectWorkflowStatus.DRAFT
            _assert_batch_generation(s, ids, status=ImportBatchStatus.APPLIED)
            _assert_imported_lineage(s, ids, count=1)
            assert_apply_success_audit(
                s,
                ids["batch"],
                actor_id=ids["user"],
                org_id=ids["org"],
                project_id=ids["project"],
            )
            assert_apply_failure_count(s, ids["batch"], 0)
            _assert_manual_immutable(s, seed)
        finally:
            s.close()
    finally:
        ap.build_apply_fingerprint = orig_fp
        seed.cleanup()


def _run_node_workflow_holds_apply_waits(engine, SessionLocal):
    """Real archive_project (authorized status transition) holds; Apply waits."""
    seed = _PGMatrixSeed(SessionLocal)
    ids = seed.seed()
    hold = threading.Event()
    release = threading.Event()
    waiter_pid = []
    errors = []
    results = []
    try:

        def holder():
            sess = SessionLocal()
            try:
                u = sess.query(User).filter_by(id=ids["user"]).one()
                # Gate first commit so Project row lock is held mid-archive
                orig_commit = sess.commit
                n = {"c": 0}

                def gated_commit():
                    n["c"] += 1
                    if n["c"] == 1:
                        sess.flush()
                        hold.set()
                        assert release.wait(timeout=30)
                    return orig_commit()

                sess.commit = gated_commit
                archive_project(
                    project_id=ids["project"], db=sess, current_user=u
                )
                results.append("archive_ok")
            except Exception as e:
                errors.append(("archive", e))
                release.set()
            finally:
                sess.close()

        def waiter():
            sess = SessionLocal()
            try:
                assert hold.wait(timeout=30)
                waiter_pid.append(
                    sess.execute(text("SELECT pg_backend_pid()")).scalar()
                )
                u = sess.query(User).filter_by(id=ids["user"]).one()
                apply_project_asset_import_batch(
                    sess,
                    org_id=ids["org"],
                    project_id=ids["project"],
                    batch_id=ids["batch"],
                    current_user=u,
                    confirm=True,
                )
                results.append("apply_ok")
            except Exception as e:
                errors.append(("apply", e))
            finally:
                sess.close()

        t1 = threading.Thread(target=holder)
        t1.start()
        assert hold.wait(timeout=30)
        t2 = threading.Thread(target=waiter)
        t2.start()
        deadline = time.monotonic() + 30
        while not waiter_pid and time.monotonic() < deadline:
            time.sleep(0.02)
        assert waiter_pid, "apply waiter never published pid"
        _wait_lock(engine, waiter_pid[0])
        release.set()
        t1.join(timeout=90)
        t2.join(timeout=90)
        assert not t1.is_alive() and not t2.is_alive()
        _assert_results_exact(results, ["archive_ok"])
        _assert_http_error(
            errors, "apply", status=400, error_code=ERR_NOT_DRAFT
        )
        s = SessionLocal()
        try:
            p = s.query(Project).filter_by(id=ids["project"]).one()
            assert p.status == ProjectWorkflowStatus.ARCHIVED or (
                getattr(p.status, "value", p.status) == "archived"
            )
            _assert_batch_generation(
                s, ids, status=ImportBatchStatus.READY_FOR_REVIEW
            )
            assert (
                s.query(ProjectAssetLine)
                .filter_by(source_import_batch_id=ids["batch"])
                .count()
                == 0
            )
            assert_apply_success_count(s, ids["batch"], 0)
            assert_apply_failure_count(s, ids["batch"], 0)
            _assert_manual_immutable(s, seed)
        finally:
            s.close()
    finally:
        seed.cleanup()


def _run_node_apply_holds_workflow_waits(engine, SessionLocal):
    seed = _PGMatrixSeed(SessionLocal)
    ids = seed.seed()
    import app.modules.excel_import.application.apply_staging as ap

    hold = threading.Event()
    release = threading.Event()
    waiter_pid = []
    errors = []
    results = []
    orig_fp = ap.build_apply_fingerprint

    def gated_fp(db, **kw):
        hold.set()
        assert release.wait(timeout=30)
        return orig_fp(db, **kw)

    ap.build_apply_fingerprint = gated_fp
    try:

        def holder():
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
                results.append("apply_ok")
            except Exception as e:
                errors.append(("apply", e))
            finally:
                sess.close()

        def waiter():
            sess = SessionLocal()
            try:
                assert hold.wait(timeout=30)
                waiter_pid.append(
                    sess.execute(text("SELECT pg_backend_pid()")).scalar()
                )
                u = sess.query(User).filter_by(id=ids["user"]).one()
                archive_project(
                    project_id=ids["project"], db=sess, current_user=u
                )
                results.append("archive_ok")
            except Exception as e:
                errors.append(("archive", e))
            finally:
                sess.close()

        t1 = threading.Thread(target=holder)
        t1.start()
        assert hold.wait(timeout=30)
        t2 = threading.Thread(target=waiter)
        t2.start()
        deadline = time.monotonic() + 30
        while not waiter_pid and time.monotonic() < deadline:
            time.sleep(0.02)
        assert waiter_pid, "workflow waiter never published pid"
        _wait_lock(engine, waiter_pid[0])
        release.set()
        t1.join(timeout=90)
        t2.join(timeout=90)
        assert not t1.is_alive() and not t2.is_alive()
        _assert_results_exact(results, ["apply_ok", "archive_ok"])
        assert errors == [], errors
        s = SessionLocal()
        try:
            p = s.query(Project).filter_by(id=ids["project"]).one()
            assert (
                p.status == ProjectWorkflowStatus.ARCHIVED
                or getattr(p.status, "value", p.status) == "archived"
            )
            _assert_batch_generation(s, ids, status=ImportBatchStatus.APPLIED)
            _assert_imported_lineage(s, ids, count=1)
            apply_evt = assert_apply_success_audit(
                s,
                ids["batch"],
                actor_id=ids["user"],
                org_id=ids["org"],
                project_id=ids["project"],
            )
            assert_apply_failure_count(s, ids["batch"], 0)
            arch_rows = (
                s.query(AuditEvent)
                .filter_by(entity_id=ids["project"], event_name="ProjectArchived")
                .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
                .all()
            )
            assert len(arch_rows) == 1
            # Apply success audit must precede ProjectArchived (commit order)
            assert (
                apply_evt.created_at,
                str(apply_evt.id),
            ) < (
                arch_rows[0].created_at,
                str(arch_rows[0].id),
            )
            _assert_manual_immutable(s, seed)
        finally:
            s.close()
    finally:
        ap.build_apply_fingerprint = orig_fp
        seed.cleanup()


_NODE_RUNNERS = {
    "pg_apply_vs_apply_lock_wait": _run_node_apply_vs_apply,
    "pg_upload_holds_apply_waits": _run_node_upload_holds_apply_waits,
    "pg_apply_holds_upload_waits": _run_node_apply_holds_upload_waits,
    "pg_validate_holds_apply_waits": _run_node_validate_holds_apply_waits,
    "pg_apply_holds_validate_waits": _run_node_apply_holds_validate_waits,
    "pg_workflow_holds_apply_waits": _run_node_workflow_holds_apply_waits,
    "pg_apply_holds_workflow_waits": _run_node_apply_holds_workflow_waits,
}


@pytest.mark.parametrize("node_id", list(PG_NODE_IDS))
def test_pg_proof_matrix_node(node_id):
    """M-1: each node body is real holder/waiter production entry points."""
    pg = _pg_url()
    if not pg:
        pytest.skip(f"SKIPPED LOCALLY - REQUIRES CI WITH POSTGRESQL ({node_id})")
    engine = create_engine(pg)
    SessionLocal = sessionmaker(bind=engine)
    runner = _NODE_RUNNERS[node_id]
    runner(engine, SessionLocal)


def test_pg_node_inventory_complete():
    """Collect-time proof that all seven node IDs have real runners."""
    assert set(_NODE_RUNNERS) == set(PG_NODE_IDS)
    assert len(PG_NODE_IDS) == 7
