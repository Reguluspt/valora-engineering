"""PostgreSQL migration and concurrency proofs for PR-05."""
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
from sqlalchemy.orm import Session, sessionmaker

from app.modules.document_workspace.application.document_revision_service import (
    create_document_with_first_revision,
)
from app.modules.document_workspace.models import DocumentRecord, DocumentRevision
from app.modules.m365_integration.application.bind_document_service import (
    bind_document_revision,
)
from app.modules.m365_integration.application.connection_service import (
    complete_onedrive_authorization,
)
from app.modules.m365_integration.infrastructure.credential_vault import (
    DatabaseCredentialVault,
)
from app.modules.m365_integration.models import M365RevisionBinding, OneDriveConnection
from app.modules.project_master_data.models import AuditEvent, User
from tests.test_pr05_m365_foundation import (
    CONTENT_CHECKSUM,
    SNAPSHOT_DIGEST,
    FakeGraphGateway,
    FakeOAuthClient,
    _connect,
    _document,
    _seed,
    _vault,
)


PR05_TABLES = {
    "document_records",
    "document_revisions",
    "document_revision_current_heads",
    "m365_encrypted_credentials",
    "onedrive_connections",
    "m365_oauth_states",
    "m365_revision_bindings",
}
PR05_INDEXES = {
    "document_records": {"idx_document_records_project"},
    "document_revisions": {"idx_document_revisions_record"},
    "m365_encrypted_credentials": {"idx_m365_credentials_owner"},
    "onedrive_connections": {"idx_onedrive_connections_owner"},
    "m365_oauth_states": {"idx_m365_oauth_state_owner"},
    "m365_revision_bindings": {"idx_m365_binding_item"},
}


def _source_url_or_skip() -> URL:
    raw = os.getenv("TEST_DATABASE_URL")
    if not raw or not raw.startswith("postgres"):
        if os.getenv("CI") == "true":
            pytest.fail("CI=true requires PostgreSQL TEST_DATABASE_URL for PR-05")
        pytest.skip("PR-05 PostgreSQL proof requires TEST_DATABASE_URL")
    url = make_url(raw)
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    finally:
        engine.dispose()
    return url


def _run_alembic(database_url: URL, *arguments: str) -> None:
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
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            f"Alembic {' '.join(arguments)} failed:\n{result.stdout}\n{result.stderr}"
        )


@pytest.fixture
def postgres_database_url() -> URL:
    source_url = _source_url_or_skip()
    database_name = f"pr05_m365_{uuid.uuid4().hex}"
    admin_engine = create_engine(
        source_url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": 5},
    )
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    database_url = source_url.set(database=database_name)
    try:
        yield database_url
    finally:
        with admin_engine.connect() as connection:
            connection.execute(
                text(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')
            )
        admin_engine.dispose()


def _artifacts(database_url: URL) -> dict[str, object]:
    engine = create_engine(database_url, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            tables = set(inspector.get_table_names()) & PR05_TABLES
            indexes = {
                table_name: {
                    index["name"]
                    for index in inspector.get_indexes(table_name)
                    if index.get("name") in expected
                }
                for table_name, expected in PR05_INDEXES.items()
                if table_name in tables
            }
            return {"tables": tables, "indexes": indexes}
    finally:
        engine.dispose()


def test_migration_upgrade_downgrade_upgrade_restores_pr05_artifacts(
    postgres_database_url: URL,
) -> None:
    _run_alembic(postgres_database_url, "upgrade", "d4b7c9e2f1a6")
    assert _artifacts(postgres_database_url)["tables"] == set()

    _run_alembic(postgres_database_url, "upgrade", "f4c8d2a1b7e9")
    reference = _artifacts(postgres_database_url)
    assert reference["tables"] == PR05_TABLES
    assert reference["indexes"] == PR05_INDEXES

    _run_alembic(postgres_database_url, "downgrade", "d4b7c9e2f1a6")
    assert _artifacts(postgres_database_url)["tables"] == set()

    _run_alembic(postgres_database_url, "upgrade", "f4c8d2a1b7e9")
    assert _artifacts(postgres_database_url) == reference


def test_concurrent_same_document_command_creates_one_fact_and_audit(
    postgres_database_url: URL,
) -> None:
    _run_alembic(postgres_database_url, "upgrade", "f4c8d2a1b7e9")
    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine)
    setup: Session = session_factory()
    try:
        seeded = _seed(setup, suffix="pg-race")
        organization_id = seeded["organization"].id
        project_id = seeded["project"].id
        actor_id = seeded["actor"].id
    finally:
        setup.close()

    barrier = threading.Barrier(2, timeout=30)
    results: list[uuid.UUID] = []
    errors: list[BaseException] = []

    def worker() -> None:
        db: Session = session_factory()
        try:
            actor = db.get(User, actor_id)
            assert actor is not None
            barrier.wait(timeout=30)
            revision = create_document_with_first_revision(
                db,
                actor=actor,
                organization_id=organization_id,
                project_id=project_id,
                document_type="valuation_report",
                title="Concurrent report",
                data_snapshot_digest_sha256=SNAPSHOT_DIGEST,
                content_checksum_sha256=CONTENT_CHECKSUM,
                idempotency_key="pr05-concurrent-document",
            )
            results.append(revision.id)
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert all(not thread.is_alive() for thread in threads)
    assert errors == []
    assert len(results) == 2
    assert len(set(results)) == 1

    verify: Session = session_factory()
    try:
        assert verify.query(DocumentRecord).filter_by(
            organization_id=organization_id
        ).count() == 1
        assert verify.query(DocumentRevision).filter_by(
            organization_id=organization_id
        ).count() == 1
        assert verify.query(AuditEvent).filter_by(
            organization_id=organization_id,
            event_name="DOCUMENT_REVISION_CREATED",
        ).count() == 1
    finally:
        verify.close()
        engine.dispose()


def test_concurrent_oauth_callback_consumes_state_once(
    postgres_database_url: URL,
) -> None:
    _run_alembic(postgres_database_url, "upgrade", "head")
    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine)
    setup: Session = session_factory()
    try:
        seeded = _seed(setup, suffix="pg-oauth-race")
        oauth = FakeOAuthClient()
        graph = FakeGraphGateway()
        vault = _vault(setup)
        from app.modules.m365_integration.application.connection_service import (
            begin_onedrive_authorization,
        )

        begin_onedrive_authorization(
            setup,
            actor=seeded["actor"],
            user_session=seeded["session"],
            oauth_client=oauth,
            credential_vault=vault,
        )
        organization_id = seeded["organization"].id
    finally:
        setup.close()

    barrier = threading.Barrier(2, timeout=30)
    results: list[uuid.UUID] = []
    errors: list[BaseException] = []

    def worker() -> None:
        db: Session = session_factory()
        try:
            barrier.wait(timeout=30)
            connection = complete_onedrive_authorization(
                db,
                auth_response={"state": oauth.state, "code": "authorization-code"},
                oauth_client=oauth,
                graph_gateway=graph,
                credential_vault=DatabaseCredentialVault(
                    db,
                    keys={"v1": b"1" * 32, "v2": b"2" * 32},
                    active_key_version="v1",
                ),
            )
            results.append(connection.id)
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert all(not thread.is_alive() for thread in threads)
    assert len(results) == 1
    assert len(errors) == 1
    assert getattr(errors[0], "status_code", None) == 400
    assert errors[0].detail["error_code"] == "onedrive_oauth_state_invalid"

    verify: Session = session_factory()
    try:
        assert verify.query(OneDriveConnection).filter_by(
            organization_id=organization_id
        ).count() == 1
        assert verify.query(AuditEvent).filter_by(
            organization_id=organization_id,
            event_name="ONEDRIVE_CONNECTION_ACTIVATED",
        ).count() == 1
    finally:
        verify.close()
        engine.dispose()


def test_concurrent_same_binding_command_creates_one_fact_and_audit(
    postgres_database_url: URL,
) -> None:
    _run_alembic(postgres_database_url, "upgrade", "head")
    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine)
    setup: Session = session_factory()
    try:
        seeded = _seed(setup, suffix="pg-binding-race")
        connection, _, _ = _connect(setup, seeded)
        revision = _document(setup, seeded)
        ids = {
            "organization": seeded["organization"].id,
            "project": seeded["project"].id,
            "actor": seeded["actor"].id,
            "connection": connection.id,
            "document": revision.document_id,
            "revision": revision.id,
        }
    finally:
        setup.close()

    barrier = threading.Barrier(2, timeout=30)
    results: list[uuid.UUID] = []
    errors: list[BaseException] = []

    def worker() -> None:
        db: Session = session_factory()
        try:
            actor = db.get(User, ids["actor"])
            assert actor is not None
            barrier.wait(timeout=30)
            binding = bind_document_revision(
                db,
                actor=actor,
                organization_id=ids["organization"],
                project_id=ids["project"],
                document_id=ids["document"],
                document_revision_id=ids["revision"],
                expected_document_revision=1,
                connection_id=ids["connection"],
                drive_item_id="concurrent-stable-item",
                idempotency_key="pr05-concurrent-binding",
                oauth_client=FakeOAuthClient(),
                graph_gateway=FakeGraphGateway(),
                credential_vault=DatabaseCredentialVault(
                    db,
                    keys={"v1": b"1" * 32, "v2": b"2" * 32},
                    active_key_version="v1",
                ),
            )
            results.append(binding.id)
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert all(not thread.is_alive() for thread in threads)
    assert errors == []
    assert len(results) == 2
    assert len(set(results)) == 1

    verify: Session = session_factory()
    try:
        assert verify.query(M365RevisionBinding).filter_by(
            organization_id=ids["organization"]
        ).count() == 1
        assert verify.query(AuditEvent).filter_by(
            organization_id=ids["organization"],
            event_name="M365_REVISION_BOUND",
        ).count() == 1
    finally:
        verify.close()
        engine.dispose()
