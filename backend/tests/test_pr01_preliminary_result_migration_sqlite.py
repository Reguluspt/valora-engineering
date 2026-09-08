"""SQLite migration proof for PR-01 PreliminaryResultArtifact idempotency hardening.

This test isolates the new migration by building the pre-migration table shape
with SQLAlchemy, then invoking the migration script's upgrade/downgrade under an
Alembic Operations context. The full migration chain is not run because older
migrations use SQLite-unsupported ALTER CONSTRAINT statements.
"""
from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

import pytest
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Uuid,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.sql import func

_migration_path = (
    Path(__file__).resolve().parents[1] / "alembic" / "versions" / "c159fab13c3a_harden_preliminary_result_idempotency.py"
)
_spec = importlib.util.spec_from_file_location(
    "c159fab13c3a_harden_preliminary_result_idempotency", _migration_path
)
_migration_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_migration_module)
migration_upgrade = _migration_module.upgrade
migration_downgrade = _migration_module.downgrade


@pytest.fixture
def sqlite_migration_env():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        yield {"db_path": db_path, "engine": engine}
    finally:
        engine.dispose()


def _create_pre_migration_table(engine) -> None:
    """Create preliminary_result_artifacts with the shape before c159fab13c3a."""
    metadata = MetaData()
    Table(
        "preliminary_result_artifacts",
        metadata,
        Column("id", Uuid, primary_key=True),
        Column("organization_id", Uuid, nullable=False),
        Column("customer_id", Uuid, nullable=False),
        Column("project_id", Uuid, nullable=False),
        Column("version", Integer, nullable=False),
        Column("original_filename", String(255), nullable=False),
        Column("content_type", String(128), nullable=False),
        Column("file_size_bytes", BigInteger, nullable=False),
        Column("content_checksum_sha256", String(64), nullable=False),
        Column("storage_object_key", String(1024), nullable=False),
        Column("source_snapshot_sha256", String(64), nullable=False),
        Column("lineage_manifest", String, nullable=False),
        Column("created_by_user_id", Uuid, nullable=False),
        Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
        Index("idx_preliminary_result_project", "organization_id", "project_id"),
    )
    metadata.create_all(engine)


def _pairing_constraint_present(conn) -> bool:
    sql = conn.execute(
        text(
            "SELECT sql FROM sqlite_master WHERE type='table' "
            "AND name='preliminary_result_artifacts'"
        )
    ).scalar_one()
    return "chk_preliminary_result_request_pairing" in sql


def test_migration_adds_idempotency_columns_and_partial_index(sqlite_migration_env: dict) -> None:
    engine = sqlite_migration_env["engine"]
    _create_pre_migration_table(engine)

    with engine.connect() as conn:
        with conn.begin():
            ctx = MigrationContext.configure(conn)
            op = Operations(ctx)
            # Bind the global alembic op proxy used by the migration script.
            import alembic.op as alembic_op_module

            original_op = getattr(alembic_op_module, "_proxy", None)
            try:
                alembic_op_module._proxy = op  # type: ignore[attr-defined]
                migration_upgrade()
            finally:
                if original_op is not None:
                    alembic_op_module._proxy = original_op  # type: ignore[attr-defined]

    with engine.connect() as conn:
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(preliminary_result_artifacts)"))}
        assert "idempotency_key" in columns
        assert "request_digest_sha256" in columns

    inspector = inspect(engine)
    indexes = {idx["name"]: idx for idx in inspector.get_indexes("preliminary_result_artifacts")}
    assert "uq_preliminary_result_idempotency" in indexes
    idx = indexes["uq_preliminary_result_idempotency"]
    assert idx["unique"]
    assert set(idx["column_names"]) == {"organization_id", "idempotency_key"}

    with engine.connect() as conn:
        assert _pairing_constraint_present(conn)


def test_migration_downgrade_removes_idempotency_columns(sqlite_migration_env: dict) -> None:
    engine = sqlite_migration_env["engine"]
    _create_pre_migration_table(engine)

    with engine.connect() as conn:
        with conn.begin():
            ctx = MigrationContext.configure(conn)
            op = Operations(ctx)
            import alembic.op as alembic_op_module

            original_op = getattr(alembic_op_module, "_proxy", None)
            try:
                alembic_op_module._proxy = op  # type: ignore[attr-defined]
                migration_upgrade()
                migration_downgrade()
            finally:
                if original_op is not None:
                    alembic_op_module._proxy = original_op  # type: ignore[attr-defined]

    with engine.connect() as conn:
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(preliminary_result_artifacts)"))}
        assert "idempotency_key" not in columns
        assert "request_digest_sha256" not in columns

    inspector = inspect(engine)
    indexes = {idx["name"] for idx in inspector.get_indexes("preliminary_result_artifacts")}
    assert "uq_preliminary_result_idempotency" not in indexes

    with engine.connect() as conn:
        assert not _pairing_constraint_present(conn)
