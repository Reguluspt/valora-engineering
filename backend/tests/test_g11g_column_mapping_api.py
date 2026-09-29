"""G1.1G public mapping commands and ADR 0046 service boundaries."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.modules.excel_import.application.column_mapping_service import (
    confirm_column_mapping,
    materialize_confirmed_mapping_to_staging,
    propose_column_mapping,
    reject_column_mapping,
)
from app.modules.excel_import.infrastructure.object_storage import (
    FakeObjectStorage,
    set_object_storage_override,
)
from app.modules.excel_import.models import (
    ColumnMappingDecision,
    ColumnMappingProfile,
    ColumnMappingProfileUsage,
)
from app.modules.project_master_data.application.preliminary_project_lifecycle_service import (
    bind_preliminary_project_customer,
)
from app.modules.project_master_data.application.preliminary_analysis_service import (
    finalize_preliminary_analysis,
)
from app.modules.project_master_data.application.preliminary_result_service import (
    generate_preliminary_result_artifact,
)
from app.modules.project_master_data.application.official_intake_service import (
    commit_project_official_intake,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    OrganizationStatus,
    ProjectAssetImportBatch,
    ProjectOfficialIntakeCommit,
    Role,
    UserRole,
    UserStatus,
)
from tests.test_s13_pr_004_column_mapping import _propose, _seed
from tests.test_pr01_preliminary_analysis_service import _line


@pytest.fixture
def mapping_db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    try:
        yield db
    finally:
        set_object_storage_override(None)
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def api_client(mapping_db):
    app.dependency_overrides[get_db] = lambda: mapping_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        set_object_storage_override(None)


def _api_seed(db, *, unbound: bool = True):
    storage = FakeObjectStorage()
    seeded = _seed(db, storage=storage)
    role = Role(
        code=f"g11g-{uuid.uuid4().hex[:12]}",
        display_name="Mapping operator",
        permissions=[
            "workbench:edit", "project:read", "project:update",
            "project:preliminary_analysis:finalize",
            "project:preliminary_result:generate", "project:official_intake:commit",
        ],
    )
    db.add(role)
    db.flush()
    db.add(UserRole(user_id=seeded["user"].id, role_id=role.id, is_active=True))
    seeded["project"].current_preliminary_import_batch_id = seeded["batch"].id
    if unbound:
        seeded["project"].customer_id = None
    db.commit()
    seeded["role"] = role
    seeded["storage"] = storage
    set_object_storage_override(storage)
    return seeded


def _path(seeded, action):
    return (
        f"/api/v1/projects/{seeded['project'].id}/asset-imports/"
        f"{seeded['batch'].id}/column-mapping/{action}"
    )


def _headers(seeded):
    return {"X-User-Id": str(seeded["user"].id), "X-Correlation-Id": "g11g-api"}


def _proposal_payload(seeded, *, command_id=None):
    return {
        "source_artifact_id": str(seeded["artifact"].id),
        "structure_snapshot_id": str(seeded["snapshot"].id),
        "candidate_index": 0,
        "command_id": str(command_id or uuid.uuid4()),
    }


def _confirm(db, seeded, proposal, *, scope="none", command_id=None):
    return confirm_column_mapping(
        db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, batch_id=seeded["batch"].id,
        proposal_decision_id=proposal.id, mapping_snapshot=proposal.mapping_snapshot,
        memory_scope=scope, command_id=command_id or uuid.uuid4(),
    )


def _materialize(db, seeded, confirmation, *, command_id=None):
    return materialize_confirmed_mapping_to_staging(
        db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, batch_id=seeded["batch"].id,
        confirmation_decision_id=confirmation.id,
        command_id=command_id or uuid.uuid4(), storage=seeded["storage"],
    )


def _error_code(exc, status, code):
    assert exc.value.status_code == status
    assert exc.value.detail["error_code"] == code


def test_public_mapping_round_trip_unbound_replay_and_rbac(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    headers = _headers(seeded)
    proposal_payload = _proposal_payload(seeded)
    proposal_url = _path(seeded, "proposals")
    assert api_client.post(proposal_url, headers=headers, json={
        **proposal_payload, "actor_id": str(seeded["user"].id),
    }).status_code == 422
    assert api_client.post(proposal_url, headers=headers, json={
        **proposal_payload, "candidate_index": True,
    }).status_code == 422
    seeded["role"].permissions = ["project:read"]
    mapping_db.commit()
    assert api_client.post(proposal_url, headers=headers, json=proposal_payload).status_code == 403
    seeded["role"].permissions = [
        "workbench:edit", "project:read", "project:update",
        "project:preliminary_analysis:finalize",
        "project:preliminary_result:generate", "project:official_intake:commit",
    ]
    mapping_db.commit()

    proposed = api_client.post(proposal_url, headers=headers, json=proposal_payload)
    assert proposed.status_code == 201, proposed.text
    body = proposed.json()
    assert body["review_required"] is True
    assert body["exact_profile_id"] is None
    assert body["similar_profile_ids"] == []
    assert body["mapping_snapshot"]["source"]["source_artifact_id"] == str(seeded["artifact"].id)
    assert api_client.post(proposal_url, headers=headers, json=proposal_payload).json() == body
    assert api_client.post(proposal_url, headers=headers, json={
        **proposal_payload, "candidate_index": 1,
    }).status_code == 409

    confirm_url = _path(seeded, "confirmations")
    confirm_payload = {
        "proposal_decision_id": body["decision_id"],
        "mapping_snapshot": body["mapping_snapshot"],
        "memory_scope": "none", "command_id": str(uuid.uuid4()),
    }
    assert api_client.post(confirm_url, headers=headers, json={
        **confirm_payload, "memory_scope": "organization",
    }).status_code == 422
    assert api_client.post(confirm_url, headers=headers, json={
        **confirm_payload, "mapping_snapshot": {"fields": []},
    }).status_code == 422
    confirmed = api_client.post(confirm_url, headers=headers, json=confirm_payload)
    assert confirmed.status_code == 201, confirmed.text
    assert confirmed.json()["profile_id"] is None
    assert confirmed.json()["memory_scope"] == "none"
    assert api_client.post(confirm_url, headers=headers, json=confirm_payload).json() == confirmed.json()
    assert api_client.post(confirm_url, headers=headers, json={
        **confirm_payload, "memory_scope": "customer",
    }).status_code == 409

    materialize_url = _path(seeded, "materializations")
    materialize_payload = {
        "confirmation_decision_id": confirmed.json()["decision_id"],
        "command_id": str(uuid.uuid4()),
    }
    materialized = api_client.post(materialize_url, headers=headers, json=materialize_payload)
    assert materialized.status_code == 201, materialized.text
    assert materialized.json()["materialized_asset_row_count"] == 3
    assert api_client.post(materialize_url, headers=headers, json=materialize_payload).json() == materialized.json()
    assert api_client.post(materialize_url, headers=headers, json={
        **materialize_payload, "confirmation_decision_id": str(uuid.uuid4()),
    }).status_code == 409
    assert mapping_db.query(ColumnMappingDecision).count() == 2
    assert mapping_db.query(ColumnMappingProfile).count() == 0
    assert mapping_db.query(ColumnMappingProfileUsage).one().customer_id is None


def test_service_current_batch_and_customer_memory_fail_closed(mapping_db):
    seeded = _api_seed(mapping_db)
    project = seeded["project"]
    project.current_preliminary_import_batch_id = None
    mapping_db.commit()
    with pytest.raises(HTTPException) as exc:
        _propose(mapping_db, seeded)
    _error_code(exc, 409, "mapping_batch_not_current")

    other_batch = ProjectAssetImportBatch(
        organization_id=seeded["org"].id, project_id=project.id,
        source_filename="other.xlsx", status="created", created_by_user_id=seeded["user"].id,
    )
    mapping_db.add(other_batch)
    mapping_db.flush()
    project.current_preliminary_import_batch_id = other_batch.id
    mapping_db.commit()
    with pytest.raises(HTTPException) as exc:
        _propose(mapping_db, seeded)
    _error_code(exc, 409, "mapping_batch_not_current")

    project.current_preliminary_import_batch_id = seeded["batch"].id
    mapping_db.commit()
    proposal = _propose(mapping_db, seeded).decision
    with pytest.raises(HTTPException) as exc:
        _confirm(mapping_db, seeded, proposal, scope="customer")
    _error_code(exc, 409, "mapping_customer_required")
    assert mapping_db.query(ColumnMappingDecision).count() == 1
    assert mapping_db.query(ColumnMappingProfile).count() == 0
    assert mapping_db.query(AuditEvent).filter_by(event_name="ColumnMappingConfirmed").count() == 0

    project.current_preliminary_import_batch_id = other_batch.id
    mapping_db.commit()
    with pytest.raises(HTTPException) as exc:
        _confirm(mapping_db, seeded, proposal)
    _error_code(exc, 409, "mapping_batch_not_current")
    with pytest.raises(HTTPException) as exc:
        reject_column_mapping(
            mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
            project_id=project.id, batch_id=seeded["batch"].id,
            proposal_decision_id=proposal.id, command_id=uuid.uuid4(),
        )
    _error_code(exc, 409, "mapping_batch_not_current")


def test_historical_null_customer_and_true_replay_survive_binding_and_intake(mapping_db):
    seeded = _api_seed(mapping_db)
    proposal_key, confirmation_key, usage_key = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    proposal = propose_column_mapping(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, batch_id=seeded["batch"].id,
        artifact_id=seeded["artifact"].id, snapshot_id=seeded["snapshot"].id,
        candidate_index=0, command_id=proposal_key,
    ).decision
    confirmation = _confirm(mapping_db, seeded, proposal, command_id=confirmation_key)
    usage = _materialize(mapping_db, seeded, confirmation, command_id=usage_key)
    bind_preliminary_project_customer(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, customer_id=seeded["customer"].id,
        expected_project_version=seeded["project"].row_version,
        idempotency_key="g11g-bind-after-mapping",
    )
    mapping_db.expire_all()
    assert mapping_db.get(ColumnMappingDecision, proposal.id).customer_id is None
    assert mapping_db.get(ColumnMappingDecision, confirmation.id).customer_id is None
    assert mapping_db.get(ColumnMappingProfileUsage, usage.id).customer_id is None
    analysis = finalize_preliminary_analysis(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        expected_project_version=seeded["project"].row_version,
        import_batch_id=seeded["batch"].id,
        source_artifact_id=seeded["artifact"].id,
        structure_snapshot_id=seeded["snapshot"].id,
        mapping_decision_id=confirmation.id,
        mapping_profile_usage_id=usage.id,
        mapping_decision_digest_sha256=confirmation.mapping_digest_sha256,
        profile_usage_mapping_digest_sha256=usage.mapping_digest_sha256,
        line_manifest=[_line(source_row_number=7)],
        idempotency_key="g11g-analysis-after-bind", confirmed=True,
    )
    assert analysis.customer_id == seeded["customer"].id
    assert analysis.mapping_profile_usage_id == usage.id
    result = generate_preliminary_result_artifact(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        preliminary_analysis_snapshot_id=analysis.id,
        expected_project_version=seeded["project"].row_version,
        idempotency_key="g11g-result-after-bind", confirmed=True,
    )
    commit_project_official_intake(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        preliminary_result_artifact_id=result.id,
        expected_project_version=seeded["project"].row_version,
        expected_preliminary_result_version=result.version,
        idempotency_key="g11g-intake-after-bind", confirmed=True,
    )
    assert mapping_db.query(ProjectOfficialIntakeCommit).count() == 1

    assert propose_column_mapping(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, batch_id=seeded["batch"].id,
        artifact_id=seeded["artifact"].id, snapshot_id=seeded["snapshot"].id,
        candidate_index=0, command_id=proposal_key,
    ).decision.id == proposal.id
    assert _confirm(mapping_db, seeded, proposal, command_id=confirmation_key).id == confirmation.id
    assert _materialize(mapping_db, seeded, confirmation, command_id=usage_key).id == usage.id
    with pytest.raises(HTTPException) as exc:
        _propose(mapping_db, seeded)
    _error_code(exc, 409, "mapping_official_intake_closed")
    with pytest.raises(HTTPException) as exc:
        _confirm(mapping_db, seeded, proposal)
    _error_code(exc, 409, "mapping_official_intake_closed")
    with pytest.raises(HTTPException) as exc:
        _materialize(mapping_db, seeded, confirmation)
    _error_code(exc, 409, "mapping_official_intake_closed")
    with pytest.raises(HTTPException) as exc:
        reject_column_mapping(
            mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
            project_id=seeded["project"].id, batch_id=seeded["batch"].id,
            proposal_decision_id=proposal.id, command_id=uuid.uuid4(),
        )
    _error_code(exc, 409, "mapping_official_intake_closed")
    assert mapping_db.query(ColumnMappingDecision).count() == 2
    assert mapping_db.query(ColumnMappingProfileUsage).count() == 1


def test_public_mapping_rejects_inactive_and_cross_tenant(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    other = _api_seed(mapping_db)
    url = _path(seeded, "proposals")
    payload = _proposal_payload(seeded)
    headers = _headers(seeded)
    assert api_client.post(_path(other, "proposals"), headers=headers, json=payload).status_code == 404
    assert api_client.post(url, headers=headers, json={
        **payload, "source_artifact_id": str(other["artifact"].id),
    }).status_code == 404
    assert api_client.post(url, headers=headers, json={
        **payload, "structure_snapshot_id": str(other["snapshot"].id),
    }).status_code == 404
    seeded["batch"].current_source_artifact_id = None
    mapping_db.commit()
    source_stale = api_client.post(url, headers=headers, json=payload)
    assert source_stale.status_code == 409
    assert source_stale.json()["detail"]["error_code"] == "mapping_source_not_current"
    seeded["batch"].current_source_artifact_id = seeded["artifact"].id
    mapping_db.commit()
    seeded["user"].status = UserStatus.INACTIVE
    mapping_db.commit()
    assert api_client.post(url, headers=headers, json=payload).status_code in (401, 403)
    seeded["user"].status = UserStatus.ACTIVE
    seeded["org"].status = OrganizationStatus.INACTIVE
    mapping_db.commit()
    assert api_client.post(url, headers=headers, json=payload).status_code in (401, 403)


def test_public_rejection_requires_proposal_and_preserves_reason(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    headers = _headers(seeded)
    proposal = api_client.post(
        _path(seeded, "proposals"), headers=headers, json=_proposal_payload(seeded),
    )
    assert proposal.status_code == 201, proposal.text
    reject_url = _path(seeded, "rejections")
    payload = {
        "proposal_decision_id": proposal.json()["decision_id"],
        "command_id": str(uuid.uuid4()),
        "reason_code": "wrong_columns", "reason_text": "Cần chọn lại cột tài sản.",
    }
    rejected = api_client.post(reject_url, headers=headers, json=payload)
    assert rejected.status_code == 201, rejected.text
    assert rejected.json()["outcome"] == "rejected"
    assert api_client.post(reject_url, headers=headers, json=payload).json() == rejected.json()
    assert api_client.post(reject_url, headers=headers, json={
        **payload, "reason_code": "other",
    }).status_code == 409
    stored = mapping_db.get(ColumnMappingDecision, uuid.UUID(rejected.json()["decision_id"]))
    assert stored.reason_code == "wrong_columns"
    assert stored.reason_text == "Cần chọn lại cột tài sản."
    assert api_client.post(_path(seeded, "materializations"), headers=headers, json={
        "confirmation_decision_id": rejected.json()["decision_id"],
        "command_id": str(uuid.uuid4()),
    }).status_code == 409
    assert mapping_db.query(ColumnMappingProfileUsage).count() == 0


def test_unbound_project_can_use_approved_organization_template(mapping_db):
    first = _api_seed(mapping_db, unbound=False)
    proposal = _propose(mapping_db, first).decision
    confirmation = _confirm(mapping_db, first, proposal, scope="customer")
    template = mapping_db.get(ColumnMappingProfile, confirmation.profile_id)
    user_id = first["user"].id
    template.approved_by_user_id = user_id
    template.approved_at = datetime.now(timezone.utc)
    template.scope_type = "organization_template"
    template.customer_id = None
    mapping_db.commit()

    second = _seed(
        mapping_db, org=first["org"], user=first["user"], customer=first["customer"],
    )
    second["project"].customer_id = None
    mapping_db.commit()
    result = _propose(mapping_db, second)
    assert result.organization_template_id == template.id
    assert result.exact_profile_id is None
    assert result.similar_profile_ids == ()
    assert result.decision.customer_id is None
