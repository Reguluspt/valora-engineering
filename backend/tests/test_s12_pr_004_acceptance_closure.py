"""S12-PR-004 acceptance closure proofs A-1..A-8."""
from __future__ import annotations

import tempfile
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.modules.excel_import.application.apply_staging import (
    FAILURE_EVENT,
    SUCCESS_EVENT,
    apply_project_asset_import_batch,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    Currency,
    ImportBatchStatus,
    ProjectAssetLine,
    ReferenceStatus,
    Unit,
)
from tests.test_s12_pr_004_staging_apply import ApplyHarness


def official_line_snapshot(line: ProjectAssetLine) -> dict:
    """Field-complete ProjectAssetLine snapshot (excludes timestamps)."""
    def sv(v):
        return v.value if hasattr(v, "value") else v

    return {
        "id": line.id,
        "project_id": line.project_id,
        "asset_name": line.asset_name,
        "description": line.description,
        "quantity": line.quantity,
        "unit_id": line.unit_id,
        "raw_price": line.raw_price,
        "raw_price_currency_id": line.raw_price_currency_id,
        "appraised_unit_price": line.appraised_unit_price,
        "appraised_currency_id": line.appraised_currency_id,
        "review_status": sv(line.review_status),
        "validation_status": sv(line.validation_status),
        "brand_id": line.brand_id,
        "manufacturer_id": line.manufacturer_id,
        "row_version": line.row_version,
        "matched_asset_id": line.matched_asset_id,
        "matched_knowledge_id": line.matched_knowledge_id,
        "taxonomy_id": line.taxonomy_id,
        "suggested_taxonomy_node_id": line.suggested_taxonomy_node_id,
        "approved_taxonomy_node_id": line.approved_taxonomy_node_id,
        "suggested_canonical_asset_id": line.suggested_canonical_asset_id,
        "approved_canonical_asset_id": line.approved_canonical_asset_id,
        "suggested_asset_variant_id": line.suggested_asset_variant_id,
        "approved_asset_variant_id": line.approved_asset_variant_id,
        "source_import_batch_id": line.source_import_batch_id,
        "source_staging_row_id": line.source_staging_row_id,
    }


class TestA1SelectedTierResolution:
    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()

    def test_inactive_code_blocks_active_display_fallback(self):
        # inactive unit with code X; active unit with display_name X
        # Selected tier is code (1 match, inactive) â†’ reject; no fallback to display.
        self.h.db.add(
            Unit(code="X", display_name="Other", symbol="xo", status=ReferenceStatus.INACTIVE)
        )
        self.h.db.add(
            Unit(code="Y", display_name="X", symbol="yo", status=ReferenceStatus.ACTIVE)
        )
        self.h.db.commit()
        self.h.add_row(name="N", unit="x")
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error_code"] == "apply_mapping_invalid"

    def test_ambiguous_display_rejects(self):
        # Two display matches (active+inactive) select display tier â†’ ambiguous â†’ reject.
        self.h.db.add(
            Unit(code="D1", display_name="Same", symbol="a1", status=ReferenceStatus.ACTIVE)
        )
        self.h.db.add(
            Unit(code="D2", display_name="Same", symbol="a2", status=ReferenceStatus.INACTIVE)
        )
        self.h.db.commit()
        self.h.add_row(name="N", unit="same")
        assert (
            self.h.client()
            .post(
                f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
                json={"confirm": True},
            )
            .status_code
            == 400
        )

    def test_inactive_display_blocks_active_symbol(self):
        # Display tier selected with single inactive match â†’ reject; no symbol fallback.
        self.h.db.add(
            Unit(
                code="ID1",
                display_name="Shared",
                symbol="ss",
                status=ReferenceStatus.INACTIVE,
            )
        )
        self.h.db.add(
            Unit(
                code="ID2",
                display_name="Other",
                symbol="Shared",
                status=ReferenceStatus.ACTIVE,
            )
        )
        self.h.db.commit()
        self.h.add_row(name="N", unit="shared")
        assert (
            self.h.client()
            .post(
                f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
                json={"confirm": True},
            )
            .status_code
            == 400
        )

    def test_higher_tier_active_code_wins(self):
        self.h.add_row(name="N", unit="CAI")
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 200
        line = (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .one()
        )
        assert line.unit_id == self.h.unit.id

    def test_unique_active_symbol_resolves(self):
        # Resolve via unique ACTIVE symbol (Unicode casefold exact match).
        self.h.add_row(name="N", unit="cái")
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 200, r.text
        line = (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .one()
        )
        assert line.unit_id == self.h.unit.id

    def test_currency_inactive_code_blocks_active_display(self):
        self.h.db.add(
            Currency(
                code="ZZZ", display_name="Other", symbol="z1", status=ReferenceStatus.INACTIVE
            )
        )
        self.h.db.add(
            Currency(
                code="AAA", display_name="ZZZ", symbol="z2", status=ReferenceStatus.ACTIVE
            )
        )
        self.h.db.commit()
        self.h.add_row(name="N", currency="zzz")
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 400

    def test_currency_active_display_resolves(self):
        self.h.add_row(name="N", currency="Dong")
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 200
        line = (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .one()
        )
        assert line.raw_price_currency_id == self.h.cur.id

    def test_currency_symbol_forbidden_even_unique(self):
        self.h.add_row(name="N", currency="â‚«")
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 400


class TestA8PostCommitRegression:
    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()

    def test_no_orm_after_successful_commit(self, monkeypatch):
        self.h.add_row(name="Z")
        committed = {"ok": False}
        orig_commit = self.h.db.commit

        def commit_then_arm():
            orig_commit()
            committed["ok"] = True

        def fail_query(*a, **k):
            if committed["ok"]:
                raise RuntimeError("post-commit query forbidden")
            return orig_query(*a, **k)

        def fail_refresh(*a, **k):
            if committed["ok"]:
                raise RuntimeError("post-commit refresh forbidden")
            return orig_refresh(*a, **k)

        orig_query = self.h.db.query
        orig_refresh = self.h.db.refresh
        monkeypatch.setattr(self.h.db, "commit", commit_then_arm)
        monkeypatch.setattr(self.h.db, "query", fail_query)
        monkeypatch.setattr(self.h.db, "refresh", fail_refresh)

        out = apply_project_asset_import_batch(
            self.h.db,
            org_id=self.h.org.id,
            project_id=self.h.project.id,
            batch_id=self.h.batch.id,
            current_user=self.h.user,
            confirm=True,
        )
        assert committed["ok"] is True
        assert out["status"] == "applied"
        assert out["created_count"] == 1


class TestA4RawPriceAndForbidden:
    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()

    @pytest.mark.parametrize(
        "price,ok,expect_null",
        [
            (None, True, True),
            ("", True, True),
            ("0", True, False),
            ("1.12", True, False),
            ("1.123", False, False),
            ("1234567890123", True, False),  # 13 int digits
            ("12345678901234", False, False),
            ("1e2", True, False),
            ("1e20", False, False),
            ("-1", False, False),
            ("NaN", False, False),
            ("Infinity", False, False),
            ("-Infinity", False, False),
        ],
    )
    def test_raw_price(self, price, ok, expect_null):
        self.h.add_row(name="N", price=price)
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert (r.status_code == 200) is ok, (price, r.text)
        if ok:
            line = (
                self.h.db.query(ProjectAssetLine)
                .filter_by(source_import_batch_id=self.h.batch.id)
                .one()
            )
            if expect_null:
                assert line.raw_price is None
            else:
                assert line.raw_price is not None

    def test_unicode_trim_nbsp(self):
        nbsp = "\u00a0"
        self.h.add_row(name=f"{nbsp}Name{nbsp}")
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 200
        line = (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=self.h.batch.id)
            .one()
        )
        assert line.asset_name == "Name"

    @pytest.mark.parametrize(
        "qty,ok,expect",
        [
            (None, True, Decimal("1.0000")),
            ("", True, Decimal("1.0000")),
            ("0", True, Decimal("0")),
            ("1.1234", True, Decimal("1.1234")),
            ("1.12345", False, None),
            ("12345678901", True, Decimal("12345678901")),  # 11 int digits
            ("123456789012", False, None),
            ("-1", False, None),
            ("NaN", False, None),
            ("Infinity", False, None),
        ],
    )
    def test_quantity(self, qty, ok, expect):
        self.h.add_row(name="N", qty=qty)
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert (r.status_code == 200) is ok, (qty, r.text)
        if ok:
            line = (
                self.h.db.query(ProjectAssetLine)
                .filter_by(source_import_batch_id=self.h.batch.id)
                .one()
            )
            assert Decimal(str(line.quantity)) == expect

    def test_blank_name_rejected(self):
        self.h.add_row(name="   ")
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 400

    def test_name_over_255_rejected(self):
        self.h.add_row(name="N" * 256)
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 400

    def test_description_over_5000_rejected(self):
        self.h.add_row(name="N", desc="D" * 5001)
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 400

    def test_forbidden_inputs_inert(self):
        self.h.add_row(name="N")
        row = (
            self.h.db.query(__import__(
                "app.modules.project_master_data.models", fromlist=["ProjectAssetImportStagingRow"]
            ).ProjectAssetImportStagingRow)
            .filter_by(import_batch_id=self.h.batch.id)
            .one()
        )
        row.proposed_appraised_unit_price = "99999.99"
        row.proposed_review_status = "accepted"
        row.proposed_validation_status = "valid"
        row.raw_values = {"cells": [{"value": "SECRET"}]}
        row.mapped_values = {"evil": "x"}
        self.h.db.commit()
        pre = official_line_snapshot(self.h.manual)
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
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
        self.h.db.expire_all()
        m = self.h.db.query(ProjectAssetLine).filter_by(id=pre["id"]).one()
        assert official_line_snapshot(m) == pre


class TestA3FlushAndStale:
    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()

    def test_flush_failure_after_partial_insert(self, monkeypatch):
        self.h.add_row(name="A", source_row_number=1)
        self.h.add_row(name="B", source_row_number=2)
        # Capture IDs before monkeypatch â€” attribute access can autoflush.
        org_id = self.h.org.id
        project_id = self.h.project.id
        batch_id = self.h.batch.id
        user = self.h.user
        manual_id = self.h.manual.id
        pre_manual = official_line_snapshot(
            self.h.db.query(ProjectAssetLine).filter_by(id=manual_id).one()
        )

        orig_flush = self.h.db.flush
        line_flushes = {"n": 0}

        def boom_flush(*a, **k):
            # Only count flushes that include ProjectAssetLine inserts (not pre-loop autoflush).
            pending_lines = [
                obj for obj in self.h.db.new if isinstance(obj, ProjectAssetLine)
            ]
            if pending_lines:
                line_flushes["n"] += 1
                if line_flushes["n"] >= 2:
                    raise RuntimeError("flush fail after partial")
            return orig_flush(*a, **k)

        monkeypatch.setattr(self.h.db, "flush", boom_flush)
        with pytest.raises(HTTPException) as exc:
            apply_project_asset_import_batch(
                self.h.db,
                org_id=org_id,
                project_id=project_id,
                batch_id=batch_id,
                current_user=user,
                confirm=True,
            )
        assert exc.value.status_code == 500
        assert line_flushes["n"] >= 2

        self.h.db.expire_all()
        self.h.db.refresh(self.h.batch)
        assert self.h.batch.status == ImportBatchStatus.READY_FOR_REVIEW
        assert (
            self.h.db.query(ProjectAssetLine)
            .filter_by(source_import_batch_id=batch_id)
            .count()
            == 0
        )
        assert (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=batch_id, event_name=SUCCESS_EVENT)
            .count()
            == 0
        )
        fails = (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=batch_id, event_name=FAILURE_EVENT)
            .count()
        )
        assert fails == 1
        self.h.db.expire_all()
        m = self.h.db.query(ProjectAssetLine).filter_by(id=manual_id).one()
        assert official_line_snapshot(m) == pre_manual

    def test_success_audit_flush_failure(self, monkeypatch):
        import app.modules.excel_import.application.apply_staging as ap

        self.h.add_row()
        orig = ap.log_audit_event

        def boom(*a, **k):
            if k.get("event_name") == SUCCESS_EVENT or (
                len(a) > 1 and a[1] == SUCCESS_EVENT
            ):
                raise RuntimeError("audit fail")
            # keyword style
            if a and hasattr(a[0], "__dict__"):
                pass
            return orig(*a, **k)

        def boom_kw(*a, **k):
            if k.get("event_name") == SUCCESS_EVENT:
                raise RuntimeError("audit fail")
            return orig(*a, **k)

        monkeypatch.setattr(ap, "log_audit_event", boom_kw)
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
        assert self.h.batch.status == ImportBatchStatus.READY_FOR_REVIEW
        assert (
            self.h.db.query(AuditEvent)
            .filter_by(entity_id=self.h.batch.id, event_name=SUCCESS_EVENT)
            .count()
            == 0
        )


class TestA5AlembicHead:
    def test_single_head(self):
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        heads = ScriptDirectory.from_config(Config("alembic.ini")).get_heads()
        # Single graph head advances with later migrations (S13-PR-002: f2a3b4c5d6e7).
        assert heads == ["f2a3b4c5d6e7"]

    def test_migration_file_has_lineage_columns(self):
        mig = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "e1f2a3b4c5d6_add_project_asset_line_import_lineage.py"
        )
        text_src = mig.read_text(encoding="utf-8")
        assert "source_import_batch_id" in text_src
        assert "source_staging_row_id" in text_src
        assert "RESTRICT" in text_src or "restrict" in text_src.lower()
        assert "unique" in text_src.lower()


class TestA6ImmutabilityHelper:
    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()

    def test_official_line_snapshot_full_field_set(self):
        snap = official_line_snapshot(self.h.manual)
        required = {
            "id",
            "project_id",
            "asset_name",
            "description",
            "quantity",
            "unit_id",
            "raw_price",
            "raw_price_currency_id",
            "appraised_unit_price",
            "appraised_currency_id",
            "review_status",
            "validation_status",
            "brand_id",
            "manufacturer_id",
            "row_version",
            "matched_asset_id",
            "matched_knowledge_id",
            "taxonomy_id",
            "suggested_taxonomy_node_id",
            "approved_taxonomy_node_id",
            "suggested_canonical_asset_id",
            "approved_canonical_asset_id",
            "suggested_asset_variant_id",
            "approved_asset_variant_id",
            "source_import_batch_id",
            "source_staging_row_id",
        }
        assert required.issubset(snap.keys())
        assert snap["asset_name"] == "Manual"
        assert snap["source_import_batch_id"] is None
        assert snap["source_staging_row_id"] is None

    def test_apply_leaves_preexisting_line_byte_equal_snapshot(self):
        pre = official_line_snapshot(self.h.manual)
        self.h.add_row(name="New")
        r = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert r.status_code == 200
        self.h.db.expire_all()
        post = official_line_snapshot(
            self.h.db.query(ProjectAssetLine).filter_by(id=pre["id"]).one()
        )
        assert post == pre


class TestA7ScannerFailClosed:
    def test_missing_apply_file(self):
        from tests import check_security as m

        with tempfile.TemporaryDirectory() as tmp:
            issues = m.check_apply_path_blockers(tmp)
            assert issues >= 1

    def test_missing_projects_api_file(self):
        from tests import check_security as m

        with tempfile.TemporaryDirectory() as tmp:
            app_dir = Path(tmp) / "app" / "modules" / "excel_import" / "application"
            app_dir.mkdir(parents=True)
            (app_dir / "apply_staging.py").write_text(
                "def apply():\n"
                "    rows = db.query(ProjectAssetImportStagingRow).with_for_update().all()\n",
                encoding="utf-8",
            )
            issues = m.check_apply_path_blockers(tmp)
            assert issues >= 1

    def test_missing_staging_for_update_only(self):
        from tests import check_security as m

        backend = Path(__file__).resolve().parents[1]
        src = (
            backend
            / "app"
            / "modules"
            / "excel_import"
            / "application"
            / "apply_staging.py"
        ).read_text(encoding="utf-8")
        # remove only staging with_for_update by rewriting the staging chain
        bad = src.replace(
            ".order_by(\n"
            "            ProjectAssetImportStagingRow.source_row_number,\n"
            "            ProjectAssetImportStagingRow.id,\n"
            "        )\n"
            "        .with_for_update()\n"
            "        .all()",
            ".order_by(\n"
            "            ProjectAssetImportStagingRow.source_row_number,\n"
            "            ProjectAssetImportStagingRow.id,\n"
            "        )\n"
            "        .all()",
        )
        assert bad != src
        with tempfile.TemporaryDirectory() as tmp:
            app_dir = Path(tmp) / "app" / "modules" / "excel_import" / "application"
            app_dir.mkdir(parents=True)
            (app_dir / "apply_staging.py").write_text(bad, encoding="utf-8")
            api_dir = Path(tmp) / "app" / "api"
            api_dir.mkdir(parents=True)
            (api_dir / "projects.py").write_text(
                (
                    backend / "app" / "api" / "projects.py"
                ).read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            issues = m.check_apply_path_blockers(tmp)
            assert issues > 0

    def test_setattr_and_raw_values_flagged(self):
        from tests import check_security as m

        with tempfile.TemporaryDirectory() as tmp:
            app_dir = Path(tmp) / "app" / "modules" / "excel_import" / "application"
            app_dir.mkdir(parents=True)
            (app_dir / "apply_staging.py").write_text(
                "def apply():\n"
                "    rows = db.query(ProjectAssetImportStagingRow).with_for_update().all()\n"
                "    setattr(x, 'a', 1)\n"
                "    v = row.raw_values\n",
                encoding="utf-8",
            )
            api_dir = Path(tmp) / "app" / "api"
            api_dir.mkdir(parents=True)
            (api_dir / "projects.py").write_text(
                "@router.post('/x/apply')\n"
                "def apply_project_asset_import_batch_endpoint():\n"
                "    require_permission(user, 'workbench:edit')\n"
                "    return apply_project_asset_import_batch()\n",
                encoding="utf-8",
            )
            issues = m.check_apply_path_blockers(tmp)
            assert issues >= 2



# PostgreSQL matrix nodes live in test_s12_pr_004_proof_matrix.py (M-1).
# This module retains SQLite acceptance proofs only; no placeholder PG runners.
