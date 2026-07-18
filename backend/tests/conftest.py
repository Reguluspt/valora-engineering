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
    """M-04: each marked N+1 rejection node must complete exactly one strong helper call."""
    marker = request.node.get_closest_marker("s13_pr_002_http_nplus1_reject")
    if marker is None:
        yield
        return
    from tests.support.s13_pr_002_http_preserve import (
        get_strong_helper_completed_calls,
        reset_strong_helper_calls,
    )

    reset_strong_helper_calls()
    yield
    completed = get_strong_helper_completed_calls()
    assert completed == 1, (
        f"{request.node.nodeid}: expected exactly 1 completed "
        f"assert_http_rejection_preserve call, got {completed}"
    )


@pytest.fixture(autouse=True)
def setup_test_auth():
    def override_get_current_user(
        request: Request,
        db: Session = Depends(get_db)
    ) -> User:
        # Check for X-User-Id header used by legacy test suite
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
            
        # Fallback to cookie authentication if cookies are present
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
    # No need to clear here as the client fixtures do it, but we can do it safely
    app.dependency_overrides.pop(get_current_user, None)
