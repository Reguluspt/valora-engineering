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


def _reachability_from_func(func: str) -> str:
    if (
        "request_bytes" in func
        or "upload_bytes" in func
        or "upload_too_large" in func
    ):
        return "intake"
    # xlsx before xls (xlsx_extra contains xls_extra as substring)
    if "xlsx" in func:
        return "xlsx"
    if (
        "_xls_" in func
        or "xls_adapter" in func
        or "xls_extra" in func
        or "endpoint_xls" in func
    ):
        return "xls"
    if "cell_limit" in func or "endpoint_cell" in func:
        return "xlsx"
    return "xlsx"


@pytest.fixture(autouse=True)
def _s13_pr_002_strong_helper_runtime_guard(request):
    """R-06: per-marked-node A/B/C guard with unconditional finally clear."""
    marker = request.node.get_closest_marker("s13_pr_002_http_nplus1_reject")
    if marker is None:
        # Ensure unmarked tests do not see dirty TLS
        from tests.support.s13_pr_002_http_preserve import clear_evidence_context

        clear_evidence_context()
        yield
        clear_evidence_context()
        return

    from tests.support.s13_pr_002_http_preserve import (
        CaseInput,
        clear_evidence_context,
        get_accepted_events,
        get_case_input,
        get_rejection_events,
        register_case_input,
        set_ledger_row,
        set_runtime_node,
    )
    from tests.support.s13_pr_002_matrix import (
        assert_runtime_guard as matrix_guard,
        ledger_by_nodeid,
        ledger_by_row_id,
    )

    clear_evidence_context()
    nodeid = request.node.nodeid
    set_runtime_node(nodeid)
    by_node = ledger_by_nodeid()
    if nodeid not in by_node:
        clear_evidence_context()
        raise AssertionError(f"marked node missing from static ledger: {nodeid}")
    row = by_node[nodeid]
    set_ledger_row(row)

    # Bind B early for parametrized cases (limit_field from callspec)
    callspec = getattr(request.node, "callspec", None)
    if callspec is not None and "limit_field" in getattr(callspec, "params", {}):
        bound = str(callspec.params["limit_field"])
        func = nodeid.split("::")[-1].split("[", 1)[0]
        reach = _reachability_from_func(func)
        register_case_input(
            CaseInput(reachability=reach, bound=bound, case_id=f"{func}::{bound}")
        )

    try:
        yield
        case = get_case_input()
        if case is None:
            raise AssertionError(
                f"{nodeid}: missing CaseInput — parametrized tests auto-bind; "
                "non-param must call register_case_input() before helpers"
            )
        matrix_guard(
            actual_nodeid=nodeid,
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
    def override_get_current_user(
        request: Request,
        db: Session = Depends(get_db)
    ) -> User:
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
            session = db.query(UserSession).filter(
                UserSession.access_token_hash == acc_hash,
                UserSession.status == "active"
            ).first()
            if session:
                user = db.query(User).filter(User.id == session.user_id).first()
                if user:
                    return user

        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
