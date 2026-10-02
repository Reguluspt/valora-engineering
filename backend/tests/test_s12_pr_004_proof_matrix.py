"""S12-PR-004 proof-matrix integrity: M-1..M-5 executable evidence."""
from __future__ import annotations

import os
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.modules.excel_import.application.apply_staging import (
    _map_row,
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
    UserStatus,
)
from tests.test_s12_pr_004_acceptance_closure import official_line_snapshot
from tests.test_s12_pr_004_staging_apply import ApplyHarness


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _pg_url():
    pg = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    return pg if pg and "postgres" in pg else None


class TestM5MappingAssertions:
    def setup_method(self):
        self.h = ApplyHarness()

    def teardown_method(self):
        self.h.close()


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
        row = self.h.add_row(name="N", price=price)
        assert _map_row(self.h.db, row)["raw_price"] == expect
        self.h.assert_manual_immutable()
        assert self.h.db.query(AuditEvent).count() == 0

    @pytest.mark.parametrize(
        "price",
        ["1.123", "1e20", "1.23e-1", "-1", "NaN", "Infinity", "-Infinity"],
    )
    def test_raw_price_reject_no_rounding(self, price):
        row = self.h.add_row(name="N", price=price)
        with pytest.raises(ValueError):
            _map_row(self.h.db, row)
        self.h.assert_manual_immutable()
        assert self.h.db.query(AuditEvent).count() == 0

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
        row = self.h.add_row(name="N", qty=qty)
        assert _map_row(self.h.db, row)["quantity"] == expect
        self.h.assert_manual_immutable()

    @pytest.mark.parametrize(
        "qty",
        ["1.12345", "1e20", "1.23e-5", "-1", "NaN", "Infinity"],
    )
    def test_quantity_reject(self, qty):
        row = self.h.add_row(name="N", qty=qty)
        with pytest.raises(ValueError):
            _map_row(self.h.db, row)
        self.h.assert_manual_immutable()

    def test_accent_preserved_exact_match_only(self):
        accented = Unit(code="ACC1", display_name="Mét", symbol="m²", status=ReferenceStatus.ACTIVE)
        self.h.db.add(accented)
        self.h.db.commit()
        row = self.h.add_row(name="Máy bơm", unit="Mét")
        fields = _map_row(self.h.db, row)
        assert fields["asset_name"] == "Máy bơm"
        assert fields["unit_id"] == accented.id
        for unit in ("Met", "Mé", "M e t"):
            row = self.h.add_row(name="Near match", unit=unit)
            with pytest.raises(ValueError):
                _map_row(self.h.db, row)
        self.h.assert_manual_immutable()

    def test_forbidden_inputs_explicit_defaults(self):
        row = self.h.add_row(name="N")
        row.proposed_appraised_unit_price = "99999.99"
        row.proposed_review_status = "accepted"
        row.proposed_validation_status = "valid"
        row.raw_values = {"cells": [{"value": "SECRET"}], "evil": True}
        row.mapped_values = {"unregistered": "x", "appraised_unit_price": "1"}
        self.h.db.commit()
        fields = _map_row(self.h.db, row)
        assert fields["asset_name"] == "N"
        assert set(fields) == {"asset_name", "description", "quantity", "unit_id",
                               "raw_price", "raw_price_currency_id"}
        self.h.assert_manual_immutable()
        assert self.h.db.query(AuditEvent).count() == 0


# ---------------------------------------------------------------------------
# M-3 — real stale-generation recovery
# ---------------------------------------------------------------------------




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
# S12 Apply lineage revision (not necessarily the live Alembic graph tip).
LINEAGE_HEAD_REV = "e1f2a3b4c5d6"
# Live single graph head across release branches.
CURRENT_ALEMBIC_HEAD = "head"

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
        # Keep the newer G1.1A pointer representable for the historical
        # downgrade exercised below.
        project.current_preliminary_import_batch_id = batch.id
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
            assert len(script.get_heads()) == 1
            rev = script.get_revision(LINEAGE_HEAD_REV)
            assert rev.down_revision == LINEAGE_PARENT_REV

            # 1) upgrade to parent (lineage columns must not exist)
            command.upgrade(cfg, LINEAGE_PARENT_REV)
            isolated_engine = create_engine(isolated_url_str)
            _assert_no_lineage_artifacts(isolated_engine)

            # 2) upgrade to S12 lineage revision + inspect lineage columns
            command.upgrade(cfg, LINEAGE_HEAD_REV)
            isolated_engine.dispose()
            isolated_engine = create_engine(isolated_url_str)
            _assert_lineage_artifacts_at_head(isolated_engine)

            # 2b) advance to live graph head so ORM model columns match schema
            # (e.g. S13-PR-002 current_source_artifact_id on import batches).
            command.upgrade(cfg, CURRENT_ALEMBIC_HEAD)
            isolated_engine.dispose()
            isolated_engine = create_engine(isolated_url_str)
            _assert_lineage_artifacts_at_head(isolated_engine)

            # 3) DML RESTRICT + unique + null manual lineage (ORM against live head)
            _run_lineage_dml_proof(isolated_engine)
            isolated_engine.dispose()
            isolated_engine = None

            # 4) downgrade to parent → lineage artifacts gone
            command.downgrade(cfg, LINEAGE_PARENT_REV)
            isolated_engine = create_engine(isolated_url_str)
            _assert_no_lineage_artifacts(isolated_engine)
            isolated_engine.dispose()
            isolated_engine = None

            # 5) upgrade live head again → lineage + later schema restored
            command.upgrade(cfg, CURRENT_ALEMBIC_HEAD)
            isolated_engine = create_engine(isolated_url_str)
            _assert_lineage_artifacts_at_head(isolated_engine)

            assert len(ScriptDirectory.from_config(cfg).get_heads()) == 1
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
# Historical M-1 races are superseded by the real v2 matrix below.
# ---------------------------------------------------------------------------



# Current mutation, failure-recovery and PostgreSQL race proof: test_g2_authority*.py.
