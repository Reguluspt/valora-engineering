"""PostgreSQL-only S13-PR-004 concurrency and migration evidence."""
from __future__ import annotations

import importlib.util
import os
import threading
import uuid
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
import app.modules.excel_import.models  # noqa: F401
from app.modules.excel_import.application.column_mapping_service import (
    confirm_column_mapping,
    materialize_confirmed_mapping_to_staging,
)
from app.modules.excel_import.infrastructure.object_storage import FakeObjectStorage
from app.modules.excel_import.models import (
    ColumnMappingDecision,
    ColumnMappingField,
    ColumnMappingProfile,
    ColumnMappingProfileUsage,
    ImportSourceArtifact,
    WorkbookStructureSnapshot,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    Customer,
    OrganizationProfile,
    Project,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    User,
)
from tests.test_s13_pr_004_column_mapping import _propose, _seed


def _postgres_engine_or_skip():
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url or not url.startswith("postgres"):
        if os.getenv("CI") == "true":
            pytest.fail("CI=true requires PostgreSQL TEST_DATABASE_URL for S13-PR-004")
        pytest.skip("PostgreSQL is required for S13-PR-004 concurrency/migration proof")
    engine = create_engine(url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT to_regclass('column_mapping_profile_usages')")
        ).scalar_one()
    if exists is None:
        engine.dispose()
        if os.getenv("CI") == "true":
            pytest.fail("CI PostgreSQL is not migrated to the S13-PR-004 head")
        pytest.skip("PostgreSQL schema is not migrated to the S13-PR-004 head")
    return engine


def _cleanup(SessionLocal, org_id: uuid.UUID) -> None:
    db: Session = SessionLocal()
    try:
        db.query(ColumnMappingProfileUsage).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(ProjectAssetImportStagingRow).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(AuditEvent).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(ColumnMappingDecision).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        profile_ids = [
            row[0]
            for row in db.query(ColumnMappingProfile.id)
            .filter_by(organization_id=org_id)
            .all()
        ]
        if profile_ids:
            db.query(ColumnMappingField).filter(ColumnMappingField.profile_id.in_(profile_ids)).delete(
                synchronize_session=False
            )
        db.query(ColumnMappingProfile).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(WorkbookStructureSnapshot).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(ProjectAssetImportBatch).filter_by(organization_id=org_id).update(
            {ProjectAssetImportBatch.current_source_artifact_id: None},
            synchronize_session=False,
        )
        db.flush()
        db.query(ImportSourceArtifact).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(ProjectAssetImportBatch).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(Project).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(Customer).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(User).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(OrganizationProfile).filter_by(id=org_id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_postgresql_concurrent_materialization_creates_at_most_one_usage_and_audit():
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    storage = FakeObjectStorage()
    setup = SessionLocal()
    try:
        seeded = _seed(setup, storage=storage, asset_rows=8)
        proposal = _propose(setup, seeded).decision
        confirmation = confirm_column_mapping(
            setup,
            actor=seeded["user"],
            org_id=seeded["org"].id,
            project_id=seeded["project"].id,
            batch_id=seeded["batch"].id,
            proposal_decision_id=proposal.id,
            mapping_snapshot=proposal.mapping_snapshot,
            memory_scope="none",
            command_id=uuid.uuid4(),
        )
        ids = {
            "org": seeded["org"].id,
            "user": seeded["user"].id,
            "project": seeded["project"].id,
            "batch": seeded["batch"].id,
            "confirmation": confirmation.id,
        }
    finally:
        setup.close()

    barrier = threading.Barrier(2, timeout=30)
    command_ids = [uuid.uuid4(), uuid.uuid4()]
    results: list[uuid.UUID] = []
    errors: list[BaseException] = []

    def worker(command_id: uuid.UUID) -> None:
        db = SessionLocal()
        try:
            actor = db.get(User, ids["user"])
            barrier.wait(timeout=30)
            usage = materialize_confirmed_mapping_to_staging(
                db,
                actor=actor,
                org_id=ids["org"],
                project_id=ids["project"],
                batch_id=ids["batch"],
                confirmation_decision_id=ids["confirmation"],
                command_id=command_id,
                storage=storage,
            )
            results.append(usage.id)
        except BaseException as exc:  # thread transports evidence to parent assertion
            errors.append(exc)
        finally:
            db.close()

    threads = [
        threading.Thread(target=worker, args=(command_id,), daemon=True)
        for command_id in command_ids
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    try:
        assert all(not thread.is_alive() for thread in threads)
        assert len(results) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], HTTPException)
        assert errors[0].detail["error_code"] == "mapping_usage_conflict"
        verify = SessionLocal()
        try:
            assert verify.query(ColumnMappingProfileUsage).filter_by(
                organization_id=ids["org"], import_batch_id=ids["batch"]
            ).count() == 1
            assert verify.query(AuditEvent).filter_by(
                organization_id=ids["org"], event_name="ConfirmedMappingMaterialized"
            ).count() == 1
            assert verify.query(ProjectAssetImportStagingRow).filter_by(
                organization_id=ids["org"], import_batch_id=ids["batch"]
            ).count() == 8
        finally:
            verify.close()
    finally:
        _cleanup(SessionLocal, ids["org"])
        engine.dispose()


def test_postgresql_concurrent_customer_confirmation_has_one_active_profile():
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    setup = SessionLocal()
    try:
        seeded = _seed(setup)
        proposal = _propose(setup, seeded).decision
        ids = {
            "org": seeded["org"].id,
            "user": seeded["user"].id,
            "project": seeded["project"].id,
            "batch": seeded["batch"].id,
            "proposal": proposal.id,
            "snapshot": proposal.mapping_snapshot,
        }
    finally:
        setup.close()
    barrier = threading.Barrier(2, timeout=30)
    results: list[uuid.UUID] = []
    errors: list[BaseException] = []

    def worker() -> None:
        db = SessionLocal()
        try:
            actor = db.get(User, ids["user"])
            barrier.wait(timeout=30)
            decision = confirm_column_mapping(
                db,
                actor=actor,
                org_id=ids["org"],
                project_id=ids["project"],
                batch_id=ids["batch"],
                proposal_decision_id=ids["proposal"],
                mapping_snapshot=ids["snapshot"],
                memory_scope="customer",
                command_id=uuid.uuid4(),
            )
            results.append(decision.profile_id)
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    try:
        assert all(not thread.is_alive() for thread in threads)
        assert errors == []
        assert len(results) == 2 and len(set(results)) == 1
        verify = SessionLocal()
        try:
            active = verify.query(ColumnMappingProfile).filter_by(
                organization_id=ids["org"], status="active", scope_type="customer"
            ).all()
            assert len(active) == 1
        finally:
            verify.close()
    finally:
        _cleanup(SessionLocal, ids["org"])
        engine.dispose()


def test_postgresql_concurrent_materialization_of_different_batches_is_independent():
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    storage = FakeObjectStorage()
    setup = SessionLocal()
    try:
        first = _seed(setup, storage=storage, asset_rows=4)
        second = _seed(
            setup,
            storage=storage,
            asset_rows=5,
            org=first["org"],
            user=first["user"],
            customer=first["customer"],
        )
        work: list[dict[str, uuid.UUID]] = []
        for seeded in (first, second):
            proposal = _propose(setup, seeded).decision
            confirmation = confirm_column_mapping(
                setup,
                actor=seeded["user"],
                org_id=seeded["org"].id,
                project_id=seeded["project"].id,
                batch_id=seeded["batch"].id,
                proposal_decision_id=proposal.id,
                mapping_snapshot=proposal.mapping_snapshot,
                command_id=uuid.uuid4(),
            )
            work.append(
                {
                    "org": seeded["org"].id,
                    "user": seeded["user"].id,
                    "project": seeded["project"].id,
                    "batch": seeded["batch"].id,
                    "confirmation": confirmation.id,
                    "command": uuid.uuid4(),
                }
            )
        org_id = first["org"].id
    finally:
        setup.close()

    barrier = threading.Barrier(2, timeout=30)
    results: list[tuple[uuid.UUID, int]] = []
    errors: list[BaseException] = []

    def worker(item: dict[str, uuid.UUID]) -> None:
        db = SessionLocal()
        try:
            actor = db.get(User, item["user"])
            barrier.wait(timeout=30)
            usage = materialize_confirmed_mapping_to_staging(
                db,
                actor=actor,
                org_id=item["org"],
                project_id=item["project"],
                batch_id=item["batch"],
                confirmation_decision_id=item["confirmation"],
                command_id=item["command"],
                storage=storage,
            )
            results.append((usage.import_batch_id, usage.materialized_asset_row_count))
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [
        threading.Thread(target=worker, args=(item,), daemon=True) for item in work
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    try:
        assert all(not thread.is_alive() for thread in threads)
        assert errors == []
        assert sorted(count for _, count in results) == [4, 5]
        assert len({batch_id for batch_id, _ in results}) == 2
        verify = SessionLocal()
        try:
            assert verify.query(ColumnMappingProfileUsage).filter_by(
                organization_id=org_id
            ).count() == 2
            assert verify.query(AuditEvent).filter_by(
                organization_id=org_id, event_name="ConfirmedMappingMaterialized"
            ).count() == 2
        finally:
            verify.close()
    finally:
        _cleanup(SessionLocal, org_id)
        engine.dispose()


def _table_signature(connection, table_name: str) -> dict:
    inspector = inspect(connection)

    def normalized_sql(value) -> str | None:
        return " ".join(str(value).split()) if value is not None else None

    return {
        "columns": tuple(
            (
                column["name"],
                str(column["type"]),
                column["nullable"],
                normalized_sql(column.get("default")),
            )
            for column in inspector.get_columns(table_name)
        ),
        "foreign_keys": tuple(
            sorted(
                (
                    foreign_key.get("name"),
                    tuple(foreign_key["constrained_columns"]),
                    foreign_key.get("referred_schema"),
                    foreign_key["referred_table"],
                    tuple(foreign_key["referred_columns"]),
                    tuple(
                        sorted(
                            (key, str(value))
                            for key, value in (foreign_key.get("options") or {}).items()
                        )
                    ),
                )
                for foreign_key in inspector.get_foreign_keys(table_name)
            )
        ),
        "checks": tuple(
            sorted(
                (check.get("name"), normalized_sql(check.get("sqltext")))
                for check in inspector.get_check_constraints(table_name)
            )
        ),
        "unique_constraints": tuple(
            sorted(
                (constraint.get("name"), tuple(constraint["column_names"]))
                for constraint in inspector.get_unique_constraints(table_name)
            )
        ),
        "indexes": tuple(
            sorted(
                (
                    index.get("name"),
                    bool(index.get("unique")),
                    tuple(index.get("column_names") or ()),
                    normalized_sql(
                        (index.get("dialect_options") or {}).get("postgresql_where")
                    ),
                )
                for index in inspector.get_indexes(table_name)
                if not index.get("duplicates_constraint")
            )
        ),
    }


def test_postgresql_prior_head_upgrade_downgrade_upgrade_and_full_model_parity():
    engine = _postgres_engine_or_skip()
    schema = f"s13_pr004_{uuid.uuid4().hex}"
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "b4c5d6e7f8a9_create_column_mapping_memory.py"
    )
    spec = importlib.util.spec_from_file_location("s13_pr004_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    mapping_tables = {
        "column_mapping_profiles",
        "column_mapping_fields",
        "column_mapping_decisions",
        "column_mapping_profile_usages",
    }
    lineage_parent_tables = {
        "users",
        "customers",
        "projects",
        "import_source_artifacts",
        "workbook_structure_snapshots",
    }
    parity_tables = mapping_tables | lineage_parent_tables
    owned_parent_constraints = {
        "uq_s13_pr004_user_tenant_id",
        "uq_s13_pr004_customer_tenant_id",
        "uq_s13_pr004_project_tenant_customer_id",
        "uq_workbook_structure_tenant_source_id",
        "fk_source_artifact_creator_tenant",
        "fk_workbook_structure_creator_tenant",
    }
    later_tables = (
        "dossier_row_alignments",
        "dossier_alignment_runs",
        "dossier_extracted_rows",
        "dossier_extracted_tables",
        "dossier_extraction_snapshots",
        "task_job_attempts",
        "task_jobs",
        "dossier_source_files",
        "dossier_bundles",
        "learning_feedback_events",
        "contextual_asset_aliases",
        "asset_identity_decisions",
        "raw_asset_observations",
        "tenant_boundary_checks",
        "security_audit_logs",
        "security_events",
    )
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            Base.metadata.create_all(connection)
            reference = {
                table_name: _table_signature(connection, table_name)
                for table_name in parity_tables
            }
            for table_name in later_tables:
                table = Base.metadata.tables.get(table_name)
                if table is not None:
                    table.drop(connection, checkfirst=True)
            operations = Operations(MigrationContext.configure(connection))
            migration.op = operations
            migration.downgrade()
            assert mapping_tables.isdisjoint(inspect(connection).get_table_names())

        for _cycle in range(2):
            with engine.begin() as connection:
                connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                operations = Operations(MigrationContext.configure(connection))
                migration.op = operations
                migration.upgrade()
                restored = set(inspect(connection).get_table_names())
                assert mapping_tables.issubset(restored)
                assert {
                    table_name: _table_signature(connection, table_name)
                    for table_name in parity_tables
                } == reference
                migration.downgrade()
                remaining = set(inspect(connection).get_table_names())
                assert mapping_tables.isdisjoint(remaining)
                remaining_constraint_names = {
                    constraint.get("name")
                    for table_name in lineage_parent_tables
                    for constraint in (
                        inspect(connection).get_unique_constraints(table_name)
                        + inspect(connection).get_foreign_keys(table_name)
                    )
                }
                assert owned_parent_constraints.isdisjoint(remaining_constraint_names)

        with engine.begin() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            operations = Operations(MigrationContext.configure(connection))
            migration.op = operations
            migration.upgrade()
            assert {
                table_name: _table_signature(connection, table_name)
                for table_name in parity_tables
            } == reference
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
