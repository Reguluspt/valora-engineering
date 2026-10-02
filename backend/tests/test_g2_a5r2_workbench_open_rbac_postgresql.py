"""Issue84 grant, provenance and production cookie/session boundary on real PostgreSQL."""

import json
import os
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.rbac import derive_effective_permissions, get_current_user
from app.core.security import hash_password
from app.db import get_db
from app.main import app
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, Project, ProjectWorkflowStatus,
    Role, User, UserRole, UserStatus, WorkbenchSession,
)


PREDECESSOR = "a4b5c6d7e8f9"
REVISION = "b5c6d7e8f9a0"
EVENT = "G2A5R2StandardOperatorWorkbenchOpenGrantAdded"
PERMISSION = "workbench:open"
TARGET_ROLES = {"owner", "appraiser"}
STANDARD_ROLES = TARGET_ROLES | {"admin", "viewer", "reviewer", "knowledge_curator"}
BACKEND = Path(__file__).resolve().parents[1]


def _test_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url or not url.startswith("postgres"):
        if os.getenv("CI") == "true":
            pytest.fail("A5R2 requires PostgreSQL TEST_DATABASE_URL in CI")
        pytest.skip("A5R2 requires PostgreSQL TEST_DATABASE_URL")
    return url


@contextmanager
def _isolated_database():
    base_url = make_url(_test_url())
    name = f"g2a5r2_{uuid.uuid4().hex}"
    admin = create_engine(base_url, isolation_level="AUTOCOMMIT")
    database_url = base_url.set(database=name)
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        engine = create_engine(database_url)
        try:
            yield database_url, engine
        finally:
            engine.dispose()
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def _alembic(database_url, action: str, revision: str) -> None:
    environment = os.environ.copy()
    environment.update({
        "POSTGRES_HOST": database_url.host or "localhost",
        "POSTGRES_PORT": str(database_url.port or 5432),
        "POSTGRES_DB": database_url.database,
        "POSTGRES_USER": database_url.username or "valora",
        "POSTGRES_PASSWORD": database_url.password or "",
        "VALORA_ENV": "test",
    })
    result = subprocess.run(
        [sys.executable, "-c", "from alembic import command; from alembic.config import Config; "
         f"command.{action}(Config('alembic.ini'), '{revision}')"],
        cwd=BACKEND, env=environment, text=True, capture_output=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _roles(engine):
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT id, code, permissions FROM roles ORDER BY code")).all()
    return {code: (role_id, permissions) for role_id, code, permissions in rows}


def _audit(engine):
    with engine.connect() as connection:
        return connection.execute(text(
            "SELECT entity_id, entity_type, command_name, payload FROM audit_events "
            "WHERE event_name = :event ORDER BY entity_id, created_at, id"
        ), {"event": EVENT}).all()


def _assert_head(engine, expected):
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == expected


def _set_permissions(connection, role_id, permissions):
    connection.execute(text("UPDATE roles SET permissions = CAST(:permissions AS json) WHERE id = :id"),
                       {"permissions": json.dumps(permissions), "id": role_id})


def _assert_delta(before, after):
    assert STANDARD_ROLES <= before.keys()
    assert set(after) == set(before)
    for code, (role_id, permissions) in before.items():
        added = [PERMISSION] if code in TARGET_ROLES and PERMISSION not in permissions else []
        assert after[code] == (role_id, permissions + added)
        assert len(after[code][1]) == len(set(after[code][1]))
        for unchanged in ("workbench:edit", "workbench:read", "workbench:undo_redo"):
            assert after[code][1].count(unchanged) == permissions.count(unchanged)


def _assert_provenance(engine, before):
    rows = _audit(engine)
    assert len(rows) == 2
    by_id = {row.entity_id: row for row in rows}
    assert set(by_id) == {before[code][0] for code in TARGET_ROLES}
    for code in TARGET_ROLES:
        role_id, permissions = before[code]
        row = by_id[role_id]
        assert row.entity_type == "Role"
        assert row.command_name == REVISION
        assert row.payload == {"role_code": code,
            "added_permissions": [] if PERMISSION in permissions else [PERMISSION]}


def _assert_production_endpoints(engine):
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint")
    identity_override = app.dependency_overrides.pop(get_current_user, None)
    database_override = app.dependency_overrides.get(get_db)
    try:
        first = OrganizationProfile(legal_name="A5R2 synthetic first tenant",
            organization_slug=f"a5r2-first-{uuid.uuid4().hex}", status=OrganizationStatus.ACTIVE)
        second = OrganizationProfile(legal_name="A5R2 synthetic second tenant",
            organization_slug=f"a5r2-second-{uuid.uuid4().hex}", status=OrganizationStatus.ACTIVE)
        db.add_all([first, second])
        db.flush()
        password = uuid.uuid4().hex
        password_hash = hash_password(password)
        users = {}
        for code in sorted(STANDARD_ROLES) + ["cross_owner", "cross_appraiser"]:
            role_code = code.removeprefix("cross_")
            organization = second if code.startswith("cross_") else first
            role = db.query(Role).filter_by(code=role_code).one()
            user = User(organization_id=organization.id, email=f"{code}@a5r2.invalid",
                full_name=code, password_hash=password_hash, status=UserStatus.ACTIVE)
            db.add(user)
            db.flush()
            db.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))
            users[code] = user
        project = Project(organization_id=first.id, customer_id=None, code="A5R2-SYNTH",
            name="Synthetic session authority", status=ProjectWorkflowStatus.DRAFT,
            created_by=users["owner"].id)
        db.add(project)
        db.commit()
        db.expire_all()
        for code, user in users.items():
            assert (PERMISSION in derive_effective_permissions(user, db)) == (
                code.removeprefix("cross_") in TARGET_ROLES)

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        # Restore production authentication; do not override require_permission or create sessions.
        assert get_current_user not in app.dependency_overrides
        with TestClient(app) as client:
            def login(code):
                client.cookies.clear()
                response = client.post("/api/v1/auth/login", json={
                    "organization_slug": users[code].organization.organization_slug,
                    "email": users[code].email, "password": password})
                assert response.status_code == 200, response.text
                return {"X-CSRF-Token": client.cookies["XSRF-TOKEN"],
                        "Origin": "http://localhost:5173"}

            payload = {"project_id": str(project.id)}
            sessions = {}
            for code in ("owner", "appraiser"):
                headers = login(code)
                created = client.post("/api/v1/workbench/sessions", json=payload, headers=headers)
                assert created.status_code == 201, created.text
                assert created.json()["project_id"] == str(project.id)
                assert created.json()["user_id"] == str(users[code].id)
                sessions[code] = created.json()
                obtained = client.post("/api/v1/workbench/sessions", json=payload, headers=headers)
                assert obtained.status_code == 200
                assert obtained.json()["id"] == sessions[code]["id"]
                heartbeat = client.post(f"/api/v1/workbench/sessions/{sessions[code]['id']}/heartbeat",
                    json={"expected_row_version": obtained.json()["row_version"]}, headers=headers)
                assert heartbeat.status_code == 200, heartbeat.text
                assert client.get(f"/api/v1/workbench/sessions/{sessions[code]['id']}").status_code == 403
                for command in ("undo", "redo"):
                    assert client.post(f"/api/v1/workbench/sessions/{sessions[code]['id']}/{command}",
                                       headers=headers).status_code == 403
            for code in sorted(STANDARD_ROLES - TARGET_ROLES):
                assert client.post("/api/v1/workbench/sessions", json=payload,
                                   headers=login(code)).status_code == 403
            for code in ("cross_owner", "cross_appraiser"):
                headers = login(code)
                response = client.post("/api/v1/workbench/sessions", json=payload, headers=headers)
                assert response.status_code == 404, response.text
                assert client.post(f"/api/v1/workbench/sessions/{sessions['owner']['id']}/heartbeat",
                    json={"expected_row_version": 1}, headers=headers).status_code == 404
            # A same-tenant operator still cannot maintain another operator's owned session.
            assert client.post(f"/api/v1/workbench/sessions/{sessions['owner']['id']}/heartbeat",
                json={"expected_row_version": 1}, headers=login("appraiser")).status_code == 404
            client.cookies.clear()
            assert client.post("/api/v1/workbench/sessions", json=payload).status_code == 401
            assert db.query(WorkbenchSession).count() == 2
    finally:
        if identity_override is not None:
            app.dependency_overrides[get_current_user] = identity_override
        if database_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = database_override
        db.close()
        transaction.rollback()
        connection.close()


def test_exact_grant_provenance_production_sessions_and_downgrade():
    with _isolated_database() as (database_url, engine):
        _alembic(database_url, "upgrade", PREDECESSOR)
        _assert_head(engine, PREDECESSOR)
        before = _roles(engine)
        assert all(PERMISSION not in before[code][1] for code in STANDARD_ROLES)
        _alembic(database_url, "upgrade", REVISION)
        _assert_head(engine, REVISION)
        _assert_delta(before, _roles(engine))
        _assert_provenance(engine, before)
        _assert_production_endpoints(engine)
        _alembic(database_url, "downgrade", PREDECESSOR)
        _assert_head(engine, PREDECESSOR)
        assert _roles(engine) == before


def test_preexisting_target_and_admin_grants_are_preserved():
    with _isolated_database() as (database_url, engine):
        _alembic(database_url, "upgrade", PREDECESSOR)
        roles = _roles(engine)
        with engine.begin() as connection:
            _set_permissions(connection, roles["owner"][0], roles["owner"][1] + [PERMISSION])
            _set_permissions(connection, roles["admin"][0], roles["admin"][1] +
                             [PERMISSION, "workbench:read", "workbench:undo_redo"])
        before = _roles(engine)
        _alembic(database_url, "upgrade", REVISION)
        _assert_delta(before, _roles(engine))
        _assert_provenance(engine, before)
        _alembic(database_url, "downgrade", PREDECESSOR)
        _assert_head(engine, PREDECESSOR)
        assert _roles(engine) == before


def test_repeated_round_trip_retains_history_and_uses_latest_provenance():
    with _isolated_database() as (database_url, engine):
        _alembic(database_url, "upgrade", PREDECESSOR)
        before = _roles(engine)
        for cycle in range(2):
            _alembic(database_url, "upgrade", REVISION)
            _assert_delta(before, _roles(engine))
            assert len(_audit(engine)) == 2 * (cycle + 1)
            _alembic(database_url, "downgrade", PREDECESSOR)
            _assert_head(engine, PREDECESSOR)
            assert _roles(engine) == before


@pytest.mark.parametrize("fault", ("missing", "wrong_revision", "wrong_entity", "wrong_role_id"))
def test_latest_cycle_fault_cannot_reuse_historical_grant_provenance(fault):
    with _isolated_database() as (database_url, engine):
        _alembic(database_url, "upgrade", REVISION)
        _alembic(database_url, "downgrade", PREDECESSOR)
        roles = _roles(engine)
        # This grant predates the next upgrade and must not be removed using the old cycle's audit.
        with engine.begin() as connection:
            _set_permissions(connection, roles["appraiser"][0], roles["appraiser"][1] + [PERMISSION])
        _alembic(database_url, "upgrade", REVISION)
        with engine.begin() as connection:
            where = ("event_name = :event AND entity_id = :role_id AND created_at = "
                     "(SELECT max(created_at) FROM audit_events WHERE event_name = :event)")
            params = {"event": EVENT, "role_id": roles["appraiser"][0]}
            if fault == "missing":
                connection.execute(text(f"DELETE FROM audit_events WHERE {where}"), params)
            else:
                field, value = {"wrong_revision": ("command_name", "other-revision"),
                                "wrong_entity": ("entity_type", "User"),
                                "wrong_role_id": ("entity_id", uuid.uuid4())}[fault]
                connection.execute(text(f"UPDATE audit_events SET {field} = :value WHERE {where}"),
                                   {**params, "value": value})
        before = _roles(engine)
        before_audit = _audit(engine)
        with pytest.raises(AssertionError, match="Invalid A5R2 grant provenance"):
            _alembic(database_url, "downgrade", PREDECESSOR)
        _assert_head(engine, REVISION)
        assert _roles(engine) == before
        assert _audit(engine) == before_audit


@pytest.mark.parametrize("fault", ("missing", "non_list", "non_string", "duplicate"))
def test_upgrade_failure_rolls_back_owner_and_provenance(fault):
    with _isolated_database() as (database_url, engine):
        _alembic(database_url, "upgrade", PREDECESSOR)
        roles = _roles(engine)
        with engine.begin() as connection:
            if fault == "missing":
                connection.execute(text("DELETE FROM roles WHERE code = 'appraiser'"))
            else:
                malformed = {"non_list": 42, "non_string": [1],
                             "duplicate": ["project:read", "project:read"]}[fault]
                _set_permissions(connection, roles["appraiser"][0], malformed)
        before = _roles(engine)
        message = "Missing standard role" if fault == "missing" else "Invalid permissions"
        with pytest.raises(AssertionError, match=message):
            _alembic(database_url, "upgrade", REVISION)
        _assert_head(engine, PREDECESSOR)
        assert _roles(engine) == before
        assert _audit(engine) == []


@pytest.mark.parametrize("fault", (
    "missing", "non_object", "wrong_role", "wrong_permission", "missing_added",
    "wrong_revision", "wrong_entity", "ambiguous_latest", "missing_grant", "duplicate_permissions",
))
def test_downgrade_failure_rolls_back_owner_without_retreating_version(fault):
    with _isolated_database() as (database_url, engine):
        _alembic(database_url, "upgrade", REVISION)
        roles = _roles(engine)
        role_id, permissions = roles["appraiser"]
        with engine.begin() as connection:
            params = {"event": EVENT, "role_id": role_id}
            where = "event_name = :event AND entity_id = :role_id AND command_name = :revision"
            params["revision"] = REVISION
            if fault == "missing":
                connection.execute(text(f"DELETE FROM audit_events WHERE {where}"), params)
            elif fault == "ambiguous_latest":
                connection.execute(text(
                    "INSERT INTO audit_events (id, event_name, entity_type, entity_id, command_name, payload, created_at) "
                    f"SELECT :id, event_name, entity_type, entity_id, command_name, payload, created_at FROM audit_events WHERE {where}"
                ), {**params, "id": uuid.uuid4()})
            elif fault == "wrong_revision":
                connection.execute(text(f"UPDATE audit_events SET command_name = 'other-revision' WHERE {where}"), params)
            elif fault == "wrong_entity":
                connection.execute(text(f"UPDATE audit_events SET entity_type = 'User' WHERE {where}"), params)
            elif fault in ("missing_grant", "duplicate_permissions"):
                updated = ([p for p in permissions if p != PERMISSION] if fault == "missing_grant"
                           else permissions + [PERMISSION])
                _set_permissions(connection, role_id, updated)
            else:
                payload = {"non_object": 42,
                    "wrong_role": {"role_code": "owner", "added_permissions": [PERMISSION]},
                    "wrong_permission": {"role_code": "appraiser", "added_permissions": ["workbench:read"]},
                    "missing_added": {"role_code": "appraiser"}}[fault]
                connection.execute(text(f"UPDATE audit_events SET payload = CAST(:payload AS json) WHERE {where}"),
                                   {**params, "payload": json.dumps(payload)})
        before = _roles(engine)
        before_audit = _audit(engine)
        message = "Invalid permissions" if fault == "duplicate_permissions" else "Invalid A5R2 grant provenance"
        with pytest.raises(AssertionError, match=message):
            _alembic(database_url, "downgrade", PREDECESSOR)
        _assert_head(engine, REVISION)
        assert _roles(engine) == before
        assert _audit(engine) == before_audit
