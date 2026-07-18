import pytest
import uuid
from fastapi import Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.main import app
from app.db import get_db
from app.core.rbac import get_current_user
from app.modules.project_master_data.models import User, UserSession


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "s13_pr_002_http_nplus1_reject: retained HTTP N+1 source-artifact rejection parameter",
    )


@pytest.fixture(autouse=True)
def _s13_pr_002_strong_helper_runtime_guard(request):
    """R-06: per-marked-node A/B/C guard with unconditional finally clear."""
    from tests.support.s13_pr_002_http_preserve import (
        clear_evidence_context,
        get_accepted_events,
        get_case_input,
        get_rejection_events,
        set_ledger_row,
        set_runtime_identity,
    )
    from tests.support.s13_pr_002_matrix import (
        assert_runtime_guard as matrix_guard,
        ledger_by_nodeid,
        ledger_by_row_id,
    )

    clear_evidence_context()
    try:
        marker = request.node.get_closest_marker("s13_pr_002_http_nplus1_reject")
        if marker is None:
            yield
            return

        nodeid = request.node.nodeid
        runtime_case_id = request.node.name
        set_runtime_identity(nodeid, runtime_case_id)
        by_node = ledger_by_nodeid()
        if nodeid not in by_node:
            raise AssertionError(f"marked node missing from static ledger: {nodeid}")
        row = by_node[nodeid]
        set_ledger_row(row)

        yield
        case = get_case_input()
        if case is None:
            raise AssertionError(
                f"{nodeid}: missing CaseInput — the test must use one CaseInput "
                "for its actual limits and artifact branch"
            )
        matrix_guard(
            actual_nodeid=nodeid,
            actual_case_id=runtime_case_id,
            ledger_row=row,
            rejection_events=get_rejection_events(),
            accepted_events=get_accepted_events(),
            case=case,
            ledger_index=ledger_by_row_id(),
        )
    finally:
        clear_evidence_context()


@pytest.fixture(autouse=True)
def setup_test_auth():
    def override_get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
        x_user_id = request.headers.get("X-User-Id")
        if x_user_id:
            try:
                user_uuid = uuid.UUID(x_user_id)
            except ValueError:
                raise HTTPException(status_code=401, detail="Not authenticated")
            user = db.query(User).filter(User.id == user_uuid).first()
            if not user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return user

        from app.api.auth import get_cookie_keys, hash_token

        acc_key, _ = get_cookie_keys()
        access_token = request.cookies.get(acc_key)
        if access_token:
            acc_hash = hash_token(access_token)
            session = (
                db.query(UserSession)
                .filter(UserSession.access_token_hash == acc_hash, UserSession.status == "active")
                .first()
            )
            if session:
                user = db.query(User).filter(User.id == session.user_id).first()
                if user:
                    return user

        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
