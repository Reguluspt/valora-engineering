import runpy
import os
import subprocess
import sys
from pathlib import Path
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError

from app.db.session import engine, SessionLocal
from app.modules.project_master_data.models import (
    AuditEvent,
    OrganizationProfile,
    User,
    Project,
    Role,
    UserRole,
    UserSession,
    PreliminaryProjectCreateReceipt as Receipt,
)
from tests.test_preliminary_project_create import command
from tests.test_preliminary_project_create_postgresql import principal as principal_fixture

from app.modules.project_master_data.application import (
    preliminary_project_create_service as service,
)

principal = principal_fixture


@pytest.mark.parametrize(
    "violation",
    [
        "organization_id",
        "actor_user_id",
        "project_id",
        "audit_event_id",
        "duplicate_key",
        "audit_binding",
    ],
)
def test_a28_database_rejects_foreign_scope_and_duplicate_evidence(principal, violation, monkeypatch):
    other = principal_fixture.__wrapped__(monkeypatch)
    first, second, foreign = command(), command(), command()
    service.create_preliminary_request(principal, first)
    service.create_preliminary_request(principal, second)
    service.create_preliminary_request(other, foreign)
    with SessionLocal() as db:
        row = service.find_receipt(db, principal, uuid.UUID(second.request_id))
        original = service.find_receipt(db, principal, uuid.UUID(first.request_id))
        other_row = service.find_receipt(db, other, uuid.UUID(foreign.request_id))
        before = (
            row.organization_id,
            row.actor_user_id,
            row.project_id,
            row.audit_event_id,
            row.request_id,
        )
        if violation == "duplicate_key":
            row.request_id = original.request_id
        elif violation == "audit_binding":
            row.audit_event_id = original.audit_event_id
        else:
            setattr(row, violation, getattr(other_row, violation))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert (
            row.organization_id,
            row.actor_user_id,
            row.project_id,
            row.audit_event_id,
            row.request_id,
        ) == before
        assert db.query(Receipt).filter_by(organization_id=principal.organization_id).count() == 2


def test_a28_retained_metadata_matches_database_and_downgrade_refuses(principal):
    migration = runpy.run_path(
        str(
            Path(__file__).parents[1]
            / "alembic/versions/0a1b2c3d4e5f_preliminary_project_create_receipts.py"
        )
    )
    assert migration["down_revision"] == "f9a0b1c2d3e4"
    inspector = inspect(engine)
    assert {c["name"] for c in inspector.get_foreign_keys(Receipt.__tablename__)} == {
        "fk_pcreate_org",
        "fk_pcreate_actor",
        "fk_pcreate_project",
        "fk_pcreate_audit",
    }
    assert {c["name"] for c in inspector.get_unique_constraints(Receipt.__tablename__)} == {
        "uq_pcreate_scope",
        "uq_pcreate_project",
        "uq_pcreate_audit",
    }
    with pytest.raises(RuntimeError, match="retained"):
        migration["downgrade"]()
    assert inspector.has_table(Receipt.__tablename__)


def test_a28_nullable_historical_audit_and_restricted_deletion(principal):
    with SessionLocal() as db:
        legacy = AuditEvent(event_name="Synthetic historical", entity_type="Historical")
        db.add(legacy)
        db.commit()
    result, _ = service.create_preliminary_request(principal, command())
    with SessionLocal() as db:
        with pytest.raises(IntegrityError):
            db.execute(
                text("DELETE FROM projects WHERE id=:id"),
                {"id": uuid.UUID(result["project"]["id"])},
            )
            db.commit()
        db.rollback()
        assert db.query(Receipt).filter_by(organization_id=principal.organization_id).count() == 1


@pytest.mark.parametrize("populated", [False, True])
def test_a28_additive_upgrade_preserves_synthetic_history(principal, monkeypatch, populated):
    name = "valora_issue217_disposable_migration_" + uuid.uuid4().hex
    assert name.startswith("valora_issue217_disposable_migration_") and name.isidentifier()
    admin = create_engine(engine.url, isolation_level="AUTOCOMMIT")
    target = create_engine(engine.url.set(database=name))
    env = {**os.environ, "POSTGRES_DB": name}

    def migrate(revision, action="upgrade"):
        return subprocess.run(
            [sys.executable, "-m", "alembic", action, revision],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    try:
        with admin.connect() as db:
            db.execute(text(f'CREATE DATABASE "{name}"'))
        result = migrate("f9a0b1c2d3e4")
        assert result.returncode == 0, result.stderr
        with Session(target) as db:
            org = OrganizationProfile(legal_name="Historic synthetic", organization_slug="historic")
            db.add(org)
            db.flush()
            user = User(
                organization_id=org.id,
                email="historic@example.invalid",
                full_name="Historic synthetic",
            )
            db.add(user)
            db.flush()
            project = Project(
                organization_id=org.id,
                created_by=user.id,
                code="Historic-X",
                name="Historic synthetic",
            )
            db.add_all([project, AuditEvent(event_name="Legacy nullable", entity_type="Legacy")])
            db.flush()
            before = (project.id, project.code, project.name)
            before_audits = db.query(AuditEvent).count()
            db.commit()
        result = migrate("head")
        assert result.returncode == 0, result.stderr
        with Session(target) as db:
            project = db.get(Project, before[0])
            assert (project.id, project.code, project.name) == before
            assert db.query(Receipt).count() == 0
            assert db.query(AuditEvent).count() == before_audits
        if populated:
            now = datetime.now(timezone.utc)
            with Session(target) as db:
                project = db.get(Project, before[0])
                role = Role(
                    code="synthetic-owner",
                    display_name="Owner",
                    permissions=["project:create", "project:read"],
                )
                db.add(role)
                db.flush()
                db.add(UserRole(user_id=project.created_by, role_id=role.id))
                session = UserSession(
                    user_id=project.created_by,
                    organization_id=project.organization_id,
                    access_token_hash="a" * 64,
                    access_expires_at=now + timedelta(hours=1),
                    idle_expires_at=now + timedelta(hours=1),
                    absolute_expires_at=now + timedelta(hours=2),
                )
                db.add(session)
                db.flush()
                who = service.Principal(project.organization_id, project.created_by, session.id)
                db.commit()
            with monkeypatch.context() as patch:
                patch.setattr(service, "engine", target)
                patch.setattr(service, "SessionLocal", sessionmaker(bind=target))
                result, status = service.create_preliminary_request(who, command())
                assert status == 201
        with target.connect() as db:
            tables = ["projects", "audit_events", "preliminary_project_create_receipts"]
            before_rows = {
                table: db.execute(text(f'SELECT * FROM "{table}" ORDER BY id')).all()
                for table in tables
            }
            assert len(before_rows[tables[2]]) == int(populated)
            version = db.scalar(text("SELECT version_num FROM alembic_version"))
            assert version == "0a1b2c3d4e5f"
        result = migrate("f9a0b1c2d3e4", "downgrade")
        assert result.returncode != 0 and "must be retained" in result.stderr
        assert inspect(target).has_table(Receipt.__tablename__)
        with target.connect() as db:
            assert db.scalar(text("SELECT version_num FROM alembic_version")) == version
            assert {
                table: db.execute(text(f'SELECT * FROM "{table}" ORDER BY id')).all()
                for table in tables
            } == before_rows
    finally:
        target.dispose()
        with admin.connect() as db:
            db.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()
