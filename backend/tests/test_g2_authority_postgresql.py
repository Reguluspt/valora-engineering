"""Project-lock serialization proofs on real guarded Asset Review lineage."""

from __future__ import annotations

import threading
import time

import pytest
from fastapi import HTTPException
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from tests.test_g2_authority import entry_db as _entry_db

entry_db = _entry_db


def _authority(db, entry):
    from app.modules.project_master_data.application.asset_review_authority import resolve_authority

    return resolve_authority(
        db, org_id=entry["org"].id, project_id=entry["project"].id, locked=True,
    )


def _validate(db, entry, case_version):
    from app.modules.excel_import.application.validate_staging import (
        validate_project_asset_import_batch,
    )

    return validate_project_asset_import_batch(
        db, org_id=entry["org"].id, project_id=entry["project"].id,
        batch_id=entry["batch"].id, current_user=db.merge(entry["user"]),
        expected_case_version=case_version,
    )


def _apply(db, entry, case_version):
    from app.modules.excel_import.application.apply_staging import apply_project_asset_import_batch

    return apply_project_asset_import_batch(
        db, org_id=entry["org"].id, project_id=entry["project"].id,
        batch_id=entry["batch"].id, current_user=db.merge(entry["user"]), confirm=True,
        contract_version="s12-post-intake-guarded-apply-v2", expected_case_version=case_version,
    )


def _run_ordered_pair(db, holder_command, waiter_command, *, holder_lock_number=1, lock_table="projects"):
    """Pause a returned Project lock, then prove the competitor blocks on that Project."""
    engine = db.get_bind()
    db.rollback()
    holder_locked = threading.Event()
    release_holder = threading.Event()
    waiter_ready = threading.Event()
    pids = {}
    results = {}
    errors = {}
    worker_labels = {}
    executing_sql = {}
    project_lock_counts = {"holder": 0, "waiter": 0}

    def before_sql(connection, cursor, statement, parameters, context, executemany):
        label = worker_labels.get(threading.get_ident())
        if label is not None:
            executing_sql[label] = statement

    def after_sql(connection, cursor, statement, parameters, context, executemany):
        label = worker_labels.get(threading.get_ident())
        normalized = " ".join(statement.lower().split())
        if label not in project_lock_counts or not any(c in normalized for c in ("for update", "for share")):
            return
        if f".{lock_table} " not in normalized and f"from {lock_table} " not in normalized:
            return
        project_lock_counts[label] += 1
        if label == "holder" and project_lock_counts[label] == holder_lock_number:
            holder_locked.set()
            if not release_holder.wait(timeout=30):
                raise AssertionError("holder Project lock was not released")

    def run(label, command):
        with Session(engine, expire_on_commit=False) as worker_db:
            try:
                worker_labels[threading.get_ident()] = label
                pids[label] = worker_db.execute(text("SELECT pg_backend_pid()")).scalar_one()
                if label == "waiter":
                    waiter_ready.set()
                results[label] = command(worker_db)
                worker_db.commit()
            except BaseException as exc:
                worker_db.rollback()
                errors[label] = exc
            finally:
                worker_labels.pop(threading.get_ident(), None)

    event.listen(engine, "before_cursor_execute", before_sql)
    event.listen(engine, "after_cursor_execute", after_sql)
    holder = threading.Thread(target=run, args=("holder", holder_command), daemon=True)
    waiter = threading.Thread(target=run, args=("waiter", waiter_command), daemon=True)
    try:
        holder.start()
        assert holder_locked.wait(timeout=20), f"holder did not acquire Project: {errors}"
        waiter.start()
        assert waiter_ready.wait(timeout=5), f"waiter did not publish pid: {errors}"
        deadline = time.monotonic() + 15
        observed = None
        while time.monotonic() < deadline:
            with engine.connect() as observer:
                observed = observer.execute(text(
                    "SELECT wait_event_type, pg_blocking_pids(pid) AS blockers, query "
                    "FROM pg_stat_activity WHERE pid = :pid"
                ), {"pid": pids["waiter"]}).mappings().one()
            if observed["wait_event_type"] == "Lock" and pids["holder"] in observed["blockers"]:
                break
            if "waiter" in results or "waiter" in errors:
                raise AssertionError(f"waiter escaped Project serialization: {results}, {errors}")
            threading.Event().wait(0.02)
        assert observed is not None
        assert observed["wait_event_type"] == "Lock", observed
        assert pids["holder"] in observed["blockers"], observed
        assert lock_table in observed["query"].lower(), observed
        assert lock_table in executing_sql["waiter"].lower(), executing_sql
        assert any(c in executing_sql["waiter"].lower() for c in ("for update", "for share")), executing_sql
        release_holder.set()
        holder.join(timeout=30)
        waiter.join(timeout=30)
        assert not holder.is_alive() and not waiter.is_alive(), "race worker did not finish"
        return results, errors, project_lock_counts
    finally:
        release_holder.set()
        if holder.ident is not None:
            holder.join(timeout=30)
        if waiter.ident is not None:
            waiter.join(timeout=30)
        event.remove(engine, "after_cursor_execute", after_sql)
        event.remove(engine, "before_cursor_execute", before_sql)
        db.expire_all()


def _assert_conflict(error, expected_code=None):
    assert isinstance(error, HTTPException), repr(error)
    assert error.status_code == 409, error.detail
    if expected_code is not None:
        assert isinstance(error.detail, dict), error.detail
        assert error.detail["error_code"] == expected_code


def _ready(db, entry):
    _validate(db, entry, _authority(db, entry).case_version)
    token = _authority(db, entry).case_version
    db.rollback()
    return token


def _assert_set(db, entry, expected_lines, expected_seals):
    from app.modules.project_master_data.models import ProjectAssetLine, ProjectAssetReviewSeal

    assert db.query(ProjectAssetLine).filter_by(project_id=entry["project"].id).count() == expected_lines
    assert db.query(ProjectAssetReviewSeal).filter_by(project_id=entry["project"].id).count() == expected_seals


@pytest.mark.parametrize("first", ["left", "right"])
def test_apply_vs_apply_has_one_set_and_one_success_audit(entry_db, first):
    from app.modules.project_master_data.models import AuditEvent

    db, entry = entry_db
    token = _ready(db, entry)
    commands = {"left": lambda s: _apply(s, entry, token), "right": lambda s: _apply(s, entry, token)}
    second = "right" if first == "left" else "left"
    results, errors, _ = _run_ordered_pair(db, commands[first], commands[second])
    assert set(results) == {"holder"}, errors
    assert results["holder"]["created_count"] == 3
    _assert_conflict(errors["waiter"])
    _assert_set(db, entry, 3, 1)
    assert db.query(AuditEvent).filter_by(
        entity_id=entry["batch"].id, event_name="ProjectAssetImportBatchApplied",
    ).count() == 1


@pytest.mark.parametrize("first", ["validation", "apply"])
def test_validation_vs_apply_uses_the_winning_generation(entry_db, first):
    db, entry = entry_db
    token = _ready(db, entry)
    commands = {
        "validation": lambda s: _validate(s, entry, token),
        "apply": lambda s: _apply(s, entry, token),
    }
    second = "apply" if first == "validation" else "validation"
    results, errors, _ = _run_ordered_pair(db, commands[first], commands[second])
    assert set(results) == {"holder"}, errors
    _assert_conflict(errors["waiter"])
    _assert_set(db, entry, 0 if first == "validation" else 3, 0 if first == "validation" else 1)
    assert _authority(db, entry).case_version != token


@pytest.mark.parametrize("first", ["manual", "apply"])
def test_manual_creation_vs_apply_never_adds_unlinked_membership(entry_db, first):
    from app.api.projects import create_project_asset_line
    from app.modules.project_master_data.schemas import ProjectAssetLineCreate

    db, entry = entry_db
    token = _ready(db, entry)

    def manual(s):
        return create_project_asset_line(
            entry["project"].id, ProjectAssetLineCreate(asset_name="Unlinked competitor"),
            db=s, current_user=s.merge(entry["user"]),
        )

    commands = {"manual": manual, "apply": lambda s: _apply(s, entry, token)}
    second = "apply" if first == "manual" else "manual"
    results, errors, _ = _run_ordered_pair(db, commands[first], commands[second])
    apply_label = "holder" if first == "apply" else "waiter"
    manual_label = "waiter" if first == "apply" else "holder"
    assert set(results) == {apply_label}, errors
    _assert_conflict(errors[manual_label], "asset_line_membership_closed")
    _assert_set(db, entry, 3, 1)


@pytest.mark.parametrize("first", ["left", "right"])
def test_line_edit_vs_cas_serializes_and_invalidates_case_version(entry_db, first):
    from app.api.projects import update_project_asset_line
    from app.modules.project_master_data.models import ProjectAssetLine
    from app.modules.project_master_data.schemas import ProjectAssetLineUpdate

    db, entry = entry_db
    _apply(db, entry, _ready(db, entry))
    token = _authority(db, entry).case_version
    line = db.query(ProjectAssetLine).filter_by(project_id=entry["project"].id).first()
    line_id, row_version = line.id, line.row_version

    def edit(s, name):
        return update_project_asset_line(
            entry["project"].id, line_id,
            ProjectAssetLineUpdate(asset_name=name, row_version=row_version),
            db=s, current_user=s.merge(entry["user"]),
        )

    second = "right" if first == "left" else "left"
    results, errors, _ = _run_ordered_pair(
        db, lambda s: edit(s, first), lambda s: edit(s, second),
    )
    assert set(results) == {"holder"}, errors
    _assert_conflict(errors["waiter"])
    changed = db.get(ProjectAssetLine, line_id)
    assert changed.asset_name == first
    assert changed.row_version > row_version
    assert _authority(db, entry).case_version != token
    _assert_set(db, entry, 3, 1)


@pytest.mark.parametrize("first", ["mutation", "apply"])
@pytest.mark.parametrize("mutation", ["status", "current_pointer"])
def test_project_status_or_currentness_vs_apply_is_serialized(entry_db, first, mutation):
    from app.api.projects import archive_project
    from app.modules.project_master_data.application.asset_review_authority import lock_project

    db, entry = entry_db
    token = _ready(db, entry)

    def mutate(s):
        if mutation == "status":
            return archive_project(entry["project"].id, db=s, current_user=s.merge(entry["user"]))
        project = lock_project(s, org_id=entry["org"].id, project_id=entry["project"].id)
        project.current_preliminary_import_batch_id = None
        s.commit()
        return project.id

    commands = {"mutation": mutate, "apply": lambda s: _apply(s, entry, token)}
    second = "apply" if first == "mutation" else "mutation"
    results, errors, _ = _run_ordered_pair(db, commands[first], commands[second])
    assert "holder" in results, errors
    if first == "mutation":
        if mutation == "status":
            assert isinstance(errors["waiter"], HTTPException)
            assert errors["waiter"].status_code == 400
            assert errors["waiter"].detail["error_code"] == "apply_project_not_draft"
        else:
            _assert_conflict(errors["waiter"])
        _assert_set(db, entry, 0, 0)
    else:
        assert errors == {}
        assert set(results) == {"holder", "waiter"}
        _assert_set(db, entry, 3, 1)


@pytest.mark.parametrize("first", ["issue", "apply"])
def test_blocking_issue_mutation_vs_apply_is_serialized(entry_db, first):
    from app.api.workflow import update_validation_issue
    from app.modules.project_master_data.models import (
        ValidationIssue, ValidationIssueSeverity, ValidationIssueStatus, ValidationRule,
    )
    from app.modules.project_master_data.workflow_schemas import ValidationIssueUpdate

    db, entry = entry_db
    rule = ValidationRule(rule_code="g2-race-blocker", category="identity", name="Race blocker")
    db.add(rule)
    db.flush()
    issue = ValidationIssue(
        validation_rule_id=rule.id,
        target_type="project", target_id=entry["project"].id,
        severity=ValidationIssueSeverity.WARNING, status=ValidationIssueStatus.OPEN,
        issue_message="Initially nonblocking",
    )
    db.add(issue)
    db.commit()
    issue_id, issue_version = issue.id, issue.row_version
    token = _ready(db, entry)

    def block(s):
        return update_validation_issue(
            issue_id,
            ValidationIssueUpdate(severity=ValidationIssueSeverity.BLOCKING,
                                  expected_row_version=issue_version),
            db=s, current_user=s.merge(entry["user"]),
        )

    commands = {"issue": block, "apply": lambda s: _apply(s, entry, token)}
    second = "apply" if first == "issue" else "issue"
    results, errors, _ = _run_ordered_pair(db, commands[first], commands[second])
    assert "holder" in results, errors
    if first == "issue":
        _assert_conflict(errors["waiter"])
        _assert_set(db, entry, 0, 0)
    else:
        assert errors == {}
        _assert_set(db, entry, 3, 1)
    assert db.get(ValidationIssue, issue_id).severity == ValidationIssueSeverity.BLOCKING


@pytest.mark.parametrize("first", ["recovery", "mutation"])
@pytest.mark.parametrize("kind", ["apply", "validation"])
def test_failure_recovery_vs_newer_generation_never_overwrites_new_facts(
    entry_db, monkeypatch, first, kind,
):
    import app.modules.excel_import.application.apply_staging as apply_service
    import app.modules.excel_import.application.validate_staging as validation_service
    from app.modules.project_master_data.application.asset_review_authority import lock_project
    from app.modules.project_master_data.models import AuditEvent, ProjectAssetImportBatch

    db, entry = entry_db
    _ready(db, entry)
    snapshot = _authority(db, entry)
    if kind == "apply":
        service = apply_service
        fingerprint = service.build_apply_fingerprint(
            db, project=snapshot.project, batch=snapshot.batch, rows=snapshot.rows,
        )
    else:
        service = validation_service
        fingerprint = service.build_validation_fingerprint(db, snapshot.batch)
    source_status = str(getattr(snapshot.batch.status, "value", snapshot.batch.status))
    calls = []
    original_audit = service._record_failure_audit

    def record_actual_failure(**kwargs):
        calls.append(kwargs["batch"].id)
        return original_audit(**kwargs)

    monkeypatch.setattr(service, "_record_failure_audit", record_actual_failure)

    def recover(s):
        args = dict(
            org_id=entry["org"].id, project_id=entry["project"].id,
            batch_id=entry["batch"].id, actor_id=entry["user"].id,
            pre_fingerprint=fingerprint, source_status=source_status,
            correlation_id="g2-recovery-race",
        )
        if kind == "apply":
            return service._recover_apply_failure(s, **args, error_code=service.ERR_ENGINE)
        return service._recover_validation_failure(s, **args)

    def mutate(s):
        lock_project(s, org_id=entry["org"].id, project_id=entry["project"].id)
        return _validate(s, entry, _authority(s, entry).case_version)

    commands = {"recovery": recover, "mutation": mutate}
    second = "mutation" if first == "recovery" else "recovery"
    results, errors, locks = _run_ordered_pair(db, commands[first], commands[second])
    assert errors == {}
    assert set(results) == {"holder", "waiter"}
    assert locks["holder"] >= 1 and locks["waiter"] >= 1
    expected_failures = 1 if first == "recovery" else 0
    assert len(calls) == expected_failures
    assert db.query(AuditEvent).filter_by(
        entity_id=entry["batch"].id, event_name=service.FAILURE_EVENT,
        correlation_id="g2-recovery-race",
    ).count() == expected_failures
    batch = db.get(ProjectAssetImportBatch, entry["batch"].id)
    assert str(getattr(batch.status, "value", batch.status)) == "ready_for_review"
    assert batch.valid_rows == 3
    _assert_set(db, entry, 0, 0)
