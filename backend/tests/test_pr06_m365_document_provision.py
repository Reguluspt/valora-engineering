"""Canonical producer proofs for the PR-06 live-classification extension."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import replace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_db
from app.main import app
from app.modules.document_workspace.models import (
    DocumentRecord,
    DocumentRevision,
    DocumentRevisionCurrentHead,
)
from app.modules.m365_integration.application.provision_document_service import (
    provision_onedrive_document,
)
from app.modules.m365_integration.domain.managed_regions import MAX_DOCX_BYTES
from app.modules.m365_integration.infrastructure.credential_vault import DatabaseCredentialVault
from app.modules.m365_integration.models import (
    M365ManagedContentBaseline,
    M365ManagedRegionBaseline,
    M365RevisionBinding,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    DocumentTemplate,
    DocumentTemplateStatus,
    GeneratedDocument,
    RenderJob,
    TemplateVersion,
    TemplateVersionStatus,
)
from tests.test_pr05_m365_foundation import _vault
from tests.test_pr06_m365_revalidation import _setup

pytest_plugins = ("tests.test_pr06_m365_revalidation",)


def _authority(db: Session, context: dict[str, object]) -> TemplateVersion:
    template = DocumentTemplate(
        organization_id=context["organization"].id,
        document_type="valuation_report",
        code=f"PR06-PRODUCER-{uuid.uuid4().hex[:8]}",
        name="PR-06 canonical producer",
        status=DocumentTemplateStatus.ACTIVE,
        created_by=context["actor"].id,
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
    db.commit()
    return version


def _provision(
    db: Session,
    context: dict[str, object],
    version: TemplateVersion,
    *,
    key: str,
    snapshot: dict[str, object] | None = None,
    item_id: str = "producer-item",
):
    return provision_onedrive_document(
        db,
        actor=context["actor"],
        organization_id=context["organization"].id,
        project_id=context["project"].id,
        template_version_id=version.id,
        connection_id=context["binding"].connection_id,
        drive_item_id=item_id,
        title="Báo cáo canonical",
        data_snapshot=snapshot or {"appraised_value": 1_000_000},
        idempotency_key=key,
        oauth_client=context["oauth"],
        graph_gateway=context["graph"],
        credential_vault=_vault(db),
        correlation_id="corr-pr06-producer",
    )


@pytest.fixture
def producer_context(pr06_db: Session) -> dict[str, object]:
    context = _setup(pr06_db)
    context["version"] = _authority(pr06_db, context)
    return context


def test_producer_creates_complete_lineage_and_sanitized_audits(
    producer_context: dict[str, object],
    pr06_db: Session,
) -> None:
    context = producer_context
    result = _provision(pr06_db, context, context["version"], key="producer-success")

    revision = pr06_db.get(DocumentRevision, result.document_revision_id)
    render_job = pr06_db.get(RenderJob, result.render_job_id)
    generated = pr06_db.get(GeneratedDocument, result.generated_document_id)
    baseline = pr06_db.get(M365ManagedContentBaseline, result.baseline_id)
    assert pr06_db.get(DocumentRecord, result.document_id) is not None
    assert pr06_db.get(
        DocumentRevisionCurrentHead,
        (context["organization"].id, context["project"].id, result.document_id),
    ).current_revision_id == result.document_revision_id
    assert revision.data_snapshot_digest_sha256 == render_job.data_snapshot_hash
    assert render_job.data_snapshot == {"appraised_value": 1_000_000}
    assert generated.render_job_id == render_job.id
    assert generated.checksum_sha256 == hashlib.sha256(context["original"]).hexdigest()
    assert generated.checksum_sha256 == revision.content_checksum_sha256
    assert baseline.binding_id == result.binding_id
    assert (
        pr06_db.query(M365ManagedRegionBaseline)
        .filter(M365ManagedRegionBaseline.content_baseline_id == baseline.id)
        .count()
        == 1
    )
    audits = (
        pr06_db.query(AuditEvent)
        .filter(AuditEvent.command_name == "ProvisionOneDriveDocument")
        .all()
    )
    assert len(audits) == 3
    assert all("data_snapshot" not in str(event.payload) for event in audits)
    assert all("appraised_value" not in str(event.payload) for event in audits)


def test_exact_replay_short_circuits_oauth_and_graph(
    producer_context: dict[str, object],
    pr06_db: Session,
) -> None:
    context = producer_context
    first = _provision(pr06_db, context, context["version"], key="producer-replay")
    graph_calls = context["graph"].item_calls
    content_calls = context["graph"].content_calls
    refresh_calls = context["oauth"].refresh_calls

    replay = _provision(pr06_db, context, context["version"], key="producer-replay")

    assert replay == first
    assert context["graph"].item_calls == graph_calls
    assert context["graph"].content_calls == content_calls
    assert context["oauth"].refresh_calls == refresh_calls


def test_idempotency_collision_is_rejected_before_provider_io(
    producer_context: dict[str, object],
    pr06_db: Session,
) -> None:
    context = producer_context
    _provision(pr06_db, context, context["version"], key="producer-collision")
    graph_calls = context["graph"].item_calls
    content_calls = context["graph"].content_calls

    with pytest.raises(HTTPException) as exc_info:
        _provision(
            pr06_db,
            context,
            context["version"],
            key="producer-collision",
            snapshot={"appraised_value": 2_000_000},
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error_code"] == "idempotency_key_reused"
    assert context["graph"].item_calls == graph_calls
    assert context["graph"].content_calls == content_calls


def test_operational_snapshot_tampering_is_rejected_before_provider_io(
    producer_context: dict[str, object],
    pr06_db: Session,
) -> None:
    context = producer_context
    graph_calls = context["graph"].item_calls
    refresh_calls = context["oauth"].refresh_calls
    forged_snapshot = {
        "contract_version": "valora-operational-adoption-v1",
        "project_id": str(context["project"].id),
        "project_code": context["project"].code,
        "project_name": "Tên hồ sơ đã bị sửa ở client",
        "project_row_version": context["project"].row_version,
    }

    with pytest.raises(HTTPException) as exc_info:
        _provision(
            pr06_db,
            context,
            context["version"],
            key="producer-forged-operational-snapshot",
            snapshot=forged_snapshot,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error_code"] == (
        "operational_adoption_snapshot_stale"
    )
    assert context["graph"].item_calls == graph_calls
    assert context["oauth"].refresh_calls == refresh_calls


def test_operational_replay_precedes_current_snapshot_and_authority_staleness(
    producer_context: dict[str, object],
    pr06_db: Session,
) -> None:
    context = producer_context
    snapshot = {
        "contract_version": "valora-operational-adoption-v1",
        "project_id": str(context["project"].id),
        "project_code": context["project"].code,
        "project_name": context["project"].name,
        "project_row_version": context["project"].row_version,
    }
    first = _provision(
        pr06_db,
        context,
        context["version"],
        key="producer-operational-replay",
        snapshot=snapshot,
    )
    graph_calls = context["graph"].item_calls
    refresh_calls = context["oauth"].refresh_calls
    context["project"].name = "Tên hồ sơ đã đổi sau lần nhận đầu tiên"
    context["version"].status = TemplateVersionStatus.DEPRECATED
    pr06_db.commit()

    replay = _provision(
        pr06_db,
        context,
        context["version"],
        key="producer-operational-replay",
        snapshot=snapshot,
    )

    assert replay == first
    assert context["graph"].item_calls == graph_calls
    assert context["oauth"].refresh_calls == refresh_calls


def test_graph_race_leaves_no_partial_lineage(
    producer_context: dict[str, object],
    pr06_db: Session,
) -> None:
    context = producer_context
    counts = {
        model: pr06_db.query(model).count()
        for model in (
            DocumentRecord,
            DocumentRevision,
            DocumentRevisionCurrentHead,
            RenderJob,
            GeneratedDocument,
            M365RevisionBinding,
            M365ManagedContentBaseline,
            M365ManagedRegionBaseline,
        )
    }
    context["graph"].after_next_metadata_e_tag = '"etag-raced"'

    with pytest.raises(HTTPException) as exc_info:
        _provision(pr06_db, context, context["version"], key="producer-race")

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error_code"] == "m365_content_race"
    assert all(pr06_db.query(model).count() == count for model, count in counts.items())


def test_oversize_metadata_is_rejected_before_content_download(
    producer_context: dict[str, object],
    pr06_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = producer_context
    original_get = context["graph"].get_drive_item

    def oversized_item(**kwargs):
        return replace(original_get(**kwargs), size_bytes=MAX_DOCX_BYTES + 1)

    monkeypatch.setattr(context["graph"], "get_drive_item", oversized_item)
    with pytest.raises(HTTPException) as exc_info:
        _provision(pr06_db, context, context["version"], key="producer-oversize")

    assert exc_info.value.status_code == 422
    assert context["graph"].content_calls == 0


def test_existing_item_cannot_seed_a_second_document(
    producer_context: dict[str, object],
    pr06_db: Session,
) -> None:
    context = producer_context
    before = pr06_db.query(DocumentRecord).count()

    with pytest.raises(HTTPException) as exc_info:
        _provision(
            pr06_db,
            context,
            context["version"],
            key="producer-duplicate-item",
            item_id=context["binding"].drive_item_id,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error_code"] == "onedrive_item_already_bound"
    assert pr06_db.query(DocumentRecord).count() == before


def test_foreign_project_is_hidden_before_provider_io(
    producer_context: dict[str, object],
    pr06_db: Session,
) -> None:
    context = producer_context
    calls = context["graph"].item_calls
    with pytest.raises(HTTPException) as exc_info:
        provision_onedrive_document(
            pr06_db,
            actor=context["actor"],
            organization_id=context["organization"].id,
            project_id=uuid.uuid4(),
            template_version_id=context["version"].id,
            connection_id=context["binding"].connection_id,
            drive_item_id="hidden-item",
            title="Hidden",
            data_snapshot={},
            idempotency_key="producer-hidden",
            oauth_client=context["oauth"],
            graph_gateway=context["graph"],
            credential_vault=_vault(pr06_db),
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error_code"] == "project_not_found"
    assert context["graph"].item_calls == calls


def test_provision_api_rejects_client_derived_fields(
    producer_context: dict[str, object],
    pr06_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = producer_context

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
        client = TestClient(app)
        response = client.post(
            f"/api/v1/m365/onedrive/projects/{context['project'].id}/documents/provision",
            headers={"X-User-Id": str(context["actor"].id)},
            json={
                "template_version_id": str(context["version"].id),
                "connection_id": str(context["binding"].connection_id),
                "drive_item_id": "api-producer-item",
                "title": "API producer",
                "data_snapshot": {"appraised_value": 1_000_000},
                "idempotency_key": "api-producer-extra",
                "content_checksum_sha256": "0" * 64,
            },
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422
    assert context["graph"].content_calls == 0
