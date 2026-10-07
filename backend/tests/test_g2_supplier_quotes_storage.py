"""One migration head, PostgreSQL pinning, round trip and tenant constraints."""
import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

from app.modules.project_master_data.supplier_quote_models import SupplierQuoteFact
from tests.test_g2_supplier_quotes import (
    entry_db as _entry_db, line_db as _line_db, workbench_db as _workbench_db,
    evidence_db as _evidence_db, covered_db as _covered_db, quote_db as _quote_db,
    request_for, execute, draft_all, counts, provider,
)

entry_db, line_db, workbench_db = _entry_db, _line_db, _workbench_db
evidence_db, covered_db, quote_db = _evidence_db, _covered_db, _quote_db


def revision():
    path = Path(__file__).parents[1] / "alembic/versions/e8f9a0b1c2d3_supplier_quotes_authority.py"
    spec = importlib.util.spec_from_file_location("a13_revision", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_round_trip_append_only_pinned_sources_and_constraints(quote_db):
    db, entry = quote_db
    migration = revision()
    assert migration.down_revision == "d7e8f9a0b1c2"
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
    # A13 commands cannot invoke these existing ingestion functions.
    draft_all(db, entry)
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    assert counts(db) == (5, 5, 5)
    for table in migration.TABLES:
        for operation in (f'UPDATE "{schema}".{table} SET id=id', f'DELETE FROM "{schema}".{table}'):
            with pytest.raises(DBAPIError, match="append-only"):
                with db.begin_nested():
                    db.execute(text(operation))
    for table, field, id_value in (("document_revisions", "content_checksum_sha256", entry["quote_binding"].document_revision_id),
            ("storage_object_bindings", "object_key", entry["quote_binding"].id)):
        with pytest.raises(DBAPIError, match="immutable"):
            with db.begin_nested():
                db.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                db.execute(text(f'UPDATE "{schema}".{table} SET {field}={field} WHERE id=:id'), {"id": id_value})
    db.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    with Operations.context(MigrationContext.configure(db.connection())):
        migration.downgrade()
    db.commit()
    assert set(inspect(db.get_bind()).get_table_names(schema=schema)) == before - set(migration.TABLES)
    db.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    with Operations.context(MigrationContext.configure(db.connection())):
        migration.upgrade()
    db.commit()
    assert provider(db, entry).result == "STALE"  # Surviving audits are orphaned history, never new authority.


def test_orm_refuses_fact_overwrite(quote_db):
    db, entry = quote_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    fact = db.query(SupplierQuoteFact).one()
    fact.kind = "confirmation"
    with pytest.raises(ValueError, match="append-only"):
        db.flush()
    db.rollback()
