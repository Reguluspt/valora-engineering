"""Real PostgreSQL concurrency, recovery, migration and isolation proofs for G8."""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.modules.document_workspace.domain.document_blob_store import (
    InMemoryDocumentBlobStore,
)
from app.modules.document_workspace.models import (
    DocumentRevision,
    DocumentRevisionCurrentHead,
)
from app.modules.excel_import.infrastructure.object_storage import (
    FakeObjectStorage,
    set_object_storage_override,
)
from app.modules.excel_import.models import ImportSourceArtifact
from app.modules.m365_integration.application import (
    exchange_import_service,
    exchange_service,
)
from app.modules.m365_integration.application.exchange_import_service import (
    create_docx_working_copy,
    import_inbox_docx,
    import_inbox_xlsx,
    reimport_working_docx,
)
from app.modules.m365_integration.application.exchange_service import (
    execute_exchange_create,
    prepare_exchange_create,
    provision_exchange_namespace,
)
from app.modules.m365_integration.domain.exchange_fake import InMemoryM365GraphGateway
from app.modules.m365_integration.models import (
    M365ConnectionCapability,
    M365ConnectionGrantedScope,
    M365ExchangeArtifact,
    M365ExchangeOperation,
)
from app.modules.project_master_data.models import (
    Project,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    User,
)
from tests.test_g8_onedrive_exchange import (
    REGIONS,
    RETENTION_ANCHOR,
    RETENTION_UNTIL,
    _docx,
    _xlsx,
)
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
        "actor_id": seeded["actor"].id,
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


def test_exchange_execute_replay_race_returns_one_artifact(
    postgres_exchange_database: URL, monkeypatch
):
    engine, sessions, graph, namespace, ids = _context(postgres_exchange_database)
    content = b"execute-race-postgres"
    setup = sessions()
    operation = _prepare(setup, ids, namespace, key="execute-race", content=content)
    created = graph.create_file(
        access_token="offline-token",
        drive_id=operation.drive_id,
        parent_item_id=operation.destination_parent_item_id,
        exact_name=operation.destination_name,
        content=content,
    )
    assert created.item is not None
    operation.state = "PROVIDER_UNKNOWN"
    operation_id = operation.id
    setup.commit()
    setup.close()

    barrier = threading.Barrier(2, timeout=30)
    original_reconcile = exchange_service._reconcile_created_item

    def synchronized_reconcile(**kwargs):
        item = original_reconcile(**kwargs)
        barrier.wait(timeout=30)
        return item

    monkeypatch.setattr(
        exchange_service, "_reconcile_created_item", synchronized_reconcile
    )
    artifact_ids: list[uuid.UUID] = []
    errors: list[BaseException] = []

    def run() -> None:
        db = sessions()
        try:
            artifact = execute_exchange_create(
                db,
                organization_id=ids["organization_id"],
                operation_id=operation_id,
                content=content,
                graph_gateway=graph,
                access_token="offline-token",
                source_authority_type="PROVIDER_TRANSPORT",
            )
            assert artifact is not None
            artifact_ids.append(artifact.id)
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=run, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    verify = sessions()
    try:
        assert all(not thread.is_alive() for thread in threads)
        assert not errors
        assert len(artifact_ids) == 2 and len(set(artifact_ids)) == 1
        assert verify.query(M365ExchangeArtifact).count() == 1
        assert verify.get(M365ExchangeOperation, operation_id).state == "FINALIZED"
    finally:
        verify.close()
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


def test_exchange_docx_reimport_current_head_race_is_fail_closed(
    postgres_exchange_database: URL, monkeypatch
):
    engine, sessions, graph, namespace, ids = _context(postgres_exchange_database)
    blob_store = InMemoryDocumentBlobStore()
    setup = sessions()
    actor = setup.get(User, ids["actor_id"])
    inbox = graph.seed_file(
        parent_item_id=namespace.inbox_item_id,
        name="PG-initial.docx",
        content=_docx(outside="PG initial"),
    )
    initial, _, _ = asyncio.run(
        import_inbox_docx(
            setup,
            actor=actor,
            organization_id=ids["organization_id"],
            project_id=ids["project_id"],
            connection_id=ids["connection_id"],
            drive_item_id=inbox.drive_item_id,
            document_type="valuation_report",
            title="Báo cáo PG",
            definition_set=REGIONS,
            idempotency_key="pg-docx-initial",
            graph_gateway=graph,
            access_token="offline-token",
            blob_store=blob_store,
            storage_profile_id="g8-fake",
            container_name="g8-documents",
            retention_policy_code="official-document-10y",
            retention_anchor_at=RETENTION_ANCHOR,
            minimum_retain_until=RETENTION_UNTIL,
        )
    )
    working = []
    for suffix in ("older", "winner"):
        artifact = asyncio.run(
            create_docx_working_copy(
                setup,
                actor=actor,
                organization_id=ids["organization_id"],
                project_id=ids["project_id"],
                connection_id=ids["connection_id"],
                document_id=initial.document_id,
                destination_name=f"PG-{suffix}.docx",
                idempotency_key=f"pg-docx-{suffix}",
                graph_gateway=graph,
                access_token="offline-token",
                blob_store=blob_store,
            )
        )
        assert artifact is not None
        working.append(artifact.id)
        graph.replace_file_content(
            drive_item_id=artifact.drive_item_id,
            content=_docx(outside=f"PG {suffix}"),
        )
    document_id = initial.document_id
    initial_revision_id = initial.id
    setup.close()

    entered = threading.Event()
    release = threading.Event()
    calls_lock = threading.Lock()
    calls = 0
    original_finalize = exchange_import_service.finalize_storage_revision

    def gated_finalize(db, **kwargs):
        nonlocal calls
        with calls_lock:
            calls += 1
            is_older = calls == 1
        if is_older:
            entered.set()
            assert release.wait(timeout=30), "older DOCX finalize was not released"
        return original_finalize(db, **kwargs)

    monkeypatch.setattr(
        exchange_import_service, "finalize_storage_revision", gated_finalize
    )
    older_errors: list[BaseException] = []

    def run_older() -> None:
        db = sessions()
        try:
            asyncio.run(
                reimport_working_docx(
                    db,
                    actor=db.get(User, ids["actor_id"]),
                    organization_id=ids["organization_id"],
                    project_id=ids["project_id"],
                    artifact_id=working[0],
                    definition_set=REGIONS,
                    idempotency_key="pg-docx-reimport-older",
                    graph_gateway=graph,
                    access_token="offline-token",
                    blob_store=blob_store,
                    storage_profile_id="g8-fake",
                    container_name="g8-documents",
                    retention_policy_code="official-document-10y",
                    retention_anchor_at=RETENTION_ANCHOR,
                    minimum_retain_until=RETENTION_UNTIL,
                )
            )
        except BaseException as exc:
            older_errors.append(exc)
        finally:
            db.close()

    older = threading.Thread(target=run_older, daemon=True)
    older.start()
    assert entered.wait(timeout=30), "older DOCX reimport never reached finalize"
    winner_db = sessions()
    try:
        winner = asyncio.run(
            reimport_working_docx(
                winner_db,
                actor=winner_db.get(User, ids["actor_id"]),
                organization_id=ids["organization_id"],
                project_id=ids["project_id"],
                artifact_id=working[1],
                definition_set=REGIONS,
                idempotency_key="pg-docx-reimport-winner",
                graph_gateway=graph,
                access_token="offline-token",
                blob_store=blob_store,
                storage_profile_id="g8-fake",
                container_name="g8-documents",
                retention_policy_code="official-document-10y",
                retention_anchor_at=RETENTION_ANCHOR,
                minimum_retain_until=RETENTION_UNTIL,
            )
        )
        winner_revision_id = winner.revision.id
    finally:
        winner_db.close()
        release.set()
    older.join(timeout=60)

    verify = sessions()
    try:
        assert not older.is_alive()
        assert len(older_errors) == 1
        assert isinstance(older_errors[0], HTTPException)
        assert older_errors[0].status_code == 409
        assert older_errors[0].detail["error_code"] == "storage_head_superseded"
        revisions = verify.query(DocumentRevision).filter_by(document_id=document_id).all()
        head = verify.query(DocumentRevisionCurrentHead).filter_by(
            document_id=document_id
        ).one()
        assert len(revisions) == 2
        assert head.document_revision == 2
        assert head.current_revision_id == winner_revision_id
        assert head.current_revision_id != initial_revision_id
    finally:
        verify.close()
        engine.dispose()


def test_exchange_xlsx_source_generation_race_blocks_stale_staging(
    postgres_exchange_database: URL,
):
    engine, sessions, graph, namespace, ids = _context(postgres_exchange_database)
    entered = threading.Event()
    release = threading.Event()

    class GatedFakeObjectStorage(FakeObjectStorage):
        def __init__(self) -> None:
            super().__init__()
            self.armed = False
            self.calls_after_arm = 0
            self.calls_lock = threading.Lock()

        def put_stream(self, key, stream, *, content_type, expected_size=None):
            result = super().put_stream(
                key,
                stream,
                content_type=content_type,
                expected_size=expected_size,
            )
            if self.armed:
                with self.calls_lock:
                    self.calls_after_arm += 1
                    is_older = self.calls_after_arm == 1
                if is_older:
                    entered.set()
                    assert release.wait(timeout=30), "older XLSX upload was not released"
            return result

    storage = GatedFakeObjectStorage()
    set_object_storage_override(storage)
    setup = sessions()
    actor = setup.get(User, ids["actor_id"])
    batch = ProjectAssetImportBatch(
        organization_id=ids["organization_id"],
        project_id=ids["project_id"],
        source_filename="PG-source.xlsx",
        created_by_user_id=ids["actor_id"],
    )
    setup.add(batch)
    setup.commit()
    item = graph.seed_file(
        parent_item_id=namespace.inbox_item_id,
        name="PG-source.xlsx",
        content=_xlsx(asset_name="PG initial"),
    )
    initial = import_inbox_xlsx(
        setup,
        actor=actor,
        organization_id=ids["organization_id"],
        project_id=ids["project_id"],
        connection_id=ids["connection_id"],
        batch_id=batch.id,
        drive_item_id=item.drive_item_id,
        graph_gateway=graph,
        access_token="offline-token",
        request=SimpleNamespace(headers={}),
    )
    batch_id = batch.id
    exchange_artifact_id = initial.id
    initial_source_id = initial.excel_source_artifact_id
    graph.replace_file_content(
        drive_item_id=item.drive_item_id,
        content=_xlsx(asset_name="PG newest"),
    )
    setup.close()
    storage.armed = True
    older_errors: list[BaseException] = []

    def run_older() -> None:
        db = sessions()
        try:
            import_inbox_xlsx(
                db,
                actor=db.get(User, ids["actor_id"]),
                organization_id=ids["organization_id"],
                project_id=ids["project_id"],
                connection_id=ids["connection_id"],
                batch_id=batch_id,
                drive_item_id=item.drive_item_id,
                graph_gateway=graph,
                access_token="offline-token",
                request=SimpleNamespace(headers={}),
                reimport=True,
            )
        except BaseException as exc:
            older_errors.append(exc)
        finally:
            db.close()

    older = threading.Thread(target=run_older, daemon=True)
    older.start()
    try:
        assert entered.wait(timeout=30), "older XLSX reimport never wrote generation 2"
        winner_db = sessions()
        try:
            winner = import_inbox_xlsx(
                winner_db,
                actor=winner_db.get(User, ids["actor_id"]),
                organization_id=ids["organization_id"],
                project_id=ids["project_id"],
                connection_id=ids["connection_id"],
                batch_id=batch_id,
                drive_item_id=item.drive_item_id,
                graph_gateway=graph,
                access_token="offline-token",
                request=SimpleNamespace(headers={}),
                reimport=True,
            )
            winner_source_id = winner.excel_source_artifact_id
        finally:
            winner_db.close()
            release.set()
        older.join(timeout=60)
    finally:
        release.set()
        set_object_storage_override(None)

    verify = sessions()
    try:
        assert not older.is_alive()
        assert len(older_errors) == 1
        assert isinstance(older_errors[0], HTTPException)
        assert older_errors[0].status_code == 409
        assert older_errors[0].detail["error_code"] == "exchange_excel_source_conflict"
        sources = (
            verify.query(ImportSourceArtifact)
            .filter_by(import_batch_id=batch_id)
            .order_by(ImportSourceArtifact.generation)
            .all()
        )
        current = verify.get(ProjectAssetImportBatch, batch_id)
        artifact = verify.get(M365ExchangeArtifact, exchange_artifact_id)
        staged = verify.query(ProjectAssetImportStagingRow).filter_by(
            import_batch_id=batch_id
        ).all()
        assert [source.generation for source in sources] == [1, 2, 3]
        assert sources[1].state == "orphaned"
        assert current.current_source_artifact_id == winner_source_id
        assert artifact.excel_source_artifact_id == winner_source_id
        assert winner_source_id != initial_source_id
        assert [row.proposed_asset_name for row in staged] == ["PG newest"]
    finally:
        verify.close()
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
