"""Both-order real PG lock waits, CAS, currentness and atomic cardinality for A4."""

import pytest
from fastapi import HTTPException

from app.api.projects import update_project_asset_line, archive_project
from app.api.workflow import update_validation_issue
from app.modules.project_master_data.application.asset_review_authority import lock_project
from app.modules.project_master_data.commands.commit_asset_line_draft import execute_commit_asset_line_draft
from app.modules.project_master_data.models import InlineEditDraft, Unit, AssetLineValidationGeneration
from app.modules.project_master_data.schemas import ProjectAssetLineUpdate
from app.modules.project_master_data.workflow_schemas import ValidationIssueUpdate
from tests.test_g2_authority_postgresql import _run_ordered_pair
from tests.test_g2_line_decisions import (
    line_db as _line_db, entry_db as _entry_db, execute, request_for, snapshot, counts, add_issue, provider,
)

entry_db, line_db = _entry_db, _line_db


def run_pair(db, commands, first, **kw):
    second = next(k for k in commands if k != first)
    return _run_ordered_pair(db, commands[first], commands[second], **kw)


def conflict(error, status=409):
    assert isinstance(error, HTTPException), repr(error)
    assert error.status_code == status, error.detail


@pytest.mark.parametrize("first", ["left", "right"])
@pytest.mark.parametrize("kind", ["validate", "review", "mixed"])
def test_validate_validate_review_review_and_validate_review_serialize_one_winner(line_db, first, kind):
    db, entry = line_db
    if kind == "mixed":
        execute(db, entry, request_for(db, entry))
        db.commit()
    left = request_for(db, entry, review="flagged" if kind == "review" else None,
                       **({"reason_note": "Left human hold"} if kind == "review" else {}))
    right = request_for(db, entry, review="rejected" if kind == "review" else "accepted" if kind == "mixed" else None,
                        **({"reason_note": "Right human hold"} if kind == "review" else {}))
    before = counts(db)
    results, errors, _ = run_pair(db, {"left": lambda s: execute(s, entry, left),
                                      "right": lambda s: execute(s, entry, right)}, first)
    assert set(results) == {"holder"}, errors
    conflict(errors["waiter"])
    after = counts(db)
    assert after[0] + after[1] == before[0] + before[1] + 1
    assert after[3:] == (before[3] + 1, before[4] + 1)


@pytest.mark.parametrize("first", ["writer", "validate"])
@pytest.mark.parametrize("writer", ["human_commit", "patch"])
def test_official_value_writers_vs_validation_are_project_first(line_db, first, writer):
    db, entry = line_db
    line = next(item for item in snapshot(db, entry).lines if item.id == entry["line_id"])
    line_id, version = line.id, line.row_version
    if writer == "human_commit":
        db.add(InlineEditDraft(session_id=entry["session"].id, target_type="ProjectAssetLine", target_id=line_id,
            field_key="description", draft_value={"value": "Human committed description"}, base_row_version=version))
        db.commit()
    req = request_for(db, entry)
    def write(s):
        if writer == "human_commit":
            return execute_commit_asset_line_draft(s, s.merge(entry["user"]), entry["project"].id,
                line_id, ["description"], True, str(version))
        return update_project_asset_line(entry["project"].id, line_id,
            ProjectAssetLineUpdate(asset_name="Human patched name", row_version=version), s, s.merge(entry["user"]))
    results, errors, _ = run_pair(db, {"writer": write, "validate": lambda s: execute(s, entry, req)}, first)
    assert set(results) == {"holder"}, errors
    conflict(errors["waiter"])
    assert counts(db)[0] == (1 if first == "validate" else 0)
    assert next(item for item in snapshot(db, entry).lines if item.id == line_id).row_version == version + 1


@pytest.mark.parametrize("first", ["reference", "validate"])
def test_reference_status_vs_validation_holds_global_share_lock_through_commit(line_db, first):
    db, entry = line_db
    line = next(item for item in snapshot(db, entry).lines if item.id == entry["line_id"])
    if line.unit_id is None:
        line = next(item for item in snapshot(db, entry).lines if item.unit_id)
        entry["line_id"] = line.id
    unit_id = line.unit_id
    req = request_for(db, entry)
    def reference(s):
        unit = s.query(Unit).filter_by(id=unit_id).with_for_update().one()
        unit.status = "inactive"
        s.flush()
        return str(unit.id)
    results, errors, locks = run_pair(db,
        {"reference": reference, "validate": lambda s: execute(s, entry, req)}, first, lock_table="units")
    assert "holder" in results and locks["holder"] >= 1, errors
    if first == "reference":
        assert set(results) == {"holder"}
        conflict(errors["waiter"])
        assert counts(db)[0] == 0
    else:
        assert not errors and set(results) == {"holder", "waiter"}
        assert counts(db)[0] == 1
        assert results["holder"]["result"]["validation_outcome"] == "valid"
        assert not snapshot(db, entry).line_proofs[line.id]["validation_current"]
        assert provider(db, entry).next_action["semantic_route_key"] == "asset_review_line_validate_required"
    assert db.get(Unit, unit_id).status == "inactive"


@pytest.mark.parametrize("first", ["issue", "review"])
def test_blocker_mutation_vs_review_never_accepts_using_old_case_token(line_db, first):
    db, entry = line_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    issue = add_issue(db, entry)
    issue.severity = "warning"
    db.commit()
    issue_id, issue_version = issue.id, issue.row_version
    req = request_for(db, entry, review="accepted")
    def block(s):
        return update_validation_issue(issue_id, ValidationIssueUpdate(severity="blocking",
            expected_row_version=issue_version), s, s.merge(entry["user"]))
    results, errors, _ = run_pair(db, {"issue": block, "review": lambda s: execute(s, entry, req)}, first)
    assert "holder" in results, errors
    if first == "issue":
        conflict(errors["waiter"])
        assert counts(db)[1] == 0
    else:
        assert not errors and set(results) == {"holder", "waiter"}
        assert counts(db)[1] == 1
    assert provider(db, entry).result == "BLOCKED"


@pytest.mark.parametrize("first", ["project", "command"])
@pytest.mark.parametrize("mutation", ["status", "currentness"])
@pytest.mark.parametrize("kind", ["validate", "review"])
def test_project_status_currentness_vs_each_command(line_db, first, mutation, kind):
    db, entry = line_db
    if kind == "review":
        execute(db, entry, request_for(db, entry))
        db.commit()
    req = request_for(db, entry, review="accepted" if kind == "review" else None)
    before = counts(db)
    def project(s):
        if mutation == "status":
            return archive_project(entry["project"].id, s, s.merge(entry["user"]))
        p = lock_project(s, org_id=entry["org"].id, project_id=entry["project"].id)
        p.current_preliminary_import_batch_id = None
        s.flush()
        return p.id
    results, errors, _ = run_pair(db, {"project": project, "command": lambda s: execute(s, entry, req)}, first)
    assert "holder" in results, errors
    if first == "project":
        conflict(errors["waiter"], 400 if mutation == "status" else 409)
        assert counts(db) == before
    else:
        assert not errors and set(results) == {"holder", "waiter"}
        assert counts(db)[3:] == (before[3] + 1, before[4] + 1)


@pytest.mark.parametrize("first", ["replay", "newer"])
def test_exact_replay_vs_newer_mutation_returns_original_without_new_effects(line_db, first):
    db, entry = line_db
    req = request_for(db, entry)
    original = execute(db, entry, req)
    db.commit()
    newer = request_for(db, entry)
    results, errors, _ = run_pair(db, {"replay": lambda s: execute(s, entry, req),
                                     "newer": lambda s: execute(s, entry, newer)}, first)
    assert not errors and set(results) == {"holder", "waiter"}
    replay = results["holder" if first == "replay" else "waiter"]
    assert replay["replayed"] and replay["result"] == original["result"]
    assert replay["historical"] is (first == "newer")
    assert counts(db) == (2, 0, 0, 2, 2)
    assert db.query(AssetLineValidationGeneration).order_by(AssetLineValidationGeneration.generation).all()[-1].generation == 2


@pytest.mark.parametrize("first", ["recovery_snapshot", "newer_commit"])
def test_read_only_receipt_recovery_vs_newer_authority_keeps_one_snapshot(line_db, first):
    import threading
    import uuid
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    from app.modules.project_master_data.application.asset_review_line_commands import read_asset_review_receipt
    db, entry = line_db
    req = request_for(db, entry)
    original = execute(db, entry, req)
    db.commit()
    newer = request_for(db, entry)
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
                    results.append(read_asset_review_receipt(s, actor=entry["user"], org_id=entry["org"].id,
                        project_id=entry["project"].id, line_id=entry["line_id"], command_id=uuid.UUID(req["command_id"])))
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
            execute(writer, entry, newer)
            writer.commit()
        if first == "newer_commit":
            worker.start()
        resume.set()
        worker.join(20)
        assert not worker.is_alive() and not errors, errors
        assert results[0]["result"] == original["result"]
        assert results[0]["historical"] is (first == "newer_commit")
        assert not any("for update" in q or "for share" in q or q.lstrip().startswith(("update ", "insert ", "delete "))
                       for q in sql)
        assert counts(db) == (2, 0, 0, 2, 2)
    finally:
        resume.set()
        if worker.ident is not None:
            worker.join(20)
