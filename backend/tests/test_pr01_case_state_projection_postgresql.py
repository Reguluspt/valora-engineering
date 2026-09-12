"""PostgreSQL single-session and read-consistency evidence for Global Case State projection (VALORA-PR01-IMPL-003)."""
from __future__ import annotations

import os
import threading
import uuid
from typing import Any


import pytest
from fastapi.testclient import TestClient

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_db
from app.main import app
from app.modules.project_master_data.application.case_state_projection import (
    get_case_state_projection,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    Customer,
    CustomerStatus,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    Role,
    User,
    UserRole,
    UserStatus,
)


def _postgres_engine_or_skip():
    url = os.getenv("TEST_DATABASE_URL")
    if not url or not url.startswith("postgres"):
        if os.getenv("CI") == "true":
            pytest.fail("CI=true requires PostgreSQL TEST_DATABASE_URL for PR-01 case-state projection")
        pytest.skip("PR-01 case-state projection proof requires PostgreSQL TEST_DATABASE_URL")
    engine = create_engine(url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT to_regclass('project_official_intake_commits')")
        ).scalar_one()
    if exists is None:
        engine.dispose()
        if os.getenv("CI") == "true":
            pytest.fail("CI PostgreSQL is not migrated to the PR-01 head")
        pytest.skip("PostgreSQL is not migrated to the PR-01 head")
    return engine


def _seed(SessionLocal) -> dict[str, Any]:
    db: Session = SessionLocal()
    try:
        suffix = uuid.uuid4().hex[:8]
        org = OrganizationProfile(
            legal_name=f"PG Projection Org {suffix}",
            organization_slug=f"pg-proj-org-{suffix}",
            status=OrganizationStatus.ACTIVE,
        )
        db.add(org)
        db.flush()

        actor = User(
            organization_id=org.id,
            email=f"pg-proj-{suffix}@example.com",
            full_name="PG Projection Human",
            status=UserStatus.ACTIVE,
        )
        db.add(actor)
        db.flush()

        role = Role(
            code=f"pg-role-{suffix}",
            display_name="PG Projection Role",
            permissions=["project:read"],
        )
        db.add(role)
        db.flush()

        user_role = UserRole(user_id=actor.id, role_id=role.id, is_active=True)
        db.add(user_role)

        customer = Customer(
            organization_id=org.id,
            legal_name=f"PG Customer {suffix}",
            status=CustomerStatus.ACTIVE,
            created_by=actor.id,
        )
        db.add(customer)
        db.flush()

        project = Project(
            organization_id=org.id,
            customer_id=customer.id,
            code=f"PG-{suffix[:6]}",
            name="PG Project",
            created_by=actor.id,
        )
        db.add(project)
        db.commit()

        return {
            "org_id": org.id,
            "actor_id": actor.id,
            "project_id": project.id,
            "role_id": role.id,
        }
    finally:
        db.close()


def _cleanup(SessionLocal, ids: dict[str, uuid.UUID]) -> None:
    db: Session = SessionLocal()
    try:
        org_id = ids["org_id"]
        db.query(Project).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(Customer).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(UserRole).filter_by(user_id=ids["actor_id"]).delete(synchronize_session=False)
        db.query(Role).filter_by(id=ids["role_id"]).delete(synchronize_session=False)
        db.query(User).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(OrganizationProfile).filter_by(id=org_id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_postgresql_single_session_read_consistency() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine)
    ids = _seed(SessionLocal)
    db: Session = SessionLocal()
    try:
        actor = db.get(User, ids["actor_id"])
        assert actor is not None

        # Multiple consecutive reads in the same transaction
        p1 = get_case_state_projection(
            db, actor=actor, org_id=ids["org_id"], project_id=ids["project_id"]
        )
        p2 = get_case_state_projection(
            db, actor=actor, org_id=ids["org_id"], project_id=ids["project_id"]
        )

        assert p1.case_version == p2.case_version
        assert p1.current_stage == p2.current_stage
        assert p1.next_action == p2.next_action
        assert not db.dirty
        assert not db.new
        assert not db.deleted
    finally:
        db.close()
        _cleanup(SessionLocal, ids)
        engine.dispose()


def test_postgresql_concurrent_reads_do_not_block_and_are_consistent() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine)
    ids = _seed(SessionLocal)

    results: list[str] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(3, timeout=15)

    def worker() -> None:
        db: Session = SessionLocal()
        try:
            actor = db.get(User, ids["actor_id"])
            assert actor is not None
            barrier.wait(timeout=15)
            proj = get_case_state_projection(
                db, actor=actor, org_id=ids["org_id"], project_id=ids["project_id"]
            )
            results.append(proj.case_version)
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    try:
        assert not errors, f"Concurrent read errors: {errors}"
        assert len(results) == 3
        assert results[0] == results[1] == results[2]
    finally:
        _cleanup(SessionLocal, ids)
        engine.dispose()


def test_postgresql_no_for_update_and_no_audit() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine)
    ids = _seed(SessionLocal)
    db: Session = SessionLocal()

    statements: list[str] = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        init_audits = db.query(AuditEvent).count()
        actor = db.get(User, ids["actor_id"])
        assert actor is not None

        proj = get_case_state_projection(
            db, actor=actor, org_id=ids["org_id"], project_id=ids["project_id"]
        )
        assert proj is not None

        # Verify no FOR UPDATE in any executed SQL statement
        for stmt in statements:
            assert "FOR UPDATE" not in stmt.upper(), f"Unexpected FOR UPDATE in statement: {stmt}"

        # Verify no AuditEvent was created
        assert db.query(AuditEvent).count() == init_audits
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        db.close()
        _cleanup(SessionLocal, ids)
        engine.dispose()


def test_postgresql_http_endpoint_is_read_only() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine)
    ids = _seed(SessionLocal)
    db: Session = SessionLocal()
    statements: list[str] = []

    def override_get_db():
        yield db

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    app.dependency_overrides[get_db] = override_get_db
    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        initial_audits = db.query(AuditEvent).count()
        response = TestClient(app).get(
            f"/api/v1/projects/{ids['project_id']}/case-state",
            headers={"X-User-Id": str(ids["actor_id"])},
        )

        assert response.status_code == 200
        assert response.json()["current_stage"] == "PRELIMINARY_REQUEST"
        assert len(response.json()["stages"]) == 16
        assert all("FOR UPDATE" not in statement.upper() for statement in statements)
        assert db.query(AuditEvent).count() == initial_audits
        assert not db.new
        assert not db.dirty
        assert not db.deleted
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        app.dependency_overrides.pop(get_db, None)
        db.close()
        _cleanup(SessionLocal, ids)
        engine.dispose()
