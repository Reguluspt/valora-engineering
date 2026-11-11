import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import engine as app_engine
from app.modules.project_master_data.models import AuditEvent, OrganizationProfile, User, UserActionLog

_BASE = "0a1b2c3d4e5f"
_REVISION = "84bf42a19d31"
_DATABASE = "valora_sec001_migration"
_SCHEMA_TABLES = (
    "document_templates", "template_versions", "computed_placeholder_expressions",
    "template_placeholders", "audit_events", "user_action_logs",
)


@pytest.fixture
def migration_database(monkeypatch):
    if os.environ.get("VALORA_SEC001_DISPOSABLE_PG") != "1":
        pytest.skip("requires the explicitly selected SEC-001 disposable PostgreSQL instance")
    password = os.environ["VALORA_SEC001_MIGRATOR_PASSWORD"]
    url = app_engine.url.set(database=_DATABASE, username="sec001_migrator", password=password)
    assert (url.drivername, url.host, url.database, url.username) == (
        "postgresql+psycopg", "127.0.0.1", _DATABASE, "sec001_migrator",
    )
    assert url.port and url.port != 5432 and not url.query

    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            identity = conn.execute(text("""
                SELECT current_database(), current_user, current_setting('server_version_num')::int,
                       shobj_description(oid, 'pg_database'), pg_get_userbyid(datdba)
                FROM pg_database WHERE datname = current_database()
            """)).one()
        assert identity[:2] == (_DATABASE, "sec001_migrator")
        assert 160000 <= identity[2] < 170000
        assert identity[3:] == ("VALORA SEC-001 disposable synthetic", "sec001_migrator")

        with monkeypatch.context() as env:
            env.setenv("POSTGRES_HOST", url.host)
            env.setenv("POSTGRES_PORT", str(url.port))
            env.setenv("POSTGRES_DB", url.database)
            env.setenv("POSTGRES_USER", url.username)
            env.setenv("POSTGRES_PASSWORD", password)
            get_settings.cache_clear()
            assert get_settings().database_url == url.render_as_string(hide_password=False)
            config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
            try:
                yield engine, config
            finally:
                get_settings.cache_clear()
    finally:
        engine.dispose()


def _historical_rows(engine):
    metadata = MetaData()
    with engine.connect() as conn:
        return {
            name: {
                row["id"]: {key: value for key, value in row.items() if key != "template_version_id"
                            or name != "computed_placeholder_expressions"}
                for row in conn.execute(select(Table(name, metadata, autoload_with=conn))).mappings()
            }
            for name in _SCHEMA_TABLES
        }


def _seed_legacy(engine):
    metadata = MetaData()
    with Session(engine) as db, db.begin():
        org_a = OrganizationProfile(legal_name="Synthetic A", organization_slug="sec001-migration-a")
        org_b = OrganizationProfile(legal_name="Synthetic B", organization_slug="sec001-migration-b")
        db.add_all([org_a, org_b])
        db.flush()
        actor_a = User(organization_id=org_a.id, email="mig-a@example.invalid", full_name="Synthetic A")
        actor_b = User(organization_id=org_b.id, email="mig-b@example.invalid", full_name="Synthetic B")
        db.add_all([actor_a, actor_b])
        db.flush()

        template_table = Table("document_templates", metadata, autoload_with=db.connection())
        version_table = Table("template_versions", metadata, autoload_with=db.connection())
        expression_table = Table("computed_placeholder_expressions", metadata, autoload_with=db.connection())
        placeholder_table = Table("template_placeholders", metadata, autoload_with=db.connection())
        template_a, template_b = uuid.uuid4(), uuid.uuid4()
        code_a, code_b = " MiXeD_Đ ", "Mixed_Đ"
        db.execute(template_table.insert(), [
            dict(id=template_a, organization_id=org_a.id, code=code_a, created_by=actor_a.id,
                 document_type="report", name="Synthetic A", status="draft", row_version=3),
            dict(id=template_b, organization_id=org_b.id, code=code_b, created_by=actor_b.id,
                 document_type="report", name="Synthetic B", status="draft", row_version=2),
        ])
        first, second, foreign = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        db.execute(version_table.insert(), [
            dict(id=first, document_template_id=template_a, version_number=1, template_format="docx",
                 status="deprecated", deprecation_reason="Synthetic history", replacement_version_id=None, row_version=4),
            dict(id=second, document_template_id=template_a, version_number=2, template_format="docx",
                 status="active", deprecation_reason=None, replacement_version_id=None, row_version=1),
            dict(id=foreign, document_template_id=template_b, version_number=1, template_format="docx",
                 status="active", deprecation_reason=None, replacement_version_id=None, row_version=1),
        ])
        db.execute(version_table.update().where(version_table.c.id == first).values(replacement_version_id=second))
        db.execute(template_table.update().where(template_table.c.id == template_a).values(current_version_id=second))

        legacy = [
            (actor_a.id, []), (actor_a.id, [first]), (actor_a.id, [first, second]),
            (actor_a.id, [first, foreign]), (actor_b.id, [first]),
        ]
        for number, (creator, versions) in enumerate(legacy):
            expression_id = uuid.uuid4()
            db.execute(expression_table.insert().values(
                id=expression_id, placeholder_key=f"synthetic-{number}", expression_type="valora_expr",
                inputs={"seed": number}, expression=f"{number} + 1", output_data_type="scalar",
                status="draft", created_by=creator,
            ))
            for version in versions:
                db.execute(placeholder_table.insert().values(
                    id=uuid.uuid4(), template_version_id=version, placeholder_key=f"synthetic-{number}",
                    label_vi="Synthetic", data_type="scalar", source_context="custom", source_path="$.synthetic",
                    is_required=True, computed_expression_id=expression_id, status="active",
                ))
        db.add(AuditEvent(
            organization_id=org_a.id, actor_user_id=actor_a.id, event_name="DOCUMENT_TEMPLATE_CREATE",
            entity_type="document_template", entity_id=template_a,
        ))
        db.add(UserActionLog(
            user_id=actor_a.id, action_type="create_template", target_type="document_template",
            target_id=template_a, action_payload={"code": code_a},
        ))
        return template_b, code_a


def _revision(engine):
    with engine.connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


def _uniques(engine):
    return {item["name"]: item["column_names"] for item in inspect(engine).get_unique_constraints("document_templates")}


def test_upgrade_preserves_legacy_rows_and_downgrade_rejects_code_collision(migration_database):
    engine, config = migration_database
    command.upgrade(config, _BASE)
    assert _revision(engine) == _BASE
    assert _uniques(engine) == {"document_templates_code_key": ["code"]}
    template_b, shared_code = _seed_legacy(engine)
    before = _historical_rows(engine)

    with engine.connect() as conn:
        inventory = conn.execute(text("""
            SELECT count(DISTINCT p.template_version_id) AS version_count,
                   count(DISTINCT t.organization_id) AS tenant_count,
                   coalesce(bool_or(t.organization_id <> u.organization_id), false) AS creator_mismatch
            FROM computed_placeholder_expressions e
            JOIN users u ON u.id = e.created_by
            LEFT JOIN template_placeholders p ON p.computed_expression_id = e.id
            LEFT JOIN template_versions v ON v.id = p.template_version_id
            LEFT JOIN document_templates t ON t.id = v.document_template_id
            GROUP BY e.id
            ORDER BY version_count, tenant_count, creator_mismatch
        """)).all()
    assert inventory == [(0, 0, False), (1, 1, False), (1, 1, True), (2, 1, False), (2, 2, True)]
    print(f"Synthetic historical expression inventory (version count, tenant count, creator mismatch): {inventory}")

    command.upgrade(config, _REVISION)
    assert _revision(engine) == _REVISION
    assert _uniques(engine) == {"uq_document_templates_org_code": ["organization_id", "code"]}
    assert _historical_rows(engine) == before
    schema = inspect(engine)
    expressions = "computed_placeholder_expressions"
    owner = next(col for col in schema.get_columns(expressions) if col["name"] == "template_version_id")
    assert owner["nullable"] and owner["default"] is None
    foreign_key = next(fk for fk in schema.get_foreign_keys(expressions) if fk["constrained_columns"] == ["template_version_id"])
    assert (foreign_key["referred_table"], foreign_key["referred_columns"], foreign_key["options"]["ondelete"]) == (
        "template_versions", ["id"], "RESTRICT",
    )
    assert any(index["column_names"] == ["template_version_id"] for index in schema.get_indexes(expressions))
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM computed_placeholder_expressions WHERE template_version_id IS NOT NULL")).scalar_one() == 0

    command.downgrade(config, _BASE)
    assert _revision(engine) == _BASE
    assert _uniques(engine) == {"document_templates_code_key": ["code"]}
    assert _historical_rows(engine) == before

    command.upgrade(config, _REVISION)
    with engine.begin() as conn:
        conn.execute(text("UPDATE document_templates SET code = :code WHERE id = :id"),
                     {"code": shared_code, "id": template_b})
    collision = _historical_rows(engine)
    with pytest.raises(RuntimeError, match="codes are shared by multiple organizations"):
        command.downgrade(config, _BASE)
    assert _revision(engine) == _REVISION
    assert _uniques(engine) == {"uq_document_templates_org_code": ["organization_id", "code"]}
    assert _historical_rows(engine) == collision
