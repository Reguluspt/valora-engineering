"""Tenant-safe API proofs for PR-06 explicit revalidation and readiness readback."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app
from app.modules.m365_integration.infrastructure.credential_vault import DatabaseCredentialVault
from app.modules.m365_integration.models import (
    M365ManagedContentBaseline,
    M365ManagedRegionBaseline,
)
from app.modules.project_master_data.models import (
    DocumentTemplate,
    DocumentTemplateStatus,
    GeneratedDocument,
    GeneratedDocumentStatus,
    RenderJob,
    RenderJobStatus,
    TemplateVersion,
    TemplateVersionStatus,
)
from tests.test_pr06_m365_revalidation import _setup

pytest_plugins = ("tests.test_pr06_m365_revalidation",)


@pytest.fixture
def api_context(pr06_db: Session, monkeypatch: pytest.MonkeyPatch):
    context = _setup(pr06_db)

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
    monkeypatch.setattr("app.api.m365._components", components)
    try:
        yield context, TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _url(context: dict[str, object]) -> str:
    return (
        f"/api/v1/m365/onedrive/projects/{context['project'].id}"
        f"/documents/{context['revision'].document_id}/revalidation"
    )


def _headers(context: dict[str, object]) -> dict[str, str]:
    return {"X-User-Id": str(context["actor"].id), "X-Correlation-Id": "corr-pr06-api"}


def _baseline_url(context: dict[str, object]) -> str:
    return f"{_url(context)}/baseline"


def _seed_managed_region_authority(
    db: Session, context: dict[str, object]
) -> GeneratedDocument:
    actor = context["actor"]
    revision = context["revision"]
    template = DocumentTemplate(
        organization_id=context["organization"].id,
        document_type="valuation_report",
        code=f"PR06-{uuid.uuid4().hex[:8]}",
        name="PR-06 managed-region template",
        status=DocumentTemplateStatus.ACTIVE,
        created_by=actor.id,
    )
    db.add(template)
    db.flush()
    version = TemplateVersion(
        document_template_id=template.id,
        version_number=1,
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
    render_job = RenderJob(
        project_id=context["project"].id,
        template_version_id=version.id,
        render_mode="official",
        output_formats=["docx"],
        data_snapshot={},
        data_snapshot_hash=revision.data_snapshot_digest_sha256,
        status=RenderJobStatus.COMPLETED,
        created_by=actor.id,
    )
    db.add(render_job)
    db.flush()
    generated = GeneratedDocument(
        project_id=context["project"].id,
        render_job_id=render_job.id,
        document_type="valuation_report",
        output_format="docx",
        filename="pr06-authority.docx",
        storage_key="documents/pr06-authority.docx",
        # The current production writer records the data-snapshot hash here;
        # DOCX byte equality is independently proven by DocumentRevision and Graph.
        checksum_sha256=revision.data_snapshot_digest_sha256,
        file_size_bytes=4096,
        template_version_id=version.id,
        data_snapshot_hash=revision.data_snapshot_digest_sha256,
        status=GeneratedDocumentStatus.DRAFT,
    )
    db.add(generated)
    db.commit()
    return generated


def test_existing_binding_baseline_enrollment_uses_server_resolved_authority(
    api_context,
    pr06_db: Session,
) -> None:
    context, client = api_context
    pr06_db.query(M365ManagedRegionBaseline).delete()
    pr06_db.query(M365ManagedContentBaseline).delete()
    pr06_db.commit()
    generated = _seed_managed_region_authority(pr06_db, context)

    response = client.post(
        _baseline_url(context),
        headers=_headers(context),
        json={
            "expected_document_revision_id": str(context["revision"].id),
            "expected_document_revision": 1,
            "binding_id": str(context["binding"].id),
            "generated_document_id": str(generated.id),
            "idempotency_key": "api-enroll-baseline",
        },
    )

    assert response.status_code == 201
    assert response.json()["binding_id"] == str(context["binding"].id)
    assert response.json()["authority_ref"] == (
        f"template-version:{generated.template_version_id}:valora-managed-regions-v1"
    )
    assert pr06_db.query(M365ManagedContentBaseline).count() == 1
    assert pr06_db.query(M365ManagedRegionBaseline).count() == 1


def test_baseline_enrollment_rejects_client_authored_region_facts(api_context) -> None:
    context, client = api_context
    response = client.post(
        _baseline_url(context),
        headers=_headers(context),
        json={
            "expected_document_revision_id": str(context["revision"].id),
            "expected_document_revision": 1,
            "binding_id": str(context["binding"].id),
            "generated_document_id": str(uuid.uuid4()),
            "idempotency_key": "api-reject-client-regions",
            "managed_regions": [
                {
                    "region_key": "forged",
                    "locator": "FORGED",
                    "semantic_type": "text",
                    "normalization_contract": "text-whitespace-v1",
                }
            ],
        },
    )

    assert response.status_code == 422


def test_explicit_revalidation_and_readback(api_context) -> None:
    context, client = api_context
    response = client.post(
        _url(context),
        headers=_headers(context),
        json={
            "expected_document_revision_id": str(context["revision"].id),
            "expected_document_revision": 1,
            "trigger": "explicit_refresh",
            "idempotency_key": "api-explicit-refresh",
        },
    )

    assert response.status_code == 200
    assert response.json()["classification"] == "no_change"
    assert response.json()["affected_region_keys"] == []

    readback = client.get(_url(context), headers=_headers(context))
    assert readback.status_code == 200
    assert readback.json()["baseline_eligible"] is True
    assert readback.json()["classification"] == "no_change"
    assert readback.json()["is_safe_for_freshness_required_action"] is True
    assert readback.json()["drive_item_id"] == context["binding"].drive_item_id
    assert readback.json()["file_name"] == context["binding"].name


def test_revalidation_request_rejects_client_derived_fields(api_context) -> None:
    context, client = api_context
    response = client.post(
        _url(context),
        headers=_headers(context),
        json={
            "expected_document_revision_id": str(context["revision"].id),
            "expected_document_revision": 1,
            "trigger": "explicit_refresh",
            "idempotency_key": "api-forbidden-field",
            "classification": "no_change",
        },
    )

    assert response.status_code == 422


def test_foreign_project_is_hidden_before_provider_call(api_context) -> None:
    context, client = api_context
    calls = context["graph"].item_calls
    url = (
        f"/api/v1/m365/onedrive/projects/{uuid.uuid4()}"
        f"/documents/{context['revision'].document_id}/revalidation"
    )
    response = client.post(
        url,
        headers=_headers(context),
        json={
            "expected_document_revision_id": str(context["revision"].id),
            "expected_document_revision": 1,
            "trigger": "explicit_refresh",
            "idempotency_key": "api-foreign",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "project_not_found"
    assert context["graph"].item_calls == calls
