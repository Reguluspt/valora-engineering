"""Real PostgreSQL concurrency, recovery, migration and isolation proofs for G8."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.modules.m365_integration.application.exchange_service import (
    execute_exchange_create,
    prepare_exchange_create,
    provision_exchange_namespace,
)
from app.modules.m365_integration.domain.exchange_fake import InMemoryM365GraphGateway
from app.modules.m365_integration.models import (
    M365ConnectionCapability,
    M365ConnectionGrantedScope,
    M365ExchangeOperation,
)
from app.modules.project_master_data.models import Project
from tests.test_pr05_m365_foundation import _connect, _seed


def _postgres_url() -> URL:
    raw = os.getenv("TEST_DATABASE_URL")
    if not raw or not raw.startswith("postgres"):
        if os.getenv("CI", "").strip().lower() in {"1", "true", "yes"}:
            pytest.fail("G8 PostgreSQL proofs require TEST_DATABASE_URL in CI")
        pytest.skip("G8 PostgreSQL proofs require TEST_DATABASE_URL")
    source = make_url(raw)
    engine = create_engine(source, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    finally:
        engine.dispose()
    return source


def _alembic(database_url: URL, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "VALORA_ENV": "test",
            "POSTGRES_HOST": database_url.host or "localhost",
            "POSTGRES_PORT": str(database_url.port or 5432),
            "POSTGRES_DB": database_url.database or "",
            "POSTGRES_USER": database_url.username or "",
            "POSTGRES_PASSWORD": database_url.password or "",
        }
    )
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_alembic(database_url: URL, *arguments: str) -> None:
    result = _alembic(database_url, *arguments)
    if result.returncode != 0:
        pytest.fail(f"Alembic {' '.join(arguments)} failed:\n{result.stdout}\n{result.stderr}")


@pytest.fixture
def postgres_exchange_database() -> URL:
    source = _postgres_url()
    name = f"exchange_g8_{uuid.uuid4().hex}"
    admin = create_engine(
        source.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": 5},
    )
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    database_url = source.set(database=name)
    try:
        yield database_url
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def _context(database_url: URL):
    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    setup = sessions()
    seeded = _seed(setup, suffix="g8-pg")
    connection, _, _ = _connect(setup, seeded)
    graph = InMemoryM365GraphGateway()
    connection.drive_id = graph.drive_id
    capability = setup.query(M365ConnectionCapability).filter_by(
        organization_id=seeded["organization"].id,
        connection_id=connection.id,
        capability_code="APPFOLDER_WRITE_AVAILABLE",
    ).one()
    capability.available = True
    capability.evidence_scope = "files.readwrite.appfolder"
    capability.provenance = "oauth_grant"
    setup.add(
        M365ConnectionGrantedScope(
            organization_id=seeded["organization"].id,
            user_id=seeded["actor"].id,
            connection_id=connection.id,
            normalized_scope="files.readwrite.appfolder",
            provenance="oauth_grant",
        )
    )
    setup.commit()
    identifiers = {
        "organization_id": seeded["organization"].id,
        "project_id": seeded["project"].id,
        "connection_id": connection.id,
    }
    setup.close()
    namespace = provision_exchange_namespace(
        graph_gateway=graph, access_token="offline-token"
    )
    return engine, sessions, graph, namespace, identifiers


def _prepare(db, ids, namespace, *, key: str, content: bytes = b"postgres-g8"):
    return prepare_exchange_create(
        db,
        organization_id=ids["organization_id"],
        project_id=ids["project_id"],
        connection_id=ids["connection_id"],
        idempotency_key=key,
        operation_kind="CREATE_WORKING",
        target_role="working",
        media="docx",
        drive_id=namespace.drive_id,
        destination_parent_item_id=namespace.working_item_id,
        destination_name=f"{key}.docx",
        content=content,
    )


def test_exchange_operation_idempotency_race(postgres_exchange_database: URL):
    engine, sessions, _, namespace, ids = _context(postgres_exchange_database)
    barrier = threading.Barrier(2, timeout=30)
    operation_ids: list[uuid.UUID] = []
    errors: list[BaseException] = []

    def run() -> None:
        db = sessions()
        try:
            barrier.wait(timeout=30)
            operation = _prepare(db, ids, namespace, key="race")
            operation_ids.append(operation.id)
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=run, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert not errors
    assert len(operation_ids) == 2 and len(set(operation_ids)) == 1
    verify = sessions()
    try:
        assert verify.query(M365ExchangeOperation).count() == 1
    finally:
        verify.close()
        engine.dispose()


def test_exchange_duplicate_request_reuses_one_operation(postgres_exchange_database: URL):
    engine, sessions, _, namespace, ids = _context(postgres_exchange_database)
    db = sessions()
    try:
        first = _prepare(db, ids, namespace, key="duplicate")
        second = _prepare(db, ids, namespace, key="duplicate")
        assert first.id == second.id
        assert db.query(M365ExchangeOperation).count() == 1
    finally:
        db.close()
        engine.dispose()


def test_provider_unknown_recovery_after_new_session(postgres_exchange_database: URL):
    engine, sessions, graph, namespace, ids = _context(postgres_exchange_database)
    content = b"provider-unknown-postgres"
    setup = sessions()
    operation = _prepare(setup, ids, namespace, key="unknown", content=content)
    graph.set_fault("after_commit_unknown")
    graph.create_file(
        access_token="offline-token",
        drive_id=operation.drive_id,
        parent_item_id=operation.destination_parent_item_id,
        exact_name=operation.destination_name,
        content=content,
    )
    operation.state = "PROVIDER_UNKNOWN"
    operation_id = operation.id
    setup.commit()
    setup.close()
    recovered = sessions()
    try:
        artifact = execute_exchange_create(
            recovered,
            organization_id=ids["organization_id"],
            operation_id=operation_id,
            content=content,
            graph_gateway=graph,
            access_token="offline-token",
            source_authority_type="PROVIDER_TRANSPORT",
        )
        assert artifact is not None
        assert graph.create_calls == 1
        assert recovered.get(M365ExchangeOperation, operation_id).state == "FINALIZED"
    finally:
        recovered.close()
        engine.dispose()


def test_exchange_tenant_and_project_isolation(postgres_exchange_database: URL):
    engine, sessions, _, namespace, ids = _context(postgres_exchange_database)
    db = sessions()
    second = _seed(db, suffix="g8-isolation")
    wrong_project = second["project"].id
    db.commit()
    try:
        with pytest.raises(Exception) as exc:
            prepare_exchange_create(
                db,
                organization_id=ids["organization_id"],
                project_id=wrong_project,
                connection_id=ids["connection_id"],
                idempotency_key="isolation",
                operation_kind="CREATE_WORKING",
                target_role="working",
                media="docx",
                drive_id=namespace.drive_id,
                destination_parent_item_id=namespace.working_item_id,
                destination_name="Isolation.docx",
                content=b"isolation",
            )
        assert getattr(exc.value, "status_code", None) == 404
        assert db.query(Project).filter_by(id=ids["project_id"]).count() == 1
    finally:
        db.close()
        engine.dispose()


def test_exchange_migration_up_down_up_when_empty(postgres_exchange_database: URL):
    _run_alembic(postgres_exchange_database, "upgrade", "b8d9e0f1a2b3")
    _run_alembic(postgres_exchange_database, "upgrade", "head")
    engine = create_engine(postgres_exchange_database)
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        assert {"m365_exchange_artifacts", "m365_exchange_operations"} <= tables
        assert "intent_kind" in {
            column["name"]
            for column in inspect(connection).get_columns("document_storage_execution_intents")
        }
    _run_alembic(postgres_exchange_database, "downgrade", "b8d9e0f1a2b3")
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        assert "m365_exchange_artifacts" not in tables
        assert "m365_exchange_operations" not in tables
    _run_alembic(postgres_exchange_database, "upgrade", "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "c9d0e1f2a3b4"
        )
    engine.dispose()
