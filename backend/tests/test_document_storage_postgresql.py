"""PostgreSQL two-session current-head CAS proofs for T8/T9/T14."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.modules.document_workspace.application.document_storage_service import (
    create_or_recover_storage_object,
    finalize_storage_revision,
    prepare_storage_intent,
    record_storage_candidate,
)
from app.modules.document_workspace.domain.document_blob_store import InMemoryDocumentBlobStore
from app.modules.document_workspace.models import (
    DocumentRevision,
    DocumentRevisionCurrentHead,
    DocumentStorageExecutionState,
    StorageObjectBinding,
)
from app.modules.project_master_data.models import User
from tests.test_document_storage_service import (
    DECISION_DIGEST,
    PLAN_DIGEST,
    REQUEST_DIGEST,
    RETENTION_ANCHOR,
    RETENTION_UNTIL,
    _content,
    _invoke,
)
from tests.test_pr05_m365_foundation import _document, _seed


def _postgres_url() -> URL:
    raw = os.getenv("TEST_DATABASE_URL")
    if not raw or not raw.startswith("postgres"):
        if os.getenv("CI", "").strip().lower() in {"1", "true", "yes"}:
            pytest.fail("VALORA-STORAGE-FAKE-001 PostgreSQL CAS proof requires TEST_DATABASE_URL in CI")
        pytest.skip("VALORA-STORAGE-FAKE-001 PostgreSQL CAS proof requires TEST_DATABASE_URL")
    source = make_url(raw)
    engine = create_engine(source, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    finally:
        engine.dispose()
    return source


def _alembic_result(
    database_url: URL, *arguments: str
) -> subprocess.CompletedProcess[str]:
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
    result = _alembic_result(database_url, *arguments)
    if result.returncode != 0:
        pytest.fail(f"Alembic {' '.join(arguments)} failed:\n{result.stdout}\n{result.stderr}")


@pytest.fixture
def postgres_storage_database() -> URL:
    source = _postgres_url()
    name = f"storage_fake_{uuid.uuid4().hex}"
    admin = create_engine(source.set(database="postgres"), isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 5})
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    database_url = source.set(database=name)
    try:
        yield database_url
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def _ctx(database_url: URL, suffix: str) -> dict[str, Any]:
    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    setup = sessions()
    seeded = _seed(setup, suffix=suffix)
    revision = _document(setup, seeded)
    setup.refresh(revision, attribute_names=["document_id"])
    scalar_ids = {
        "organization_id": inspect(seeded["organization"]).identity[0],
        "project_id": inspect(seeded["project"]).identity[0],
        "actor_id": inspect(seeded["actor"]).identity[0],
        "document_id": revision.document_id,
        "revision_id": inspect(revision).identity[0],
    }
    setup.close()
    return {"engine": engine, "sessions": sessions, **scalar_ids}


def _prepare(db: Session, ctx: dict[str, Any], key: str) -> uuid.UUID:
    actor = db.get(User, ctx["actor_id"])
    intent = prepare_storage_intent(
        db, actor=actor, organization_id=ctx["organization_id"], project_id=ctx["project_id"],
        document_id=ctx["document_id"], idempotency_key=key,
        request_digest_sha256=REQUEST_DIGEST, plan_digest_sha256=PLAN_DIGEST,
        decision_digest_sha256=DECISION_DIGEST,
    )
    identity = inspect(intent).identity
    assert identity is not None
    return identity[0]


def _candidate_and_verify(
    db: Session, ctx: dict[str, Any], intent_id: uuid.UUID, label: str, provider
):
    content, checksum = _content(label)
    candidate = record_storage_candidate(
        db, organization_id=ctx["organization_id"], intent_id=intent_id, content=content,
        provider_kind="fake",
        storage_profile_id="fake-local", container_name="valora-test",
        object_key=f"tenant/{ctx['organization_id']}/intent/{intent_id}",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        generator_version="test-generator-v1",
    )
    db.refresh(candidate, attribute_names=["content_sha256"])
    assert candidate.content_sha256 == checksum
    state = _invoke(create_or_recover_storage_object(
        db, organization_id=ctx["organization_id"], intent_id=intent_id,
        content=content, blob_store=provider,
    ))
    assert state.current_state == "OBJECT_VERIFIED"
    return content


def _finalize(db: Session, ctx: dict[str, Any], intent_id: uuid.UUID):
    return finalize_storage_revision(
        db, organization_id=ctx["organization_id"], intent_id=intent_id,
        retention_policy_code="official-document-10y", retention_anchor_at=RETENTION_ANCHOR,
        minimum_retain_until=RETENTION_UNTIL,
    )


def test_t8_two_mandatory_competing_writers_only_one_advances_head(postgres_storage_database: URL) -> None:
    ctx = _ctx(postgres_storage_database, "t8")
    setup = ctx["sessions"]()
    intent_ids = [_prepare(setup, ctx, f"writer-{i}") for i in ("a", "b")]
    providers = [InMemoryDocumentBlobStore(), InMemoryDocumentBlobStore()]
    for intent_id, label, provider in zip(intent_ids, ("writer-a", "writer-b"), providers):
        _candidate_and_verify(setup, ctx, intent_id, label, provider)
    setup.close()
    barrier = threading.Barrier(2, timeout=30)
    results: list[uuid.UUID] = []
    errors: list[BaseException] = []

    def run(index: int) -> None:
        db = ctx["sessions"]()
        try:
            barrier.wait(timeout=30)
            binding = _finalize(db, ctx, intent_ids[index])
            binding_identity = inspect(binding).identity
            assert binding_identity is not None
            results.append(binding_identity[0])
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=run, args=(i,), daemon=True) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert all(not thread.is_alive() for thread in threads)
    assert len(results) == 1
    assert len(errors) == 1
    assert getattr(errors[0], "status_code", None) == 409
    verify = ctx["sessions"]()
    try:
        assert verify.query(DocumentRevision).filter_by(document_id=ctx["document_id"]).count() == 2
        assert verify.query(DocumentStorageExecutionState).filter_by(current_state="SUPERSEDED").count() == 1
        assert verify.query(StorageObjectBinding).filter_by(document_id=ctx["document_id"]).count() == 1
        assert verify.query(DocumentRevisionCurrentHead).one().document_revision == 2
    finally:
        verify.close()
        ctx["engine"].dispose()


def test_t9_current_head_cas_loss_rolls_back_loser_revision_and_binding(postgres_storage_database: URL) -> None:
    ctx = _ctx(postgres_storage_database, "t9")
    setup = ctx["sessions"]()
    intent_a_id = _prepare(setup, ctx, "writer-a")
    intent_b_id = _prepare(setup, ctx, "writer-b")
    _candidate_and_verify(setup, ctx, intent_a_id, "writer-a", InMemoryDocumentBlobStore())
    _candidate_and_verify(setup, ctx, intent_b_id, "writer-b", InMemoryDocumentBlobStore())
    setup.close()
    db_b = ctx["sessions"]()
    try:
        result_b = _finalize(db_b, ctx, intent_b_id)
        db_b.refresh(result_b, attribute_names=["document_revision_id"])
        result_b_revision_id = result_b.document_revision_id
        del result_b
    finally:
        db_b.close()
    db_a = ctx["sessions"]()
    try:
        with pytest.raises(Exception) as exc:
            _finalize(db_a, ctx, intent_a_id)
        assert getattr(exc.value, "status_code", None) == 409
    finally:
        db_a.close()
    verify = ctx["sessions"]()
    try:
        assert verify.query(DocumentRevision).filter_by(document_id=ctx["document_id"]).count() == 2
        assert verify.query(DocumentRevisionCurrentHead).one().current_revision_id == result_b_revision_id
        assert verify.query(StorageObjectBinding).filter_by(execution_intent_id=intent_a_id).count() == 0
        assert verify.query(DocumentStorageExecutionState).filter_by(execution_intent_id=intent_a_id).one().current_state == "SUPERSEDED"
    finally:
        verify.close()
        ctx["engine"].dispose()


def test_t14_postgresql_replayed_finalize_keeps_one_revision(postgres_storage_database: URL) -> None:
    ctx = _ctx(postgres_storage_database, "t14")
    db = ctx["sessions"]()
    try:
        intent_id = _prepare(db, ctx, "replay-key")
        _candidate_and_verify(db, ctx, intent_id, "replay", InMemoryDocumentBlobStore())
        first = _finalize(db, ctx, intent_id)
        first_identity = inspect(first).identity
        assert first_identity is not None
        replay = _finalize(db, ctx, intent_id)
        replay_identity = inspect(replay).identity
        assert replay_identity == first_identity
        assert db.query(DocumentRevision).filter_by(document_id=ctx["document_id"]).count() == 2
    finally:
        db.close()
        ctx["engine"].dispose()


def test_s5_storage_migration_roundtrip_restores_tables_and_checksum_constraint(
    postgres_storage_database: URL,
) -> None:
    storage_tables = {
        "document_storage_execution_intents",
        "document_storage_candidates",
        "document_storage_execution_events",
        "document_storage_execution_states",
        "storage_object_bindings",
    }

    def artifacts() -> tuple[set[str], set[str], dict[str, str]]:
        engine = create_engine(postgres_storage_database, connect_args={"connect_timeout": 5})
        try:
            with engine.connect() as connection:
                inspector = inspect(connection)
                tables = set(inspector.get_table_names())
                return (
                    tables,
                    {
                        constraint["name"]
                        for constraint in inspector.get_unique_constraints("document_revisions")
                    },
                    (
                        {
                            constraint["name"]: constraint["sqltext"]
                            for constraint in inspector.get_check_constraints(
                                "document_storage_candidates"
                            )
                        }
                        if "document_storage_candidates" in tables
                        else {}
                    ),
                )
        finally:
            engine.dispose()

    _run_alembic(postgres_storage_database, "upgrade", "b7c8d9e0f1a2")
    _run_alembic(postgres_storage_database, "upgrade", "head")
    tables, constraints, checks = artifacts()
    assert storage_tables <= tables
    assert "uq_document_revision_content_checksum" in constraints
    assert "'local'" in checks["chk_storage_candidate_provider"]

    _run_alembic(postgres_storage_database, "downgrade", "a6d9e4c2b8f1")
    tables, constraints, _ = artifacts()
    assert storage_tables.isdisjoint(tables)
    assert "uq_document_revision_content_checksum" not in constraints

    _run_alembic(postgres_storage_database, "upgrade", "head")
    tables, constraints, checks = artifacts()
    assert storage_tables <= tables
    assert "uq_document_revision_content_checksum" in constraints
    assert "'local'" in checks["chk_storage_candidate_provider"]


def test_local_provider_migration_refuses_downgrade_while_local_rows_exist(
    postgres_storage_database: URL,
) -> None:
    _run_alembic(postgres_storage_database, "upgrade", "head")
    engine = create_engine(postgres_storage_database, connect_args={"connect_timeout": 5})
    try:
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL session_replication_role = replica"))
            connection.execute(
                text(
                    "INSERT INTO document_storage_candidates "
                    "(id, organization_id, execution_intent_id, storage_profile_id, "
                    "provider_kind, container_name, object_key, content_sha256, byte_length, "
                    "media_type, generator_version) VALUES "
                    "(:id, :organization_id, :intent_id, 'local-test', 'local', "
                    "'local', 'tenant/test', :checksum, 0, 'application/octet-stream', 'test')"
                ),
                {
                    "id": uuid.uuid4(),
                    "organization_id": uuid.uuid4(),
                    "intent_id": uuid.uuid4(),
                    "checksum": "0" * 64,
                },
            )

        result = _alembic_result(
            postgres_storage_database, "downgrade", "b7c8d9e0f1a2"
        )
        output = f"{result.stdout}\n{result.stderr}"
        assert result.returncode != 0
        assert "cannot downgrade while local document blob rows exist" in output

        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
                "b8d9e0f1a2b3"
            )
            checks = {
                constraint["name"]: constraint["sqltext"]
                for constraint in inspect(connection).get_check_constraints(
                    "document_storage_candidates"
                )
            }
        assert "'local'" in checks["chk_storage_candidate_provider"]
    finally:
        engine.dispose()
