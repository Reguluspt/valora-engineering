"""Exercise the exact migration trigger DDL and durable scoped constraints on PG."""
import importlib.util
from pathlib import Path

import pytest
from alembic.operations import Operations
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.modules.project_master_data.models import (
    AssetReviewCommandReceipt, AssetLineValidationGeneration, User, WorkbenchSession,
)
from tests.test_g2_line_decisions import line_db as _line_db, entry_db as _entry_db, execute, request_for, counts

entry_db, line_db = _entry_db, _line_db


def test_migration_append_only_triggers_and_orm_block_all_four_tables(line_db):
    db, entry = line_db
    assert counts(db) == (0, 0, 0, 0, 0)  # No backfill from staging/Apply status.
    execute(db, entry, request_for(db, entry))
    db.commit()
    old = execute(db, entry, request_for(db, entry, review="flagged", reason_note="Hold"))
    db.commit()
    execute(db, entry, request_for(db, entry, review="accepted", reason_note="Resolved",
                                 supersedes_decision_id=old["result"]["proof_id"]))
    db.commit()
    path = Path(__file__).parents[1] / "alembic/versions/a4b5c6d7e8f9_asset_review_line_decisions.py"
    spec = importlib.util.spec_from_file_location("a4_revision", path)
    revision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(revision)
    assert revision.down_revision == "f3a4b5c6d7e8"
    schema = db.get_bind().get_execution_options()["schema_translate_map"][None]
    db.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    with Operations.context(MigrationContext.configure(db.connection())):
        revision.install_append_only()
    db.commit()
    before = counts(db)
    for table in revision.TABLES:
        for statement in (f'UPDATE "{schema}".{table} SET id=id', f'DELETE FROM "{schema}".{table}'):
            with pytest.raises(DBAPIError, match="append-only"):
                with db.begin_nested():
                    db.execute(text(statement))
    assert counts(db) == before
    receipt = db.query(AssetReviewCommandReceipt).first()
    receipt.request_sha256 = "0" * 64
    with pytest.raises(ValueError, match="append-only"):
        db.flush()
    db.rollback()


def test_proof_receipt_actor_session_and_tenant_bindings_are_database_enforced(line_db):
    import uuid
    db, entry = line_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    generation = db.query(AssetLineValidationGeneration).one()
    actor = User(organization_id=entry["org"].id, email=uuid.uuid4().hex + "@example.test", full_name="Other actor")
    db.add(actor)
    db.flush()
    session = WorkbenchSession(user_id=actor.id, project_id=entry["project"].id)
    db.add(session)
    db.commit()
    receipt = db.query(AssetReviewCommandReceipt).one()
    receipt_values = {column.name: getattr(receipt, column.name) for column in receipt.__table__.columns}
    receipt_values.update(id=uuid.uuid4(), command_id=uuid.uuid4())
    values = {column.name: getattr(generation, column.name) for column in generation.__table__.columns}
    values.update(id=uuid.uuid4(), generation=2, receipt_id=receipt_values["id"],
                  actor_user_id=actor.id, session_id=session.id)
    with pytest.raises(IntegrityError) as denied:
        with db.begin_nested():
            db.execute(receipt.__table__.insert().values(**receipt_values))
            db.execute(generation.__table__.insert().values(**values))
    assert denied.value.orig.diag.constraint_name == "fk_ar_validation_receipt"
    assert counts(db) == (1, 0, 0, 1, 1)
