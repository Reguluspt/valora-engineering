"""Exact A7 migration round trip, SQL/ORM immutability and tenant FK enforcement."""
import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text, inspect
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.modules.project_master_data.models import (
    ProjectAssetWorkbenchConfirmation, AssetWorkbenchCommandReceipt,
)
from tests.test_g2_asset_workbench import (
    entry_db as _entry_db, line_db as _line_db, workbench_db as _workbench_db,
    request_for, execute, counts, provider,
)

entry_db, line_db, workbench_db = _entry_db, _line_db, _workbench_db


def revision():
    path = Path(__file__).parents[1] / "alembic/versions/c6d7e8f9a0b1_asset_workbench_confirmation.py"
    spec = importlib.util.spec_from_file_location("a7_revision", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_exact_migration_round_trip_only_owned_tables_and_append_only(workbench_db):
    db, entry = workbench_db
    migration = revision()
    assert migration.down_revision == "b5c6d7e8f9a0"
    schema = db.get_bind().get_execution_options()["schema_translate_map"][None]
    db.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    # Base.metadata fixture includes candidate tables: remove those three before exact upgrade.
    with Operations.context(MigrationContext.configure(db.connection())):
        from alembic import op
        # The successor's empty table references this predecessor migration.
        op.drop_constraint("fk_pe_confirmation_upstream", "project_price_evidence_confirmations", type_="foreignkey")
        op.drop_constraint("fk_aw_confirmation_reversal", migration.TABLES[1], type_="foreignkey")
        for table in reversed(migration.TABLES):
            op.drop_table(table)
        migration.upgrade()
    db.commit()
    assert counts(db) == (0, 0, 0, 0)
    execute(db, entry, request_for(db, entry))
    db.commit()
    execute(db, entry, request_for(db, entry, withdraw=True))
    db.commit()
    assert counts(db) == (1, 1, 2, 2)
    for table in migration.TABLES:
        for statement in (f'UPDATE "{schema}".{table} SET id=id', f'DELETE FROM "{schema}".{table}'):
            with pytest.raises(DBAPIError, match="append-only"):
                with db.begin_nested():
                    db.execute(text(statement))
    db.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    with Operations.context(MigrationContext.configure(db.connection())):
        migration.downgrade()
    db.commit()
    tables = inspect(db.get_bind()).get_table_names(schema=schema)
    assert all(table not in tables for table in migration.TABLES)
    assert "asset_line_human_decisions" in tables and "project_asset_review_seals" in tables
    db.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    with Operations.context(MigrationContext.configure(db.connection())):
        migration.upgrade()
        op.create_foreign_key("fk_pe_confirmation_upstream", "project_price_evidence_confirmations",
            "project_asset_workbench_confirmations", ["organization_id", "project_id", "workbench_confirmation_id"],
            ["organization_id", "project_id", "id"], ondelete="RESTRICT")
    db.commit()
    # Historical audits survive downgrade: unsupported evidence can never manufacture COMPLETE.
    assert provider(db, entry).result == "STALE"


def test_orm_and_database_scope_constraints_reject_evidence_mutation(workbench_db):
    import uuid
    db, entry = workbench_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    proof = db.query(ProjectAssetWorkbenchConfirmation).one()
    receipt = db.query(AssetWorkbenchCommandReceipt).one()
    receipt_values = {c.name: getattr(receipt, c.name) for c in receipt.__table__.columns}
    receipt_values.update(id=uuid.uuid4(), command_id=uuid.uuid4())
    proof_values = {c.name: getattr(proof, c.name) for c in proof.__table__.columns}
    proof_values.update(id=uuid.uuid4(), receipt_id=receipt_values["id"], confirmation_version=2,
        supersedes_confirmation_id=proof.id, reason_note="Superseding", actor_user_id=uuid.uuid4())
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(AssetWorkbenchCommandReceipt.__table__.insert().values(**receipt_values))
            db.execute(ProjectAssetWorkbenchConfirmation.__table__.insert().values(**proof_values))
    assert counts(db) == (1, 0, 1, 1)
    proof.reason_note = "Unauthorized overwrite"
    with pytest.raises(ValueError, match="append-only"):
        db.flush()
    db.rollback()
