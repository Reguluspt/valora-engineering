"""Guarded entry uses real accepted lineage, never historical Apply fixtures."""
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.base_class import Base
from tests.g2_asset_review_helpers import seed_guarded_entry
from fastapi import HTTPException


@pytest.fixture
def entry_db():
    import os
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("Issue75 certification requires TEST_DATABASE_URL PostgreSQL")
    engine = create_engine(url)
    schema = "g2_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = engine.execution_options(schema_translate_map={None: schema})
    Base.metadata.create_all(scoped)
    with Session(scoped, expire_on_commit=False) as db:
        entry = seed_guarded_entry(db)
        yield db, entry
    with engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()


def test_real_entry_resolver_and_guarded_seal(entry_db):
    from app.modules.project_master_data.application.asset_review_authority import resolve_authority
    from app.modules.excel_import.application.apply_staging import apply_project_asset_import_batch
    from app.modules.excel_import.application.validate_staging import validate_project_asset_import_batch
    from app.modules.project_master_data.models import ProjectAssetReviewSeal
    db, entry = entry_db
    args = dict(org_id=entry["org"].id, project_id=entry["project"].id)
    snapshot = resolve_authority(db, **args, locked=True)
    assert snapshot.lineage_current
    validate_project_asset_import_batch(db, **args, batch_id=entry["batch"].id,
        current_user=entry["user"], expected_case_version=snapshot.case_version)
    snapshot = resolve_authority(db, **args, locked=True)
    result = apply_project_asset_import_batch(db, **args, batch_id=entry["batch"].id,
        current_user=entry["user"], confirm=True,
        contract_version="s12-post-intake-guarded-apply-v2", expected_case_version=snapshot.case_version)
    assert result["created_count"] == 3
    assert db.query(ProjectAssetReviewSeal).count() == 1
    after = resolve_authority(db, **args, locked=True)
    assert after.lineage_current and after.seal_current
    assert after.case_version != snapshot.case_version


def _snapshot(db, entry):
    from app.modules.project_master_data.application.asset_review_authority import resolve_authority
    return resolve_authority(db, org_id=entry["org"].id, project_id=entry["project"].id, locked=True)


def _ready(db, entry):
    from app.modules.excel_import.application.validate_staging import validate_project_asset_import_batch
    validate_project_asset_import_batch(db, org_id=entry["org"].id, project_id=entry["project"].id,
        batch_id=entry["batch"].id, current_user=entry["user"], expected_case_version=_snapshot(db, entry).case_version)
    return _snapshot(db, entry).case_version


def _apply(db, entry, token, **overrides):
    from app.modules.excel_import.application.apply_staging import apply_project_asset_import_batch
    kwargs = dict(org_id=entry["org"].id, project_id=entry["project"].id,
        batch_id=entry["batch"].id, current_user=entry["user"], confirm=True,
        contract_version="s12-post-intake-guarded-apply-v2", expected_case_version=token)
    kwargs.update(overrides)
    return apply_project_asset_import_batch(db, **kwargs)


def _counts(db):
    from app.modules.project_master_data.models import ProjectAssetLine, ProjectAssetReviewSeal, AuditEvent
    return (db.query(ProjectAssetLine).count(), db.query(ProjectAssetReviewSeal).count(),
        db.query(AuditEvent).filter(AuditEvent.event_name == "ProjectAssetImportBatchApplied").count(),
        db.query(AuditEvent).filter(AuditEvent.event_name == "ProjectAssetImportBatchApplyFailed").count())


@pytest.mark.parametrize("overrides,code", [
    ({"confirm": None}, "apply_confirmation_required"), ({"confirm": False}, "apply_confirmation_required"),
    ({"contract_version": None}, "apply_contract_invalid"),
    ({"contract_version": "s12-pr-004-v1"}, "apply_contract_invalid"),
    ({"expected_case_version": None}, "apply_contract_invalid"),
    ({"expected_case_version": "A" * 64}, "apply_contract_invalid"),
    ({"expected_case_version": "f" * 64}, "apply_version_conflict"),
])
def test_guard_denials_leave_zero_effects(entry_db, overrides, code):
    db, entry = entry_db
    token = _ready(db, entry)
    with pytest.raises(HTTPException) as caught:
        _apply(db, entry, token, **overrides)
    assert caught.value.detail["error_code"] == code
    assert _counts(db) == (0, 0, 0, 0)


@pytest.mark.parametrize("mutation,code", [
    ("input", "apply_lineage_conflict"), ("usage", "apply_lineage_conflict"),
    ("pending", "apply_rows_not_ready"), ("warning", "apply_rows_not_ready"),
    ("counter", "apply_rows_not_ready"), ("manual", "apply_entry_conflict"),
    ("blocker", "apply_entry_conflict"), ("inactive", None), ("permission", None),
    ("non_draft", "apply_project_not_draft"), ("wrong_batch", None),
    ("wrong_project", None), ("no_intake", "apply_intake_required"),
])
def test_current_domain_guards(entry_db, mutation, code):
    from app.modules.project_master_data.models import (
        ProjectAssetLine, ProjectWorkflowStatus, ImportRowValidationStatus, UserStatus,
        ValidationIssue, ValidationIssueSeverity, ValidationIssueStatus,
        ValidationRule,
    )
    db, entry = entry_db
    token = _ready(db, entry)
    overrides = {}
    if mutation == "input":
        entry["staging_rows"][0].proposed_description = "changed"
    elif mutation == "usage":
        entry["usage"].materialized_input_sha256 = None
    elif mutation in ("pending", "warning"):
        entry["staging_rows"][0].validation_status = ImportRowValidationStatus(mutation)
    elif mutation == "counter":
        entry["batch"].valid_rows = 2
    elif mutation == "manual":
        db.add(ProjectAssetLine(project_id=entry["project"].id, asset_name="unlinked"))
    elif mutation == "blocker":
        rule = ValidationRule(rule_code="g2-domain", category="identity", name="Guard")
        db.add(rule)
        db.flush()
        db.add(ValidationIssue(target_type="Project", target_id=entry["project"].id,
            validation_rule_id=rule.id, severity=ValidationIssueSeverity.BLOCKING,
            status=ValidationIssueStatus.OPEN, issue_message="test"))
    elif mutation == "inactive":
        entry["user"].status = UserStatus.INACTIVE
    elif mutation == "permission":
        entry["role"].permissions = ["project:read"]
    elif mutation == "non_draft":
        entry["project"].status = ProjectWorkflowStatus.ARCHIVED
    elif mutation == "wrong_batch":
        overrides["batch_id"] = uuid.uuid4()
    elif mutation == "wrong_project":
        overrides["project_id"] = uuid.uuid4()
    elif mutation == "no_intake":
        db.delete(entry["intake"])
    db.commit()
    if mutation in ("pending", "warning", "counter"):
        token = _snapshot(db, entry).case_version
    before = _counts(db)
    with pytest.raises(HTTPException) as caught:
        _apply(db, entry, token, **overrides)
    if code:
        assert caught.value.detail["error_code"] == code
    else:
        assert caught.value.status_code == (403 if mutation in ("inactive", "permission") else 404)
    assert _counts(db) == before


@pytest.mark.parametrize("fault", ["mapping", "partial_flush", "audit", "savepoint", "savepoint_begin", "outer_commit", "failure_audit", "committed_unknown"])
def test_apply_atomic_fault_and_unknown_outcome(entry_db, monkeypatch, fault):
    from app.modules.excel_import.application import apply_staging as service
    from app.modules.project_master_data.models import ProjectAssetLine, ImportBatchStatus
    db, entry = entry_db
    token = _ready(db, entry)
    original_flush, original_audit, original_commit = db.flush, service.log_audit_event, db.commit
    original_nested = db.begin_nested
    if fault in ("mapping", "failure_audit"):
        def bad_map(*args):
            raise ValueError("mapping")
        monkeypatch.setattr(service, "_map_row", bad_map)
    if fault == "failure_audit":
        monkeypatch.setattr(service, "_record_failure_audit", lambda **kw: (_ for _ in ()).throw(RuntimeError("audit")))
    if fault == "partial_flush":
        seen = [0]
        def flush(*args, **kwargs):
            if any(isinstance(item, ProjectAssetLine) for item in db.new):
                seen[0] += 1
                if seen[0] == 2:
                    raise RuntimeError("second line")
            return original_flush(*args, **kwargs)
        monkeypatch.setattr(db, "flush", flush)
    if fault == "audit":
        def audit(**kwargs):
            if kwargs["event_name"] == service.SUCCESS_EVENT:
                raise RuntimeError("success audit")
            return original_audit(**kwargs)
        monkeypatch.setattr(service, "log_audit_event", audit)
    if fault == "savepoint":
        def nested():
            sp = original_nested()
            monkeypatch.setattr(sp, "commit", lambda: (_ for _ in ()).throw(RuntimeError("savepoint")))
            return sp
        monkeypatch.setattr(db, "begin_nested", nested)
    if fault == "savepoint_begin":
        monkeypatch.setattr(db, "begin_nested", lambda: (_ for _ in ()).throw(RuntimeError("savepoint begin")))
    if fault in ("outer_commit", "committed_unknown"):
        attempts = [0]
        def commit():
            attempts[0] += 1
            if attempts[0] == 1:
                if fault == "committed_unknown":
                    original_commit()
                raise RuntimeError("response lost")
            return original_commit()
        monkeypatch.setattr(db, "commit", commit)
    with pytest.raises(HTTPException) as caught:
        _apply(db, entry, token)
    assert caught.value.status_code == (400 if fault in ("mapping", "failure_audit") else 500)
    if fault == "committed_unknown":
        assert _counts(db) == (3, 1, 1, 0)
        assert _snapshot(db, entry).seal_current
    else:
        assert _counts(db) == (0, 0, 0, 0 if fault == "failure_audit" else 1)
        db.refresh(entry["batch"])
        assert entry["batch"].status == ImportBatchStatus.READY_FOR_REVIEW


def test_read_projection_token_matches_cas_and_full_set(entry_db, monkeypatch):
    from app.modules.project_master_data.application.case_state_projection import get_case_state_projection
    from app.modules.project_master_data.models import ProjectAssetLine, AssetLineReviewStatus, AssetLineValidationStatus, WorkbenchSession
    db, entry = entry_db
    token = _ready(db, entry)
    bind = db.get_bind().execution_options(isolation_level="REPEATABLE READ")
    db.rollback()
    def read():
        with Session(bind) as reader:
            def forbidden(*args, **kw):
                raise AssertionError("projection attempted mutation")
            for name in ("flush", "commit", "rollback"):
                monkeypatch.setattr(reader, name, forbidden)
            return get_case_state_projection(reader, actor=entry["user"], org_id=entry["org"].id,
                project_id=entry["project"].id)
    projection = read()
    assert projection.case_version == token
    assert projection.current_stage == "ASSET_REVIEW"
    assert projection.next_action.semantic_route_key == "asset_import_apply_confirm"
    _apply(db, entry, projection.case_version)
    db.add(WorkbenchSession(project_id=entry["project"].id, user_id=entry["user"].id))
    db.commit()
    after = read()
    assert after.stages[4].result == "INCOMPLETE"
    assert after.next_action.semantic_route_key == "asset_review_line_validate_required"
    for line in db.query(ProjectAssetLine).all():
        line.review_status = AssetLineReviewStatus.ACCEPTED
        line.validation_status = AssetLineValidationStatus.VALID
        line.row_version += 1
    db.commit()
    complete = read()
    assert complete.case_version != after.case_version
    assert complete.current_stage == "ASSET_REVIEW" and complete.stages[4].result == "INCOMPLETE"
    assert complete.next_action.semantic_route_key == "asset_review_line_validate_required"
    assert complete.stages[5].result == "INCOMPLETE"
    assert all(stage.result == "NOT_AVAILABLE" for stage in complete.stages[6:])
    db.add(ProjectAssetLine(project_id=entry["project"].id, asset_name="illegal phantom"))
    db.commit()
    divergent = read()
    assert divergent.case_version != complete.case_version
    assert divergent.stages[4].result == "BLOCKED"
