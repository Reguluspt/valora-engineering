"""PostgreSQL migration, model-parity, and concurrency proofs for PR-06."""

from __future__ import annotations

import threading
import uuid

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint, create_engine
from sqlalchemy import inspect
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from app.modules.m365_integration.application.revalidation_service import (
    revalidate_document,
)
from app.modules.m365_integration.application.provision_document_service import (
    provision_onedrive_document,
)
from app.modules.m365_integration.infrastructure.credential_vault import (
    DatabaseCredentialVault,
)
from app.modules.m365_integration.models import (
    M365ManagedContentBaseline,
    M365ManagedRegionBaseline,
    M365RevalidationObservation,
    M365RevisionBinding,
)
from app.modules.document_workspace.models import DocumentRecord, DocumentRevision
from app.modules.project_master_data.models import AuditEvent, GeneratedDocument, RenderJob, User
from tests.test_pr05_m365_postgresql import _run_alembic
from tests.test_pr06_m365_revalidation import RevalidationGraph, _docx, _setup
from tests.test_pr06_m365_document_provision import _authority
from tests.test_pr05_m365_foundation import FakeOAuthClient


pytest_plugins = ("tests.test_pr05_m365_postgresql",)

PR06_MODELS = (
    M365ManagedContentBaseline,
    M365ManagedRegionBaseline,
    M365RevalidationObservation,
)
PR06_TABLES = {model.__tablename__ for model in PR06_MODELS}
PR06_INDEXES = {
    "m365_managed_content_baselines": {"idx_m365_content_baseline_revision"},
    "m365_managed_region_baselines": {"idx_m365_region_baseline_parent"},
    "m365_revalidation_observations": {"idx_m365_revalidation_current"},
}


def _artifacts(database_url: URL) -> dict[str, object]:
    engine = create_engine(database_url, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            tables = set(inspector.get_table_names()) & PR06_TABLES
            indexes = {
                table_name: {
                    index["name"]
                    for index in inspector.get_indexes(table_name)
                    if index["name"] in PR06_INDEXES[table_name]
                }
                for table_name in tables
            }
            return {"tables": tables, "indexes": indexes}
    finally:
        engine.dispose()


def _model_constraint_names(model, constraint_type: type) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, constraint_type) and constraint.name is not None
    }


def test_pr06_migration_round_trip_and_model_parity(postgres_database_url: URL) -> None:
    _run_alembic(postgres_database_url, "upgrade", "f4c8d2a1b7e9")
    assert _artifacts(postgres_database_url)["tables"] == set()

    _run_alembic(postgres_database_url, "upgrade", "a6d9e4c2b8f1")
    reference = _artifacts(postgres_database_url)
    assert reference["tables"] == PR06_TABLES
    assert reference["indexes"] == PR06_INDEXES

    engine = create_engine(postgres_database_url, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            for model in PR06_MODELS:
                table_name = model.__tablename__
                assert {column.name for column in model.__table__.columns} == {
                    column["name"] for column in inspector.get_columns(table_name)
                }
                assert _model_constraint_names(model, UniqueConstraint) == {
                    constraint["name"]
                    for constraint in inspector.get_unique_constraints(table_name)
                }
                assert _model_constraint_names(model, CheckConstraint) == {
                    constraint["name"] for constraint in inspector.get_check_constraints(table_name)
                }
                assert _model_constraint_names(model, ForeignKeyConstraint) == {
                    constraint["name"] for constraint in inspector.get_foreign_keys(table_name)
                }
    finally:
        engine.dispose()

    _run_alembic(postgres_database_url, "downgrade", "f4c8d2a1b7e9")
    assert _artifacts(postgres_database_url)["tables"] == set()
    _run_alembic(postgres_database_url, "upgrade", "a6d9e4c2b8f1")
    assert _artifacts(postgres_database_url) == reference


def test_concurrent_same_revalidation_command_creates_one_fact_and_audit(
    postgres_database_url: URL,
) -> None:
    _run_alembic(postgres_database_url, "upgrade", "a6d9e4c2b8f1")
    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine)
    setup: Session = session_factory()
    try:
        context = _setup(setup)
        ids = {
            "actor": context["actor"].id,
            "organization": context["organization"].id,
            "project": context["project"].id,
            "document": context["revision"].document_id,
            "revision": context["revision"].id,
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
            observation = revalidate_document(
                db,
                actor=actor,
                organization_id=ids["organization"],
                project_id=ids["project"],
                document_id=ids["document"],
                expected_document_revision_id=ids["revision"],
                expected_document_revision=1,
                trigger="explicit_refresh",
                idempotency_key="pr06-concurrent-revalidation",
                oauth_client=FakeOAuthClient(),
                graph_gateway=RevalidationGraph(_docx()),
                credential_vault=DatabaseCredentialVault(
                    db,
                    keys={"v1": b"1" * 32, "v2": b"2" * 32},
                    active_key_version="v1",
                ),
            )
            results.append(observation.id)
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
        assert (
            verify.query(M365RevalidationObservation)
            .filter_by(organization_id=ids["organization"])
            .count()
            == 1
        )
        assert (
            verify.query(AuditEvent)
            .filter_by(
                organization_id=ids["organization"],
                event_name="M365_REVALIDATION_COMPLETED",
            )
            .count()
            == 1
        )
    finally:
        verify.close()
        engine.dispose()


def test_concurrent_same_producer_command_creates_one_complete_lineage(
    postgres_database_url: URL,
) -> None:
    _run_alembic(postgres_database_url, "upgrade", "a6d9e4c2b8f1")
    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine)
    setup: Session = session_factory()
    try:
        context = _setup(setup)
        version = _authority(setup, context)
        ids = {
            "actor": context["actor"].id,
            "organization": context["organization"].id,
            "project": context["project"].id,
            "connection": context["binding"].connection_id,
            "version": version.id,
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
            provisioned = provision_onedrive_document(
                db,
                actor=actor,
                organization_id=ids["organization"],
                project_id=ids["project"],
                template_version_id=ids["version"],
                connection_id=ids["connection"],
                drive_item_id="pr06-concurrent-producer-item",
                title="Concurrent canonical producer",
                data_snapshot={"appraised_value": 1_000_000},
                idempotency_key="pr06-concurrent-producer",
                oauth_client=FakeOAuthClient(),
                graph_gateway=RevalidationGraph(_docx()),
                credential_vault=DatabaseCredentialVault(
                    db,
                    keys={"v1": b"1" * 32, "v2": b"2" * 32},
                    active_key_version="v1",
                ),
            )
            results.append(provisioned.document_id)
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
        document_id = results[0]
        assert verify.query(DocumentRecord).filter_by(id=document_id).count() == 1
        assert verify.query(DocumentRevision).filter_by(document_id=document_id).count() == 1
        assert verify.query(RenderJob).filter_by(project_id=ids["project"]).count() >= 1
        assert (
            verify.query(GeneratedDocument)
            .filter_by(storage_key=f"onedrive-adoption/{document_id}")
            .count()
            == 1
        )
        assert verify.query(M365RevisionBinding).filter_by(document_id=document_id).count() == 1
        assert (
            verify.query(M365ManagedContentBaseline)
            .filter_by(document_id=document_id)
            .count()
            == 1
        )
        assert (
            verify.query(AuditEvent)
            .filter_by(
                organization_id=ids["organization"],
                event_name="M365_CANONICAL_DOCUMENT_PROVISIONED",
            )
            .count()
            == 1
        )
    finally:
        verify.close()
        engine.dispose()
