"""S12-PR-004 corrective proof: C-1..C-7 regressions."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.modules.excel_import.application.apply_staging import (
    _map_row,
)
from app.modules.excel_import.application.validate_staging import (
    validate_project_asset_import_batch,
)
from app.modules.excel_import.application.import_service import upload_excel_file_orchestrator
from app.modules.project_master_data.models import (
    AuditEvent,
    ImportBatchStatus,
    ProjectAssetLine,
    ReferenceStatus,
    Unit,
)
from tests.test_s12_pr_004_staging_apply import ApplyHarness




class TestC2StagingForUpdate:
    def test_source_contains_staging_for_update(self):
        p = Path("app/modules/excel_import/application/apply_staging.py")
        if not p.exists():
            p = Path(__file__).resolve().parents[1] / "app" / "modules" / "excel_import" / "application" / "apply_staging.py"
        src = p.read_text(encoding="utf-8")
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
        row = self.h.add_row(name=name)
        if ok:
            _map_row(self.h.db, row)
        else:
            with pytest.raises(ValueError):
                _map_row(self.h.db, row)

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
        row = self.h.add_row(name="N", desc=desc)
        if not ok:
            with pytest.raises(ValueError):
                _map_row(self.h.db, row)
            return
        fields = _map_row(self.h.db, row)
        assert fields["description"] == (None if expect_null else desc.strip())

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
        row = self.h.add_row(qty=qty)
        if ok:
            _map_row(self.h.db, row)
        else:
            with pytest.raises(ValueError):
                _map_row(self.h.db, row)

    def test_unit_priority_code_over_display(self):
        # display name matches another unit's display; code match wins for CAI
        self.h.db.add(Unit(code="ZZ", display_name="CAI", symbol="z", status=ReferenceStatus.ACTIVE))
        self.h.db.commit()
        row = self.h.add_row(name="N", unit="cai")
        assert _map_row(self.h.db, row)["unit_id"] == self.h.unit.id

    def test_unit_inactive_unknown_ambiguous_symbol(self):
        self.h.db.add_all([
            Unit(code="S1", display_name="S1", symbol="dup", status=ReferenceStatus.ACTIVE),
            Unit(code="S2", display_name="S2", symbol="dup", status=ReferenceStatus.ACTIVE),
        ])
        self.h.db.commit()
        for unit in ("OLD", "unknown", "dup"):
            row = self.h.add_row(name="N", unit=unit)
            with pytest.raises(ValueError):
                _map_row(self.h.db, row)

    def test_currency_symbol_and_inactive(self):
        for currency in ("₫", "XXX"):
            row = self.h.add_row(name="N", currency=currency)
            with pytest.raises(ValueError):
                _map_row(self.h.db, row)

    def test_exclusions_and_duplicate_names(self):
        second = self.h.add_row(name="Same", source_row_number=2)
        first = self.h.add_row(name="Same", source_row_number=1)
        for row in (first, second):
            fields = _map_row(self.h.db, row)
            assert fields["asset_name"] == "Same"
            assert not {"appraised_unit_price", "review_status", "validation_status"} & fields.keys()
        assert self.h.db.query(ProjectAssetLine).count() == 1
        assert self.h.db.query(AuditEvent).count() == 0




class TestC6LifecycleAndMigration:
    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()

    def test_upload_rejects_applied(self):
        self.h.add_row()
        self.h.batch.status = ImportBatchStatus.APPLIED
        self.h.db.commit()
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
        self.h.batch.status = ImportBatchStatus.APPLIED
        self.h.db.commit()
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
        from sqlalchemy.exc import IntegrityError
        row = self.h.add_row()
        line = ProjectAssetLine(project_id=self.h.project.id, asset_name="Historical", quantity=1,
                                source_import_batch_id=self.h.batch.id, source_staging_row_id=row.id)
        self.h.db.add(line)
        self.h.db.commit()
        self.h.assert_manual_immutable()
        self.h.db.add(ProjectAssetLine(project_id=self.h.project.id, asset_name="Dup", quantity=1,
                                      source_import_batch_id=self.h.batch.id, source_staging_row_id=row.id))
        with pytest.raises(IntegrityError):
            self.h.db.commit()
        self.h.db.rollback()

    def test_alembic_single_head(self):
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        ini = Path("alembic.ini")
        if not ini.exists():
            ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        cfg = Config(str(ini))
        heads = ScriptDirectory.from_config(cfg).get_heads()
        # Single graph head check (no branching or multiple heads).
        assert len(heads) == 1


# Current success, fault and concurrency proof uses real v2 lineage in test_g2_authority*.py.
