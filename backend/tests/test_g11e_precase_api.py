"""HTTP contracts for the bounded G1.1E Pre-case commands."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.modules.excel_import.infrastructure.object_storage import set_object_storage_override
from app.modules.excel_import.models import ColumnMappingDecision, ProjectColumnMappingAuthority
from app.modules.project_master_data.models import (
    AuditEvent, CustomerStatus, OrganizationStatus, PreliminaryResultArtifact,
    Project, ProjectOfficialIntakeCommit, UserStatus, ValidationIssue, ValidationIssueSeverity,
    ValidationIssueStatus,
)
from tests.test_g11b_lifecycle_service import _batch, _seed_case
from tests.test_pr01_preliminary_analysis_service import _line, _seed as seed_analysis
from tests.test_pr01_official_intake_service import _add_issue
from tests.test_pr01_preliminary_result_service import (
    _append_analysis_version, _seed as seed_result,
)


COMMAND_PERMISSIONS = [
    "project:preliminary_analysis:finalize",
    "project:preliminary_result:generate",
    "project:official_intake:commit",
]


@pytest.fixture
def api_db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app), db
    finally:
        app.dependency_overrides.pop(get_db, None)
        set_object_storage_override(None)
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _headers(seeded):
    return {"X-User-Id": str(seeded["actor"].id)}


def _url(seeded, command):
    return f"/api/v1/projects/{seeded['project'].id}/{command}"


def _result_payload(seeded, *, key="result-1"):
    return {
        "preliminary_analysis_snapshot_id": str(seeded["snapshot"].id),
        "expected_project_version": seeded["project"].row_version,
        "idempotency_key": key, "confirmed": True,
    }


def _intake_payload(seeded, result, *, key="intake-1"):
    return {
        "preliminary_result_artifact_id": result["id"],
        "expected_project_version": seeded["project"].row_version,
        "expected_preliminary_result_version": result["version"],
        "idempotency_key": key, "confirmed": True,
    }


def test_project_create_optional_customer_and_tenant_validation(api_db):
    client, db = api_db
    seeded = seed_result(db, suffix="api-create")
    seeded["role"].permissions = ["project:create", "project:read"]
    other = seed_result(db, suffix="api-create-other")
    db.commit()
    headers = _headers(seeded)
    base = {"code": "PRECASE-NULL", "name": "Pre-case"}
    unbound = client.post("/api/v1/projects", headers=headers, json=base)
    assert unbound.status_code == 201
    assert unbound.json()["customer_id"] is None
    assert unbound.json()["current_preliminary_import_batch_id"] is None
    assert unbound.json()["row_version"] == 1
    explicit_null = client.post(
        "/api/v1/projects", headers=headers, json={**base, "code": "PRECASE-NULL-2", "customer_id": None},
    )
    assert explicit_null.status_code == 201
    assert explicit_null.json()["customer_id"] is None
    active = client.post(
        "/api/v1/projects", headers=headers,
        json={**base, "code": "PRECASE-BOUND", "customer_id": str(seeded["customer"].id)},
    )
    assert active.status_code == 201
    assert active.json()["customer_id"] == str(seeded["customer"].id)
    cross = client.post(
        "/api/v1/projects", headers=headers,
        json={**base, "code": "PRECASE-CROSS", "customer_id": str(other["customer"].id)},
    )
    assert cross.status_code == 404
    seeded["customer"].status = CustomerStatus.INACTIVE
    db.commit()
    inactive = client.post(
        "/api/v1/projects", headers=headers,
        json={**base, "code": "PRECASE-INACTIVE", "customer_id": str(seeded["customer"].id)},
    )
    assert inactive.status_code == 422


def test_bind_customer_http_replay_cas_and_scope(api_db):
    client, db = api_db
    seeded = _seed_case(db)
    project = seeded["project"]
    before = project.row_version
    url = _url(seeded, "preliminary-customer")
    payload = {"customer_id": str(seeded["customer"].id),
               "expected_project_version": before, "idempotency_key": "bind-api"}
    cross = _seed_case(db)
    assert client.post(url, headers=_headers(seeded), json={
        **payload, "customer_id": str(cross["customer"].id),
    }).status_code == 404
    seeded["customer"].status = CustomerStatus.INACTIVE
    db.commit()
    assert client.post(url, headers=_headers(seeded), json=payload).status_code == 409
    seeded["customer"].status = CustomerStatus.ACTIVE
    db.commit()
    assert client.post(url, headers=_headers(seeded), json={
        **payload, "expected_project_version": before + 1,
    }).status_code == 409
    first = client.post(url, headers=_headers(seeded), json=payload)
    assert first.status_code == 201
    assert first.json()["committed_project_version"] == before + 1
    assert client.post(url, headers=_headers(seeded), json=payload).json() == first.json()
    assert client.post(url, headers=_headers(seeded), json={
        **payload, "customer_id": str(cross["customer"].id),
    }).status_code == 409
    assert client.post(url, headers=_headers(seeded), json={
        **payload, "idempotency_key": "bind-again", "expected_project_version": before + 1,
    }).status_code == 409
    assert db.query(AuditEvent).filter_by(event_name="PreliminaryProjectCustomerBound").count() == 1


def test_switch_batch_http_cas_replay_and_unresolved_pointer(api_db):
    client, db = api_db
    seeded = _seed_case(db)
    target = _batch(db, seeded)
    before = seeded["project"].row_version
    current_id = seeded["batch"].id
    url = _url(seeded, "preliminary-import-batch/current")
    payload = {"target_import_batch_id": str(target.id),
               "expected_current_import_batch_id": str(current_id),
               "expected_project_version": before, "idempotency_key": "switch-api"}
    other = _seed_case(db)
    assert client.post(url, headers=_headers(seeded), json={
        **payload, "target_import_batch_id": str(other["batch"].id),
    }).status_code == 404
    assert client.post(url, headers=_headers(seeded), json={
        **payload, "expected_current_import_batch_id": str(uuid.uuid4()),
    }).status_code == 409
    assert client.post(url, headers=_headers(seeded), json={
        **payload, "expected_project_version": before + 1,
    }).status_code == 409
    assert client.post(url, headers=_headers(seeded), json={
        **payload, "target_import_batch_id": str(current_id),
    }).status_code == 409
    first = client.post(url, headers=_headers(seeded), json=payload)
    assert first.status_code == 201
    assert first.json()["target_import_batch_id"] == str(target.id)
    assert client.post(url, headers=_headers(seeded), json=payload).json() == first.json()
    seeded["project"].current_preliminary_import_batch_id = None
    db.commit()
    assert client.post(url, headers=_headers(seeded), json={
        **payload, "idempotency_key": "switch-unresolved",
        "expected_project_version": seeded["project"].row_version,
        "expected_current_import_batch_id": None,
    }).json()["detail"]["error_code"] == "current_import_batch_unresolved"


def test_analysis_http_v2_contract_currentness_and_permission(api_db):
    client, db = api_db
    seeded = seed_analysis(db, suffix="api-analysis")
    payload = {
        "expected_project_version": seeded["project"].row_version,
        "import_batch_id": str(seeded["batch"].id),
        "source_artifact_id": str(seeded["artifact"].id),
        "structure_snapshot_id": str(seeded["structure"].id),
        "mapping_decision_id": str(seeded["decision"].id),
        "mapping_profile_usage_id": str(seeded["usage"].id),
        "mapping_decision_digest_sha256": seeded["decision"].mapping_digest_sha256,
        "profile_usage_mapping_digest_sha256": seeded["usage"].mapping_digest_sha256,
        "line_manifest": [_line()], "idempotency_key": "analysis-api", "confirmed": True,
    }
    url = _url(seeded, "preliminary-analyses")
    assert client.post(url, headers=_headers(seeded), json={
        **payload, "line_manifest": [{"identity": "old-v1"}],
    }).status_code == 422
    assert client.post(url, headers=_headers(seeded), json={
        key: value for key, value in payload.items() if key != "confirmed"
    }).status_code == 422
    seeded["role"].permissions = ["project:update"]
    db.commit()
    assert client.post(url, headers=_headers(seeded), json=payload).status_code == 403
    seeded["role"].permissions = COMMAND_PERMISSIONS
    db.commit()
    first = client.post(url, headers=_headers(seeded), json=payload)
    assert first.status_code == 201, first.text
    assert first.json()["version"] == 1
    assert client.post(url, headers=_headers(seeded), json=payload).json() == first.json()
    assert client.post(url, headers=_headers(seeded), json={
        **payload, "import_batch_id": str(uuid.uuid4()), "idempotency_key": "historical-api",
    }).status_code == 409


def test_result_and_intake_http_currentness_replay_and_binding(api_db):
    client, db = api_db
    seeded = seed_result(db, suffix="api-journey")
    seeded["role"].permissions = ["project:read", "project:update", *COMMAND_PERMISSIONS]
    seeded["project"].customer_id = None
    proposal = db.get(ColumnMappingDecision, seeded["decision"].proposal_decision_id)
    for fact in (proposal, seeded["decision"], seeded["usage"], seeded["snapshot"]):
        fact.customer_id = None
    db.commit()
    headers = _headers(seeded)
    result_url = _url(seeded, "preliminary-results")
    result_payload = _result_payload(seeded)
    assert client.post(result_url, headers=headers, json={
        **result_payload, "confirmed": False,
    }).status_code == 400
    first = client.post(result_url, headers=headers, json=result_payload)
    assert first.status_code == 201, first.text
    assert first.json()["version"] == 1
    assert client.post(result_url, headers=headers, json=result_payload).json() == first.json()
    second = client.post(result_url, headers=headers, json={
        **result_payload, "idempotency_key": "result-2",
    })
    assert second.status_code == 201, second.text
    assert second.json()["version"] == 2
    assert client.post(result_url, headers=headers, json=result_payload).json() == first.json()
    assert client.post(result_url, headers=headers, json={
        **result_payload, "expected_project_version": 99,
    }).status_code == 409
    assert client.post(result_url, headers=headers, json={
        **result_payload, "expected_project_version": 99, "idempotency_key": "result-stale",
    }).status_code == 409
    state = client.get(_url(seeded, "case-state"), headers=headers)
    assert state.status_code == 200, state.text
    assert state.json()["preliminary"]["current_preliminary_result_artifact_id"] == second.json()["id"]
    assert state.json()["preliminary"]["current_preliminary_analysis_snapshot_id"] == str(seeded["snapshot"].id)
    intake_url = _url(seeded, "official-intake")
    intake_payload = _intake_payload(seeded, second.json())
    assert client.post(intake_url, headers=headers, json=intake_payload).status_code == 409
    bind_payload = {"customer_id": str(seeded["customer"].id),
                    "expected_project_version": seeded["project"].row_version,
                    "idempotency_key": "bind-journey"}
    bound = client.post(_url(seeded, "preliminary-customer"), headers=headers, json=bind_payload)
    assert bound.status_code == 201, bound.text
    intake_payload["expected_project_version"] = bound.json()["committed_project_version"]
    assert client.post(intake_url, headers=headers, json={
        **intake_payload, "preliminary_result_artifact_id": first.json()["id"],
        "expected_preliminary_result_version": 1, "idempotency_key": "historical-intake",
    }).status_code == 409
    assert client.post(intake_url, headers=headers, json={
        **intake_payload, "confirmed": False,
    }).status_code == 400
    commit = client.post(intake_url, headers=headers, json=intake_payload)
    assert commit.status_code == 201, commit.text
    assert commit.json()["preliminary_result_artifact_id"] == second.json()["id"]
    assert client.post(intake_url, headers=headers, json=intake_payload).json() == commit.json()
    assert db.query(ProjectOfficialIntakeCommit).count() == 1
    assert client.post(result_url, headers=headers, json={
        **result_payload, "expected_project_version": intake_payload["expected_project_version"],
        "idempotency_key": "result-after-intake",
    }).status_code == 409
    assert db.query(PreliminaryResultArtifact).count() == 2


def test_api_created_unbound_project_reaches_official_intake(api_db):
    client, db = api_db

    def create_unbound_project(session, org, actor, role, _customer):
        role.permissions = ["project:create", "project:read", "project:update", *COMMAND_PERMISSIONS]
        session.flush()
        response = client.post(
            "/api/v1/projects", headers={"X-User-Id": str(actor.id)},
            json={"code": f"G11E-{uuid.uuid4().hex[:8]}", "name": "Unbound Pre-case"},
        )
        assert response.status_code == 201, response.text
        assert response.json()["customer_id"] is None
        return session.get(Project, uuid.UUID(response.json()["id"]))

    seeded = seed_result(
        db, suffix="api-created-journey", project_factory=create_unbound_project,
    )
    proposal = db.get(ColumnMappingDecision, seeded["decision"].proposal_decision_id)
    for fact in (proposal, seeded["decision"], seeded["usage"], seeded["snapshot"]):
        fact.customer_id = None
    db.add(ProjectColumnMappingAuthority(
        organization_id=seeded["org"].id,
        project_id=seeded["project"].id,
        selection_revision=2,
        import_batch_id=seeded["batch"].id,
        source_artifact_id=seeded["artifact"].id,
        structure_snapshot_id=seeded["structure"].id,
        confirmation_decision_id=seeded["decision"].id,
        selected_usage_id=seeded["usage"].id,
        current_staging_usage_id=seeded["usage"].id,
    ))
    db.commit()
    headers = _headers(seeded)
    analysis_payload = {
        "expected_project_version": seeded["project"].row_version,
        "import_batch_id": str(seeded["batch"].id),
        "source_artifact_id": str(seeded["artifact"].id),
        "structure_snapshot_id": str(seeded["structure"].id),
        "mapping_decision_id": str(seeded["decision"].id),
        "mapping_profile_usage_id": str(seeded["usage"].id),
        "mapping_decision_digest_sha256": seeded["decision"].mapping_digest_sha256,
        "profile_usage_mapping_digest_sha256": seeded["usage"].mapping_digest_sha256,
        "line_manifest": seeded["snapshot"].line_manifest,
        "idempotency_key": "analysis-created-project", "confirmed": True,
    }
    analysis = client.post(
        _url(seeded, "preliminary-analyses"), headers=headers, json=analysis_payload,
    )
    assert analysis.status_code == 201, analysis.text
    assert analysis.json()["version"] == 2
    result = client.post(
        _url(seeded, "preliminary-results"), headers=headers,
        json={"preliminary_analysis_snapshot_id": analysis.json()["id"],
              "expected_project_version": seeded["project"].row_version,
              "idempotency_key": "result-created-project", "confirmed": True},
    )
    assert result.status_code == 201, result.text
    intake_url = _url(seeded, "official-intake")
    intake_payload = _intake_payload(seeded, result.json(), key="intake-created-project")
    assert client.post(intake_url, headers=headers, json=intake_payload).status_code == 409
    bound = client.post(
        _url(seeded, "preliminary-customer"), headers=headers,
        json={"customer_id": str(seeded["customer"].id),
              "expected_project_version": seeded["project"].row_version,
              "idempotency_key": "bind-created-project"},
    )
    assert bound.status_code == 201, bound.text
    intake_payload["expected_project_version"] = bound.json()["committed_project_version"]
    committed = client.post(intake_url, headers=headers, json=intake_payload)
    assert committed.status_code == 201, committed.text
    assert committed.json()["project_id"] == str(seeded["project"].id)


def test_official_intake_http_negative_authority_and_replay(api_db):
    client, db = api_db
    seeded = seed_result(db, suffix="api-intake-negative")
    seeded["role"].permissions = ["project:read", "project:update", *COMMAND_PERMISSIONS]
    db.commit()
    headers = _headers(seeded)
    result = client.post(_url(seeded, "preliminary-results"), headers=headers,
                         json=_result_payload(seeded)).json()
    url = _url(seeded, "official-intake")
    payload = _intake_payload(seeded, result)
    other = seed_result(db, suffix="api-intake-other")
    assert client.post(_url(other, "official-intake"), headers=headers, json=payload).status_code == 404
    assert client.post(url, headers=headers, json={
        **payload, "expected_project_version": 99,
    }).status_code == 409
    assert client.post(url, headers=headers, json={
        **payload, "expected_preliminary_result_version": 99,
    }).status_code == 409
    seeded["role"].permissions = ["project:update"]
    db.commit()
    assert client.post(url, headers=headers, json=payload).status_code == 403
    seeded["role"].permissions = COMMAND_PERMISSIONS
    seeded["customer"].status = CustomerStatus.INACTIVE
    db.commit()
    assert client.post(url, headers=headers, json=payload).status_code == 409
    seeded["customer"].status = CustomerStatus.ACTIVE
    db.commit()
    committed = client.post(url, headers=headers, json=payload)
    assert committed.status_code == 201, committed.text
    assert client.post(url, headers=headers, json={
        **payload, "expected_preliminary_result_version": 99,
    }).status_code == 409
    seeded["customer"].status = CustomerStatus.INACTIVE
    db.commit()
    assert client.post(url, headers=headers, json=payload).json() == committed.json()


def test_result_http_rejects_historical_analysis_and_permission(api_db):
    client, db = api_db
    seeded = seed_result(db, suffix="api-historical")
    seeded["role"].permissions = ["project:update", *COMMAND_PERMISSIONS]
    db.commit()
    _append_analysis_version(db, seeded["snapshot"], 2)
    url = _url(seeded, "preliminary-results")
    assert client.post(url, headers=_headers(seeded), json=_result_payload(seeded)).status_code == 409
    seeded["role"].permissions = ["project:update"]
    db.commit()
    assert client.post(url, headers=_headers(seeded), json=_result_payload(seeded)).status_code == 403
    seeded["actor"].status = UserStatus.INACTIVE
    db.commit()
    assert client.post(url, headers=_headers(seeded), json=_result_payload(seeded)).status_code == 403
    seeded["actor"].status = UserStatus.ACTIVE
    seeded["org"].status = OrganizationStatus.INACTIVE
    db.commit()
    assert client.post(url, headers=_headers(seeded), json=_result_payload(seeded)).status_code == 403


def test_official_intake_http_rejects_old_analysis_and_blocker(api_db):
    client, db = api_db
    seeded = seed_result(db, suffix="api-intake-blockers")
    seeded["role"].permissions = ["project:update", *COMMAND_PERMISSIONS]
    db.commit()
    headers = _headers(seeded)
    result = client.post(
        _url(seeded, "preliminary-results"), headers=headers, json=_result_payload(seeded),
    ).json()
    payload = _intake_payload(seeded, result)
    url = _url(seeded, "official-intake")
    _add_issue(db, seeded, ValidationIssueSeverity.BLOCKING)
    blocked = client.post(url, headers=headers, json=payload)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["error_code"] == "official_intake_blocked"
    assert db.query(ProjectOfficialIntakeCommit).count() == 0

    issue = db.query(ValidationIssue).one()
    issue.status = ValidationIssueStatus.RESOLVED
    db.commit()
    _append_analysis_version(db, seeded["snapshot"], 2)
    historical = client.post(url, headers=headers, json=payload)
    assert historical.status_code == 409
    assert historical.json()["detail"]["error_code"] == "preliminary_result_not_current"


def test_preliminary_commands_close_after_official_intake(api_db):
    client, db = api_db
    seeded = seed_result(db, suffix="api-closed")
    seeded["role"].permissions = ["project:update", *COMMAND_PERMISSIONS]
    db.commit()
    headers = _headers(seeded)
    result_url = _url(seeded, "preliminary-results")
    result_payload = _result_payload(seeded)
    result = client.post(result_url, headers=headers, json=result_payload).json()
    commit = client.post(
        _url(seeded, "official-intake"), headers=headers,
        json=_intake_payload(seeded, result),
    )
    assert commit.status_code == 201, commit.text
    assert client.post(result_url, headers=headers, json={
        **result_payload, "idempotency_key": "new-after-intake",
    }).status_code == 409
    assert client.post(result_url, headers=headers, json=result_payload).json() == result
    assert client.post(_url(seeded, "preliminary-customer"), headers=headers, json={
        "customer_id": str(seeded["customer"].id),
        "expected_project_version": seeded["project"].row_version,
        "idempotency_key": "bind-after-intake",
    }).status_code == 409
    target = _batch(db, seeded)
    assert client.post(_url(seeded, "preliminary-import-batch/current"), headers=headers, json={
        "target_import_batch_id": str(target.id),
        "expected_current_import_batch_id": str(seeded["batch"].id),
        "expected_project_version": seeded["project"].row_version,
        "idempotency_key": "switch-after-intake",
    }).status_code == 409
