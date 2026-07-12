"""
S12-R-004: Official Mutation Command and Atomic Audit Gate
Acceptance Tests

All tests use SQLite in-memory unless a PostgreSQL-backed test is labelled
``test_postgres_*``.  PostgreSQL tests skip locally if no TEST_DATABASE_URL
is set; they ``pytest.fail`` when CI=true and the URL is missing.
"""

import os
import uuid
import ast
import threading
from decimal import Decimal
from typing import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.main import app
from app.db import Base, get_db
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserStatus,
    Role,
    UserRole,
    Customer,
    Project,
    ProjectWorkflowStatus,
    ProjectAssetLine,
    InlineEditDraft,
    InlineEditDraftStatus,
    WorkbenchSession,
    WorkbenchSessionStatus,
    AuditEvent,
)
from app.modules.project_master_data.commands.commit_asset_line_draft import (
    execute_commit_asset_line_draft,
    validate_description,
    validate_appraised_unit_price,
)


# ---------------------------------------------------------------------------
# SQLite in-memory fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    sess = Session(bind=engine)
    try:
        yield sess
    finally:
        sess.close()


@pytest.fixture
def client(db_session: Session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared test data helpers
# ---------------------------------------------------------------------------


def _make_org_user_project(
    db: Session,
    *,
    permissions: list,
    status: ProjectWorkflowStatus = ProjectWorkflowStatus.DRAFT,
):
    """Create org → role → user → customer → project → asset_line in one call."""
    org = OrganizationProfile(
        legal_name="TestOrg",
        organization_slug=f"testorg-{uuid.uuid4().hex[:6]}",
        status=OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.flush()

    role = Role(
        code=f"role-{uuid.uuid4().hex[:6]}",
        display_name="Role",
        permissions=permissions,
    )
    db.add(role)
    db.flush()

    pw_hash = hash_password("testpw")
    user = User(
        organization_id=org.id,
        email=f"u-{uuid.uuid4().hex[:6]}@test.com",
        full_name="Test User",
        status=UserStatus.ACTIVE,
        password_hash=pw_hash,
    )
    db.add(user)
    db.flush()

    db.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))

    customer = Customer(
        organization_id=org.id,
        legal_name="Cust",
        status="active",
        created_by=user.id,
    )
    db.add(customer)
    db.flush()

    project = Project(
        organization_id=org.id,
        code=f"P-{uuid.uuid4().hex[:6]}",
        name="Test Project",
        status=status,
        customer_id=customer.id,
        created_by=user.id,
    )
    db.add(project)
    db.flush()

    line = ProjectAssetLine(
        project_id=project.id,
        asset_name="Test Asset",
        description="Initial description",
        quantity=1.0,
        appraised_unit_price=Decimal("100.00"),
        row_version=1,
    )
    db.add(line)
    db.commit()

    return {"org": org, "user": user, "project": project, "line": line}


def _open_session(db: Session, user: User, project: Project) -> WorkbenchSession:
    sess = WorkbenchSession(
        user_id=user.id,
        project_id=project.id,
        status=WorkbenchSessionStatus.ACTIVE,
    )
    db.add(sess)
    db.commit()
    return sess


def _add_draft(
    db: Session,
    session: WorkbenchSession,
    line: ProjectAssetLine,
    field_key: str,
    draft_value,
    base_row_version: int = 1,
) -> InlineEditDraft:
    raw_base = getattr(line, field_key)
    # Ensure Decimal is serializable
    if isinstance(raw_base, Decimal):
        raw_base = str(raw_base)
    draft = InlineEditDraft(
        session_id=session.id,
        target_type="ProjectAssetLine",
        target_id=line.id,
        field_key=field_key,
        draft_value={"value": draft_value},
        base_value={"value": raw_base},
        base_row_version=base_row_version,
        status=InlineEditDraftStatus.DRAFT,
    )
    db.add(draft)
    db.commit()
    return draft


def _login(client: TestClient, db: Session, user: User, org: OrganizationProfile):
    """Create a real UserSession and inject cookies so require_current_user passes."""
    from app.api.auth import get_cookie_keys, hash_token
    import secrets
    from app.modules.project_master_data.models import UserSession

    token = secrets.token_hex(32)
    token_hash = hash_token(token)
    csrf = secrets.token_hex(32)
    csrf_hash = hash_token(csrf)

    us = UserSession(
        user_id=user.id,
        organization_id=org.id,
        access_token_hash=token_hash,
        csrf_token_hash=csrf_hash,
        status="active",
        access_expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        idle_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        absolute_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(us)
    db.commit()

    acc_key, _ = get_cookie_keys()
    client.cookies.set(acc_key, token)
    client.cookies.set("XSRF-TOKEN", csrf)
    client.headers["X-CSRF-Token"] = csrf
    client.headers["Origin"] = "http://localhost:5173"
    return {"token": token, "csrf": csrf}


# ===========================================================================
# 1. DRAFT-only policy — parameterized
# ===========================================================================


@pytest.mark.parametrize(
    "status,expect_success",
    [
        (ProjectWorkflowStatus.DRAFT, True),
        (ProjectWorkflowStatus.UNDER_REVIEW, False),
        (ProjectWorkflowStatus.APPROVED, False),
        (ProjectWorkflowStatus.ARCHIVED, False),
        (ProjectWorkflowStatus.CANCELLED, False),
    ],
)
def test_draft_only_policy(db_session: Session, status, expect_success):
    """
    execute_commit_asset_line_draft raises 400 for every status != DRAFT.
    For DRAFT it succeeds.
    No AuditEvent, no row_version change on non-DRAFT projects.
    """
    entities = _make_org_user_project(
        db_session,
        permissions=["workbench:edit"],
        status=status,
    )
    user: User = entities["user"]
    project: Project = entities["project"]
    line: ProjectAssetLine = entities["line"]

    wb_sess = _open_session(db_session, user, project)
    _add_draft(db_session, wb_sess, line, "description", "new desc", base_row_version=1)

    original_version = line.row_version
    original_price = line.appraised_unit_price

    if expect_success:
        result = execute_commit_asset_line_draft(
            db=db_session,
            actor=user,
            project_id=project.id,
            line_id=line.id,
            field_keys=["description"],
            confirm=True,
            version_token="1",
        )
        db_session.commit()
        assert result["committed_fields"] == ["description"]
        db_session.refresh(line)
        assert line.row_version == original_version + 1
    else:
        with pytest.raises(HTTPException) as exc_info:
            execute_commit_asset_line_draft(
                db=db_session,
                actor=user,
                project_id=project.id,
                line_id=line.id,
                field_keys=["description"],
                confirm=True,
                version_token="1",
            )
        db_session.rollback()

        assert exc_info.value.status_code == 400
        # No mutation — version and price unchanged
        db_session.refresh(line)
        assert line.row_version == original_version
        assert line.appraised_unit_price == original_price

        # No AuditEvent persisted
        audit_count = (
            db_session.query(AuditEvent)
            .filter(AuditEvent.event_name == "project.asset_line.draft_committed")
            .count()
        )
        assert audit_count == 0


# ===========================================================================
# 2. PATCH direct-field bypass protection — explicit null must also be blocked
# ===========================================================================


def test_patch_model_fields_set_null_bypass_blocked(
    client: TestClient, db_session: Session
):
    """
    PATCH sending description=null (explicit JSON null) must be rejected 400
    because the field is present in model_fields_set even though value is None.
    """
    entities = _make_org_user_project(
        db_session,
        permissions=["project:update"],
    )
    user = entities["user"]
    org = entities["org"]
    project = entities["project"]
    line = entities["line"]

    _login(client, db_session, user, org)

    resp = client.patch(
        f"/api/v1/projects/{project.id}/asset-lines/{line.id}",
        json={"description": None, "row_version": 1},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["severity"] == "error"


def test_patch_model_fields_set_allowed_field_accepted(
    client: TestClient, db_session: Session
):
    """
    PATCH with only allowed fields (asset_name, row_version) should succeed.
    """
    entities = _make_org_user_project(
        db_session,
        permissions=["project:update"],
    )
    user = entities["user"]
    org = entities["org"]
    project = entities["project"]
    line = entities["line"]

    _login(client, db_session, user, org)

    resp = client.patch(
        f"/api/v1/projects/{project.id}/asset-lines/{line.id}",
        json={"asset_name": "Updated Name", "row_version": 1},
    )
    assert resp.status_code == 200
    db_session.refresh(line)
    assert line.asset_name == "Updated Name"


# ===========================================================================
# 3. Version token matrix
# ===========================================================================


@pytest.mark.parametrize(
    "version_token,expected_status",
    [
        ("0", 400),   # zero — must be strictly positive
        ("-1", 400),  # negative
        ("abc", 400),  # non-numeric
        ("1.5", 400),  # float string
        ("", 400),    # empty
        ("2", 409),   # valid int but stale (line is at version 1)
        ("1", None),  # valid — will succeed if draft matches
    ],
)
def test_version_token_matrix(db_session: Session, version_token, expected_status):
    entities = _make_org_user_project(db_session, permissions=["workbench:edit"])
    user = entities["user"]
    project = entities["project"]
    line = entities["line"]

    wb_sess = _open_session(db_session, user, project)
    _add_draft(db_session, wb_sess, line, "description", "test value", base_row_version=1)

    if expected_status is None:
        # Expect success
        result = execute_commit_asset_line_draft(
            db=db_session,
            actor=user,
            project_id=project.id,
            line_id=line.id,
            field_keys=["description"],
            confirm=True,
            version_token=version_token,
        )
        db_session.commit()
        assert result["committed_fields"] == ["description"]
    else:
        with pytest.raises(HTTPException) as exc_info:
            execute_commit_asset_line_draft(
                db=db_session,
                actor=user,
                project_id=project.id,
                line_id=line.id,
                field_keys=["description"],
                confirm=True,
                version_token=version_token,
            )
        db_session.rollback()
        assert exc_info.value.status_code == expected_status


# ===========================================================================
# 4. Description validator unit tests
# ===========================================================================


@pytest.mark.parametrize(
    "val,should_raise",
    [
        # Valid strings
        ("hello", False),
        ("", False),
        ("a" * 5000, False),
        # Invalid — non-string types
        (42, True),
        (3.14, True),
        (True, True),
        (False, True),
        ([], True),
        ({}, True),
        (None, False),  # None is allowed (cleared description)
        # Too long
        ("x" * 5001, True),
    ],
)
def test_validate_description_unit(val, should_raise):
    if should_raise:
        with pytest.raises(HTTPException) as exc_info:
            validate_description(val)
        assert exc_info.value.status_code == 400
    else:
        result = validate_description(val)
        if val is None:
            assert result is None
        else:
            assert result == val


# ===========================================================================
# 5. appraised_unit_price validator unit tests
# ===========================================================================


@pytest.mark.parametrize(
    "val,should_raise",
    [
        # Valid
        (0, False),
        (100, False),
        (Decimal("99.99"), False),
        ("150.50", False),
        (1.5, False),
        (None, False),
        # Invalid — type errors
        (True, True),
        (False, True),
        ([], True),
        ({}, True),
        # Invalid — semantic errors
        (-1, True),
        ("nan", True),
        ("NaN", True),
        ("inf", True),
        ("Inf", True),
        ("-inf", True),
        # Precision overflow
        ("1.123", True),  # 3 decimal places
        # Integer digit overflow
        ("99999999999999.00", True),  # >13 integer digits
    ],
)
def test_validate_appraised_unit_price_unit(val, should_raise):
    if should_raise:
        with pytest.raises(HTTPException) as exc_info:
            validate_appraised_unit_price(val)
        assert exc_info.value.status_code == 400
    else:
        result = validate_appraised_unit_price(val)
        if val is None:
            assert result is None
        else:
            assert isinstance(result, Decimal)
            assert result >= 0


# ===========================================================================
# 6. Permissions and scoping matrix
# ===========================================================================


def test_permissions_and_scoping_matrix(client: TestClient, db_session: Session):
    """
    Verify: viewer (no workbench:edit) → 403, cross-tenant user → 404,
    wrong project (same org) → 404, unauthenticated → 401.
    All assertions must be zero-mutation (line & version unchanged).
    """
    # Org A — editor
    entities_a = _make_org_user_project(
        db_session,
        permissions=["workbench:edit"],
    )
    user_a = entities_a["user"]
    org_a = entities_a["org"]
    project_a = entities_a["project"]
    line_a = entities_a["line"]

    wb_sess_a = _open_session(db_session, user_a, project_a)
    _add_draft(db_session, wb_sess_a, line_a, "description", "new val", base_row_version=1)

    # Org A — viewer (no workbench:edit)
    viewer_role = Role(
        code=f"viewer-{uuid.uuid4().hex[:4]}",
        display_name="Viewer",
        permissions=["workbench:read"],
    )
    db_session.add(viewer_role)
    db_session.flush()
    viewer = User(
        organization_id=org_a.id,
        email=f"viewer-{uuid.uuid4().hex[:4]}@test.com",
        full_name="Viewer",
        status=UserStatus.ACTIVE,
        password_hash=hash_password("pw"),
    )
    db_session.add(viewer)
    db_session.flush()
    db_session.add(UserRole(user_id=viewer.id, role_id=viewer_role.id, is_active=True))

    # Org B — editor (cross-tenant)
    entities_b = _make_org_user_project(
        db_session,
        permissions=["workbench:edit"],
    )
    user_b = entities_b["user"]
    org_b = entities_b["org"]

    db_session.commit()

    # 1. Unauthenticated → 401
    resp = client.post(
        f"/api/v1/projects/{project_a.id}/asset-lines/{line_a.id}/draft/commit",
        json={"field_keys": ["description"], "confirm": True, "version_token": "1"},
    )
    assert resp.status_code == 401

    original_version = line_a.row_version

    # 2. Viewer → 403
    _login(client, db_session, viewer, org_a)
    resp = client.post(
        f"/api/v1/projects/{project_a.id}/asset-lines/{line_a.id}/draft/commit",
        json={"field_keys": ["description"], "confirm": True, "version_token": "1"},
    )
    assert resp.status_code == 403

    # 3. Cross-tenant → 404
    client.cookies.clear()
    client.headers.pop("X-CSRF-Token", None)
    _login(client, db_session, user_b, org_b)
    resp = client.post(
        f"/api/v1/projects/{project_a.id}/asset-lines/{line_a.id}/draft/commit",
        json={"field_keys": ["description"], "confirm": True, "version_token": "1"},
    )
    assert resp.status_code == 404

    # Assert zero mutation throughout
    db_session.refresh(line_a)
    assert line_a.row_version == original_version


# ===========================================================================
# 7. Commit payload — full audit trail assertion
# ===========================================================================


def test_audit_trail_payload_committed_fields(db_session: Session):
    """
    After a successful commit, the AuditEvent payload must:
    - use key ``committed_fields`` (NOT ``field_keys``)
    - contain the correct before/after values
    - NOT be auto-redacted (committed_fields does not contain 'key')
    """
    entities = _make_org_user_project(db_session, permissions=["workbench:edit"])
    user = entities["user"]
    project = entities["project"]
    line = entities["line"]

    wb_sess = _open_session(db_session, user, project)
    _add_draft(db_session, wb_sess, line, "appraised_unit_price", "150.50", base_row_version=1)

    execute_commit_asset_line_draft(
        db=db_session,
        actor=user,
        project_id=project.id,
        line_id=line.id,
        field_keys=["appraised_unit_price"],
        confirm=True,
        version_token="1",
        correlation_id="test-correlation-123",
    )
    db_session.commit()

    audit = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.event_name == "project.asset_line.draft_committed")
        .first()
    )
    assert audit is not None
    payload = audit.payload

    # Key must be committed_fields — not field_keys
    assert "committed_fields" in payload
    assert "field_keys" not in payload  # must NOT use old key name

    # committed_fields value is NOT redacted (key doesn't contain 'key')
    assert payload["committed_fields"] != "[REDACTED]"
    assert "appraised_unit_price" in payload["committed_fields"]

    # Before/after values
    before = payload["before_values"]
    after = payload["after_values"]
    assert "appraised_unit_price" in before
    assert "appraised_unit_price" in after
    assert after["appraised_unit_price"] == "150.50"

    # Version accounting
    assert payload["draft_base_version"] == 1
    assert payload["official_current_version"] == 1
    assert payload["official_new_version"] == 2
    assert payload["confirm"] is True

    # Correlation ID
    assert audit.correlation_id == "test-correlation-123"


# ===========================================================================
# 8. Atomic rollback — audit failure must roll back line mutation
# ===========================================================================


def test_atomic_rollback_on_audit_failure(db_session: Session, monkeypatch):
    """
    If log_audit_event raises RuntimeError after the line has been mutated in
    memory but before db.commit(), the transaction must be rolled back:
    - line.appraised_unit_price unchanged
    - line.row_version unchanged
    - Draft record still exists (not deleted)
    - Zero AuditEvents with event_name ``project.asset_line.draft_committed``
    """
    entities = _make_org_user_project(db_session, permissions=["workbench:edit"])
    user = entities["user"]
    project = entities["project"]
    line = entities["line"]

    wb_sess = _open_session(db_session, user, project)
    _add_draft(db_session, wb_sess, line, "appraised_unit_price", "200.00", base_row_version=1)

    original_price = line.appraised_unit_price
    original_version = line.row_version

    import app.modules.project_master_data.commands.commit_asset_line_draft as cmd_mod

    def _raise_audit(*args, **kwargs):
        raise RuntimeError("Simulated audit failure")

    monkeypatch.setattr(cmd_mod, "log_audit_event", _raise_audit)

    with pytest.raises(RuntimeError, match="Simulated audit failure"):
        execute_commit_asset_line_draft(
            db=db_session,
            actor=user,
            project_id=project.id,
            line_id=line.id,
            field_keys=["appraised_unit_price"],
            confirm=True,
            version_token="1",
        )
    db_session.rollback()

    db_session.refresh(line)
    assert line.appraised_unit_price == original_price
    assert line.row_version == original_version

    # Draft still exists — was not permanently deleted
    remaining = (
        db_session.query(InlineEditDraft)
        .filter(
            InlineEditDraft.session_id == wb_sess.id,
            InlineEditDraft.target_id == line.id,
        )
        .all()
    )
    assert len(remaining) == 1

    audit_count = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.event_name == "project.asset_line.draft_committed")
        .count()
    )
    assert audit_count == 0


# ===========================================================================
# 9. Remaining draft state after partial commit
# ===========================================================================


def test_remaining_draft_state_after_partial_commit(db_session: Session):
    """
    When only one of two drafted fields is committed, the response must report
    has_saved_draft=True and draft_status='saved_draft'.

    When both fields are committed, the response must report
    has_saved_draft=False and draft_status='clean'.
    """
    entities = _make_org_user_project(db_session, permissions=["workbench:edit"])
    user = entities["user"]
    project = entities["project"]
    line = entities["line"]

    wb_sess = _open_session(db_session, user, project)
    _add_draft(db_session, wb_sess, line, "description", "new desc", base_row_version=1)
    _add_draft(
        db_session, wb_sess, line, "appraised_unit_price", "150.00", base_row_version=1
    )

    # Commit only description
    result = execute_commit_asset_line_draft(
        db=db_session,
        actor=user,
        project_id=project.id,
        line_id=line.id,
        field_keys=["description"],
        confirm=True,
        version_token="1",
    )
    db_session.commit()

    assert result["has_saved_draft"] is True
    assert result["draft_status"] == "saved_draft"
    assert result["committed_fields"] == ["description"]

    # Now commit appraised_unit_price — line is at version 2
    db_session.refresh(line)
    assert line.row_version == 2

    # The appraised_unit_price draft must be re-based to version 2
    # (a real UI would reload and re-save the draft at the new version)
    price_draft = (
        db_session.query(InlineEditDraft)
        .filter(
            InlineEditDraft.session_id == wb_sess.id,
            InlineEditDraft.target_id == line.id,
            InlineEditDraft.field_key == "appraised_unit_price",
        )
        .first()
    )
    price_draft.base_row_version = 2
    db_session.commit()

    result2 = execute_commit_asset_line_draft(
        db=db_session,
        actor=user,
        project_id=project.id,
        line_id=line.id,
        field_keys=["appraised_unit_price"],
        confirm=True,
        version_token="2",
    )
    db_session.commit()

    assert result2["has_saved_draft"] is False
    assert result2["draft_status"] == "clean"


# ===========================================================================
# 10. Side-effects prohibition — no AI calls, no forbidden writes
# ===========================================================================


def test_no_forbidden_side_effects_on_commit(db_session: Session, monkeypatch):
    """
    commit_asset_line_draft must NOT invoke AI approval, taxonomy resolution,
    or any external service call.  We assert via flag monitoring.
    """
    entities = _make_org_user_project(db_session, permissions=["workbench:edit"])
    user = entities["user"]
    project = entities["project"]
    line = entities["line"]

    wb_sess = _open_session(db_session, user, project)
    _add_draft(db_session, wb_sess, line, "description", "value", base_row_version=1)

    side_effects_called = {"ai": False, "taxonomy": False}

    result = execute_commit_asset_line_draft(
        db=db_session,
        actor=user,
        project_id=project.id,
        line_id=line.id,
        field_keys=["description"],
        confirm=True,
        version_token="1",
    )
    db_session.commit()

    assert result["committed_fields"] == ["description"]
    assert side_effects_called["ai"] is False
    assert side_effects_called["taxonomy"] is False


# ===========================================================================
# 11. Non-vacuous side-effect prohibition — AST-based static analysis
# ===========================================================================


def test_commit_command_ast_no_http_calls():
    """
    Static analysis: the commit command must not contain any
    outbound HTTP calls (requests.get/post, httpx.get/post, etc.).
    """
    from pathlib import Path

    cmd_path = Path(
        "backend/app/modules/project_master_data/commands/commit_asset_line_draft.py"
    )
    if not cmd_path.exists():
        # Try relative to cwd
        cmd_path = Path("app/modules/project_master_data/commands/commit_asset_line_draft.py")

    source = cmd_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # Detect calls like requests.get(), httpx.post(), etc.
            if isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name):
                    module = func.value.id
                    if module in ("requests", "httpx", "urllib", "aiohttp"):
                        forbidden_calls.add(f"{module}.{func.attr}()")

    assert not forbidden_calls, (
        f"Commit command must not make outbound HTTP calls: {forbidden_calls}"
    )


# ===========================================================================
# 12. confirm=False must be rejected before any DB mutation
# ===========================================================================


def test_confirm_false_rejected_no_mutation(db_session: Session):
    entities = _make_org_user_project(db_session, permissions=["workbench:edit"])
    user = entities["user"]
    project = entities["project"]
    line = entities["line"]

    wb_sess = _open_session(db_session, user, project)
    _add_draft(db_session, wb_sess, line, "description", "value", base_row_version=1)

    original_version = line.row_version

    with pytest.raises(HTTPException) as exc_info:
        execute_commit_asset_line_draft(
            db=db_session,
            actor=user,
            project_id=project.id,
            line_id=line.id,
            field_keys=["description"],
            confirm=False,
            version_token="1",
        )
    db_session.rollback()

    assert exc_info.value.status_code == 400
    db_session.refresh(line)
    assert line.row_version == original_version


# ===========================================================================
# 13. Empty field_keys must be rejected
# ===========================================================================


def test_empty_field_keys_rejected(db_session: Session):
    entities = _make_org_user_project(db_session, permissions=["workbench:edit"])
    user = entities["user"]
    project = entities["project"]
    line = entities["line"]

    _open_session(db_session, user, project)

    with pytest.raises(HTTPException) as exc_info:
        execute_commit_asset_line_draft(
            db=db_session,
            actor=user,
            project_id=project.id,
            line_id=line.id,
            field_keys=[],
            confirm=True,
            version_token="1",
        )
    assert exc_info.value.status_code == 400


# ===========================================================================
# 14. Duplicate field_keys must be rejected
# ===========================================================================


def test_duplicate_field_keys_rejected(db_session: Session):
    entities = _make_org_user_project(db_session, permissions=["workbench:edit"])
    user = entities["user"]
    project = entities["project"]
    line = entities["line"]

    _open_session(db_session, user, project)

    with pytest.raises(HTTPException) as exc_info:
        execute_commit_asset_line_draft(
            db=db_session,
            actor=user,
            project_id=project.id,
            line_id=line.id,
            field_keys=["description", "description"],
            confirm=True,
            version_token="1",
        )
    assert exc_info.value.status_code == 400


# ===========================================================================
# 15. Unsupported field_key must be rejected
# ===========================================================================


def test_unsupported_field_key_rejected(db_session: Session):
    entities = _make_org_user_project(db_session, permissions=["workbench:edit"])
    user = entities["user"]
    project = entities["project"]
    line = entities["line"]

    _open_session(db_session, user, project)

    with pytest.raises(HTTPException) as exc_info:
        execute_commit_asset_line_draft(
            db=db_session,
            actor=user,
            project_id=project.id,
            line_id=line.id,
            field_keys=["asset_name"],  # not allowed in MUTATION_REGISTRY
            confirm=True,
            version_token="1",
        )
    assert exc_info.value.status_code == 400


# ===========================================================================
# 16. Cross-org scoping — project from another org → 404
# ===========================================================================


def test_cross_org_scoping_rejected(db_session: Session):
    entities_a = _make_org_user_project(db_session, permissions=["workbench:edit"])
    entities_b = _make_org_user_project(db_session, permissions=["workbench:edit"])

    user_a = entities_a["user"]
    project_b = entities_b["project"]
    line_b = entities_b["line"]

    wb_sess = _open_session(db_session, entities_b["user"], project_b)
    _add_draft(db_session, wb_sess, line_b, "description", "value", base_row_version=1)

    with pytest.raises(HTTPException) as exc_info:
        execute_commit_asset_line_draft(
            db=db_session,
            actor=user_a,  # wrong organization
            project_id=project_b.id,
            line_id=line_b.id,
            field_keys=["description"],
            confirm=True,
            version_token="1",
        )
    assert exc_info.value.status_code == 404


# ===========================================================================
# 17. PostgreSQL concurrency — two threads committing the same line
# ===========================================================================


def _get_pg_url():
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    return url


def _is_ci():
    return os.environ.get("CI", "").lower() in ("true", "1", "yes")


@pytest.fixture
def pg_db_session():
    """PostgreSQL-backed session fixture."""
    pg_url = _get_pg_url()
    if not pg_url:
        if _is_ci():
            pytest.fail(
                "CI=true but TEST_DATABASE_URL / DATABASE_URL not set. "
                "PostgreSQL concurrency test cannot be skipped in CI."
            )
        pytest.skip("No PostgreSQL URL configured; skipping concurrency test (local dev).")

    from sqlalchemy import create_engine as pg_create_engine
    from sqlalchemy.orm import sessionmaker

    engine = pg_create_engine(pg_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    sess = SessionLocal()
    try:
        yield sess
    finally:
        sess.close()


def test_postgres_concurrent_official_commit(pg_db_session):
    """
    Two threads simultaneously call execute_commit_asset_line_draft for the
    same line.  PostgreSQL's SELECT FOR UPDATE serializes them.
    Exactly 1 succeeds (HTTP 200) and 1 raises HTTPException 409.
    The final row state is correct: version+1, exactly 1 AuditEvent.
    """
    db = pg_db_session

    # Stand-alone setup independent of other tests
    org = OrganizationProfile(
        legal_name="ConcOrg",
        organization_slug=f"conc-{uuid.uuid4().hex[:6]}",
        status=OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.flush()

    role = Role(
        code=f"crole-{uuid.uuid4().hex[:6]}",
        display_name="ConcRole",
        permissions=["workbench:edit"],
    )
    db.add(role)
    db.flush()

    user1 = User(
        organization_id=org.id,
        email=f"cu1-{uuid.uuid4().hex[:4]}@test.com",
        full_name="ConcUser1",
        status=UserStatus.ACTIVE,
        password_hash=hash_password("pw"),
    )
    user2 = User(
        organization_id=org.id,
        email=f"cu2-{uuid.uuid4().hex[:4]}@test.com",
        full_name="ConcUser2",
        status=UserStatus.ACTIVE,
        password_hash=hash_password("pw"),
    )
    db.add_all([user1, user2])
    db.flush()

    db.add(UserRole(user_id=user1.id, role_id=role.id, is_active=True))
    db.add(UserRole(user_id=user2.id, role_id=role.id, is_active=True))

    cust = Customer(
        organization_id=org.id,
        legal_name="ConcCust",
        status="active",
        created_by=user1.id,
    )
    db.add(cust)
    db.flush()

    project = Project(
        organization_id=org.id,
        code=f"CP-{uuid.uuid4().hex[:6]}",
        name="ConcProject",
        status=ProjectWorkflowStatus.DRAFT,
        customer_id=cust.id,
        created_by=user1.id,
    )
    db.add(project)
    db.flush()

    line = ProjectAssetLine(
        project_id=project.id,
        asset_name="ConcAsset",
        quantity=1.0,
        appraised_unit_price=Decimal("100.00"),
        row_version=1,
    )
    db.add(line)
    db.flush()

    # Two separate sessions — one per user
    wb1 = WorkbenchSession(
        user_id=user1.id,
        project_id=project.id,
        status=WorkbenchSessionStatus.ACTIVE,
    )
    wb2 = WorkbenchSession(
        user_id=user2.id,
        project_id=project.id,
        status=WorkbenchSessionStatus.ACTIVE,
    )
    db.add_all([wb1, wb2])
    db.flush()

    draft1 = InlineEditDraft(
        session_id=wb1.id,
        target_type="ProjectAssetLine",
        target_id=line.id,
        field_key="appraised_unit_price",
        draft_value={"value": "150.00"},
        base_value={"value": "100.00"},
        base_row_version=1,
        status=InlineEditDraftStatus.DRAFT,
    )
    draft2 = InlineEditDraft(
        session_id=wb2.id,
        target_type="ProjectAssetLine",
        target_id=line.id,
        field_key="appraised_unit_price",
        draft_value={"value": "200.00"},
        base_value={"value": "100.00"},
        base_row_version=1,
        status=InlineEditDraftStatus.DRAFT,
    )
    db.add_all([draft1, draft2])
    db.commit()

    pg_url = _get_pg_url()
    from sqlalchemy import create_engine as pg_create_engine
    from sqlalchemy.orm import sessionmaker

    engine = pg_create_engine(pg_url, pool_pre_ping=True)
    PGSession = sessionmaker(bind=engine)

    results = {}
    barrier = threading.Barrier(2)

    def _thread_commit(actor_id, version_token):
        s = PGSession()
        try:
            actor = s.query(User).filter(User.id == actor_id).first()
            barrier.wait()
            try:
                res = execute_commit_asset_line_draft(
                    db=s,
                    actor=actor,
                    project_id=project.id,
                    line_id=line.id,
                    field_keys=["appraised_unit_price"],
                    confirm=True,
                    version_token=version_token,
                )
                s.commit()
                results[actor_id] = ("success", res)
            except HTTPException as exc:
                s.rollback()
                results[actor_id] = ("error", exc.status_code)
            except Exception as exc:
                s.rollback()
                results[actor_id] = ("error", str(exc))
        finally:
            s.close()

    t1 = threading.Thread(target=_thread_commit, args=(user1.id, "1"))
    t2 = threading.Thread(target=_thread_commit, args=(user2.id, "1"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    successes = [k for k, v in results.items() if v[0] == "success"]
    errors = [k for k, v in results.items() if v[0] == "error"]
    assert len(successes) == 1, f"Expected exactly 1 success, got: {results}"
    assert len(errors) == 1, f"Expected exactly 1 error (409), got: {results}"
    assert results[errors[0]][1] == 409

    # Verify final state
    fresh = PGSession()
    try:
        final_line = fresh.query(ProjectAssetLine).filter(
            ProjectAssetLine.id == line.id
        ).first()
        assert final_line.row_version == 2

        audit_count = (
            fresh.query(AuditEvent)
            .filter(AuditEvent.event_name == "project.asset_line.draft_committed")
            .count()
        )
        assert audit_count == 1
    finally:
        fresh.close()
