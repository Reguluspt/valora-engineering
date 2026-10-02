"""PostgreSQL snapshot coherence and canonical authority invalidation proofs."""

from __future__ import annotations

import threading
import uuid
from unittest.mock import patch

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.api.workflow import update_validation_issue
from app.modules.excel_import.models import ImportSourceArtifact, ProjectColumnMappingAuthority
from app.modules.project_master_data.application.asset_review_authority import (
    lock_project, resolve_authority,
)
from app.modules.project_master_data.application.case_state_projection import get_case_state_projection
from app.modules.project_master_data.models import (
    ProjectAssetImportBatch, ProjectAssetImportStagingRow, ProjectAssetLine,
    User, ValidationIssue, ValidationRule,
)
from app.modules.project_master_data.workflow_schemas import ValidationIssueUpdate
from tests.test_g2_authority import entry_db as _entry_db, _apply, _ready


entry_db = _entry_db


def _scope(entry):
    return {"org_id": entry["org"].id, "project_id": entry["project"].id}


def _read(engine, entry):
    with Session(engine.execution_options(isolation_level="REPEATABLE READ")) as reader:
        actor = reader.get(User, entry["user"].id)
        return get_case_state_projection(reader, actor=actor, **_scope(entry))


def _asset_result(projection):
    return next(stage.result for stage in projection.stages if stage.stage == "ASSET_REVIEW")


def _warning(db, entry):
    lock_project(db, **_scope(entry))
    rule = ValidationRule(rule_code=f"g2-snapshot-{uuid.uuid4().hex[:8]}", category="evidence",
                          name="Snapshot warning", is_blocking=False)
    db.add(rule)
    db.flush()
    issue = ValidationIssue(validation_rule_id=rule.id, target_type="project",
                            target_id=entry["project"].id, severity="warning", status="open",
                            issue_message="Nonblocking fixture authority")
    db.add(issue)
    db.commit()
    return issue.id


def test_repeatable_read_keeps_prefix_membership_and_issues_in_one_generation(entry_db):
    db, entry = entry_db
    _apply(db, entry, _ready(db, entry))
    issue_id = _warning(db, entry)
    engine = db.get_bind()
    line_id = db.query(ProjectAssetLine.id).filter_by(project_id=entry["project"].id).first()[0]
    db.rollback()
    old = _read(engine, entry)
    assert _asset_result(old) == "INCOMPLETE"
    assert len(old.warnings) == 1 and old.blockers == []

    paused, resume = threading.Event(), threading.Event()
    results, errors = {}, []
    reader_sql, writer_sql = [], []
    forbidden_calls = []
    pause_sql_index = []

    def run_reader():
        with Session(engine.execution_options(isolation_level="REPEATABLE READ")) as reader:
            connection = reader.connection()

            def observe(_connection, _cursor, sql, _params, _context, _many):
                reader_sql.append(sql)

            def pause_after_source(_connection, _cursor, sql, _params, _context, _many):
                normalized = " ".join(sql.lower().split())
                if "import_source_artifacts" in normalized and not paused.is_set():
                    pause_sql_index.append(len(reader_sql))
                    paused.set()
                    if not resume.wait(timeout=20):
                        raise AssertionError("Writer did not release the paused snapshot reader")

            def forbidden(name):
                def called(*_args, **_kwargs):
                    forbidden_calls.append(name)
                    raise AssertionError(f"Case State read called {name}")
                return called

            event.listen(connection, "before_cursor_execute", observe)
            event.listen(connection, "after_cursor_execute", pause_after_source)
            try:
                actor = reader.get(User, entry["user"].id)
                with patch.object(reader, "flush", side_effect=forbidden("flush")), \
                     patch.object(reader, "commit", side_effect=forbidden("commit")), \
                     patch.object(reader, "rollback", side_effect=forbidden("rollback")):
                    results["paused"] = get_case_state_projection(reader, actor=actor, **_scope(entry))
                    results["same_transaction"] = get_case_state_projection(
                        reader, actor=actor, **_scope(entry),
                    )
                assert not reader.new and not reader.dirty and not reader.deleted
            except BaseException as exc:
                errors.append(exc)
            finally:
                event.remove(connection, "after_cursor_execute", pause_after_source)
                event.remove(connection, "before_cursor_execute", observe)

    thread = threading.Thread(target=run_reader, daemon=True)
    thread.start()
    try:
        assert paused.wait(timeout=15), f"Reader did not reach source authority: {errors}"
        with Session(engine, expire_on_commit=False) as writer:
            connection = writer.connection()

            def observe_writer(_connection, _cursor, sql, _params, _context, _many):
                writer_sql.append(sql)

            event.listen(connection, "before_cursor_execute", observe_writer)
            try:
                lock_project(writer, **_scope(entry))
                line = writer.get(ProjectAssetLine, line_id)
                old_line_version = line.row_version
                line.review_status, line.validation_status = "accepted", "valid"
                issue = writer.get(ValidationIssue, issue_id)
                update_validation_issue(
                    issue_id, ValidationIssueUpdate(severity="blocking",
                                                    expected_row_version=issue.row_version),
                    db=writer, current_user=writer.get(User, entry["user"].id),
                )
                assert line.row_version > old_line_version
            finally:
                event.remove(connection, "before_cursor_execute", observe_writer)
        # The writer committed without waiting for the paused reader's transaction.
        new = _read(engine, entry)
        assert new.case_version != old.case_version
        assert _asset_result(new) == "BLOCKED"
        assert new.warnings == [] and len(new.blockers) == 1
        resume.set()
        thread.join(timeout=20)
        assert not thread.is_alive() and not errors, errors
        assert results["paused"] == results["same_transaction"] == old
        assert forbidden_calls == []
        assert any("project_asset_lines" in sql.lower()
                   for sql in reader_sql[pause_sql_index[0]:])
        assert all("for update" not in sql.lower() for sql in reader_sql)
        assert all(sql.lstrip().lower().startswith(("select", "show")) for sql in reader_sql)
        project_lock = next(n for n, sql in enumerate(writer_sql)
                            if "projects" in sql.lower() and "for update" in sql.lower())
        first_write = next(n for n, sql in enumerate(writer_sql)
                           if sql.lstrip().lower().startswith("update"))
        assert project_lock < first_write
    finally:
        resume.set()
        thread.join(timeout=20)


def test_read_tokens_cover_validation_project_issues_and_current_entry_authority(entry_db):
    from app.modules.excel_import.application.validate_staging import (
        validate_project_asset_import_batch,
    )

    db, entry = entry_db
    _ready(db, entry)
    engine = db.get_bind()
    previous = _read(engine, entry)
    seen = {previous.case_version}

    def changed(family, *, expected_asset=None):
        nonlocal previous
        current = _read(engine, entry)
        assert current.case_version != previous.case_version, family
        assert current.case_version not in seen, family
        if expected_asset is not None:
            assert _asset_result(current) == expected_asset, family
        seen.add(current.case_version)
        previous = current

    rows = db.query(ProjectAssetImportStagingRow).filter_by(import_batch_id=entry["batch"].id).all()
    verdicts = [(row.id, row.validation_status, row.validation_errors, row.validation_warnings)
                for row in rows]
    token = resolve_authority(db, **_scope(entry), locked=True).case_version
    validate_project_asset_import_batch(
        db, **_scope(entry), batch_id=entry["batch"].id, current_user=entry["user"],
        expected_case_version=token,
    )
    assert verdicts == [(row.id, row.validation_status, row.validation_errors, row.validation_warnings)
                        for row in rows]
    changed("validation_generation_with_identical_verdicts", expected_asset="INCOMPLETE")

    project = lock_project(db, **_scope(entry))
    project.row_version += 1
    db.commit()
    changed("project_row_version", expected_asset="INCOMPLETE")

    issue_id = _warning(db, entry)
    changed("open_scoped_warning", expected_asset="INCOMPLETE")
    for status in ("resolved", "ignored"):
        issue = db.get(ValidationIssue, issue_id)
        update_validation_issue(
            issue_id, ValidationIssueUpdate(status=status, expected_row_version=issue.row_version),
            db=db, current_user=entry["user"],
        )
        changed("warning_to_" + status, expected_asset="INCOMPLETE")

    lock_project(db, **_scope(entry))
    slot = db.query(ProjectColumnMappingAuthority).filter_by(project_id=entry["project"].id).one()
    slot.selection_revision += 1
    db.commit()
    changed("mapping_selection_generation", expected_asset="INCOMPLETE")

    lock_project(db, **_scope(entry))
    original_usage_id = slot.current_staging_usage_id
    slot.current_staging_usage_id = None
    db.commit()
    changed("current_staging_usage_absence", expected_asset="STALE")
    lock_project(db, **_scope(entry))
    slot.current_staging_usage_id = original_usage_id
    slot.selection_revision += 1
    db.commit()
    changed("restored_staging_authority_generation", expected_asset="INCOMPLETE")

    lock_project(db, **_scope(entry))
    original = entry["source"]
    replacement = ImportSourceArtifact(
        organization_id=original.organization_id, project_id=original.project_id,
        import_batch_id=original.import_batch_id, generation=original.generation + 1,
        original_filename="snapshot-replacement.xlsx", detected_format=original.detected_format,
        content_type=original.content_type, file_size_bytes=original.file_size_bytes,
        checksum_sha256="c" * 64, storage_object_key=f"snapshot-replacement-{uuid.uuid4()}",
        state="available", created_by_user_id=entry["user"].id,
    )
    db.add(replacement)
    db.flush()
    batch = db.get(ProjectAssetImportBatch, entry["batch"].id)
    batch.current_source_artifact_id = replacement.id
    db.commit()
    changed("current_source_generation", expected_asset="STALE")

    lock_project(db, **_scope(entry))
    rows[0].proposed_description = "Changed immutable registered input"
    db.commit()
    changed("materialized_staging_input", expected_asset="STALE")


def test_read_token_covers_each_official_version_and_extra_phantom_membership(entry_db):
    db, entry = entry_db
    _apply(db, entry, _ready(db, entry))
    engine = db.get_bind()
    original = _read(engine, entry)
    lock_project(db, **_scope(entry))
    lines = db.query(ProjectAssetLine).filter_by(project_id=entry["project"].id).order_by(
        ProjectAssetLine.id,
    ).all()
    # Change the last member rather than the currently selected first-line action.
    lines[-1].row_version += 1
    db.commit()
    version_changed = _read(engine, entry)
    assert version_changed.case_version != original.case_version
    assert _asset_result(version_changed) == "INCOMPLETE"

    lock_project(db, **_scope(entry))
    phantom = ProjectAssetLine(project_id=entry["project"].id, asset_name="Unauthorized phantom",
                               quantity=1)
    db.add(phantom)
    db.commit()
    diverged = _read(engine, entry)
    assert diverged.case_version != version_changed.case_version
    assert _asset_result(diverged) == "BLOCKED"
    assert diverged.next_action.context["reason_code"] == "membership_conflict"
    assert any(item["reason_code"] == "membership_conflict"
               for stage in diverged.stages if stage.stage == "ASSET_REVIEW"
               for item in stage.diagnostics)
