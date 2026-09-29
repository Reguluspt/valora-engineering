"""Real PostgreSQL migration, backfill and null-safe FK proofs for G1.1A."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import projects as project_api
from app.modules.excel_import.models import (
    ColumnMappingDecision,
    ColumnMappingProfileUsage,
    RawAssetObservation,
)
from app.modules.project_master_data.application import preliminary_result_service
from app.modules.project_master_data.models import (
    AuditEvent,
    PreliminaryAnalysisSnapshot,
    PreliminaryResultArtifact,
    Project,
    ProjectAssetImportBatch,
    ProjectOfficialIntakeCommit,
    User,
)
from app.modules.project_master_data.workbench_schemas import ProjectAssetImportBatchCreate
from tests.test_pr01_preliminary_result_postgresql import _seed


PRIOR = "c9d0e1f2a3b4"
CURRENT = "e4f5a6b7c8d9"
RUNTIME_HEAD = "d1e2f3a4b5c6"
MIGRATION = Path(__file__).parents[1] / "alembic/versions/e4f5a6b7c8d9_precase_identity_batch_foundation.py"


def _alembic(url, *args):
    env = os.environ.copy()
    env.update({
        "POSTGRES_HOST": url.host or "127.0.0.1",
        "POSTGRES_PORT": str(url.port or 5432),
        "POSTGRES_DB": url.database,
        "POSTGRES_USER": url.username,
        "POSTGRES_PASSWORD": url.password,
    })
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=Path(__file__).parents[1], env=env,
        capture_output=True, text=True, check=False,
    )


def _must_alembic(url, *args):
    result = _alembic(url, *args)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture
def pg_database():
    raw = os.getenv("TEST_DATABASE_URL")
    if not raw or not raw.startswith("postgres"):
        pytest.fail("G1.1A PostgreSQL proof requires TEST_DATABASE_URL")
    source = make_url(raw)
    database = f"g11a_{uuid.uuid4().hex}"
    admin = create_engine(source.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{database}"'))
    try:
        yield source.set(database=database)
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))
        admin.dispose()


def _seed_prior_minimal(conn, *, batches: int):
    org, actor, customer, project = [uuid.uuid4() for _ in range(4)]
    conn.execute(text(
        "INSERT INTO organization_profiles(id,legal_name,organization_slug,status) "
        "VALUES (:id,'G11A Org',:slug,'active')"
    ), {"id": org, "slug": f"g11a-{org.hex}"})
    conn.execute(text(
        "INSERT INTO users(id,organization_id,email,full_name,status) "
        "VALUES (:id,:org,:email,'G11A Actor','active')"
    ), {"id": actor, "org": org, "email": f"g11a-{actor.hex}@example.com"})
    conn.execute(text(
        "INSERT INTO customers(id,organization_id,legal_name,status,created_by) "
        "VALUES (:id,:org,'G11A Customer','active',:actor)"
    ), {"id": customer, "org": org, "actor": actor})
    conn.execute(text(
        "INSERT INTO projects(id,organization_id,customer_id,code,name,status,knowledge_status,created_by) "
        "VALUES (:id,:org,:customer,:code,'G11A Project','draft','pending',:actor)"
    ), {"id": project, "org": org, "customer": customer,
        "code": f"G11A-{project.hex[:12]}", "actor": actor})
    batch_ids = []
    for _ in range(batches):
        batch = uuid.uuid4()
        conn.execute(text(
            "INSERT INTO project_asset_import_batches "
            "(id,organization_id,project_id,source_filename,status,total_rows,valid_rows,"
            "invalid_rows,warning_rows,created_by_user_id) "
            "VALUES (:id,:org,:project,'legacy.xlsx','created',0,0,0,0,:actor)"
        ), {"id": batch, "org": org, "project": project, "actor": actor})
        batch_ids.append(batch)
    return org, customer, project, batch_ids


def test_migration_backfills_zero_one_and_ambiguous_multiple_then_roundtrips(pg_database):
    _must_alembic(pg_database, "upgrade", PRIOR)
    engine = create_engine(pg_database)
    with engine.begin() as conn:
        zero = _seed_prior_minimal(conn, batches=0)
        one = _seed_prior_minimal(conn, batches=1)
        many = _seed_prior_minimal(conn, batches=2)
    _must_alembic(pg_database, "upgrade", CURRENT)
    with engine.connect() as conn:
        pointers = dict(conn.execute(text(
            "SELECT id,current_preliminary_import_batch_id FROM projects "
            "WHERE id IN (:zero,:one,:many)"
        ), {"zero": zero[2], "one": one[2], "many": many[2]}).all())
        assert pointers == {zero[2]: None, one[2]: one[3][0], many[2]: None}
        assert dict(conn.execute(text(
            "SELECT id,customer_id FROM projects WHERE id IN (:zero,:one,:many)"
        ), {"zero": zero[2], "one": one[2], "many": many[2]}).all()) == {
            zero[2]: zero[1], one[2]: one[1], many[2]: many[1],
        }
    refused = _alembic(pg_database, "downgrade", PRIOR)
    assert refused.returncode != 0
    assert "current batch or multi-batch state is not representable by v1" in refused.stderr
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == CURRENT
    # Removing only this fixture's ambiguous, dependency-free batches makes v1 representable.
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM project_asset_import_batches WHERE project_id=:project"),
                     {"project": many[2]})
    _must_alembic(pg_database, "downgrade", PRIOR)
    _must_alembic(pg_database, "upgrade", CURRENT)
    with engine.connect() as conn:
        assert conn.execute(text(
            "SELECT current_preliminary_import_batch_id FROM projects WHERE id=:id"
        ), {"id": one[2]}).scalar_one() == one[3][0]
    engine.dispose()


def test_nullable_project_customer_pointer_and_all_fact_ownership_fks(pg_database):
    _must_alembic(pg_database, "upgrade", RUNTIME_HEAD)
    engine = create_engine(pg_database)
    db = Session(engine)
    try:
        first = _seed(db, suffix=f"g11a-first-{uuid.uuid4().hex[:6]}")
        second = _seed(db, suffix=f"g11a-second-{uuid.uuid4().hex[:6]}")
        snapshot = db.get(PreliminaryAnalysisSnapshot, first["snapshot_id"])
        second_snapshot = db.get(PreliminaryAnalysisSnapshot, second["snapshot_id"])
        assert snapshot is not None and second_snapshot is not None
        decision = db.get(ColumnMappingDecision, snapshot.mapping_decision_id)
        usage = db.get(ColumnMappingProfileUsage, snapshot.mapping_profile_usage_id)
        assert decision is not None and usage is not None
        proposal = db.get(ColumnMappingDecision, decision.proposal_decision_id)
        assert proposal is not None
        batch = db.get(ProjectAssetImportBatch, snapshot.import_batch_id)
        assert batch is not None
        project = db.get(Project, first["project_id"])
        assert project is not None
        project.customer_id = None
        project.current_preliminary_import_batch_id = batch.id
        for fact in (proposal, decision, usage, snapshot):
            fact.customer_id = None
        raw = RawAssetObservation(
            organization_id=first["org_id"], customer_id=None,
            project_id=project.id, import_batch_id=batch.id,
            source_artifact_id=snapshot.source_artifact_id,
            structure_snapshot_id=snapshot.structure_snapshot_id,
            row_index=1, sheet_name="Assets", raw_asset_name="Pump",
        )
        db.add(raw)
        result = PreliminaryResultArtifact(
            organization_id=first["org_id"], customer_id=None,
            project_id=project.id, version=1, original_filename="result.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_size_bytes=1, content_checksum_sha256="a" * 64,
            storage_object_key=f"g11a/{uuid.uuid4()}", source_snapshot_sha256="b" * 64,
            lineage_manifest={"analysis_snapshot": {"id": str(snapshot.id)}},
            created_by_user_id=first["actor_id"],
        )
        db.add(result)
        db.commit()
        assert db.get(Project, project.id).customer_id is None

        def rejects(sql, **params):
            with pytest.raises(IntegrityError), db.begin_nested():
                db.execute(text(sql), params)
                db.flush()

        rejects("UPDATE projects SET customer_id=:bad WHERE id=:id",
                bad=second["customer_id"], id=project.id)
        rejects("UPDATE projects SET current_preliminary_import_batch_id=:bad WHERE id=:id",
                bad=second_snapshot.import_batch_id, id=project.id)
        sibling = Project(
            organization_id=first["org_id"], customer_id=first["customer_id"],
            code=f"G11A-SIBLING-{uuid.uuid4().hex[:8]}", name="Sibling",
            created_by=first["actor_id"],
        )
        db.add(sibling)
        db.flush()
        sibling_batch = ProjectAssetImportBatch(
            organization_id=first["org_id"], project_id=sibling.id,
            source_filename="sibling.xlsx", status="created", total_rows=0,
            valid_rows=0, invalid_rows=0, warning_rows=0,
            created_by_user_id=first["actor_id"],
        )
        db.add(sibling_batch)
        db.commit()
        rejects("UPDATE projects SET current_preliminary_import_batch_id=:bad WHERE id=:id",
                bad=sibling_batch.id, id=project.id)
        rejects("UPDATE column_mapping_decisions SET project_id=:bad WHERE id=:id",
                bad=second["project_id"], id=proposal.id)
        rejects("UPDATE column_mapping_decisions SET proposal_decision_id=:bad WHERE id=:id",
                bad=second_snapshot.mapping_decision_id, id=decision.id)
        rejects("UPDATE column_mapping_profile_usages SET confirmation_decision_id=:bad WHERE id=:id",
                bad=second_snapshot.mapping_decision_id, id=usage.id)
        rejects("UPDATE preliminary_analysis_snapshots SET mapping_decision_id=:bad WHERE id=:id",
                bad=second_snapshot.mapping_decision_id, id=snapshot.id)
        rejects("UPDATE raw_asset_observations SET source_artifact_id=:bad WHERE id=:id",
                bad=second_snapshot.source_artifact_id, id=raw.id)
        rejects("UPDATE preliminary_result_artifacts SET project_id=:bad WHERE id=:id",
                bad=second["project_id"], id=result.id)
        # A bound official fact may reference a valid result created before binding.
        project.customer_id = first["customer_id"]
        db.add(ProjectOfficialIntakeCommit(
            organization_id=first["org_id"], customer_id=first["customer_id"],
            project_id=project.id, preliminary_result_artifact_id=result.id,
            preliminary_result_version=1, preliminary_result_sha256="a" * 64,
            source_snapshot_sha256="b" * 64,
            project_version_before=project.row_version,
            idempotency_key=f"g11a-null-result-{uuid.uuid4()}",
            request_digest_sha256="c" * 64,
            committed_by_user_id=first["actor_id"],
        ))
        db.commit()
        refused = _alembic(pg_database, "downgrade", PRIOR)
        assert refused.returncode != 0
        assert "unbound Customer history" in refused.stderr
    finally:
        db.close()
        engine.dispose()


def test_multiple_batches_use_only_unique_accepted_commit_chain(pg_database):
    _must_alembic(pg_database, "upgrade", RUNTIME_HEAD)
    engine = create_engine(pg_database)
    db = Session(engine)
    try:
        seeded = _seed(db, suffix=f"g11a-proven-{uuid.uuid4().hex[:6]}")
        snapshot = db.get(PreliminaryAnalysisSnapshot, seeded["snapshot_id"])
        project = db.get(Project, seeded["project_id"])
        assert snapshot is not None and project is not None
        db.add(ProjectAssetImportBatch(
            organization_id=seeded["org_id"], project_id=project.id,
            source_filename="second.xlsx", status="created", total_rows=0,
            valid_rows=0, invalid_rows=0, warning_rows=0,
            created_by_user_id=seeded["actor_id"],
        ))
        digest = preliminary_result_service._snapshot_canonical_digest(snapshot)
        result = PreliminaryResultArtifact(
            organization_id=seeded["org_id"], customer_id=seeded["customer_id"],
            project_id=project.id, version=1, original_filename="accepted.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_size_bytes=1, content_checksum_sha256="a" * 64,
            storage_object_key=f"g11a/accepted/{uuid.uuid4()}",
            source_snapshot_sha256=digest,
            lineage_manifest={
                "import_batch_id": str(snapshot.import_batch_id),
                "analysis_snapshot": {
                    "id": str(snapshot.id), "version": snapshot.version,
                    "canonical_digest_sha256": digest,
                    "line_manifest_digest_sha256": snapshot.line_manifest_digest_sha256,
                },
            },
            created_by_user_id=seeded["actor_id"],
        )
        db.add(result)
        db.flush()
        db.add(ProjectOfficialIntakeCommit(
            organization_id=seeded["org_id"], customer_id=seeded["customer_id"],
            project_id=project.id, preliminary_result_artifact_id=result.id,
            preliminary_result_version=1, preliminary_result_sha256="a" * 64,
            source_snapshot_sha256=digest, project_version_before=project.row_version,
            idempotency_key=f"g11a-{uuid.uuid4()}", request_digest_sha256="c" * 64,
            committed_by_user_id=seeded["actor_id"],
        ))
        db.commit()
        spec = importlib.util.spec_from_file_location("g11a_migration", MIGRATION)
        assert spec and spec.loader
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with engine.begin() as conn:
            migration.op = Operations(MigrationContext.configure(conn))
            migration._backfill_pointer()
        db.expire_all()
        assert db.get(Project, project.id).current_preliminary_import_batch_id == snapshot.import_batch_id
        # A mutually consistent but forged manifest/commit digest cannot prove
        # a batch: the migration recomputes the immutable analysis digest.
        with engine.begin() as conn:
            conn.execute(text(
                "UPDATE projects SET current_preliminary_import_batch_id=NULL WHERE id=:id"
            ), {"id": project.id})
            conn.execute(text(
                "UPDATE preliminary_result_artifacts SET source_snapshot_sha256=:forged, "
                "lineage_manifest=jsonb_set(lineage_manifest, "
                "'{analysis_snapshot,canonical_digest_sha256}', to_jsonb(CAST(:manifest_digest AS text))) "
                "WHERE id=:id"
            ), {"forged": "f" * 64, "manifest_digest": "f" * 64, "id": result.id})
            conn.execute(text(
                "UPDATE project_official_intake_commits SET source_snapshot_sha256=:forged "
                "WHERE preliminary_result_artifact_id=:id"
            ), {"forged": "f" * 64, "id": result.id})
        with engine.begin() as conn:
            migration.op = Operations(MigrationContext.configure(conn))
            migration._backfill_pointer()
        db.expire_all()
        assert db.get(Project, project.id).current_preliminary_import_batch_id is None
    finally:
        db.close()
        engine.dispose()


def test_postgresql_first_batch_transaction_and_second_no_switch(pg_database, monkeypatch):
    _must_alembic(pg_database, "upgrade", RUNTIME_HEAD)
    engine = create_engine(pg_database)
    with engine.begin() as conn:
        org_id, _, project_id, _ = _seed_prior_minimal(conn, batches=0)
    db = Session(engine)
    try:
        project = db.get(Project, project_id)
        assert project is not None
        actor = db.get(User, project.created_by)
        assert actor is not None
        before = project.row_version

        def create(filename):
            return project_api.create_project_asset_import(
                project_id, ProjectAssetImportBatchCreate(source_filename=filename),
                db=db, current_user=actor,
            )

        original_audit = project_api.log_audit_event

        def fail_audit(**_kwargs):
            raise RuntimeError("forced PostgreSQL audit failure")

        monkeypatch.setattr(project_api, "log_audit_event", fail_audit)
        with pytest.raises(RuntimeError, match="forced PostgreSQL audit failure"):
            create("failed.xlsx")
        db.refresh(project)
        assert project.current_preliminary_import_batch_id is None
        assert project.row_version == before
        assert db.query(ProjectAssetImportBatch).filter_by(project_id=project_id).count() == 0
        assert db.query(AuditEvent).filter_by(
            organization_id=org_id, event_name="ProjectAssetImportBatchCreated"
        ).count() == 0

        monkeypatch.setattr(project_api, "log_audit_event", original_audit)
        first = create("first.xlsx")
        db.refresh(project)
        assert project.current_preliminary_import_batch_id == first.id
        assert project.row_version == before + 1
        assert db.query(AuditEvent).filter_by(
            organization_id=org_id, event_name="ProjectAssetImportBatchCreated",
            entity_id=first.id,
        ).count() == 1
        second = create("second.xlsx")
        db.refresh(project)
        assert second.id != first.id
        assert project.current_preliminary_import_batch_id == first.id
        assert project.row_version == before + 1
    finally:
        db.close()
        engine.dispose()
