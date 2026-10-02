"""A4 command/proof/domain/API certification on real sealed PostgreSQL lineage."""
from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.main import app
from app.db import get_db
from app.db.session import get_case_state_db
from app.core.rbac import get_current_user
from app.modules.project_master_data.application.asset_review_authority import resolve_authority
from app.modules.project_master_data.application.asset_review_line_commands import (
    validate_project_asset_line, decide_project_asset_line_review, read_asset_review_receipt,
)
from app.modules.project_master_data.application.asset_review_provider import evaluate_asset_review_provider
from app.modules.project_master_data.application.asset_line_validation_rules import evaluate_rules, exact_numeric
from app.modules.project_master_data.models import (
    WorkbenchSession, AssetLineValidationGeneration, AssetLineHumanDecision, AssetLineDecisionReversal,
    AssetReviewCommandReceipt, AuditEvent, User, ValidationIssue, ValidationRule,
)
from tests.test_g2_authority import entry_db as _entry_db, _ready, _apply

entry_db = _entry_db


def snapshot(db, entry, *, locked=True):
    return resolve_authority(db, org_id=entry["org"].id, project_id=entry["project"].id, locked=locked)


@pytest.fixture
def line_db(entry_db):
    db, entry = entry_db
    _apply(db, entry, _ready(db, entry))
    session = WorkbenchSession(project_id=entry["project"].id, user_id=entry["user"].id)
    db.add(session)
    db.commit()
    line = snapshot(db, entry).lines[0]
    entry.update(session=session, line_id=line.id)
    db.rollback()
    yield db, entry


def request_for(db, entry, *, review=None, line_id=None, **changes):
    snap = snapshot(db, entry)
    line = next(item for item in snap.lines if item.id == (line_id or entry["line_id"]))
    request = dict(command_id=str(uuid.uuid4()), confirm=True, expected_row_version=line.row_version,
        expected_case_version=snap.case_version,
        contract_version="asset-line-validation-v1" if review is None else "asset-line-human-review-v1")
    if review:
        request["target_review_status"] = review
    request.update(changes)
    return request


def execute(db, entry, request, *, line_id=None, actor=None):
    command = (validate_project_asset_line if request["contract_version"] == "asset-line-validation-v1"
               else decide_project_asset_line_review)
    return command(db, actor=actor or db.merge(entry["user"]), org_id=entry["org"].id,
                   project_id=entry["project"].id, line_id=line_id or entry["line_id"], request=request)


def counts(db):
    return tuple(db.query(m).count() for m in (AssetLineValidationGeneration, AssetLineHumanDecision,
        AssetLineDecisionReversal, AssetReviewCommandReceipt)) + (db.query(AuditEvent).filter(
            AuditEvent.event_name.in_(("ProjectAssetLineValidated", "ProjectAssetLineReviewDecided"))).count(),)


def provider(db, entry):
    return evaluate_asset_review_provider(snapshot(db, entry), effective_permissions={"workbench:edit"},
                                         has_active_session=True)


def test_validation_acceptance_revalidation_requires_new_human_decision(line_db):
    db, entry = line_db
    before = snapshot(db, entry).case_version
    validated = execute(db, entry, request_for(db, entry))
    assert validated["result"]["validation_outcome"] == "valid"
    db.commit()
    assert counts(db) == (1, 0, 0, 1, 1)
    assert snapshot(db, entry).case_version != before
    accepted = execute(db, entry, request_for(db, entry, review="accepted"))
    db.commit()
    assert counts(db) == (1, 1, 0, 2, 2)
    assert snapshot(db, entry).line_proofs[entry["line_id"]]["positive_current"]
    again = execute(db, entry, request_for(db, entry))
    db.commit()
    assert again["result"]["validation_generation"] == 2
    state = snapshot(db, entry).line_proofs[entry["line_id"]]
    assert state["validation_current"] and not state["positive_current"]
    assert state["decision"].id == uuid.UUID(accepted["result"]["proof_id"])
    assert counts(db) == (2, 1, 0, 3, 3)
    accepted2 = execute(db, entry, request_for(db, entry, review="accepted", reason_note="Revalidated",
        supersedes_decision_id=accepted["result"]["proof_id"]))
    db.commit()
    assert accepted2["result"]["reversal_id"]
    assert counts(db) == (2, 2, 1, 4, 4)


@pytest.mark.parametrize("target", ["flagged", "rejected"])
def test_negative_hold_survives_edit_and_validation_and_requires_explicit_reversal(line_db, target):
    from app.api.projects import update_project_asset_line
    from app.modules.project_master_data.schemas import ProjectAssetLineUpdate
    db, entry = line_db
    decision = execute(db, entry, request_for(db, entry, review=target, reason_note="  Human impediment  "))
    db.commit()
    line = snapshot(db, entry).lines[0]
    update_project_asset_line(entry["project"].id, line.id,
        ProjectAssetLineUpdate(asset_name="Edited official value", row_version=line.row_version), db, entry["user"])
    execute(db, entry, request_for(db, entry))
    db.commit()
    assert snapshot(db, entry).line_proofs[line.id]["negative_hold"] == target
    assert provider(db, entry).result == "BLOCKED"
    execute(db, entry, request_for(db, entry, review="accepted", reason_note="Hold resolved",
                                 supersedes_decision_id=decision["result"]["proof_id"]))
    db.commit()
    assert snapshot(db, entry).line_proofs[line.id]["positive_current"]
    assert db.query(AssetLineHumanDecision).first().reason_note == "Human impediment"


def test_full_set_completion_requires_actual_proofs_and_caps_stage(line_db):
    from app.modules.project_master_data.application.case_state_projection import get_case_state_projection
    db, entry = line_db
    for line in snapshot(db, entry).lines:
        line.review_status, line.validation_status = "accepted", "valid"
    db.commit()
    assert provider(db, entry).result == "INCOMPLETE"
    ids = [line.id for line in snapshot(db, entry).lines]
    for line_id in ids:
        execute(db, entry, request_for(db, entry, line_id=line_id), line_id=line_id)
        db.commit()
        execute(db, entry, request_for(db, entry, review="accepted", line_id=line_id), line_id=line_id)
        db.commit()
    assert provider(db, entry).result == "COMPLETE"
    db.rollback()
    with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as reader:
        projection = get_case_state_projection(reader, actor=entry["user"], org_id=entry["org"].id,
                                              project_id=entry["project"].id)
        assert projection.current_stage == "ASSET_REVIEW"
        from app.modules.project_master_data.application.case_state_projection import CAPABILITY_REGISTRY_VERSION
        assert CAPABILITY_REGISTRY_VERSION == "global-case-state-v3-asset-review-line-decision-v1"
        assert projection.capabilities[4].provider_key == "asset_review_line_decision_v1"
        assert projection.next_action.kind == "NO_AUTHORIZED_DOWNSTREAM_ACTION"
        assert all(s.result == "NOT_AVAILABLE" for s in projection.stages[5:])


@pytest.mark.parametrize("kind", ["warning", "invalid", "obsolete_invalid"])
def test_business_outcomes_and_obsolete_invalid_are_unfinished_not_permanent_holds(line_db, kind):
    db, entry = line_db
    line = snapshot(db, entry).lines[0]
    if kind == "warning":
        line.description = "   "
    else:
        line.quantity = Decimal("0")
    db.commit()
    result = execute(db, entry, request_for(db, entry))
    db.commit()
    expected = "warning" if kind == "warning" else "invalid"
    assert result["result"]["validation_outcome"] == expected
    if kind == "obsolete_invalid":
        line.quantity = Decimal("1")
        db.commit()
    state = provider(db, entry)
    assert state.result == ("BLOCKED" if kind == "invalid" else "INCOMPLETE")
    assert state.next_action["semantic_route_key"] == ("asset_review_line_blocked" if kind == "invalid"
                                                      else "asset_review_line_validate_required")
    before = counts(db)
    with pytest.raises(HTTPException) as denied:
        execute(db, entry, request_for(db, entry, review="accepted"))
    assert denied.value.status_code == 409
    assert counts(db) == before


def add_issue(db, entry, *, target_id=None):
    rule = ValidationRule(rule_code=uuid.uuid4().hex, name="Independent blocking issue", category="test")
    db.add(rule)
    db.flush()
    issue = ValidationIssue(validation_rule_id=rule.id, target_type="ProjectAssetLine" if target_id else "Project",
        target_id=target_id or entry["project"].id, severity="blocking", status="open", issue_message="Blocking")
    db.add(issue)
    db.commit()
    return issue


@pytest.mark.parametrize("scope", ["project", "target", "other"])
def test_review_blocker_scope_and_project_truth(line_db, scope):
    db, entry = line_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    ids = [line.id for line in snapshot(db, entry).lines]
    other = next(i for i in ids if i != entry["line_id"])
    add_issue(db, entry, target_id=entry["line_id"] if scope == "target" else other if scope == "other" else None)
    if scope == "other":
        execute(db, entry, request_for(db, entry, review="accepted"))
        db.commit()
    else:
        with pytest.raises(HTTPException) as denied:
            execute(db, entry, request_for(db, entry, review="accepted"))
        assert denied.value.status_code == 409
        assert counts(db) == (1, 0, 0, 1, 1)
    assert provider(db, entry).result == "BLOCKED"


def test_replay_read_receipt_and_reuse_after_newer_authority_and_non_draft(line_db):
    db, entry = line_db
    req = request_for(db, entry)
    original = execute(db, entry, req)
    db.commit()
    assert execute(db, entry, req)["result"] == original["result"]
    assert counts(db) == (1, 0, 0, 1, 1)
    execute(db, entry, request_for(db, entry))
    db.commit()
    entry["project"].status = "in_progress"
    db.commit()
    replay = execute(db, entry, req)
    assert replay["replayed"] and replay["historical"]
    assert replay["result"] == original["result"]
    assert counts(db) == (2, 0, 0, 2, 2)
    db.rollback()
    with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as reader:
        no_writes = []
        event.listen(reader, "before_flush", lambda *args: no_writes.append(True))
        receipt = read_asset_review_receipt(reader, actor=entry["user"], org_id=entry["org"].id,
            project_id=entry["project"].id, line_id=entry["line_id"], command_id=uuid.UUID(req["command_id"]))
        assert receipt["historical"] and receipt["result"] == original["result"]
        assert not no_writes and not reader.new and not reader.dirty and not reader.deleted
    with pytest.raises(HTTPException) as denied:
        execute(db, entry, {**req, "expected_case_version": "0" * 64})
    assert denied.value.status_code == 409


@pytest.mark.parametrize("change,status", [("no_session", 404), ("inactive_user", 403),
    ("inactive_org", 403), ("no_permission", 403), ("nonhuman", 403),
    ("non_draft", 400), ("row", 409), ("case", 409), ("lineage", 409), ("cross_line", 404)])
def test_denials_have_zero_writes(line_db, change, status):
    db, entry = line_db
    req = request_for(db, entry)
    actor = None
    if change == "no_session":
        entry["session"].status = "closed"
    elif change == "inactive_user":
        entry["user"].status = "inactive"
    elif change == "inactive_org":
        entry["org"].status = "inactive"
    elif change == "no_permission":
        entry["role"].permissions = []
    elif change == "nonhuman":
        actor = SimpleNamespace(id=entry["user"].id, organization_id=entry["org"].id)
    elif change == "non_draft":
        entry["project"].status = "in_progress"
    elif change == "row":
        req["expected_row_version"] += 1
    elif change == "case":
        req["expected_case_version"] = "0" * 64
    elif change == "lineage":
        entry["project"].current_preliminary_import_batch_id = None
    db.commit()
    with pytest.raises(HTTPException) as denied:
        execute(db, entry, req, actor=actor, line_id=uuid.uuid4() if change == "cross_line" else None)
    assert denied.value.status_code == status
    db.rollback()
    assert counts(db) == (0, 0, 0, 0, 0)


def test_receipt_uuid_conflicts_across_actor_and_line(line_db):
    db, entry = line_db
    req = request_for(db, entry)
    execute(db, entry, req)
    db.commit()
    other_line = next(item.id for item in snapshot(db, entry).lines if item.id != entry["line_id"])
    with pytest.raises(HTTPException) as denied:
        execute(db, entry, req, line_id=other_line)
    assert denied.value.status_code == 409
    other = User(organization_id=entry["org"].id, email=uuid.uuid4().hex + "@example.test", full_name="Other")
    from app.modules.project_master_data.models import UserRole
    db.add(other)
    db.flush()
    db.add_all([UserRole(user_id=other.id, role_id=entry["role"].id),
                WorkbenchSession(project_id=entry["project"].id, user_id=other.id)])
    db.commit()
    with pytest.raises(HTTPException) as denied:
        execute(db, entry, req, actor=other)
    assert denied.value.status_code == 409
    assert counts(db) == (1, 0, 0, 1, 1)


def test_technical_audit_failure_rolls_back_all_effects(line_db, monkeypatch):
    import app.modules.project_master_data.application.asset_review_line_commands as service
    db, entry = line_db
    req = request_for(db, entry)
    def fail(*args, **kwargs):
        raise RuntimeError("Injected audit failure")
    monkeypatch.setattr(service, "log_audit_event", fail)
    with pytest.raises(RuntimeError):
        execute(db, entry, req)
    db.rollback()
    assert counts(db) == (0, 0, 0, 0, 0)
    assert snapshot(db, entry).lines[0].row_version == req["expected_row_version"]


def test_audit_is_safe_bounded_and_sanitizer_compatible(line_db):
    db, entry = line_db
    execute(db, entry, request_for(db, entry, review="flagged", reason_note="Private reason never audit"))
    db.commit()
    audit = db.query(AuditEvent).filter_by(event_name="ProjectAssetLineReviewDecided").one()
    assert "Private reason" not in str(audit.payload)
    assert "[REDACTED]" not in str(audit.payload)
    assert audit.payload["confirmed"] is True and audit.payload["reason_present"] is True
    assert len(audit.payload["official_input_sha256"]) == 64
    assert audit.payload["old_review_status"] == "pending"


@pytest.fixture
def line_client(line_db):
    db, entry = line_db
    def override_db():
        yield db
    def override_read():
        with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as reader:
            yield reader
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_case_state_db] = override_read
    app.dependency_overrides[get_current_user] = lambda: entry["user"]
    with TestClient(app) as client:
        yield client, db, entry
    for dep in (get_db, get_case_state_db, get_current_user):
        app.dependency_overrides.pop(dep, None)


@pytest.mark.parametrize("change", [{"confirm": False}, {"confirm": 1}, {"expected_row_version": True},
    {"expected_row_version": "1"}, {"expected_case_version": "A" * 64}, {"contract_version": "old"},
    {"command_id": "bad"}, {"validation_status": "valid"}, {"findings": []}])
def test_http_contract_denials_400_no_effects(line_client, change):
    client, db, entry = line_client
    req = request_for(db, entry)
    db.rollback()
    response = client.post(f'/api/v1/projects/{entry["project"].id}/asset-lines/{entry["line_id"]}/validate',
                           json={**req, **change})
    assert response.status_code == 400, response.text
    assert counts(db) == (0, 0, 0, 0, 0)


def test_http_commands_and_read_only_unknown_response_reconciliation(line_client):
    client, db, entry = line_client
    base = f'/api/v1/projects/{entry["project"].id}/asset-lines/{entry["line_id"]}'
    req = request_for(db, entry)
    db.rollback()
    response = client.post(base + "/validate", json=req)
    assert response.status_code == 200, response.text
    receipt = client.get(base + "/command-receipts/" + req["command_id"])
    assert receipt.status_code == 200, receipt.text
    assert receipt.json()["result"] == response.json()["result"]
    req = request_for(db, entry, review="accepted")
    db.rollback()
    response = client.post(base + "/review-decision", json=req)
    assert response.status_code == 200, response.text
    assert counts(db) == (1, 1, 0, 2, 2)


@pytest.mark.parametrize("number,scale,positive,valid", [
    ("0", 4, True, False), ("0.0001", 4, True, True), ("0.00001", 4, True, False),
    ("99999999999.9999", 4, True, True), ("100000000000", 4, True, False),
    ("9999999999999.99", 2, False, True), ("10000000000000", 2, False, False),
    ("-1", 2, False, False), ("NaN", 2, False, False), ("Infinity", 4, True, False),
    ("1.00000", 4, True, True), ("0", 2, False, True),
])
def test_exact_numeric_boundaries_without_rounding(number, scale, positive, valid):
    assert exact_numeric(Decimal(number), scale, positive=positive) is valid


def test_rules_are_closed_deterministic_and_optional_nulls_valid():
    line = SimpleNamespace(asset_name="Asset", quantity=Decimal("1"), description=None,
        appraised_unit_price=None, raw_price=None, unit_id=None, raw_price_currency_id=None,
        appraised_currency_id=None, brand_id=None, manufacturer_id=None)
    assert evaluate_rules(line, {}) == ("valid", [])
    line.asset_name, line.quantity, line.description = " ", Decimal("0"), " "
    line.raw_price, line.appraised_unit_price, line.unit_id = Decimal("-1"), Decimal("NaN"), uuid.uuid4()
    outcome, findings = evaluate_rules(line, {})
    assert outcome == "invalid"
    assert [f["code"] for f in findings] == ["asset_name_invalid", "quantity_invalid", "description_blank",
                                          "amount_invalid", "amount_invalid", "reference_invalid"]
    assert [f["field"] for f in findings if f["code"] == "amount_invalid"] == ["appraised_unit_price", "raw_price"]
    line.asset_name, line.quantity = "Asset", Decimal("1")
    line.raw_price, line.appraised_unit_price, line.unit_id = None, None, None
    line.description = " " * 5001
    outcome, findings = evaluate_rules(line, {})
    assert outcome == "invalid"
    assert [f["code"] for f in findings] == ["description_invalid", "description_blank"]


@pytest.mark.parametrize("writer", ["human_commit", "patch", "reference", "same_value", "same_human_value"])
def test_writers_invalidate_proofs_without_status_resets_or_extra_generations(line_db, writer):
    from app.api.projects import update_project_asset_line
    from app.modules.project_master_data.schemas import ProjectAssetLineUpdate
    from app.modules.project_master_data.commands.commit_asset_line_draft import execute_commit_asset_line_draft
    from app.modules.project_master_data.models import InlineEditDraft, Unit
    db, entry = line_db
    if writer == "reference":
        entry["line_id"] = next(line.id for line in snapshot(db, entry).lines if line.unit_id)
    execute(db, entry, request_for(db, entry))
    db.commit()
    execute(db, entry, request_for(db, entry, review="accepted"))
    db.commit()
    line = next(item for item in snapshot(db, entry).lines if item.id == entry["line_id"])
    token = snapshot(db, entry).case_version
    if writer in ("human_commit", "same_human_value"):
        db.add(InlineEditDraft(session_id=entry["session"].id, target_type="ProjectAssetLine", target_id=line.id,
            field_key="description", draft_value={"value": line.description if writer == "same_human_value"
                else "New description"}, base_row_version=line.row_version))
        db.commit()
        execute_commit_asset_line_draft(db, entry["user"], entry["project"].id, line.id,
                                       ["description"], True, str(line.row_version))
        db.commit()
    elif writer == "reference":
        db.get(Unit, line.unit_id).status = "inactive"
        db.commit()
    else:
        update_project_asset_line(entry["project"].id, line.id, ProjectAssetLineUpdate(
            asset_name=line.asset_name if writer == "same_value" else "New name", row_version=line.row_version),
            db, entry["user"])
    state = snapshot(db, entry)
    assert (state.case_version != token) is (writer != "same_value")
    assert state.line_proofs[line.id]["positive_current"] is (writer in ("same_value", "same_human_value"))
    assert state.line_proofs[line.id]["validation_current"] is (writer in ("same_value", "same_human_value"))
    assert line.review_status == "accepted" and line.validation_status == "valid"
    assert counts(db) == (1, 1, 0, 2, 2)


@pytest.mark.parametrize("kind", ["same_target", "wrong_prior", "missing_reason"])
def test_review_transition_denials_append_nothing(line_db, kind):
    db, entry = line_db
    old = execute(db, entry, request_for(db, entry, review="flagged", reason_note="Human hold"))
    db.commit()
    req = request_for(db, entry, review="flagged" if kind == "same_target" else "rejected",
        supersedes_decision_id=str(uuid.uuid4()) if kind == "wrong_prior" else old["result"]["proof_id"],
        **({} if kind == "missing_reason" else {"reason_note": "Changed human decision"}))
    with pytest.raises(HTTPException) as denied:
        execute(db, entry, req)
    assert denied.value.status_code == (400 if kind == "missing_reason" else 409)
    db.rollback()
    assert counts(db) == (0, 1, 0, 1, 1)


@pytest.mark.parametrize("change", [{"target_review_status": "pending"}, {"reason_note": " "},
    {"reason_note": "🙂" * 2001}, {"reason_note": 7}, {"validation_outcome": "valid"}])
def test_review_http_closed_contract_and_unicode_reason(line_client, change):
    client, db, entry = line_client
    req = request_for(db, entry, review="flagged", reason_note="Human hold")
    db.rollback()
    response = client.post(f'/api/v1/projects/{entry["project"].id}/asset-lines/{entry["line_id"]}/review-decision',
                           json={**req, **change})
    assert response.status_code == 400, response.text
    assert counts(db) == (0, 0, 0, 0, 0)


def test_exact_replay_rechecks_permission_and_session(line_db):
    db, entry = line_db
    req = request_for(db, entry)
    execute(db, entry, req)
    db.commit()
    entry["role"].permissions = []
    db.commit()
    with pytest.raises(HTTPException) as denied:
        execute(db, entry, req)
    assert denied.value.status_code == 403
    assert counts(db) == (1, 0, 0, 1, 1)
