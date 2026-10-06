"""The one A10 migration round trip and SQL/ORM immutability on PostgreSQL."""
import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text, inspect
from sqlalchemy.exc import DBAPIError

from app.modules.project_master_data.price_evidence_models import ProjectPriceEvidenceSource
from tests.test_g2_price_evidence import (
    entry_db as _entry_db, line_db as _line_db, workbench_db as _workbench_db,
    evidence_db as _evidence_db, request_for, execute, counts, cover_all, provider,
)

entry_db, line_db, workbench_db, evidence_db = _entry_db, _line_db, _workbench_db, _evidence_db


def revision():
    path = Path(__file__).parents[1] / "alembic/versions/d7e8f9a0b1c2_price_evidence_authority.py"
    spec = importlib.util.spec_from_file_location("a10_revision", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_one_head_round_trip_scope_and_sql_append_only(evidence_db):
    db, entry = evidence_db
    migration = revision()
    assert migration.down_revision == "c6d7e8f9a0b1"
    schema = db.get_bind().get_execution_options()["schema_translate_map"][None]
    before = set(inspect(db.get_bind()).get_table_names(schema=schema))
    db.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    with Operations.context(MigrationContext.configure(db.connection())):
        from alembic import op
        for table in reversed(migration.TABLES):
            op.drop_table(table)
        migration.upgrade()
    db.commit()
    assert set(inspect(db.get_bind()).get_table_names(schema=schema)) == before
    execute(db, entry, request_for(db, entry))
    db.commit()
    cover_all(db, entry)
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    execute(db, entry, request_for(db, entry, "confirmation-withdrawal"))
    db.commit()
    assert counts(db) == (6, 6, 6)
    for table in migration.TABLES:
        for statement in (f'UPDATE "{schema}".{table} SET id=id', f'DELETE FROM "{schema}".{table}'):
            with pytest.raises(DBAPIError, match="append-only"):
                with db.begin_nested():
                    db.execute(text(statement))
    db.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    with Operations.context(MigrationContext.configure(db.connection())):
        migration.downgrade()
    db.commit()
    assert set(inspect(db.get_bind()).get_table_names(schema=schema)) == before - set(migration.TABLES)
    db.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    with Operations.context(MigrationContext.configure(db.connection())):
        migration.upgrade()
    db.commit()
    assert provider(db, entry).result == "STALE"  # surviving audits prove removed history is not absence


def test_orm_rejects_source_overwrite(evidence_db):
    db, entry = evidence_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    source = db.query(ProjectPriceEvidenceSource).one()
    source.category = "prior_appraisal_result"
    with pytest.raises(ValueError, match="append-only"):
        db.flush()
    db.rollback()
    assert counts(db) == (1, 1, 1)
