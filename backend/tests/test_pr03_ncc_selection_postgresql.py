"""PostgreSQL-only concurrency and tenant proof for PR-03 NCC Selection."""
from __future__ import annotations

import os
import threading
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.modules.project_master_data.application.ncc_selection_service import (
    confirm_ncc_selection,
)
from app.modules.project_master_data.models import (
    AssetFamily,
    AuditEvent,
    CanonicalAsset,
    Customer,
    EvidenceFile,
    NccSelectionCurrentHead,
    NccSelectionRevision,
    OrganizationProfile,
    Project,
    ProjectAssetLine,
    QuoteBatch,
    QuoteLine,
    Role,
    Supplier,
    TaxonomyNode,
    User,
    UserRole,
)
from tests.test_pr03_ncc_selection_service import _seed


NCC_SELECTION_CONFIRMED = "NCC_SELECTION_CONFIRMED"


def _postgres_engine_or_skip():
    url = os.getenv("TEST_DATABASE_URL")
    if not url or not url.startswith("postgres"):
        if os.getenv("CI") == "true":
            pytest.fail("CI=true requires PostgreSQL TEST_DATABASE_URL for PR-03")
        pytest.skip("PR-03 concurrency proof requires PostgreSQL TEST_DATABASE_URL")
    engine = create_engine(url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT to_regclass('ncc_selection_revisions')")
        ).scalar_one()
    if exists is None:
        engine.dispose()
        if os.getenv("CI") == "true":
            pytest.fail("CI PostgreSQL is not migrated to the PR-03 head")
        pytest.skip("PostgreSQL is not migrated to the PR-03 head")
    return engine


def _cleanup(SessionLocal, ids: dict[str, uuid.UUID]) -> None:
    db: Session = SessionLocal()
    try:
        # Selection artifacts and audit.
        db.query(AuditEvent).filter_by(organization_id=ids["org"]).delete(
            synchronize_session=False
        )
        db.query(NccSelectionCurrentHead).filter_by(organization_id=ids["org"]).delete(
            synchronize_session=False
        )
        db.query(NccSelectionRevision).filter_by(organization_id=ids["org"]).delete(
            synchronize_session=False
        )

        # Project and its dependent lines.
        db.query(ProjectAssetLine).filter_by(id=ids["asset_line"]).delete(
            synchronize_session=False
        )
        db.query(Project).filter_by(id=ids["project"]).delete(synchronize_session=False)
        db.query(Customer).filter_by(id=ids["customer"]).delete(synchronize_session=False)

        # Quote data.
        db.query(QuoteLine).filter_by(id=ids["line"]).delete(synchronize_session=False)
        db.query(QuoteBatch).filter_by(id=ids["batch"]).delete(synchronize_session=False)
        db.query(Supplier).filter_by(id=ids["supplier"]).delete(synchronize_session=False)
        db.query(EvidenceFile).filter_by(id=ids["evidence"]).delete(
            synchronize_session=False
        )

        # Identity hierarchy (leaf-to-root).
        db.query(CanonicalAsset).filter_by(id=ids["canonical"]).delete(
            synchronize_session=False
        )
        db.query(AssetFamily).filter_by(id=ids["family"]).delete(
            synchronize_session=False
        )
        db.query(TaxonomyNode).filter_by(id=ids["taxonomy"]).delete(
            synchronize_session=False
        )

        # Users and roles.
        db.query(UserRole).filter_by(user_id=ids["actor"]).delete(
            synchronize_session=False
        )
        db.query(User).filter_by(id=ids["actor"]).delete(synchronize_session=False)
        db.query(OrganizationProfile).filter_by(id=ids["org"]).delete(
            synchronize_session=False
        )
        db.query(Role).filter_by(id=ids["role"]).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _command(
    db: Session,
    *,
    ids: dict[str, uuid.UUID],
    actor_id: uuid.UUID,
    idempotency_key: str,
    expected_selection_revision: int = 0,
) -> NccSelectionRevision:
    actor = db.get(User, actor_id)
    assert actor is not None
    return confirm_ncc_selection(
        db,
        actor=actor,
        org_id=ids["org"],
        project_id=ids["project"],
        project_asset_line_id=ids["asset_line"],
        quote_line_id=ids["line"],
        expected_selection_revision=expected_selection_revision,
        acknowledged_warning_codes=[],
        idempotency_key=idempotency_key,
        confirmed=True,
        correlation_id="corr-pr03-postgresql",
    )


def _run_pair(
    SessionLocal,
    *,
    ids: dict[str, uuid.UUID],
    work: list[tuple[uuid.UUID, str, int]],
) -> tuple[list[uuid.UUID], list[BaseException]]:
    barrier = threading.Barrier(2, timeout=30)
    results: list[uuid.UUID] = []
    errors: list[BaseException] = []

    def worker(actor_id: uuid.UUID, idempotency_key: str, expected_revision: int) -> None:
        db: Session = SessionLocal()
        try:
            barrier.wait(timeout=30)
            revision = _command(
                db,
                ids=ids,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                expected_selection_revision=expected_revision,
            )
            results.append(revision.id)
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [
        threading.Thread(
            target=worker,
            args=item,
            name=f"ncc-selection-worker-{index}",
            daemon=True,
        )
        for index, item in enumerate(work)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert all(not thread.is_alive() for thread in threads)
    return results, errors


def _seed_ids(setup: Session, *, suffix: str) -> tuple[dict[str, uuid.UUID], dict]:
    seeded = _seed(setup, suffix=suffix)
    return (
        {
            "org": seeded["org"].id,
            "actor": seeded["actor"].id,
            "project": seeded["project"].id,
            "asset_line": seeded["asset_line"].id,
            "line": seeded["line"].id,
            "customer": seeded["customer"].id,
            "taxonomy": seeded["taxonomy"].id,
            "family": seeded["family"].id,
            "canonical": seeded["canonical"].id,
            "supplier": seeded["supplier"].id,
            "evidence": seeded["evidence"].id,
            "batch": seeded["batch"].id,
            "role": seeded["role"].id,
        },
        seeded,
    )


def test_concurrent_same_idempotency_key_creates_one_revision() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine)
    setup: Session = SessionLocal()
    try:
        ids, seeded = _seed_ids(setup, suffix="pg-same")
    finally:
        setup.close()

    try:
        work = [
            (seeded["actor"].id, "ncc-same-key", 0),
            (seeded["actor"].id, "ncc-same-key", 0),
        ]
        results, errors = _run_pair(SessionLocal, ids=ids, work=work)

        # One thread creates; the other replays idempotently.
        assert len(set(results)) == 1
        assert len(errors) == 0

        verify: Session = SessionLocal()
        try:
            assert (
                verify.query(NccSelectionRevision)
                .filter_by(organization_id=ids["org"], project_id=ids["project"])
                .count()
                == 1
            )
            assert (
                verify.query(NccSelectionCurrentHead)
                .filter_by(
                    organization_id=ids["org"],
                    project_id=ids["project"],
                    project_asset_line_id=ids["asset_line"],
                )
                .count()
                == 1
            )
            assert (
                verify.query(AuditEvent)
                .filter_by(
                    organization_id=ids["org"], event_name=NCC_SELECTION_CONFIRMED
                )
                .count()
                == 1
            )
        finally:
            verify.close()
    finally:
        _cleanup(SessionLocal, ids)
        engine.dispose()


def test_concurrent_different_keys_one_wins_with_version_conflict() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine)
    setup: Session = SessionLocal()
    try:
        ids, seeded = _seed_ids(setup, suffix="pg-diff")
    finally:
        setup.close()

    try:
        work = [
            (seeded["actor"].id, "ncc-diff-key-a", 0),
            (seeded["actor"].id, "ncc-diff-key-b", 0),
        ]
        results, errors = _run_pair(SessionLocal, ids=ids, work=work)

        # Exactly one thread succeeds; the other sees the head advance.
        assert len(results) == 1
        assert len(errors) == 1
        assert errors[0].status_code == 409
        assert errors[0].detail["error_code"] == "selection_revision_conflict"

        verify: Session = SessionLocal()
        try:
            assert (
                verify.query(NccSelectionRevision)
                .filter_by(organization_id=ids["org"], project_id=ids["project"])
                .count()
                == 1
            )
            head = (
                verify.query(NccSelectionCurrentHead)
                .filter_by(
                    organization_id=ids["org"],
                    project_id=ids["project"],
                    project_asset_line_id=ids["asset_line"],
                )
                .one()
            )
            assert head.selection_revision == 1
        finally:
            verify.close()
    finally:
        _cleanup(SessionLocal, ids)
        engine.dispose()
