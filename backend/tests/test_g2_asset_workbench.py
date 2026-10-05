"""A7 whole-set confirmation, currentness, API, access, recovery and atomic evidence."""
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.main import app
from app.core.rbac import get_current_user
from app.db import get_db
from app.db.session import get_case_state_db
from app.modules.project_master_data.application.asset_workbench_commands import (
    confirm_project_asset_workbench, withdraw_project_asset_workbench_confirmation, read_asset_workbench_receipt,
)
from app.modules.project_master_data.application.asset_workbench_provider import evaluate_asset_workbench_provider
from app.modules.project_master_data.application.asset_review_provider import _membership
from app.modules.project_master_data.application.case_state_projection import get_case_state_projection
from app.modules.project_master_data.models import (
    AssetWorkbenchCommandReceipt, ProjectAssetWorkbenchConfirmation, ProjectAssetWorkbenchWithdrawal,
    AuditEvent, InlineEditDraft, User, UserRole, WorkbenchSession, Project,
)
from app.modules.project_master_data.commands.commit_asset_line_draft import execute_commit_asset_line_draft
from tests.test_g2_line_decisions import (
    entry_db as _entry_db, line_db as _line_db, snapshot, execute as line_execute, request_for as line_request,
    add_issue,
)

entry_db, line_db = _entry_db, _line_db


def accept_all(db, entry):
    for line in snapshot(db, entry).lines:
        line_execute(db, entry, line_request(db, entry, line_id=line.id), line_id=line.id)
        db.commit()
        decision = snapshot(db, entry).line_proofs[line.id]["decision"]
        args = dict(reason_note="Refreshed proof", supersedes_decision_id=str(decision.id)) if decision else {}
        line_execute(db, entry, line_request(db, entry, review="accepted", line_id=line.id, **args), line_id=line.id)
        db.commit()


@pytest.fixture
def workbench_db(line_db):
    db, entry = line_db
    for line in snapshot(db, entry).lines:
        line.description = "Prepared synthetic asset " + str(line.id)
    db.commit()
    accept_all(db, entry)
    yield db, entry


def request_for(db, entry, *, withdraw=False, **changes):
    snap = snapshot(db, entry)
    latest = snap.workbench.latest
    request = dict(contract_version="asset-workbench-withdrawal-v1" if withdraw else "asset-workbench-confirmation-v1",
        command_id=str(uuid.uuid4()), confirm=True, expected_project_row_version=snap.project.row_version,
        expected_case_version=snap.case_version, expected_seal_id=str(snap.seal.id),
        expected_authoritative_set_sha256=snap.seal.authoritative_set_sha256,
        expected_membership_version=snap.seal.membership_version,
        expected_line_versions=[dict(line_id=str(line.id), row_version=line.row_version) for line in snap.lines],
        reason_note="Withdraw readiness" if withdraw else "Confirm refreshed set" if latest else None)
    request["expected_confirmation_id" if withdraw else "supersedes_confirmation_id"] = str(latest.id) if latest else None
    request.update(changes)
    return request


def execute(db, entry, request, *, actor=None):
    command = (withdraw_project_asset_workbench_confirmation if request["contract_version"] == "asset-workbench-withdrawal-v1"
               else confirm_project_asset_workbench)
    return command(db, actor=actor or db.merge(entry["user"]), org_id=entry["org"].id,
                   project_id=entry["project"].id, request=request)


def provider(db, entry, **kwargs):
    return evaluate_asset_workbench_provider(snapshot(db, entry),
        effective_permissions=kwargs.get("permissions", {"workbench:edit"}),
        has_active_session=kwargs.get("session", True), available=kwargs.get("available", True))


def counts(db):
    return tuple(db.query(m).count() for m in (ProjectAssetWorkbenchConfirmation,
        ProjectAssetWorkbenchWithdrawal, AssetWorkbenchCommandReceipt)) + (db.query(AuditEvent).filter(
            AuditEvent.event_name.in_(("ProjectAssetWorkbenchConfirmed", "ProjectAssetWorkbenchConfirmationWithdrawn"))).count(),)


def human_commit(db, entry, field, new_value):
    snap = snapshot(db, entry)
    line = next(line for line in snap.lines if line.id == entry["line_id"])
    draft = InlineEditDraft(session_id=entry["session"].id,
        target_type="ProjectAssetLine", target_id=line.id, field_key=field,
        draft_value={"value": new_value}, base_row_version=line.row_version)
    db.add(draft)
    db.commit()
    return line.row_version


def commit_saved(db, entry, field, version):
    return execute_commit_asset_line_draft(db, actor=db.merge(entry["user"]), project_id=entry["project"].id,
        line_id=entry["line_id"], field_keys=[field], confirm=True, version_token=str(version))


def test_confirmation_is_current_after_own_increment_and_holds_downstream(workbench_db):
    db, entry = workbench_db
    before = snapshot(db, entry)
    prices = [line.appraised_unit_price for line in before.lines]
    assert all(price is None for price in prices)
    assert provider(db, entry).result == "INCOMPLETE"
    req = request_for(db, entry)
    original = execute(db, entry, req)
    db.commit()
    after = snapshot(db, entry)
    assert after.project.row_version == req["expected_project_row_version"] + 1
    assert after.case_version != req["expected_case_version"] and after.workbench.content_current
    assert not original["historical"] and counts(db) == (1, 0, 1, 1)
    assert [line.row_version for line in after.lines] == [v["row_version"] for v in req["expected_line_versions"]]
    assert provider(db, entry).result == "COMPLETE"
    assert provider(db, entry).next_action == dict(kind="NO_AUTHORIZED_DOWNSTREAM_ACTION", stage=None,
        semantic_route_key=None, validation_issue_id=None, context=None)
    db.rollback()
    with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as reader:
        projection = get_case_state_projection(reader, actor=entry["user"], org_id=entry["org"].id,
                                              project_id=entry["project"].id)
        assert projection.current_stage == "ASSET_WORKBENCH"
        assert all(stage.result == "NOT_AVAILABLE" for stage in projection.stages[6:])
        assert projection.next_action.kind == "NO_AUTHORIZED_DOWNSTREAM_ACTION"
    replay = execute(db, entry, req)
    db.commit()
    assert replay["replayed"] and replay["result"] == original["result"] and not replay["historical"]
    assert counts(db) == (1, 0, 1, 1)
    with pytest.raises(HTTPException) as denied:
        execute(db, entry, request_for(db, entry))
    assert denied.value.status_code == 409


def test_withdraw_reconfirm_append_history_and_no_value_reset(workbench_db):
    db, entry = workbench_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    before = [(line.id, line.row_version, line.description, line.review_status) for line in snapshot(db, entry).lines]
    req = request_for(db, entry, withdraw=True, reason_note="  Human withdrawal  ")
    original = execute(db, entry, req)
    db.commit()
    assert provider(db, entry).result == "INCOMPLETE" and not snapshot(db, entry).workbench.content_current
    assert before == [(line.id, line.row_version, line.description, line.review_status) for line in snapshot(db, entry).lines]
    assert execute(db, entry, req)["result"] == original["result"]
    db.commit()
    assert counts(db) == (1, 1, 2, 2)
    with pytest.raises(HTTPException) as denied:
        execute(db, entry, request_for(db, entry, withdraw=True))
    assert denied.value.status_code == 409
    db.rollback()
    execute(db, entry, request_for(db, entry))
    db.commit()
    assert counts(db) == (2, 1, 3, 3) and provider(db, entry).result == "COMPLETE"
    latest = snapshot(db, entry).workbench.latest
    assert latest.prior_reversal_id == uuid.UUID(original["result"]["reversal_id"])


@pytest.mark.parametrize("field,new_value", [("description", "Updated official description"), ("appraised_unit_price", "42.50")])
def test_human_commit_invalidates_confirmation_then_explicit_proofs_and_reconfirmation(workbench_db, field, new_value):
    db, entry = workbench_db
    req = request_for(db, entry)
    execute(db, entry, req)
    db.commit()
    version = human_commit(db, entry, field, new_value)
    assert provider(db, entry).result == "COMPLETE"  # draft alone has no authority
    commit_saved(db, entry, field, version)
    db.commit()
    assert provider(db, entry).result == "STALE"
    assert execute(db, entry, req)["historical"]
    db.rollback()
    accept_all(db, entry)
    assert provider(db, entry).result == "STALE"
    execute(db, entry, request_for(db, entry))
    db.commit()
    assert provider(db, entry).result == "COMPLETE"


@pytest.mark.parametrize("change", ["same_value", "row_version", "warning", "status", "session", "draft"])
def test_noncontent_changes_do_not_erase_complete(workbench_db, change):
    db, entry = workbench_db
    req = request_for(db, entry)
    execute(db, entry, req)
    db.commit()
    before = snapshot(db, entry).case_version
    if change == "same_value":
        line = next(line for line in snapshot(db, entry).lines if line.id == entry["line_id"])
        version = human_commit(db, entry, "description", line.description)
        commit_saved(db, entry, "description", version)
    elif change == "row_version":
        snapshot(db, entry).project.row_version += 1
    elif change == "warning":
        issue = add_issue(db, entry)
        issue.severity = "warning"
    elif change == "status":
        snapshot(db, entry).project.status = "archived"
    elif change == "session":
        db.get(WorkbenchSession, entry["session"].id).status = "closed"
    elif change == "draft":
        human_commit(db, entry, "description", "Uncommitted draft")
    db.commit()
    assert provider(db, entry, permissions=set(), session=False).result == "COMPLETE"
    if change not in ("session", "draft"):
        assert snapshot(db, entry).case_version != before
    if change == "status":
        assert execute(db, entry, req)["replayed"]
        with pytest.raises(HTTPException) as denied:
            execute(db, entry, request_for(db, entry, withdraw=True))
        assert denied.value.status_code == 400


@pytest.mark.parametrize("description", [None, "", " \t\n", "x" * 5001])
def test_description_mandatory_only_for_workbench(line_db, description):
    db, entry = line_db
    for line in snapshot(db, entry).lines:
        line.description = description
    db.commit()
    if description is None:
        accept_all(db, entry)
        assert provider(db, entry).next_action["context"]["reason_code"] == "description_required"
        assert provider(db, entry).next_action["context"]["line_id"] == str(_membership(snapshot(db, entry))[1][0].id)
    assert provider(db, entry).result != "COMPLETE"
    with pytest.raises(HTTPException) as denied:
        execute(db, entry, request_for(db, entry))
    assert denied.value.status_code == 409 and counts(db) == (0, 0, 0, 0)


@pytest.mark.parametrize("mutation,result", [("patch", "STALE"), ("validation", "STALE"), ("review", "BLOCKED"),
    ("reference", "STALE"), ("rule", "STALE"), ("preparation", "STALE"), ("blocker", "BLOCKED"),
    ("seal", "STALE"), ("membership", "BLOCKED")])
def test_existing_writers_and_contract_changes_cannot_leave_obsolete_complete(workbench_db, monkeypatch, mutation, result):
    from app.api.projects import update_project_asset_line
    from app.modules.project_master_data.schemas import ProjectAssetLineUpdate
    from app.modules.project_master_data.models import Unit, ProjectAssetLine
    import app.modules.project_master_data.application.asset_line_proofs as proofs
    import app.modules.project_master_data.application.asset_workbench_authority as authority
    db, entry = workbench_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    snap = snapshot(db, entry)
    line = next(line for line in snap.lines if line.id == entry["line_id"])
    if mutation == "patch":
        update_project_asset_line(entry["project"].id, line.id, ProjectAssetLineUpdate(asset_name="Changed name",
            row_version=line.row_version), db, entry["user"])
    elif mutation == "validation":
        line_execute(db, entry, line_request(db, entry))
    elif mutation == "review":
        decision = snap.line_proofs[line.id]["decision"]
        line_execute(db, entry, line_request(db, entry, review="flagged", reason_note="Human hold",
                     supersedes_decision_id=str(decision.id)))
    elif mutation == "reference":
        db.get(Unit, line.unit_id).status = "inactive"
    elif mutation == "rule":
        monkeypatch.setattr(proofs, "rule_digest", lambda: "0" * 64)
    elif mutation == "preparation":
        monkeypatch.setattr(authority, "preparation_digest", lambda: "0" * 64)
    elif mutation == "blocker":
        add_issue(db, entry)
    elif mutation == "seal":
        schema = db.get_bind().get_execution_options()["schema_translate_map"][None]
        db.execute(text(f'UPDATE "{schema}".project_asset_review_seals SET entry_lineage_sha256=:digest'), {"digest": "0" * 64})
    elif mutation == "membership":
        db.add(ProjectAssetLine(project_id=entry["project"].id, asset_name="Unauthorized extra"))
    db.commit()
    assert provider(db, entry).result == result
    assert counts(db) == (1, 0, 1, 1)


def test_withdrawal_of_stale_attestation_does_not_clear_upstream_impediment(workbench_db):
    db, entry = workbench_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    version = human_commit(db, entry, "description", "Changed official description")
    commit_saved(db, entry, "description", version)
    db.commit()
    assert provider(db, entry).result == "STALE"
    execute(db, entry, request_for(db, entry, withdraw=True))
    db.commit()
    assert provider(db, entry).result == "INCOMPLETE"
    assert provider(db, entry).next_action["stage"] == "ASSET_REVIEW"


@pytest.mark.parametrize("change,status", [("inactive_user", 403), ("inactive_org", 403), ("permission", 403),
    ("session", 404), ("nonhuman", 403), ("tenant", 404), ("draft", 400), ("cas", 409), ("partial", 409),
    ("extra_member", 409), ("seal", 409), ("line_version", 409), ("set_digest", 409), ("membership_version", 409)])
def test_access_and_exact_full_set_denials_leave_no_effects(workbench_db, change, status):
    from types import SimpleNamespace
    db, entry = workbench_db
    req, actor = request_for(db, entry), entry["user"]
    if change == "inactive_user":
        actor.status = "inactive"
    elif change == "inactive_org":
        entry["org"].status = "inactive"
    elif change == "permission":
        entry["role"].permissions = ["project:read"]
    elif change == "session":
        entry["session"].status = "closed"
    elif change == "nonhuman":
        actor = SimpleNamespace(id=actor.id, organization_id=actor.organization_id)
    elif change == "tenant":
        entry = {**entry, "project": type("Target", (), {"id": uuid.uuid4()})()}
    elif change == "draft":
        snapshot(db, entry).project.status = "archived"
    elif change == "cas":
        req["expected_case_version"] = "0" * 64
    elif change == "partial":
        req["expected_line_versions"].pop()
    elif change == "extra_member":
        req["expected_line_versions"].append(dict(line_id=str(uuid.uuid4()), row_version=1))
    elif change == "seal":
        req["expected_seal_id"] = str(uuid.uuid4())
    elif change == "line_version":
        req["expected_line_versions"][0]["row_version"] += 1
    elif change == "set_digest":
        req["expected_authoritative_set_sha256"] = "0" * 64
    elif change == "membership_version":
        req["expected_membership_version"] += 1
    db.commit()
    with pytest.raises(HTTPException) as denied:
        execute(db, entry, req, actor=actor)
    assert denied.value.status_code == status
    db.rollback()
    assert counts(db) == (0, 0, 0, 0)


@pytest.mark.parametrize("withdraw", [False, True])
def test_audit_failure_rolls_back_business_receipt_and_version(workbench_db, monkeypatch, withdraw):
    import app.modules.project_master_data.application.asset_workbench_commands as commands
    db, entry = workbench_db
    if withdraw:
        execute(db, entry, request_for(db, entry))
        db.commit()
    before = counts(db)
    req = request_for(db, entry, withdraw=withdraw)
    def fail(*args, **kwargs):
        raise RuntimeError("Injected atomic audit failure")
    monkeypatch.setattr(commands, "log_audit_event", fail)
    with pytest.raises(RuntimeError):
        execute(db, entry, req)
    db.rollback()
    assert counts(db) == before
    assert snapshot(db, entry).project.row_version == req["expected_project_row_version"]


def test_receipt_reconciliation_is_snapshot_read_only_and_audit_contains_no_content(workbench_db):
    db, entry = workbench_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    req = request_for(db, entry, withdraw=True, reason_note="Private reason never audit")
    original = execute(db, entry, req)
    db.commit()
    audit = db.query(AuditEvent).filter_by(event_name="ProjectAssetWorkbenchConfirmationWithdrawn").one()
    assert not any(value in str(audit.payload) for value in ("Private reason", "Prepared synthetic", "[REDACTED]", "expected_line_versions"))
    sql = []
    db.rollback()
    with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as reader:
        conn = reader.connection()
        def observe(connection, cursor, statement, parameters, context, many):
            sql.append(statement.lower())
        event.listen(conn, "after_cursor_execute", observe)
        recovered = read_asset_workbench_receipt(reader, actor=entry["user"], org_id=entry["org"].id,
            project_id=entry["project"].id, command_id=uuid.UUID(req["command_id"]))
        assert recovered["result"] == original["result"]
    assert not any("for update" in q or "for share" in q or q.lstrip().startswith(("update ", "insert ", "delete ")) for q in sql)
    assert counts(db) == (1, 1, 2, 2)


@pytest.mark.parametrize("corruption", ["receipt", "audit", "confirmation", "reversal"])
def test_unprovable_linkage_fails_closed(workbench_db, corruption):
    db, entry = workbench_db
    req = request_for(db, entry)
    execute(db, entry, req)
    db.commit()
    if corruption == "reversal":
        execute(db, entry, request_for(db, entry, withdraw=True))
        db.commit()
    schema = db.get_bind().get_execution_options()["schema_translate_map"][None]
    table, field, value_ = {
        "receipt": ("asset_workbench_command_receipts", "response_metadata", "{}"),
        "audit": ("audit_events", "payload", "{}"),
        "confirmation": ("project_asset_workbench_confirmations", "content_binding", "{}"),
        "reversal": ("project_asset_workbench_withdrawals", "content_binding", "{}"),
    }[corruption]
    if corruption == "audit":
        db.execute(text(f'UPDATE "{schema}".{table} SET {field}=CAST(:value AS json) WHERE event_name LIKE \'ProjectAssetWorkbench%\''), {"value": value_})
    else:
        db.execute(text(f'UPDATE "{schema}".{table} SET {field}=CAST(:value AS jsonb)'), {"value": value_})
    db.commit()
    assert provider(db, entry).result == "STALE"
    with pytest.raises(HTTPException) as denied:
        execute(db, entry, req)
    assert denied.value.status_code == 409


def test_uuid_reuse_scope_actor_and_fresh_replay_access(workbench_db):
    db, entry = workbench_db
    req = request_for(db, entry)
    execute(db, entry, req)
    db.commit()
    actor = User(organization_id=entry["org"].id, email=uuid.uuid4().hex + "@example.test", full_name="Other human")
    other = Project(organization_id=entry["org"].id, code=uuid.uuid4().hex, name="Other", created_by=entry["user"].id)
    db.add_all([actor, other])
    db.flush()
    db.add_all([UserRole(user_id=actor.id, role_id=entry["role"].id),
        WorkbenchSession(project_id=entry["project"].id, user_id=actor.id),
        WorkbenchSession(project_id=other.id, user_id=entry["user"].id)])
    db.commit()
    for scope, caller, payload in [(entry, actor, req), ({**entry, "project": other}, entry["user"], req),
                                    (entry, entry["user"], {**req, "expected_case_version": "0" * 64})]:
        with pytest.raises(HTTPException) as denied:
            execute(db, scope, payload, actor=caller)
        assert denied.value.status_code == 409
        db.rollback()
    entry["role"].permissions = ["project:read"]
    db.commit()
    with pytest.raises(HTTPException) as denied:
        execute(db, entry, req)
    assert denied.value.status_code == 403 and counts(db) == (1, 0, 1, 1)


def test_typed_api_strict_contracts_sanitized_errors_and_receipt(workbench_db):
    db, entry = workbench_db
    def override_db():
        yield db
    def override_read():
        with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as reader:
            yield reader
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_case_state_db] = override_read
    app.dependency_overrides[get_current_user] = lambda: entry["user"]
    try:
        with TestClient(app) as client:
            path = f'/api/v1/projects/{entry["project"].id}/asset-workbench'
            req = request_for(db, entry)
            bad = [{**req, "confirm": v} for v in (False, 1, "true")]
            bad += [{**req, "expected_project_row_version": "1"}, {**req, "reason_note": "Not first"},
                {**req, "extra": "Private contents"}, {**req, "expected_line_versions": req["expected_line_versions"] * 2},
                {**req, "expected_line_versions": [{**req["expected_line_versions"][0], "row_version": True}]}]
            for body in bad:
                response = client.post(path + "/confirm", json=body)
                assert response.status_code == 400 and "Private contents" not in response.text
            response = client.post(path + "/confirm", json=req)
            assert response.status_code == 200, response.text
            recovered = client.get(path + "/command-receipts/" + req["command_id"])
            assert recovered.status_code == 200 and recovered.json()["result"] == response.json()["result"]
            withdraw = request_for(db, entry, withdraw=True)
            assert client.post(path + "/withdraw", json={**withdraw, "reason_note": " "}).status_code == 400
            assert client.post(path + "/withdraw", json=withdraw).status_code == 200
            assert counts(db) == (1, 1, 2, 2)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_case_state_db, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_unknown_outer_commit_reconciles_committed_receipt_without_retry(workbench_db, monkeypatch):
    from app.api.asset_workbench import _mutate
    db, entry = workbench_db
    req = request_for(db, entry)
    commit = db.commit
    def lose_acknowledgment():
        commit()
        raise RuntimeError("Synthetic lost commit acknowledgment")
    monkeypatch.setattr(db, "commit", lose_acknowledgment)
    with pytest.raises(HTTPException) as failed:
        _mutate(confirm_project_asset_workbench, db, entry["user"], entry["project"].id, req)
    assert failed.value.status_code == 500 and "reconcile" in failed.value.detail
    monkeypatch.setattr(db, "commit", commit)
    assert counts(db) == (1, 0, 1, 1)
    db.rollback()
    with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as reader:
        recovered = read_asset_workbench_receipt(reader, actor=entry["user"], org_id=entry["org"].id,
            project_id=entry["project"].id, command_id=uuid.UUID(req["command_id"]))
        projection = get_case_state_projection(reader, actor=entry["user"], org_id=entry["org"].id,
                                              project_id=entry["project"].id)
        assert not recovered["historical"] and projection.stages[5].result == "COMPLETE"
        assert recovered["current_case_version"] == projection.case_version
    assert counts(db) == (1, 0, 1, 1)


def test_stage_truth_is_account_independent_and_action_context_is_bounded(workbench_db):
    from app.modules.project_master_data.schemas import CaseStateNextActionResponse
    db, entry = workbench_db
    result = provider(db, entry)
    assert result.result == "INCOMPLETE" and result.next_action["kind"] == "PENDING"
    context = result.next_action["context"]
    assert context["reason_code"] == "confirmation_required"
    assert not any(key in context for key in ("description", "appraised_unit_price", "reason_note", "expected_line_versions"))
    CaseStateNextActionResponse.model_validate(result.next_action)
    assert provider(db, entry, permissions=set()).result == "INCOMPLETE"
    assert provider(db, entry, permissions=set()).next_action["semantic_route_key"] is None
    assert provider(db, entry, session=False).next_action["semantic_route_key"] is None
    assert provider(db, entry, available=False).result == "NOT_AVAILABLE"


def test_blocker_resolution_restores_bound_completion_without_reconfirmation(workbench_db):
    from app.api.workflow import update_validation_issue
    from app.modules.project_master_data.workflow_schemas import ValidationIssueUpdate
    db, entry = workbench_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    issue = add_issue(db, entry)
    db.commit()
    assert provider(db, entry).result == "BLOCKED"
    update_validation_issue(issue.id, ValidationIssueUpdate(status="resolved", expected_row_version=issue.row_version),
                            db, entry["user"])
    db.commit()
    assert provider(db, entry).result == "COMPLETE" and counts(db) == (1, 0, 1, 1)


def test_real_foreign_tenant_and_unowned_session_cannot_disclose_or_mutate(workbench_db):
    from app.modules.project_master_data.models import OrganizationProfile
    db, entry = workbench_db
    req = request_for(db, entry)
    original = execute(db, entry, req)
    db.commit()
    other_org = OrganizationProfile(legal_name="Foreign synthetic tenant", organization_slug=uuid.uuid4().hex)
    db.add(other_org)
    db.flush()
    foreign = User(organization_id=other_org.id, email="foreign@example.test", full_name="Foreign human")
    colleague = User(organization_id=entry["org"].id, email="colleague@example.test", full_name="Colleague")
    db.add_all([foreign, colleague])
    db.flush()
    db.add(UserRole(user_id=colleague.id, role_id=entry["role"].id))
    db.commit()
    withdraw = request_for(db, entry, withdraw=True)
    before_version = snapshot(db, entry).project.row_version
    for actor, org_id in ((foreign, other_org.id), (colleague, entry["org"].id)):
        for command, payload in ((confirm_project_asset_workbench, req), (withdraw_project_asset_workbench_confirmation, withdraw)):
            with pytest.raises(HTTPException) as denied:
                command(db, actor=actor, org_id=org_id, project_id=entry["project"].id, request=payload)
            assert denied.value.status_code == 404
            db.rollback()
        with pytest.raises(HTTPException) as denied:
            with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as reader:
                read_asset_workbench_receipt(reader, actor=actor, org_id=org_id, project_id=entry["project"].id,
                                            command_id=uuid.UUID(req["command_id"]))
        assert denied.value.status_code == 404 and str(original["result"]["confirmation_id"]) not in str(denied.value.detail)
        db.rollback()
    assert counts(db) == (1, 0, 1, 1) and snapshot(db, entry).project.row_version == before_version


def test_canonically_equal_price_and_pending_read_draft_do_not_mutate_truth(workbench_db):
    db, entry = workbench_db
    version = human_commit(db, entry, "appraised_unit_price", "42.50")
    commit_saved(db, entry, "appraised_unit_price", version)
    db.commit()
    accept_all(db, entry)
    req = request_for(db, entry)
    execute(db, entry, req)
    db.commit()
    version = human_commit(db, entry, "appraised_unit_price", "42.5")
    commit_saved(db, entry, "appraised_unit_price", version)
    db.commit()
    assert provider(db, entry).result == "COMPLETE"
    db.rollback()
    statements = []
    with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as reader:
        draft = InlineEditDraft(session_id=entry["session"].id, target_type="ProjectAssetLine",
            target_id=entry["line_id"], field_key="description", draft_value={"value": "Unflushed draft"}, base_row_version=version)
        reader.add(draft)
        conn = reader.connection()
        def observe(connection, cursor, statement, parameters, context, many):
            statements.append(statement.lower())
        event.listen(conn, "before_cursor_execute", observe)
        try:
            recovered = read_asset_workbench_receipt(reader, actor=entry["user"], org_id=entry["org"].id,
                project_id=entry["project"].id, command_id=uuid.UUID(req["command_id"]))
            assert not recovered["historical"] and draft in reader.new
        finally:
            event.remove(conn, "before_cursor_execute", observe)
    assert not any(q.lstrip().startswith(("update ", "insert ", "delete ")) or "for update" in q or "for share" in q for q in statements)
    assert counts(db) == (1, 0, 1, 1)
