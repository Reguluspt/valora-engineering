"""HTTP envelope, scoped reconciliation, negative access and Case State v5."""
import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.rbac import get_current_user
from app.db import get_db
from app.db.session import get_case_state_db
from app.db.mixins import utc_now
from app.api.price_evidence import _mutate
from app.modules.project_master_data.application import price_evidence_commands as commands
from app.modules.project_master_data.models import User, UserRole, WorkbenchSession, Project, OrganizationProfile
from tests.test_g2_price_evidence import (
    entry_db as _entry_db, line_db as _line_db, workbench_db as _workbench_db,
    evidence_db as _evidence_db, covered_db as _covered_db,
    execute, request_for, snapshot, provider, counts, material, human_commit, commit_saved,
)

entry_db, line_db, workbench_db = _entry_db, _line_db, _workbench_db
evidence_db, covered_db = _evidence_db, _covered_db


@pytest.fixture
def http_client(evidence_db):
    db, entry = evidence_db
    def writable():
        yield db
    def reader():
        with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as read:
            yield read
    app.dependency_overrides[get_db] = writable
    app.dependency_overrides[get_case_state_db] = reader
    app.dependency_overrides[get_current_user] = lambda: entry["user"]
    try:
        with TestClient(app) as client:
            yield client, db, entry
    finally:
        for dependency in (get_db, get_case_state_db, get_current_user):
            app.dependency_overrides.pop(dependency, None)


def test_api_contract_preparation_and_snapshot_context(http_client):
    client, db, entry = http_client
    path = f'/api/v1/projects/{entry["project"].id}'
    prep = client.get(path + "/price-evidence/preparation")
    assert prep.status_code == 200, prep.text
    assert prep.json()["can_register"] and not prep.json()["can_confirm"]
    case = client.get(path + "/case-state")
    assert case.status_code == 200, case.text
    state = case.json()
    assert state["current_stage"] == "PRICE_EVIDENCE"
    assert state["capabilities"][6]["provider_key"] == "price_evidence_confirmation_v1"
    assert state["capabilities"][6]["available"]
    action = state["next_action"]
    assert action["kind"] == "PENDING" and action["semantic_route_key"] == "price_evidence_prepare_required"
    assert action["context"]["kind"] == "price_evidence_preparation"
    assert all(stage["result"] == "NOT_AVAILABLE" for stage in state["stages"][7:])
    assert not {"material", "retained_text", "url", "amount", "reason_note"}.intersection(action["context"])
    req = request_for(db, entry)
    for body in ({**req, "confirm": 1}, {**req, "secret": "Private source"}, {**req, "expected_line_versions": req["expected_line_versions"] * 2}):
        response = client.post(path + "/price-evidence/register", json=body)
        assert response.status_code == 400 and "Private source" not in response.text
    response = client.post(path + "/price-evidence/register", json=req)
    assert response.status_code == 200, response.text
    replay = client.post(path + "/price-evidence/register", json=req)
    assert replay.status_code == 200 and replay.json()["replayed"]
    recovered = client.get(path + "/price-evidence/command-receipts/" + req["command_id"])
    assert recovered.status_code == 200 and recovered.json()["result"] == response.json()["result"]
    assert recovered.json()["historical"] and counts(db) == (1, 1, 1)
    source = client.get(path + "/price-evidence/sources/" + response.json()["result"]["record_id"])
    from app.modules.project_master_data.price_evidence_schemas import SourceMaterial
    assert source.status_code == 200 and source.json()["material"] == SourceMaterial.model_validate(req["material"]).model_dump(mode="json")
    assert counts(db) == (1, 1, 1)
    assert client.post(path + "/price-evidence/register", content="x" * 2_000_001).status_code == 400


@pytest.mark.parametrize("denial", ["permission", "session", "user", "organization", "other_actor", "other_project", "other_tenant", "system"])
def test_new_writes_and_replays_recheck_access(evidence_db, denial):
    db, entry = evidence_db
    req = request_for(db, entry)
    execute(db, entry, req)
    db.commit()
    actor = entry["user"]
    scope = entry
    expected = 403
    if denial == "permission":
        entry["role"].permissions = ["project:read"]
    elif denial == "session":
        entry["session"].status = "closed"
        expected = 404
    elif denial == "user":
        actor.status = "inactive"
    elif denial == "organization":
        entry["org"].status = "inactive"
    elif denial == "other_actor":
        actor = User(organization_id=entry["org"].id, email=uuid.uuid4().hex + "@example.test", full_name="Other synthetic human")
        db.add(actor)
        db.flush()
        db.add_all([UserRole(user_id=actor.id, role_id=entry["role"].id), WorkbenchSession(project_id=entry["project"].id, user_id=actor.id)])
        expected = 409
    elif denial == "other_project":
        project = Project(organization_id=entry["org"].id, code=uuid.uuid4().hex, name="Other project", created_by=actor.id)
        db.add(project)
        db.flush()
        db.add(WorkbenchSession(project_id=project.id, user_id=actor.id))
        scope = {**entry, "project": project}
        expected = 409
    elif denial == "other_tenant":
        org = OrganizationProfile(legal_name="Synthetic foreign tenant", organization_slug=uuid.uuid4().hex)
        db.add(org)
        db.flush()
        scope = {**entry, "org": org}
        expected = 404
    else:
        from types import SimpleNamespace
        actor = SimpleNamespace(id=actor.id, organization_id=actor.organization_id)
    db.commit()
    with pytest.raises(HTTPException) as error:
        execute(db, scope, req, actor=actor)
    assert error.value.status_code == expected
    db.rollback()
    assert counts(db) == (1, 1, 1)


def test_unknown_commit_response_reconciles_result_receipt_and_audit(evidence_db, monkeypatch):
    db, entry = evidence_db
    req = request_for(db, entry)
    commit = db.commit
    def lost_ack():
        commit()
        raise RuntimeError("Synthetic lost response")
    monkeypatch.setattr(db, "commit", lost_ack)
    with pytest.raises(HTTPException) as error:
        _mutate(commands.register_project_price_evidence, db, entry["user"], entry["project"].id, req)
    assert error.value.status_code == 500 and "reconcile" in error.value.detail
    monkeypatch.setattr(db, "commit", commit)
    assert counts(db) == (1, 1, 1)
    db.rollback()
    with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as reader:
        receipt = commands.read_price_evidence_receipt(reader, actor=entry["user"], org_id=entry["org"].id,
            project_id=entry["project"].id, command_id=uuid.UUID(req["command_id"]))
        assert receipt["historical"] and receipt["result"]["command_id"] == req["command_id"]
    assert counts(db) == (1, 1, 1)


def test_current_completion_survives_status_but_new_writes_do_not(covered_db):
    db, entry = covered_db
    req = request_for(db, entry, "confirmation")
    execute(db, entry, req)
    db.commit()
    entry["project"].status = "archived"
    entry["project"].row_version += 1
    db.commit()
    assert provider(db, entry).result == "COMPLETE"
    assert execute(db, entry, req)["replayed"]
    db.commit()
    with pytest.raises(HTTPException) as error:
        execute(db, entry, request_for(db, entry, "confirmation-withdrawal"))
    assert error.value.status_code == 400
    db.rollback()


def test_same_canonical_value_does_not_stale(covered_db):
    db, entry = covered_db
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    line = next(line for line in snapshot(db, entry).lines if line.id == entry["line_id"])
    version = human_commit(db, entry, "description", line.description)
    commit_saved(db, entry, "description", version)
    db.commit()
    assert provider(db, entry).result == "COMPLETE"


def test_expiry_is_hard_upper_bound_and_no_file_admission(evidence_db):
    db, entry = evidence_db
    expires = utc_now() + timedelta(days=2)
    execute(db, entry, request_for(db, entry, material=material(expires_at=expires.isoformat())))
    db.commit()
    with pytest.raises(HTTPException) as error:
        execute(db, entry, request_for(db, entry, "relevance", review_due_at=(expires + timedelta(seconds=1)).isoformat()))
    assert error.value.status_code == 400
    db.rollback()
    req = request_for(db, entry)
    req["material"]["document_revision_id"] = str(uuid.uuid4())
    with pytest.raises(HTTPException) as error:
        execute(db, entry, req)
    assert error.value.status_code == 400


def test_structured_explanation_requires_exact_current_inspectable_inputs(evidence_db):
    db, entry = evidence_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    source = next(iter(snapshot(db, entry).price_evidence.source_heads.values()))
    explanation = material(category="unit_price_explanation", reference=None, capture_method="authored_explanation",
        explanation=dict(method="sum_of_scaled_source_values", inputs=[dict(evidence_revision_id=str(source.id), coefficient="1")],
            assumptions="Same unit and no FX conversion", calculations="100 times 1 = 100", units="item", currency="VND", proposed_basis_value="100"))
    execute(db, entry, request_for(db, entry, material=explanation))
    db.commit()
    execute(db, entry, request_for(db, entry, "relevance", higher_priorities_considered=["internet_survey"],
                                  source_priority_rationale="Direct survey needs the retained explicit calculation"))
    db.commit()
    assert len(snapshot(db, entry).price_evidence.qualifying) == 1
    bad = material(category="unit_price_explanation", reference=None, capture_method="authored_explanation",
                   explanation={**explanation["explanation"], "proposed_basis_value": "999"})
    with pytest.raises(HTTPException):
        execute(db, entry, request_for(db, entry, material=bad))
    db.rollback()
