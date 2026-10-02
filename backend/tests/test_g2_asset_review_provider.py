"""Pure provider checks over the shared, already scoped authority snapshot."""

from __future__ import annotations

import copy
import uuid
from types import SimpleNamespace as Fact

import pytest
from pydantic import ValidationError

from app.modules.project_master_data.schemas import (
    CaseStateNextActionResponse, CaseStateStageResponse,
)
from app.modules.project_master_data.application.asset_review_authority import membership_digest
from tests.test_g2_authority import entry_db as _g2_entry_db


entry_db = _g2_entry_db


def _snapshot(*, status="ready_for_review", sealed=False):
    org, project_id, batch_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    rows = [Fact(id=uuid.UUID(int=n + 10), source_row_number=n + 2, validation_status="valid")
            for n in range(2)]
    lines = [Fact(id=uuid.UUID(int=n + 30), project_id=project_id,
                  source_import_batch_id=batch_id, source_staging_row_id=row.id,
                  row_version=1, review_status="pending", validation_status="unvalidated",
                  appraised_unit_price=None)
             for n, row in enumerate(rows)] if sealed else []
    seal = Fact(
        id=uuid.uuid4(), import_batch_id=batch_id, membership_version=1,
        correspondence=[{"staging_row_id": str(row.id), "source_row_number": row.source_row_number,
                         "line_id": str(line.id)} for row, line in zip(rows, lines)],
    ) if sealed else None
    if seal is not None:
        seal.authoritative_set_sha256 = membership_digest(seal.correspondence)
    return Fact(
        case_version="a" * 64,
        project=Fact(id=project_id, organization_id=org, status="draft"),
        prefix=[], batch=Fact(id=batch_id, status="applied" if sealed else status,
                              total_rows=2, valid_rows=2, invalid_rows=0, warning_rows=0),
        source=Fact(id=uuid.uuid4()), result=Fact(id=uuid.uuid4()), intake=Fact(id=uuid.uuid4()),
        analysis=Fact(line_manifest=[{"source_row_number": row.source_row_number} for row in rows]),
        usage=Fact(id=uuid.uuid4(), materialized_asset_row_count=2), slot=Fact(),
        rows=rows, lines=lines, seal=seal, lineage_current=True,
        seal_current=sealed, stale=[], entry_manifest={},
    )


def _evaluate(snapshot, **options):
    from app.modules.project_master_data.application.asset_review_provider import (
        evaluate_asset_review_provider,
    )
    return evaluate_asset_review_provider(
        snapshot, effective_permissions=options.pop(
            "effective_permissions", {"workbench:edit", "project:update"}),
        has_active_session=options.pop("has_active_session", True),
        **options,
    )


def _issue(snapshot, *, number=99, severity="blocking", status="open", target_type="Project"):
    return Fact(id=uuid.UUID(int=number),
                target_type=target_type, target_id=snapshot.project.id,
                severity=severity, status=status, row_version=2)


@pytest.mark.parametrize("available,intake,reason", [
    (False, True, "provider_unwired"),
    (True, False, "official_intake_prerequisite"),
])
def test_availability_precedes_blockers(available, intake, reason):
    snapshot = _snapshot()
    snapshot.issues = [_issue(snapshot)]
    if not intake:
        snapshot.intake = None
    result = _evaluate(snapshot, available=available)
    assert result.result == "NOT_AVAILABLE"
    assert result.availability_reason == reason
    assert result.next_action["semantic_route_key"] is None


@pytest.mark.parametrize("status,key,reason", [
    ("parsed", "asset_import_validate_pending", "validation_required"),
    ("validation_failed", "asset_import_validate_pending", "validation_retry"),
    ("ready_for_review", "asset_import_apply_confirm", "apply_required"),
])
def test_valid_entry_actions_are_typed_and_do_not_change_snapshot(status, key, reason):
    snapshot = _snapshot(status=status)
    snapshot.issues = []
    snapshot.rows[0].validation_status = "pending" if status != "ready_for_review" else "valid"
    before = copy.deepcopy(snapshot)
    result = _evaluate(snapshot)
    assert result.result == "INCOMPLETE"
    assert result.next_action["semantic_route_key"] == key
    assert result.next_action["context"]["reason_code"] == reason
    action = CaseStateNextActionResponse.model_validate(result.next_action)
    assert action.context.project_id == snapshot.project.id
    assert action.context.case_version == snapshot.case_version
    assert vars(snapshot) == vars(before)
    if status == "ready_for_review":
        assert action.context.confirmation_required is True
        assert action.context.contract_version == "s12-post-intake-guarded-apply-v2"


def test_blocker_precedes_stale_and_lowest_issue_id_wins():
    snapshot = _snapshot()
    snapshot.issues = [_issue(snapshot, number=99), _issue(snapshot, number=9)]
    snapshot.lineage_current = False
    snapshot.stale = ["selection_mismatch", "lineage_mismatch"]
    result = _evaluate(snapshot)
    assert result.result == "BLOCKED"
    assert result.next_action["validation_issue_id"] == str(uuid.UUID(int=9))
    assert result.next_action["context"]["kind"] == "issue"
    assert {item["reason_code"] for item in result.stale} == {
        "lineage_mismatch", "selection_mismatch",
    }
    CaseStateNextActionResponse.model_validate(result.next_action)


@pytest.mark.parametrize("severity,status,target_type", [
    ("warning", "open", "Project"),
    ("blocking", "resolved", "project"),
    ("blocking", "ignored", "Project"),
    ("blocking", "open", "unsupported"),
])
def test_warning_closed_and_unknown_issue_targets_do_not_block(severity, status, target_type):
    snapshot = _snapshot()
    snapshot.issues = [_issue(snapshot, severity=severity, status=status, target_type=target_type)]
    assert _evaluate(snapshot).result == "INCOMPLETE"


@pytest.mark.parametrize("status", ["pending", "invalid", "warning"])
def test_ready_rows_block_but_unproved_selection_does_not(status):
    snapshot = _snapshot()
    snapshot.issues = []
    snapshot.rows[0].validation_status = status
    result = _evaluate(snapshot)
    assert result.result == "BLOCKED"
    assert result.next_action["context"]["reason_code"] == "rows_not_ready"
    snapshot.lineage_current = False
    snapshot.stale = ["selection_mismatch"]
    assert _evaluate(snapshot).result == "STALE"


def test_counter_conflict_is_blocked():
    snapshot = _snapshot()
    snapshot.issues = []
    snapshot.batch.total_rows = 3
    result = _evaluate(snapshot)
    assert result.result == "BLOCKED"
    assert result.next_action["context"]["reason_code"] == "counter_conflict"


def test_known_empty_selection_blocks_and_missing_selected_row_is_stale():
    snapshot = _snapshot()
    snapshot.issues = []
    snapshot.rows = []
    snapshot.lineage_current = False
    snapshot.stale = ["selection_mismatch"]
    assert _evaluate(snapshot).result == "STALE"
    snapshot.analysis.line_manifest = []
    result = _evaluate(snapshot)
    assert result.result == "BLOCKED"
    assert result.next_action["context"]["reason_code"] == "empty_selection"


@pytest.mark.parametrize("mutation", ["extra", "missing", "unlinked", "replaced"])
def test_membership_divergence_blocks_even_with_stale_lineage(mutation):
    snapshot = _snapshot(sealed=True)
    snapshot.issues = []
    if mutation == "extra":
        snapshot.lines.append(Fact(id=uuid.uuid4(), project_id=snapshot.project.id,
                                  source_import_batch_id=None, source_staging_row_id=None))
    elif mutation == "missing":
        snapshot.lines.pop()
    elif mutation == "unlinked":
        snapshot.lines[0].source_staging_row_id = None
    else:
        snapshot.lines[0].id = uuid.uuid4()
    snapshot.seal_current = False
    snapshot.lineage_current = False
    snapshot.stale = ["lineage_mismatch", "seal_mismatch"]
    result = _evaluate(snapshot)
    assert result.result == "BLOCKED"
    assert result.next_action["context"]["reason_code"] == "membership_conflict"
    assert result.stale


def test_preexisting_manual_line_blocks_and_historical_linked_apply_is_stale():
    snapshot = _snapshot(sealed=True)
    snapshot.issues = []
    snapshot.seal = None
    snapshot.seal_current = False
    snapshot.stale = ["seal_mismatch"]
    assert _evaluate(snapshot).result == "STALE"
    snapshot.batch.status = "ready_for_review"
    result = _evaluate(snapshot)
    assert result.result == "BLOCKED"
    assert result.next_action["context"]["reason_code"] == "manual_line_conflict"


def test_full_set_stored_strings_never_complete_without_proofs():
    snapshot = _snapshot(sealed=True)
    snapshot.issues = [_issue(snapshot, severity="warning")]
    for line in snapshot.lines:
        line.review_status = "accepted"
        line.validation_status = "valid"
    result = _evaluate(snapshot)
    assert result.result == "INCOMPLETE"
    assert result.next_action["semantic_route_key"] == "asset_review_line_validate_required"
    snapshot.lines[1].validation_status = "unvalidated"
    assert _evaluate(snapshot).result == "INCOMPLETE"


def test_first_line_uses_initial_staging_order_instead_of_query_order():
    snapshot = _snapshot(sealed=True)
    snapshot.issues = []
    snapshot.lines.reverse()
    result = _evaluate(snapshot)
    assert result.next_action["context"]["line_id"] == str(uuid.UUID(int=30))
    assert result.next_action["semantic_route_key"] == "asset_review_line_validate_required"
    CaseStateNextActionResponse.model_validate(result.next_action)


@pytest.mark.parametrize("review,validation,reason", [
    ("flagged", "unvalidated", "review_flagged"),
    ("rejected", "unvalidated", "review_rejected"),
    ("pending", "invalid", "validation_invalid"),
])
def test_negative_member_blocks_before_stale(review, validation, reason):
    snapshot = _snapshot(sealed=True)
    snapshot.issues = []
    snapshot.lines[0].review_status = review
    snapshot.lines[0].validation_status = validation
    snapshot.lineage_current = False
    snapshot.seal_current = False
    snapshot.stale = ["lineage_mismatch"]
    result = _evaluate(snapshot)
    assert result.result == ("STALE" if validation == "invalid" else "BLOCKED")
    assert result.next_action["semantic_route_key"] == (
        "asset_review_stale_recovery" if validation == "invalid" else "asset_review_line_blocked")
    assert result.next_action["context"]["reason_code"] == (
        "lineage_mismatch" if validation == "invalid" else reason)


@pytest.mark.parametrize("sealed", [False, True])
def test_non_draft_unfinished_work_blocks_but_complete_set_remains_complete(sealed):
    snapshot = _snapshot(sealed=sealed)
    snapshot.issues = []
    snapshot.project.status = "in_progress"
    result = _evaluate(snapshot)
    assert result.result == "BLOCKED"
    assert result.next_action["context"]["reason_code"] == "project_not_draft"
    if sealed:
        for line in snapshot.lines:
            line.review_status, line.validation_status = "accepted", "valid"
        assert _evaluate(snapshot).result == "BLOCKED"


@pytest.mark.parametrize("sealed", [False, True])
def test_permission_changes_action_but_not_stage_truth(sealed):
    snapshot = _snapshot(sealed=sealed)
    snapshot.issues = []
    result = _evaluate(snapshot, effective_permissions={"project:read"})
    assert result.result == _evaluate(snapshot).result == "INCOMPLETE"
    assert result.next_action["kind"] == "UNAVAILABLE"
    assert result.next_action["semantic_route_key"] is None
    assert result.next_action["context"] == {
        "kind": "permission", "project_id": str(snapshot.project.id),
        "case_version": snapshot.case_version, "reason_code": "permission_required",
    }
    CaseStateNextActionResponse.model_validate(result.next_action)


def test_line_review_uses_existing_workbench_commit_permission():
    snapshot = _snapshot(sealed=True)
    snapshot.issues = []
    assert _evaluate(snapshot, effective_permissions={"project:update"}).next_action[
        "kind"] == "UNAVAILABLE"
    assert _evaluate(snapshot, effective_permissions={"workbench:edit"}).next_action[
        "semantic_route_key"] == "asset_review_line_validate_required"
    snapshot = _snapshot()
    snapshot.issues = []
    assert _evaluate(snapshot, effective_permissions={"project:update"}).next_action[
        "kind"] == "UNAVAILABLE"
    assert _evaluate(snapshot, effective_permissions={"workbench:edit"}).next_action[
        "semantic_route_key"] == "asset_import_apply_confirm"


def test_corrupt_membership_digest_cannot_publish_negative_line_or_completion():
    snapshot = _snapshot(sealed=True)
    snapshot.issues = []
    snapshot.seal.authoritative_set_sha256 = "c" * 64
    snapshot.seal_current = False
    snapshot.lines[0].review_status = "flagged"
    result = _evaluate(snapshot)
    assert result.result == "STALE"
    assert result.next_action["semantic_route_key"] == "asset_review_stale_recovery"


def test_stale_reason_order_and_read_only_action_are_stable_without_edit_permission():
    snapshot = _snapshot()
    snapshot.issues = []
    snapshot.lineage_current = False
    snapshot.stale = ["seal_mismatch", "selection_mismatch", "lineage_mismatch"]
    result = _evaluate(snapshot, effective_permissions={"project:read"})
    assert result.result == "STALE"
    assert result.next_action["context"]["reason_code"] == "lineage_mismatch"
    assert result.next_action["context"]["reload_required"] is True
    assert result.next_action["semantic_route_key"] == "asset_review_stale_recovery"
    CaseStateNextActionResponse.model_validate(result.next_action)


def test_action_schema_is_additive_and_rejects_wrong_discriminants_and_versions():
    legacy = {"kind": "PENDING", "stage": "OFFICIAL_INTAKE",
              "semantic_route_key": "official_intake_pending", "validation_issue_id": None}
    assert CaseStateNextActionResponse.model_validate(legacy).context is None
    assert CaseStateNextActionResponse.model_validate(legacy).model_dump(mode="json") == legacy
    snapshot = _snapshot()
    snapshot.issues = []
    action = _evaluate(snapshot).next_action
    for field, value in (("kind", "unknown"), ("contract_version", "v1"),
                         ("case_version", "A" * 64), ("confirmation_required", False),
                         ("unsafe_target", str(uuid.uuid4()))):
        broken = {**action, "context": {**action["context"], field: value}}
        with pytest.raises(ValidationError):
            CaseStateNextActionResponse.model_validate(broken)


def test_domain_diagnostics_are_typed_separately_from_validation_issues():
    snapshot = _snapshot(sealed=True)
    snapshot.issues = []
    snapshot.lines.pop()
    snapshot.seal_current = False
    result = _evaluate(snapshot)
    stage = CaseStateStageResponse.model_validate({
        "stage": "ASSET_REVIEW", "result": result.result, "provider_key": result.provider_key,
        "diagnostics": result.blockers + result.stale,
    })
    assert [item.reason_code for item in stage.diagnostics] == ["membership_conflict", "seal_mismatch"]
    legacy = {"stage": "PRELIMINARY_REQUEST", "result": "INCOMPLETE", "provider_key": "v1"}
    assert CaseStateStageResponse.model_validate(legacy).model_dump(mode="json") == legacy
    with pytest.raises(ValidationError):
        CaseStateStageResponse.model_validate({
            "stage": "ASSET_REVIEW", "result": "BLOCKED", "provider_key": "asset_review_line_decision_v1",
            "diagnostics": [{"stage": "ASSET_REVIEW", "reason_code": "invented_reason"}],
        })


def test_provider_consumes_genuine_postgresql_authority_and_issue_models(entry_db):
    from app.modules.excel_import.application.apply_staging import apply_project_asset_import_batch
    from app.modules.excel_import.application.validate_staging import (
        validate_project_asset_import_batch,
    )
    from app.modules.project_master_data.application.asset_review_authority import resolve_authority
    from app.modules.project_master_data.models import ValidationIssue, ValidationRule

    db, entry = entry_db
    scope = {"org_id": entry["org"].id, "project_id": entry["project"].id}
    snapshot = resolve_authority(db, **scope, locked=True)
    assert _evaluate(snapshot).next_action["context"]["kind"] == "validate"
    validate_project_asset_import_batch(
        db, **scope, batch_id=entry["batch"].id, current_user=entry["user"],
        expected_case_version=snapshot.case_version,
    )
    snapshot = resolve_authority(db, **scope, locked=True)
    assert _evaluate(snapshot).next_action["context"]["kind"] == "apply"
    apply_project_asset_import_batch(
        db, **scope, batch_id=entry["batch"].id, current_user=entry["user"], confirm=True,
        contract_version="s12-post-intake-guarded-apply-v2", expected_case_version=snapshot.case_version,
    )
    snapshot = resolve_authority(db, **scope, locked=True)
    action = _evaluate(snapshot).next_action
    assert action["semantic_route_key"] == "asset_review_line_validate_required"
    CaseStateNextActionResponse.model_validate(action)
    rule = ValidationRule(rule_code=f"g2-provider-{uuid.uuid4().hex[:8]}",
                          category="evidence", name="Provider scoped blocker", is_blocking=True)
    db.add(rule)
    db.flush()
    issue = ValidationIssue(validation_rule_id=rule.id, target_type="ProjectAssetLine",
                            target_id=snapshot.lines[0].id, severity="blocking", status="open",
                            issue_message="Fixture blocker")
    db.add(issue)
    db.flush()
    snapshot = resolve_authority(db, **scope, locked=True)
    blocked = _evaluate(snapshot)
    assert blocked.result == "BLOCKED"
    assert blocked.next_action["validation_issue_id"] == str(issue.id)
    assert blocked.next_action["context"]["target_kind"] == "project_asset_line"
    issue.status = "resolved"
    for line in snapshot.lines:
        line.review_status, line.validation_status = "accepted", "valid"
    db.flush()
    snapshot = resolve_authority(db, **scope, locked=True)
    assert _evaluate(snapshot).result == "INCOMPLETE"
    assert not db.new and not db.dirty and not db.deleted
