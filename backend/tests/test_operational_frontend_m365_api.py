"""API acceptance for the operational session-to-OneDrive frontend surfaces."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.m365 import _frontend_return_uri, authorize_onedrive
from app.core.rbac import get_current_user
from app.db import get_db
from app.main import app
from app.modules.m365_integration.infrastructure.credential_vault import DatabaseCredentialVault
from app.modules.project_master_data.models import (
    DocumentTemplate,
    DocumentTemplateStatus,
    TemplateVersion,
    TemplateVersionStatus,
)
from tests.test_pr05_m365_foundation import _seed
from tests.test_pr06_m365_revalidation import _setup

pytest_plugins = ("tests.test_pr06_m365_revalidation",)


def _authority(db: Session, context: dict[str, object]) -> TemplateVersion:
    template = DocumentTemplate(
        organization_id=context["organization"].id,
        document_type="valuation_report",
        code=f"OPS-{uuid.uuid4().hex[:8]}",
        name="Mẫu báo cáo vận hành",
        status=DocumentTemplateStatus.ACTIVE,
        created_by=context["actor"].id,
    )
    db.add(template)
    db.flush()
    version = TemplateVersion(
        document_template_id=template.id,
        version_number=3,
        template_format="docx",
        placeholder_manifest={
            "managed_regions_contract": "valora-managed-regions-v1",
            "managed_regions": [
                {
                    "region_key": "appraised-value",
                    "locator": "VALORA_APPRAISED_VALUE",
                    "semantic_type": "text",
                    "normalization_contract": "text-whitespace-v1",
                }
            ],
        },
        status=TemplateVersionStatus.ACTIVE,
    )
    db.add(version)
    db.flush()
    template.current_version_id = version.id
    db.commit()
    return version


@pytest.fixture
def operational_api(pr06_db: Session, monkeypatch: pytest.MonkeyPatch):
    context = _setup(pr06_db)
    _authority(pr06_db, context)

    def override_get_db():
        yield pr06_db

    def components(db: Session):
        assert db is pr06_db
        return (
            DatabaseCredentialVault(
                db,
                keys={"v1": b"1" * 32, "v2": b"2" * 32},
                active_key_version="v1",
            ),
            context["oauth"],
            context["graph"],
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: context["actor"]
    monkeypatch.setattr("app.api.m365._components", components)
    try:
        yield context, TestClient(app, follow_redirects=False)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


def test_connection_status_and_tenant_safe_adoption_options(operational_api) -> None:
    context, client = operational_api
    connection = client.get("/api/v1/m365/onedrive/connection")

    assert connection.status_code == 200
    assert connection.json() == {
        "connection_id": str(context["binding"].connection_id),
        "drive_id": "personal-drive-1",
        "status": "active",
        "last_verified_at": connection.json()["last_verified_at"],
        "capability_state": "read-only",
        "read_available": True,
        "appfolder_write_available": False,
    }

    url = (
        f"/api/v1/m365/onedrive/projects/{context['project'].id}"
        "/adoption-options"
    )
    options = client.get(url)

    assert options.status_code == 200
    payload = options.json()
    assert payload["project_id"] == str(context["project"].id)
    assert payload["data_snapshot"] == {
        "contract_version": "valora-operational-adoption-v1",
        "project_id": str(context["project"].id),
        "project_code": context["project"].code,
        "project_name": context["project"].name,
        "project_row_version": context["project"].row_version,
    }
    assert [item["kind"] for item in payload["items"]] == ["folder", "docx"]
    assert payload["items"][1]["drive_item_id"] == "docx-1"
    assert len(payload["templates"]) == 1
    assert "microsoft_account_subject" not in str(payload)
    assert "credential_id" not in str(payload)


def test_adoption_options_denies_foreign_project_before_graph(operational_api) -> None:
    context, client = operational_api
    calls = context["graph"].list_calls

    response = client.get(
        f"/api/v1/m365/onedrive/projects/{uuid.uuid4()}/adoption-options"
    )

    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "project_not_found"
    assert context["graph"].list_calls == calls


def test_project_permissions_fail_before_graph(operational_api) -> None:
    context, client = operational_api
    context["actor"].roles[0].role.permissions = []
    calls = context["graph"].list_calls
    project_id = context["project"].id

    options = client.get(
        f"/api/v1/m365/onedrive/projects/{project_id}/adoption-options"
    )
    documents = client.get(
        f"/api/v1/m365/onedrive/projects/{project_id}/documents"
    )
    exchange = client.post(
        f"/api/v1/m365/onedrive/projects/{project_id}/exchange/import-xlsx",
        json={
            "connection_id": str(context["binding"].connection_id),
            "drive_item_id": "xlsx-1",
            "batch_id": str(uuid.uuid4()),
        },
    )

    assert options.status_code == 403
    assert documents.status_code == 403
    assert exchange.status_code == 403
    assert context["graph"].list_calls == calls


def test_exchange_artifacts_hide_unknown_project(operational_api) -> None:
    _, client = operational_api

    response = client.get(
        f"/api/v1/m365/onedrive/projects/{uuid.uuid4()}/exchange/artifacts"
    )

    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "project_not_found"


def test_authorize_denies_read_only_actor_before_oauth(
    operational_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    context, _ = operational_api
    context["actor"].roles[0].role.permissions = ["project:read"]
    monkeypatch.setattr(
        "app.api.m365._components",
        lambda db: pytest.fail("OAuth components loaded before permission denial"),
    )

    with pytest.raises(HTTPException) as exc_info:
        authorize_onedrive(
            request=SimpleNamespace(),
            db=Session.object_session(context["actor"]),
            session=SimpleNamespace(
                user_id=context["actor"].id,
                organization_id=context["organization"].id,
            ),
        )

    assert exc_info.value.status_code == 403


def test_document_list_returns_server_computed_readiness(operational_api) -> None:
    context, client = operational_api
    response = client.get(
        f"/api/v1/m365/onedrive/projects/{context['project'].id}/documents"
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["document_id"] == str(context["revision"].document_id)
    assert payload[0]["readiness"]["classification"] is None
    assert payload[0]["readiness"]["recovery_code"] == "revalidation_required"
    assert payload[0]["readiness"]["next_action"] == "check_changes"


def test_absent_connection_is_a_safe_authenticated_read(
    pr06_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seeded = _seed(pr06_db, suffix="no-connection")
    seeded["actor"].roles[0].role.permissions = ["project:read"]
    pr06_db.commit()

    def override_get_db():
        yield pr06_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: seeded["actor"]
    try:
        response = TestClient(app).get("/api/v1/m365/onedrive/connection")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json() == {
        "connection_id": None,
        "drive_id": None,
        "status": "not_connected",
        "last_verified_at": None,
        "capability_state": "reconsent-required",
        "read_available": False,
        "appfolder_write_available": False,
    }


def test_callback_redirect_contains_only_sanitized_result(
    pr06_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def override_get_db():
        yield pr06_db

    monkeypatch.setattr(
        "app.api.m365.get_settings",
        lambda: SimpleNamespace(
            m365_frontend_return_uri="http://localhost:5173/#/workbench/m365/return",
            parsed_cors_origins=["http://localhost:5173"],
        ),
    )
    monkeypatch.setattr("app.api.m365._components", lambda db: (object(), object(), object()))
    monkeypatch.setattr(
        "app.api.m365.complete_onedrive_authorization",
        lambda *args, **kwargs: object(),
    )
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app, follow_redirects=False).get(
            "/api/v1/m365/onedrive/oauth/callback?code=secret-code&state=secret-state"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 303
    assert response.headers["location"] == (
        "http://localhost:5173/#/workbench/m365/return?m365=connected"
    )
    assert "secret-code" not in response.headers["location"]
    assert "secret-state" not in response.headers["location"]


def test_callback_failure_redacts_provider_detail(
    pr06_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args, **kwargs):
        raise HTTPException(
            status_code=502,
            detail={
                "error_code": "onedrive_authorization_failed",
                "detail": "provider-secret-body",
            },
        )

    def override_get_db():
        yield pr06_db

    monkeypatch.setattr(
        "app.api.m365.get_settings",
        lambda: SimpleNamespace(
            m365_frontend_return_uri="http://localhost:5173/#/workbench/m365/return",
            parsed_cors_origins=["http://localhost:5173"],
        ),
    )
    monkeypatch.setattr("app.api.m365._components", lambda db: (object(), object(), object()))
    monkeypatch.setattr("app.api.m365.complete_onedrive_authorization", fail)
    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app, follow_redirects=False).get(
            "/api/v1/m365/onedrive/oauth/callback?error=provider-secret-body&state=secret"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 303
    assert response.headers["location"].endswith(
        "?m365=failed&reason=onedrive_authorization_failed"
    )
    assert "provider-secret-body" not in response.headers["location"]


@pytest.mark.parametrize(
    "target",
    [
        "https://attacker.example/#/workbench/m365/return",
        "javascript:alert(1)",
    ],
)
def test_callback_return_uri_rejects_invalid_or_unlisted_origin(
    monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    monkeypatch.setattr(
        "app.api.m365.get_settings",
        lambda: SimpleNamespace(
            m365_frontend_return_uri=target,
            parsed_cors_origins=["https://valora.example"],
        ),
    )

    with pytest.raises(RuntimeError, match="M365_FRONTEND_RETURN_URI"):
        _frontend_return_uri("connected")
