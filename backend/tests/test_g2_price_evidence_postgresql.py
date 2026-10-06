"""A10 real PostgreSQL lock waits, both orderings and historical receipt separation."""
from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.db.mixins import utc_now
from app.api.projects import archive_project, update_project_asset_line
from app.api.workflow import update_validation_issue
from app.modules.project_master_data.schemas import ProjectAssetLineUpdate
from app.modules.project_master_data.workflow_schemas import ValidationIssueUpdate
from tests.test_g2_authority_postgresql import _run_ordered_pair
from tests.test_g2_line_decisions import execute as line_execute, request_for as line_request, add_issue
from tests.test_g2_price_evidence import (
    entry_db as _entry_db, line_db as _line_db, workbench_db as _workbench_db,
    evidence_db as _evidence_db, covered_db as _covered_db,
    execute, request_for, snapshot, provider, counts, material, wb_execute, wb_request, human_commit, commit_saved,
)

entry_db, line_db, workbench_db = _entry_db, _line_db, _workbench_db
evidence_db, covered_db = _evidence_db, _covered_db


def decision_request(db, entry):
    snap = snapshot(db, entry)
    line = snap.lines[0]
    prior = next(d for d in snap.price_evidence.decision_heads.values() if d.line_id == line.id)
    return request_for(db, entry, "relevance", predecessor_relationship_id=str(prior.relationship_id),
        prior_decision_id=str(prior.id), reason_note="Renewed human suitability",
        review_due_at=(utc_now() + timedelta(days=11)).isoformat())


def correction_request(db, entry):
    prior = next(iter(snapshot(db, entry).price_evidence.source_heads.values()))
    return request_for(db, entry, source_id=str(prior.source_id), predecessor_revision_id=str(prior.id),
        reason_note="Correct observed material", material=material(retained_text="Corrected dated synthetic source excerpt retains the unit basis."))


@pytest.mark.parametrize("first", ["left", "right"])
@pytest.mark.parametrize("race", ["competing_corrections", "acceptance_withdrawal", "acceptance_supersession",
    "shared_source_multiline", "confirmation_registration", "confirmation_decision", "confirmation_withdrawal",
    "competing_confirmations", "confirmation_confirmation_withdrawal"])
def test_evidence_command_races_serialize_and_preserve_atomicity(covered_db, first, race):
    db, entry = covered_db
    if race == "confirmation_confirmation_withdrawal":
        execute(db, entry, request_for(db, entry, "confirmation"))
        db.commit()
        execute(db, entry, request_for(db, entry))
        db.commit()
    if race == "competing_corrections":
        left, right = correction_request(db, entry), correction_request(db, entry)
    elif race in ("acceptance_withdrawal", "acceptance_supersession", "shared_source_multiline"):
        left = decision_request(db, entry)
        right = request_for(db, entry, "withdrawal") if race == "acceptance_withdrawal" else correction_request(db, entry)
    else:
        left = request_for(db, entry, "confirmation")
        right = (request_for(db, entry) if race == "confirmation_registration" else
                 decision_request(db, entry) if race == "confirmation_decision" else
                 request_for(db, entry, "withdrawal") if race == "confirmation_withdrawal" else
                 request_for(db, entry, "confirmation-withdrawal") if race == "confirmation_confirmation_withdrawal" else
                 request_for(db, entry, "confirmation"))
    before = counts(db)
    def left_command(s):
        result = execute(s, entry, left)
        if race == "shared_source_multiline":
            fresh = snapshot(s, entry)
            second = fresh.lines[1]
            prior = next(d for d in fresh.price_evidence.decision_heads.values() if d.line_id == second.id)
            from app.modules.project_master_data.application.asset_review_authority import canonical_digest
            from app.modules.project_master_data.application.price_evidence_authority import line_binding
            execute(s, entry, request_for(s, entry, "relevance", line_id=str(second.id),
                predecessor_relationship_id=str(prior.relationship_id), prior_decision_id=str(prior.id),
                expected_line_proof_sha256=canonical_digest(line_binding(fresh, second.id)),
                reason_note="Separate human reassessment of second line"))
        return result
    operations = {"left": left_command, "right": lambda s: execute(s, entry, right)}
    results, errors, locks = _run_ordered_pair(db, operations[first], operations["right" if first == "left" else "left"])
    assert "holder" in results and isinstance(errors.get("waiter"), HTTPException), errors
    assert errors["waiter"].status_code == 409
    assert min(locks.values()) >= 1
    increment = 2 if race == "shared_source_multiline" and first == "left" else 1
    assert counts(db) == tuple(n + increment for n in before)
    if race == "shared_source_multiline" and first == "right":
        assert not snapshot(db, entry).price_evidence.qualifying
    if provider(db, entry).result == "COMPLETE":
        state = snapshot(db, entry).price_evidence
        assert state.content_current and all(state.qualifying.get(line.id) for line in snapshot(db, entry).lines)


@pytest.mark.parametrize("first", ["confirmation", "writer"])
@pytest.mark.parametrize("writer", ["description", "price", "patch", "validation", "review_reversal", "workbench_withdrawal", "blocker", "status"])
def test_confirmation_against_upstream_writers(covered_db, first, writer):
    db, entry = covered_db
    snap = snapshot(db, entry)
    line = next(line for line in snap.lines if line.id == entry["line_id"])
    line_version = line.row_version
    if writer in ("description", "price"):
        field = "description" if writer == "description" else "appraised_unit_price"
        line_version = human_commit(db, entry, field, "Changed human description" if writer == "description" else "25.50")
    if writer == "blocker":
        issue = add_issue(db, entry)
        issue.severity = "warning"
        db.commit()
        issue_id, issue_version = issue.id, issue.row_version
    validation = line_request(db, entry)
    review = line_request(db, entry, review="rejected", reason_note="Human reversal",
                          supersedes_decision_id=str(snapshot(db, entry).line_proofs[line.id]["decision"].id))
    withdrawal = wb_request(db, entry, withdraw=True)
    confirmation = request_for(db, entry, "confirmation")
    def mutate(s):
        if writer in ("description", "price"):
            return commit_saved(s, entry, field, line_version)
        if writer == "patch":
            return update_project_asset_line(entry["project"].id, line.id,
                ProjectAssetLineUpdate(asset_name="Changed official asset", row_version=line_version), s, s.merge(entry["user"]))
        if writer == "validation":
            return line_execute(s, entry, validation)
        if writer == "review_reversal":
            return line_execute(s, entry, review)
        if writer == "workbench_withdrawal":
            return wb_execute(s, entry, withdrawal)
        if writer == "blocker":
            return update_validation_issue(issue_id, ValidationIssueUpdate(severity="blocking", expected_row_version=issue_version), s, s.merge(entry["user"]))
        return archive_project(entry["project"].id, s, s.merge(entry["user"]))
    before = counts(db)
    operations = {"confirmation": lambda s: execute(s, entry, confirmation), "writer": mutate}
    results, errors, locks = _run_ordered_pair(db, operations[first], operations["writer" if first == "confirmation" else "confirmation"])
    assert "holder" in results and min(locks.values()) >= 1, errors
    if first == "writer":
        assert isinstance(errors.get("waiter"), HTTPException), errors
        assert errors["waiter"].status_code == (400 if writer == "status" else 409)
        assert counts(db) == before
    else:
        assert counts(db) == tuple(n + 1 for n in before)
        if writer in ("validation", "review_reversal", "workbench_withdrawal"):
            assert isinstance(errors.get("waiter"), HTTPException) and errors["waiter"].status_code == 409
            assert provider(db, entry).result == "COMPLETE"
        else:
            assert not errors, errors
            assert provider(db, entry).result == ("COMPLETE" if writer == "status" else "BLOCKED" if writer == "blocker" else "STALE")


@pytest.mark.parametrize("first", ["replay", "mutation"])
def test_receipt_replay_vs_new_evidence_returns_historical_result(covered_db, first):
    db, entry = covered_db
    req = request_for(db, entry, "confirmation")
    original = execute(db, entry, req)
    db.commit()
    new = request_for(db, entry)
    operations = {"replay": lambda s: execute(s, entry, req), "mutation": lambda s: execute(s, entry, new)}
    before = counts(db)
    results, errors, _ = _run_ordered_pair(db, operations[first], operations["mutation" if first == "replay" else "replay"])
    assert not errors and len(results) == 2
    replay = results["holder" if first == "replay" else "waiter"]
    assert replay["result"] == original["result"] and replay["historical"] and replay["replayed"]
    assert counts(db) == tuple(n + 1 for n in before)
    assert provider(db, entry).result == "STALE"


@pytest.mark.parametrize("first", ["confirmation", "resolution"])
def test_confirmation_vs_blocker_resolution_both_orders(covered_db, first):
    db, entry = covered_db
    issue = add_issue(db, entry)
    db.commit()
    req = request_for(db, entry, "confirmation")
    issue_id, version = issue.id, issue.row_version
    operations = {"confirmation": lambda s: execute(s, entry, req),
        "resolution": lambda s: update_validation_issue(issue_id,
            ValidationIssueUpdate(status="resolved", expected_row_version=version), s, s.merge(entry["user"]))}
    results, errors, locks = _run_ordered_pair(db, operations[first], operations["resolution" if first == "confirmation" else "confirmation"])
    assert min(locks.values()) >= 1
    assert len(results) == 1 and len(errors) == 1
    assert isinstance(next(iter(errors.values())), HTTPException)
    assert next(iter(errors.values())).status_code == 409
    assert counts(db) == (4, 4, 4)
    assert provider(db, entry).result == "INCOMPLETE"


@pytest.mark.parametrize("first", ["deadline", "commit"])
@pytest.mark.parametrize("boundary", ["review", "source"])
def test_deadline_and_commit_orderings_on_postgresql(evidence_db, first, boundary, monkeypatch):
    from tests.test_g2_price_evidence import cover_all
    from app.modules.project_master_data.application import price_evidence_authority as authority, price_evidence_commands as commands
    db, entry = evidence_db
    expires = utc_now() + timedelta(days=30) if boundary == "source" else None
    execute(db, entry, request_for(db, entry, material=material(expires_at=expires.isoformat() if expires else None)))
    db.commit()
    cover_all(db, entry)
    if boundary == "source":
        # Move to the source deadline; all earlier review deadlines are also no longer usable.
        deadline = expires
    else:
        deadline = snapshot(db, entry).price_evidence.earliest_deadline
    req = request_for(db, entry, "confirmation")
    original = execute(db, entry, req)
    if first == "commit":
        db.commit()
        assert provider(db, entry).result == "COMPLETE"
    monkeypatch.setattr(authority, "utc_now", lambda: deadline)
    monkeypatch.setattr(commands, "utc_now", lambda: deadline)
    if first == "deadline":
        with pytest.raises(HTTPException) as error:
            db.commit()
        assert error.value.status_code == 409
        db.rollback()
        assert counts(db) == (4, 4, 4)
    else:
        assert execute(db, entry, req)["result"] == original["result"]
        db.commit()
        assert counts(db) == (5, 5, 5)
    assert provider(db, entry).result == "STALE"
