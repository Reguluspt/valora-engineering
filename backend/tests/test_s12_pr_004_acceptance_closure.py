"""S12-PR-004 acceptance closure proofs A-1..A-8."""
from __future__ import annotations

import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from app.modules.excel_import.application.apply_staging import (
    _map_row,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    Currency,
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
        row = self.h.add_row(name="N", unit="x")
        with pytest.raises(ValueError):
            _map_row(self.h.db, row)

    def test_ambiguous_display_rejects(self):
        # Two display matches (active+inactive) select display tier â†’ ambiguous â†’ reject.
        self.h.db.add(
            Unit(code="D1", display_name="Same", symbol="a1", status=ReferenceStatus.ACTIVE)
        )
        self.h.db.add(
            Unit(code="D2", display_name="Same", symbol="a2", status=ReferenceStatus.INACTIVE)
        )
        self.h.db.commit()
        row = self.h.add_row(name="N", unit="same")
        with pytest.raises(ValueError):
            _map_row(self.h.db, row)

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
        row = self.h.add_row(name="N", unit="shared")
        with pytest.raises(ValueError):
            _map_row(self.h.db, row)

    def test_higher_tier_active_code_wins(self):
        row = self.h.add_row(name="N", unit="CAI")
        assert _map_row(self.h.db, row)["unit_id"] == self.h.unit.id

    def test_unique_active_symbol_resolves(self):
        # Resolve via unique ACTIVE symbol (Unicode casefold exact match).
        row = self.h.add_row(name="N", unit="cái")
        assert _map_row(self.h.db, row)["unit_id"] == self.h.unit.id

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
        row = self.h.add_row(name="N", currency="zzz")
        with pytest.raises(ValueError):
            _map_row(self.h.db, row)

    def test_currency_active_display_resolves(self):
        row = self.h.add_row(name="N", currency="Dong")
        assert _map_row(self.h.db, row)["raw_price_currency_id"] == self.h.cur.id

    def test_currency_symbol_forbidden_even_unique(self):
        row = self.h.add_row(name="N", currency="â‚«")
        with pytest.raises(ValueError):
            _map_row(self.h.db, row)




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
        row = self.h.add_row(name="N", price=price)
        if not ok:
            with pytest.raises(ValueError):
                _map_row(self.h.db, row)
            return
        fields = _map_row(self.h.db, row)
        assert (fields["raw_price"] is None) is expect_null
        if not expect_null:
            assert fields["raw_price"] == Decimal(price)

    def test_unicode_trim_nbsp(self):
        row = self.h.add_row(name=" Name ")
        assert _map_row(self.h.db, row)["asset_name"] == "Name"

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
        row = self.h.add_row(name="N", qty=qty)
        if not ok:
            with pytest.raises(ValueError):
                _map_row(self.h.db, row)
            return
        assert _map_row(self.h.db, row)["quantity"] == expect

    def test_blank_name_rejected(self):
        row = self.h.add_row(name="   ")
        with pytest.raises(ValueError):
            _map_row(self.h.db, row)

    def test_name_over_255_rejected(self):
        row = self.h.add_row(name="N" * 256)
        with pytest.raises(ValueError):
            _map_row(self.h.db, row)

    def test_description_over_5000_rejected(self):
        row = self.h.add_row(desc="D" * 5001)
        with pytest.raises(ValueError):
            _map_row(self.h.db, row)

    def test_forbidden_inputs_inert(self):
        row = self.h.add_row(name="N")
        row.proposed_appraised_unit_price = "99999.99"
        row.proposed_review_status = "accepted"
        row.proposed_validation_status = "valid"
        row.raw_values = {"cells": [{"value": "SECRET"}]}
        row.mapped_values = {"evil": "x"}
        self.h.db.commit()
        pre = official_line_snapshot(self.h.manual)
        fields = _map_row(self.h.db, row)
        assert fields["asset_name"] == "N"
        assert set(fields) == {"asset_name", "description", "quantity", "unit_id",
                               "raw_price", "raw_price_currency_id"}
        assert official_line_snapshot(self.h.manual) == pre
        assert self.h.db.query(AuditEvent).count() == 0




class TestA5AlembicHead:
    def test_single_head(self):
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        ini = Path("alembic.ini")
        if not ini.exists():
            ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        cfg = Config(str(ini))
        heads = ScriptDirectory.from_config(cfg).get_heads()
        # Single graph head check (no branching or multiple heads).
        assert len(heads) == 1

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
        response = self.h.client().post(
            f"/api/v1/projects/{self.h.project.id}/asset-imports/{self.h.batch.id}/apply",
            json={"confirm": True},
        )
        assert response.status_code == 400
        assert response.json()["detail"]["error_code"] == "apply_contract_invalid"
        self.h.db.expire_all()
        post = official_line_snapshot(self.h.db.get(ProjectAssetLine, pre["id"]))
        assert post == pre
        assert self.h.db.query(AuditEvent).count() == 0


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
        import ast

        class RemoveStagingLocks(ast.NodeTransformer):
            removed = 0

            def visit_Call(self, node):
                self.generic_visit(node)
                if isinstance(node.func, ast.Attribute) and node.func.attr == "with_for_update":
                    if any(isinstance(child, ast.Name) and child.id == "ProjectAssetImportStagingRow"
                           for child in ast.walk(node.func.value)):
                        self.removed += 1
                        return node.func.value
                return node

        transformer = RemoveStagingLocks()
        bad = ast.unparse(transformer.visit(ast.parse(src)))
        assert transformer.removed > 0
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
