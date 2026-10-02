"""Focused storage proof for the guarded Apply initial-set seal."""

from __future__ import annotations

import importlib.util
import os
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError

from app.modules.project_master_data import models


REVISION = "f3a4b5c6d7e8"
PREDECESSOR = "e2f3a4b5c6d7"
BACKEND = Path(__file__).resolve().parents[1]
CONTRACT = "s12-post-intake-guarded-apply-v2"
PARENTS = {
    "projects": ("organization_id", "id"),
    "users": ("organization_id", "id"),
    "project_official_intake_commits": (
        "organization_id", "project_id", "id", "preliminary_result_artifact_id",
    ),
    "project_asset_import_batches": ("organization_id", "project_id", "id"),
    "import_source_artifacts": ("organization_id", "project_id", "import_batch_id", "id"),
    "column_mapping_decisions": (
        "organization_id", "project_id", "import_batch_id", "source_artifact_id",
        "structure_snapshot_id", "id",
    ),
    "column_mapping_profile_usages": (
        "organization_id", "project_id", "import_batch_id", "source_artifact_id",
        "structure_snapshot_id", "id",
    ),
}


def _parents() -> sa.MetaData:
    metadata = sa.MetaData()
    for name, keys in PARENTS.items():
        sa.Table(
            name, metadata,
            *(sa.Column(key, sa.Uuid, nullable=False, primary_key=key == "id") for key in keys),
            sa.UniqueConstraint(*keys),
        )
    return metadata


def _seal_table(metadata):
    seal = models.ProjectAssetReviewSeal.__table__.to_metadata(metadata)
    # SQLAlchemy does not retain conditional DDL when cloning a table.
    for constraint in seal.constraints:
        if constraint.name in {
            "chk_asset_review_seal_manifest", "chk_asset_review_seal_correspondence",
        }:
            constraint.ddl_if(dialect="postgresql")
    return seal


def _seed(connection, metadata, *, organization_id=None) -> dict:
    values = {
        key: uuid.uuid4() for key in (
            "organization_id", "project_id", "official_intake_commit_id",
            "preliminary_result_artifact_id", "import_batch_id", "source_artifact_id",
            "structure_snapshot_id", "mapping_decision_id", "staging_usage_id", "actor_user_id",
        )
    }
    if organization_id is not None:
        values["organization_id"] = organization_id
    ids = {
        "projects": "project_id", "users": "actor_user_id",
        "project_official_intake_commits": "official_intake_commit_id",
        "project_asset_import_batches": "import_batch_id",
        "import_source_artifacts": "source_artifact_id",
        "column_mapping_decisions": "mapping_decision_id",
        "column_mapping_profile_usages": "staging_usage_id",
    }
    for name, keys in PARENTS.items():
        row = {key: values[ids[name]] if key == "id" else values[key] for key in keys}
        connection.execute(metadata.tables[name].insert().values(**row))
    return {
        **values, "id": uuid.uuid4(), "contract_version": CONTRACT,
        "lineage_manifest": {"result_sha256": "a" * 64},
        "correspondence": [{"staging_row_id": str(uuid.uuid4()), "line_id": str(uuid.uuid4())}],
        "entry_lineage_sha256": "a" * 64, "authoritative_set_sha256": "b" * 64,
        "membership_version": 1,
    }


@pytest.fixture(params=["sqlite", "postgresql"])
def seal_connection(request):
    if request.param == "postgresql":
        url = os.getenv("TEST_DATABASE_URL")
        if not url or not url.startswith("postgres"):
            if os.getenv("CI") == "true":
                pytest.fail("OS-G2 seal integrity requires PostgreSQL TEST_DATABASE_URL in CI")
            pytest.skip("PostgreSQL seal integrity requires TEST_DATABASE_URL")
        engine = sa.create_engine(url)
    else:
        engine = sa.create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        transaction = connection.begin()
        if request.param == "postgresql":
            schema = "seal_" + uuid.uuid4().hex
            connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(sa.text(f'SET LOCAL search_path TO "{schema}"'))
        else:
            connection.execute(sa.text("PRAGMA foreign_keys=ON"))
        try:
            yield connection
        finally:
            transaction.rollback()
    engine.dispose()


def test_seal_rejects_duplicate_and_cross_scope_lineage(seal_connection):
    connection = seal_connection
    metadata = _parents()
    seal = _seal_table(metadata)
    metadata.create_all(connection)
    values = _seed(connection, metadata)
    peer = _seed(connection, metadata, organization_id=values["organization_id"])
    other_tenant = _seed(connection, metadata)
    connection.execute(seal.insert().values(**values))
    assert connection.execute(sa.select(seal.c.membership_version)).scalar_one() == 1
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(seal.insert().values(**{**values, "id": uuid.uuid4()}))
    connection.execute(seal.delete())

    for overrides in (
        {"organization_id": other_tenant["organization_id"]},
        {"project_id": peer["project_id"]},
        {"preliminary_result_artifact_id": peer["preliminary_result_artifact_id"]},
        {"official_intake_commit_id": peer["official_intake_commit_id"]},
        {"import_batch_id": peer["import_batch_id"]},
        {"source_artifact_id": peer["source_artifact_id"]},
        {"structure_snapshot_id": peer["structure_snapshot_id"]},
        {"mapping_decision_id": peer["mapping_decision_id"]},
        {"staging_usage_id": peer["staging_usage_id"]},
        {"actor_user_id": other_tenant["actor_user_id"]},
        {"membership_version": 2},
        {"contract_version": "s12-staging-apply-v1"},
    ):
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(seal.insert().values(**{**values, "id": uuid.uuid4(), **overrides}))
    connection.execute(seal.insert().values(**values))
    assert connection.execute(sa.select(sa.func.count()).select_from(seal)).scalar_one() == 1


def test_migration_remains_in_single_chain_and_round_trips_without_backfill(seal_connection):
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    script = ScriptDirectory.from_config(config)
    assert len(script.get_heads()) == 1
    assert REVISION in {item.revision for item in script.walk_revisions()}
    spec = importlib.util.spec_from_file_location(
        "seal_migration", BACKEND / "alembic" / "versions" / f"{REVISION}_asset_review_seal.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == PREDECESSOR
    connection = seal_connection
    metadata = _parents()
    metadata.create_all(connection)
    _seed(connection, metadata)
    module.op = Operations(MigrationContext.configure(connection))
    module.upgrade()
    seal = sa.Table("project_asset_review_seals", sa.MetaData(), autoload_with=connection)
    assert connection.execute(sa.select(sa.func.count()).select_from(seal)).scalar_one() == 0
    usage = sa.Table("column_mapping_profile_usages", sa.MetaData(), autoload_with=connection)
    assert connection.execute(sa.select(usage.c.materialized_input_sha256)).scalar_one() is None
    module.downgrade()
    assert not sa.inspect(connection).has_table("project_asset_review_seals")
    assert "materialized_input_sha256" not in {
        item["name"] for item in sa.inspect(connection).get_columns("column_mapping_profile_usages")
    }
    assert connection.execute(
        sa.select(sa.func.count()).select_from(metadata.tables["project_official_intake_commits"])
    ).scalar_one() == 1


@pytest.mark.parametrize("field,value", [
    ("entry_lineage_sha256", "A" * 64),
    ("authoritative_set_sha256", "g" * 64),
    ("lineage_manifest", []),
    ("correspondence", {}),
    ("correspondence", []),
])
@pytest.mark.parametrize("seal_connection", ["postgresql"], indirect=True)
def test_postgresql_rejects_malformed_proof(seal_connection, field, value):
    metadata = _parents()
    seal = _seal_table(metadata)
    metadata.create_all(seal_connection)
    values = _seed(seal_connection, metadata)
    with pytest.raises(IntegrityError), seal_connection.begin_nested():
        seal_connection.execute(seal.insert().values(**{**values, field: value}))
