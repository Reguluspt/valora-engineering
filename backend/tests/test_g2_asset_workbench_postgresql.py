"""Both race orders on real PostgreSQL, with observed Project lock waits and cardinality."""
import pytest
from fastapi import HTTPException

from app.api.projects import update_project_asset_line, archive_project
from app.api.workflow import update_validation_issue
from app.modules.project_master_data.application.asset_review_authority import lock_project
from app.modules.project_master_data.models import ProjectAssetLine, Unit
from app.modules.project_master_data.schemas import ProjectAssetLineUpdate
from app.modules.project_master_data.workflow_schemas import ValidationIssueUpdate
from tests.test_g2_authority_postgresql import _run_ordered_pair
from tests.test_g2_asset_workbench import (
    entry_db as _entry_db, line_db as _line_db, workbench_db as _workbench_db,
    snapshot, execute, request_for, provider, counts, human_commit, commit_saved, accept_all,
    line_execute, line_request, add_issue,
)

entry_db, line_db, workbench_db = _entry_db, _line_db, _workbench_db


@pytest.mark.parametrize("first", ["confirmation", "mutation"])
@pytest.mark.parametrize("mutation", ["description", "price", "patch", "validation", "review", "blocker", "status", "membership", "seal"])
def test_confirmation_vs_every_official_writer_both_orders(workbench_db, first, mutation):
    db, entry = workbench_db
    snap = snapshot(db, entry)
    line = next(line for line in snap.lines if line.id == entry["line_id"])
    line_version, prior = line.row_version, snap.line_proofs[line.id]["decision"].id
    if mutation in ("description", "price"):
        field = "description" if mutation == "description" else "appraised_unit_price"
        line_version = human_commit(db, entry, field, "Changed asset description" if mutation == "description" else "42.50")
    if mutation == "blocker":
        issue = add_issue(db, entry)
        issue.severity = "warning"
        db.commit()
        issue_id, issue_version = issue.id, issue.row_version
    req = request_for(db, entry)
    validation_request = line_request(db, entry)
    review_request = line_request(db, entry, review="rejected", reason_note="Human refusal", supersedes_decision_id=str(prior))
    def mutate(s):
        if mutation in ("description", "price"):
            return commit_saved(s, entry, field, line_version)
        if mutation == "patch":
            return update_project_asset_line(entry["project"].id, entry["line_id"],
                ProjectAssetLineUpdate(asset_name="Changed", row_version=line_version), s, s.merge(entry["user"]))
        if mutation == "validation":
            return line_execute(s, entry, validation_request)
        if mutation == "review":
            return line_execute(s, entry, review_request)
        if mutation == "blocker":
            return update_validation_issue(issue_id, ValidationIssueUpdate(severity="blocking", expected_row_version=issue_version), s, s.merge(entry["user"]))
        if mutation == "status":
            return archive_project(entry["project"].id, s, s.merge(entry["user"]))
        lock_project(s, org_id=entry["org"].id, project_id=entry["project"].id)
        if mutation == "membership":
            s.add(ProjectAssetLine(project_id=entry["project"].id, asset_name="Synthetic corruption"))
        else:
            from sqlalchemy import text
            schema = s.get_bind().get_execution_options()["schema_translate_map"][None]
            s.execute(text(f'UPDATE "{schema}".project_asset_review_seals SET entry_lineage_sha256=:digest'), {"digest": "0" * 64})
        s.flush()
        return mutation
    commands = {"confirmation": lambda s: execute(s, entry, req), "mutation": mutate}
    results, errors, locks = _run_ordered_pair(db, commands[first], commands["mutation" if first == "confirmation" else "confirmation"])
    assert "holder" in results, errors
    assert locks["holder"] >= 1 and locks["waiter"] >= 1
    if first == "mutation":
        assert isinstance(errors.get("waiter"), HTTPException), errors
        assert errors["waiter"].status_code == (400 if mutation == "status" else 409)
        assert counts(db) == (0, 0, 0, 0)
    else:
        assert counts(db) == (1, 0, 1, 1)
        if mutation in ("validation", "review"):
            assert isinstance(errors.get("waiter"), HTTPException) and errors["waiter"].status_code == 409
            assert provider(db, entry).result == "COMPLETE"
        else:
            assert not errors and "waiter" in results, errors
            expected = ("COMPLETE" if mutation == "status" else "BLOCKED" if mutation in ("blocker", "membership") else "STALE")
            assert provider(db, entry).result == expected


@pytest.mark.parametrize("first", ["left", "right"])
@pytest.mark.parametrize("kind", ["competing_confirmation", "confirmation_withdrawal", "competing_withdrawal"])
def test_confirmation_and_withdrawal_competitors_serialize_one_winner(workbench_db, first, kind):
    db, entry = workbench_db
    if kind != "competing_confirmation":
        execute(db, entry, request_for(db, entry))
        db.commit()
    if kind == "confirmation_withdrawal":
        version = human_commit(db, entry, "description", "Refreshed description")
        commit_saved(db, entry, "description", version)
        db.commit()
        accept_all(db, entry)
    before = counts(db)
    left = request_for(db, entry, withdraw=kind == "competing_withdrawal")
    right = request_for(db, entry, withdraw=kind != "competing_confirmation")
    commands = {"left": lambda s: execute(s, entry, left), "right": lambda s: execute(s, entry, right)}
    results, errors, _ = _run_ordered_pair(db, commands[first], commands["right" if first == "left" else "left"])
    assert "holder" in results and isinstance(errors.get("waiter"), HTTPException), errors
    assert errors["waiter"].status_code == 409
    after = counts(db)
    assert after[2:] == (before[2] + 1, before[3] + 1)
    assert after[0] + after[1] == before[0] + before[1] + 1


@pytest.mark.parametrize("first", ["withdrawal", "mutation"])
@pytest.mark.parametrize("mutation", ["description", "price", "validation", "review"])
def test_withdrawal_vs_values_and_proofs_both_orders(workbench_db, first, mutation):
    db, entry = workbench_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    if mutation in ("description", "price"):
        field = "description" if mutation == "description" else "appraised_unit_price"
        version = human_commit(db, entry, field, "Changed description" if mutation == "description" else "43.50")
    state = snapshot(db, entry).line_proofs[entry["line_id"]]
    line_req = line_request(db, entry, review="flagged", reason_note="Human hold", supersedes_decision_id=str(state["decision"].id)) if mutation == "review" else line_request(db, entry)
    req, before = request_for(db, entry, withdraw=True), counts(db)
    def mutate(s):
        return commit_saved(s, entry, field, version) if mutation in ("description", "price") else line_execute(s, entry, line_req)
    commands = {"withdrawal": lambda s: execute(s, entry, req), "mutation": mutate}
    results, errors, _ = _run_ordered_pair(db, commands[first], commands["mutation" if first == "withdrawal" else "withdrawal"])
    assert "holder" in results, errors
    if first == "mutation":
        assert isinstance(errors.get("waiter"), HTTPException) and errors["waiter"].status_code == 409
        assert counts(db) == before
    else:
        assert counts(db) == (1, 1, 2, 2)
        if mutation in ("validation", "review"):
            assert isinstance(errors.get("waiter"), HTTPException) and errors["waiter"].status_code == 409
        else:
            assert not errors, errors
        assert provider(db, entry).result == "INCOMPLETE"


@pytest.mark.parametrize("first", ["replay", "mutation"])
def test_replay_vs_concurrent_content_change_has_zero_duplicate_effects(workbench_db, first):
    db, entry = workbench_db
    req = request_for(db, entry)
    original = execute(db, entry, req)
    db.commit()
    version = human_commit(db, entry, "description", "New description")
    commands = {"replay": lambda s: execute(s, entry, req), "mutation": lambda s: commit_saved(s, entry, "description", version)}
    results, errors, _ = _run_ordered_pair(db, commands[first], commands["mutation" if first == "replay" else "replay"])
    assert not errors, errors
    replay = results["holder" if first == "replay" else "waiter"]
    assert replay["replayed"] and replay["result"] == original["result"]
    assert replay["historical"] is (first == "mutation")
    assert counts(db) == (1, 0, 1, 1) and provider(db, entry).result == "STALE"


@pytest.mark.parametrize("first", ["confirmation", "revocation"])
@pytest.mark.parametrize("kind", ["session", "permission", "actor", "organization", "reference"])
def test_authorization_and_reference_changes_are_held_through_commit(workbench_db, first, kind):
    from app.modules.project_master_data.models import WorkbenchSession, Role, User, OrganizationProfile
    db, entry = workbench_db
    req = request_for(db, entry)
    line = next(line for line in snapshot(db, entry).lines if line.id == entry["line_id"])
    model, ident, field, new_value, table = {
        "session": (WorkbenchSession, entry["session"].id, "status", "closed", "workbench_sessions"),
        "permission": (Role, entry["role"].id, "permissions", ["project:read"], "roles"),
        "actor": (User, entry["user"].id, "status", "inactive", "users"),
        "organization": (OrganizationProfile, entry["org"].id, "status", "inactive", "organization_profiles"),
        "reference": (Unit, line.unit_id, "status", "inactive", "units"),
    }[kind]
    table = model.__tablename__
    def revoke(s):
        row = s.query(model).filter_by(id=ident).populate_existing().with_for_update().one()
        setattr(row, field, new_value)
        s.flush()
        return ident
    commands = {"confirmation": lambda s: execute(s, entry, req), "revocation": revoke}
    results, errors, _ = _run_ordered_pair(db, commands[first], commands["revocation" if first == "confirmation" else "confirmation"],
                                         lock_table=table)
    assert "holder" in results, errors
    if first == "revocation":
        assert isinstance(errors.get("waiter"), HTTPException), errors
        assert errors["waiter"].status_code == (404 if kind == "session" else 409 if kind == "reference" else 403)
        assert counts(db) == (0, 0, 0, 0)
    else:
        assert not errors and counts(db) == (1, 0, 1, 1), errors
        assert provider(db, entry).result == ("STALE" if kind == "reference" else "COMPLETE")


@pytest.mark.parametrize("first", ["confirmation", "resolution"])
def test_confirmation_vs_blocker_resolution_rejects_old_shared_cas(workbench_db, first):
    db, entry = workbench_db
    issue = add_issue(db, entry)
    db.commit()
    issue_id, issue_version = issue.id, issue.row_version
    req = request_for(db, entry)
    commands = {
        "confirmation": lambda s: execute(s, entry, req),
        "resolution": lambda s: update_validation_issue(issue_id,
            ValidationIssueUpdate(status="resolved", expected_row_version=issue_version), s, s.merge(entry["user"])),
    }
    results, errors, _ = _run_ordered_pair(db, commands[first], commands["resolution" if first == "confirmation" else "confirmation"])
    denied, resolved = ("holder", "waiter") if first == "confirmation" else ("waiter", "holder")
    assert isinstance(errors.get(denied), HTTPException) and errors[denied].status_code == 409, errors
    assert resolved in results and counts(db) == (0, 0, 0, 0)
    assert provider(db, entry).result == "INCOMPLETE"
    execute(db, entry, request_for(db, entry))
    db.commit()
    assert provider(db, entry).result == "COMPLETE" and counts(db) == (1, 0, 1, 1)


@pytest.mark.parametrize("first", ["recovery_snapshot", "newer_commit"])
def test_receipt_recovery_vs_official_commit_keeps_one_read_only_snapshot(workbench_db, first):
    import threading
    import uuid
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    from app.modules.project_master_data.application.asset_workbench_commands import read_asset_workbench_receipt
    db, entry = workbench_db
    req = request_for(db, entry)
    original = execute(db, entry, req)
    db.commit()
    version = human_commit(db, entry, "description", "New official description")
    engine = db.get_bind()
    db.rollback()
    paused, resume = threading.Event(), threading.Event()
    results, errors, sql = [], [], []
    def reader():
        try:
            with Session(engine.execution_options(isolation_level="REPEATABLE READ")) as s:
                conn = s.connection()
                def observe(connection, cursor, statement, parameters, context, many):
                    sql.append(statement.lower())
                    if first == "recovery_snapshot" and ".projects " in statement.lower() and not paused.is_set():
                        paused.set()
                        assert resume.wait(20)
                event.listen(conn, "after_cursor_execute", observe)
                try:
                    results.append(read_asset_workbench_receipt(s, actor=entry["user"], org_id=entry["org"].id,
                        project_id=entry["project"].id, command_id=uuid.UUID(req["command_id"])))
                    assert not s.new and not s.dirty and not s.deleted
                finally:
                    event.remove(conn, "after_cursor_execute", observe)
        except BaseException as exc:
            errors.append(exc)
    worker = threading.Thread(target=reader, daemon=True)
    try:
        if first == "recovery_snapshot":
            worker.start()
            assert paused.wait(20), errors
        with Session(engine) as writer:
            commit_saved(writer, entry, "description", version)
            writer.commit()
        if first == "newer_commit":
            worker.start()
        resume.set()
        worker.join(20)
        assert not worker.is_alive() and not errors, errors
        assert results[0]["result"] == original["result"]
        assert results[0]["historical"] is (first == "newer_commit")
        assert (results[0]["current_case_version"] == original["current_case_version"]) is (first == "recovery_snapshot")
        assert not any("for update" in q or "for share" in q or q.lstrip().startswith(("update ", "insert ", "delete ")) for q in sql)
        assert counts(db) == (1, 0, 1, 1)
    finally:
        resume.set()
        if worker.ident is not None:
            worker.join(20)
