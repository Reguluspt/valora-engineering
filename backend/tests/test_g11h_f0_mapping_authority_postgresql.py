"""Real PostgreSQL migration and legacy-bootstrap proof for ADR 0047."""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import insert, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base
from app.modules.excel_import.infrastructure.object_storage import FakeObjectStorage
from app.modules.excel_import.models import (
    ColumnMappingDecision, ColumnMappingProfileUsage, ProjectColumnMappingAuthority,
)
from tests.mapping_revision_helpers import (
    confirm_column_mapping, materialize_confirmed_mapping_to_staging,
)
from tests.test_s13_pr_004_column_mapping import _propose, _seed
from tests.test_s13_pr_004_column_mapping_postgresql import _postgres_engine_or_skip


def _migration():
    path = (
        Path(__file__).parents[1] / "alembic" / "versions"
        / "d1e2f3a4b5c6_project_column_mapping_authority.py"
    )
    spec = importlib.util.spec_from_file_location("f0_mapping_authority_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _old_schema(operations):
    operations.drop_table("column_mapping_legacy_selection_receipts")
    operations.drop_table("project_column_mapping_authorities")
    operations.drop_constraint(
        "chk_mapping_usage_expected_revision", "column_mapping_profile_usages", type_="check",
    )
    operations.drop_constraint(
        "uq_mapping_usage_project_id", "column_mapping_profile_usages", type_="unique",
    )
    operations.drop_column("column_mapping_profile_usages", "expected_selection_revision")


def test_postgresql_migration_never_selects_zero_one_many_legacy_facts():
    engine = _postgres_engine_or_skip()
    schema = f"f0_mapping_{uuid.uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.begin() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            Base.metadata.create_all(connection)
            db = Session(bind=connection)
            try:
                zero = _seed(db)
                one = _seed(db)
                many = _seed(db)
                used_storage = FakeObjectStorage()
                used = _seed(db, storage=used_storage)
                one_proposal = _propose(db, one).decision
                confirm_column_mapping(
                    db, actor=one["user"], org_id=one["org"].id,
                    project_id=one["project"].id, batch_id=one["batch"].id,
                    proposal_decision_id=one_proposal.id,
                    mapping_snapshot=one_proposal.mapping_snapshot,
                    memory_scope="none", command_id=uuid.uuid4(),
                )
                for _ in range(2):
                    proposal = _propose(db, many).decision
                    confirm_column_mapping(
                        db, actor=many["user"], org_id=many["org"].id,
                        project_id=many["project"].id, batch_id=many["batch"].id,
                        proposal_decision_id=proposal.id,
                        mapping_snapshot=proposal.mapping_snapshot,
                        memory_scope="none", command_id=uuid.uuid4(),
                    )
                used_proposal = _propose(db, used).decision
                used_confirmation = confirm_column_mapping(
                    db, actor=used["user"], org_id=used["org"].id,
                    project_id=used["project"].id, batch_id=used["batch"].id,
                    proposal_decision_id=used_proposal.id,
                    mapping_snapshot=used_proposal.mapping_snapshot,
                    memory_scope="none", command_id=uuid.uuid4(),
                )
                historical_usage = materialize_confirmed_mapping_to_staging(
                    db, actor=used["user"], org_id=used["org"].id,
                    project_id=used["project"].id, batch_id=used["batch"].id,
                    confirmation_decision_id=used_confirmation.id,
                    command_id=uuid.uuid4(), storage=used_storage,
                )
                # Simulate a pre-F0 database: facts survive but the newly added
                # authority and receipt schema do not exist yet.
                db.query(ProjectColumnMappingAuthority).delete(synchronize_session=False)
                db.flush()
                decision_count = db.query(ColumnMappingDecision).count()
                usage_id = historical_usage.id
                operations = Operations(MigrationContext.configure(connection))
                _old_schema(operations)
                migration = _migration()
                migration.op = operations
                migration.upgrade()
                assert connection.execute(text(
                    "SELECT count(*) FROM project_column_mapping_authorities"
                )).scalar_one() == 0
                assert connection.execute(text(
                    "SELECT count(*) FROM column_mapping_decisions"
                )).scalar_one() == decision_count
                assert connection.execute(text(
                    "SELECT count(*) FROM column_mapping_profile_usages"
                )).scalar_one() == 1
                assert connection.execute(text(
                    "SELECT count(*) FROM project_column_mapping_authorities "
                    "WHERE current_staging_usage_id IS NOT NULL"
                )).scalar_one() == 0
                savepoint = connection.begin_nested()
                with pytest.raises(IntegrityError):
                    connection.execute(insert(ProjectColumnMappingAuthority).values(
                        id=uuid.uuid4(), organization_id=used["org"].id,
                        project_id=used["project"].id, selection_revision=0,
                        current_staging_usage_id=usage_id,
                    ))
                savepoint.rollback()
                for seeded, expected_count in ((zero, 0), (one, 1), (many, 2), (used, 1)):
                    assert db.query(ColumnMappingDecision).filter_by(
                        organization_id=seeded["org"].id,
                        decision_kind="confirmation",
                    ).count() == expected_count
                assert db.get(ColumnMappingProfileUsage, usage_id) is not None
                assert zero["project"].id != one["project"].id != many["project"].id
                migration.downgrade()
                assert connection.execute(text(
                    "SELECT count(*) FROM column_mapping_profile_usages"
                )).scalar_one() == 1
                migration.upgrade()
                assert connection.execute(text(
                    "SELECT count(*) FROM project_column_mapping_authorities"
                )).scalar_one() == 0
            finally:
                db.close()
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_postgresql_downgrade_refuses_committed_selection():
    engine = _postgres_engine_or_skip()
    schema = f"f0_mapping_{uuid.uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.begin() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            Base.metadata.create_all(connection)
            db = Session(bind=connection)
            try:
                seeded = _seed(db)
                proposal = _propose(db, seeded).decision
                confirm_column_mapping(
                    db, actor=seeded["user"], org_id=seeded["org"].id,
                    project_id=seeded["project"].id, batch_id=seeded["batch"].id,
                    proposal_decision_id=proposal.id,
                    mapping_snapshot=proposal.mapping_snapshot,
                    memory_scope="none", command_id=uuid.uuid4(),
                )
                migration = _migration()
                migration.op = Operations(MigrationContext.configure(connection))
                with pytest.raises(RuntimeError, match="Downgrade refused"):
                    migration.downgrade()
                assert db.query(ProjectColumnMappingAuthority).count() == 1
            finally:
                db.close()
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


def test_postgresql_slot_uniqueness_and_cross_project_decision_fk():
    engine = _postgres_engine_or_skip()
    schema = f"f0_mapping_{uuid.uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.begin() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            Base.metadata.create_all(connection)
            db = Session(bind=connection)
            try:
                first_storage = FakeObjectStorage()
                first = _seed(db, storage=first_storage)
                second = _seed(db)
                first_proposal = _propose(db, first).decision
                second_proposal = _propose(db, second).decision
                first_confirmation = confirm_column_mapping(
                    db, actor=first["user"], org_id=first["org"].id,
                    project_id=first["project"].id, batch_id=first["batch"].id,
                    proposal_decision_id=first_proposal.id,
                    mapping_snapshot=first_proposal.mapping_snapshot,
                    memory_scope="none", command_id=uuid.uuid4(),
                )
                first_usage = materialize_confirmed_mapping_to_staging(
                    db, actor=first["user"], org_id=first["org"].id,
                    project_id=first["project"].id, batch_id=first["batch"].id,
                    confirmation_decision_id=first_confirmation.id,
                    command_id=uuid.uuid4(), storage=first_storage,
                )
                second_confirmation = confirm_column_mapping(
                    db, actor=second["user"], org_id=second["org"].id,
                    project_id=second["project"].id, batch_id=second["batch"].id,
                    proposal_decision_id=second_proposal.id,
                    mapping_snapshot=second_proposal.mapping_snapshot,
                    memory_scope="none", command_id=uuid.uuid4(),
                )
                slot = db.query(ProjectColumnMappingAuthority).filter_by(
                    organization_id=first["org"].id,
                ).one()
                savepoint = connection.begin_nested()
                with pytest.raises(IntegrityError):
                    connection.execute(insert(ProjectColumnMappingAuthority).values(
                        id=uuid.uuid4(), organization_id=first["org"].id,
                        project_id=first["project"].id, selection_revision=0,
                    ))
                savepoint.rollback()
                savepoint = connection.begin_nested()
                with pytest.raises(IntegrityError):
                    connection.execute(update(ProjectColumnMappingAuthority).where(
                        ProjectColumnMappingAuthority.id == slot.id,
                    ).values(confirmation_decision_id=second_confirmation.id))
                savepoint.rollback()
                savepoint = connection.begin_nested()
                with pytest.raises(IntegrityError):
                    connection.execute(update(ProjectColumnMappingAuthority).where(
                        ProjectColumnMappingAuthority.id == slot.id,
                    ).values(
                        import_batch_id=None, source_artifact_id=None,
                        structure_snapshot_id=None, confirmation_decision_id=None,
                        selected_usage_id=None,
                        current_staging_usage_id=first_usage.id,
                    ))
                savepoint.rollback()
                assert db.query(ProjectColumnMappingAuthority).count() == 2
            finally:
                db.close()
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
