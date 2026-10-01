"""Real PostgreSQL round-trip and endpoint proof for standard Workbench grants."""

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

from app.core.rbac import derive_effective_permissions
from app.db import get_db
from app.main import app
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, Project, ProjectWorkflowStatus,
    Role, User, UserRole, UserStatus,
)


PREDECESSOR = "d1e2f3a4b5c6"
REVISION = "e2f3a4b5c6d7"
EVENT = "G1KStandardOperatorWorkbenchEditGrantAdded"
PERMISSION = "workbench:edit"
STANDARD_ROLES = {"owner", "appraiser", "admin", "reviewer", "knowledge_curator", "viewer"}
BACKEND = Path(__file__).resolve().parents[1]


def _test_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url or not url.startswith("postgres"):
        if os.getenv("CI") == "true":
            pytest.fail("RBAC-001 requires PostgreSQL TEST_DATABASE_URL in CI")
        pytest.skip("RBAC-001 requires PostgreSQL TEST_DATABASE_URL")
    return url


@contextmanager
def _isolated_database():
    base_url = make_url(_test_url())
    name = f"g1rbac_{uuid.uuid4().hex}"
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


def _roles(engine) -> dict[str, tuple[uuid.UUID, list[str]]]:
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT id, code, permissions FROM roles ORDER BY code"
        )).all()
    return {code: (role_id, permissions) for role_id, code, permissions in rows}


def _audit(engine) -> dict[str, tuple[uuid.UUID, dict]]:
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT entity_id, payload FROM audit_events "
            "WHERE event_name = :event AND command_name = :revision"
        ), {"event": EVENT, "revision": REVISION}).all()
    return {payload["role_code"]: (entity_id, payload) for entity_id, payload in rows}


def _assert_head(engine, expected: str) -> None:
    with engine.connect() as connection:
        actual = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert actual == expected


def _assert_effective_permissions_and_endpoints(engine) -> None:
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        first = OrganizationProfile(
            legal_name="RBAC-001 synthetic first tenant",
            organization_slug=f"g1rbac-first-{uuid.uuid4().hex}",
            status=OrganizationStatus.ACTIVE,
        )
        second = OrganizationProfile(
            legal_name="RBAC-001 synthetic second tenant",
            organization_slug=f"g1rbac-second-{uuid.uuid4().hex}",
            status=OrganizationStatus.ACTIVE,
        )
        db.add_all([first, second])
        db.flush()
        users = {}
        for code, organization in (
            ("owner", first), ("appraiser", first), ("viewer", first),
            ("other_appraiser", second),
        ):
            role_code = "appraiser" if code == "other_appraiser" else code
            role = db.query(Role).filter_by(code=role_code).one()
            user = User(
                organization_id=organization.id, email=f"{code}@g1rbac.invalid",
                full_name=code, status=UserStatus.ACTIVE,
            )
            db.add(user)
            db.flush()
            db.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))
            users[code] = user
        projects = {}
        for code in ("owner", "appraiser"):
            project = Project(
                organization_id=first.id, customer_id=None,
                code=f"G1RBAC-{code}", name=f"Synthetic {code} project",
                status=ProjectWorkflowStatus.DRAFT, created_by=users[code].id,
            )
            db.add(project)
            projects[code] = project
        db.commit()
        db.expire_all()

        for code in ("owner", "appraiser", "other_appraiser"):
            assert PERMISSION in derive_effective_permissions(users[code], db)
        assert PERMISSION not in derive_effective_permissions(users["viewer"], db)

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app) as client:
                payload = {"source_filename": "synthetic.xlsx", "source_sheet_name": "Assets"}
                for code in ("owner", "appraiser"):
                    response = client.post(
                        f"/api/v1/projects/{projects[code].id}/asset-imports",
                        json=payload, headers={"X-User-Id": str(users[code].id)},
                    )
                    assert response.status_code == 201, response.text
                    assert response.json()["project_id"] == str(projects[code].id)
                denied = client.post(
                    f"/api/v1/projects/{projects['owner'].id}/asset-imports",
                    json=payload, headers={"X-User-Id": str(users["viewer"].id)},
                )
                assert denied.status_code == 403
                cross_tenant = client.post(
                    f"/api/v1/projects/{projects['owner'].id}/asset-imports",
                    json=payload, headers={"X-User-Id": str(users["other_appraiser"].id)},
                )
                assert cross_tenant.status_code == 404
                unauthenticated = client.post(
                    f"/api/v1/projects/{projects['owner'].id}/asset-imports",
                    json=payload,
                )
                assert unauthenticated.status_code == 401
        finally:
            app.dependency_overrides.pop(get_db, None)
    finally:
        db.close()
        transaction.rollback()
        connection.close()


def test_migration_grants_only_standard_operators_and_downgrades_safely():
    with _isolated_database() as (database_url, engine):
        _alembic(database_url, "upgrade", PREDECESSOR)
        _assert_head(engine, PREDECESSOR)
        before = _roles(engine)
        assert STANDARD_ROLES <= before.keys()
        assert all(PERMISSION not in before[code][1] for code in STANDARD_ROLES)

        _alembic(database_url, "upgrade", REVISION)
        _assert_head(engine, REVISION)
        after = _roles(engine)
        assert set(after) == set(before)
        for code in ("owner", "appraiser"):
            assert after[code][1] == before[code][1] + [PERMISSION]
            assert after[code][1].count(PERMISSION) == 1
        for code in set(before) - {"owner", "appraiser"}:
            assert after[code] == before[code]
        audit = _audit(engine)
        assert set(audit) == {"owner", "appraiser"}
        for code in audit:
            assert audit[code] == (before[code][0], {
                "role_code": code, "added_permissions": [PERMISSION],
            })
        _assert_effective_permissions_and_endpoints(engine)

        _alembic(database_url, "downgrade", PREDECESSOR)
        _assert_head(engine, PREDECESSOR)
        assert _roles(engine) == before


def test_preexisting_workbench_grant_is_preserved_on_downgrade():
    with _isolated_database() as (database_url, engine):
        _alembic(database_url, "upgrade", PREDECESSOR)
        before = _roles(engine)
        owner_id, owner_permissions = before["owner"]
        with engine.begin() as connection:
            connection.execute(text(
                "UPDATE roles SET permissions = CAST(:permissions AS json) WHERE id = :role_id"
            ), {"permissions": json.dumps(owner_permissions + [PERMISSION]),
                "role_id": owner_id})
        predecessor_state = _roles(engine)

        _alembic(database_url, "upgrade", REVISION)
        after = _roles(engine)
        assert after["owner"] == predecessor_state["owner"]
        assert after["appraiser"][1] == before["appraiser"][1] + [PERMISSION]
        assert after["owner"][1].count(PERMISSION) == 1
        audit = _audit(engine)
        assert audit["owner"][1]["added_permissions"] == []
        assert audit["appraiser"][1]["added_permissions"] == [PERMISSION]

        _alembic(database_url, "downgrade", PREDECESSOR)
        assert _roles(engine) == predecessor_state


@pytest.mark.parametrize(
    ("fault", "expected"),
    (("missing", "Missing standard role appraiser"),
     ("malformed", "Invalid permissions for standard role appraiser")),
)
def test_upgrade_fails_closed_and_rolls_back_partial_grant(fault: str, expected: str):
    with _isolated_database() as (database_url, engine):
        _alembic(database_url, "upgrade", PREDECESSOR)
        with engine.begin() as connection:
            if fault == "missing":
                connection.execute(text("DELETE FROM roles WHERE code = 'appraiser'"))
            else:
                connection.execute(text(
                    "UPDATE roles SET permissions = CAST('42' AS json) "
                    "WHERE code = 'appraiser'"
                ))
        before = _roles(engine)

        with pytest.raises(AssertionError, match=expected):
            _alembic(database_url, "upgrade", REVISION)

        _assert_head(engine, PREDECESSOR)
        assert _roles(engine) == before
        assert _audit(engine) == {}
