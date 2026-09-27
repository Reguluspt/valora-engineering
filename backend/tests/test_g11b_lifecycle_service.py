"""Direct command and Official Intake compatibility evidence for G1.1B."""

from __future__ import annotations

import copy
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
import app.modules.excel_import.models  # noqa: F401
from app.modules.excel_import.models import ColumnMappingDecision
from app.modules.project_master_data.application import preliminary_project_lifecycle_service as service
from app.modules.project_master_data.application.case_state_projection import (
    evaluate_preliminary_analysis_provider,
    evaluate_preliminary_ready_provider,
)
from app.modules.project_master_data.application.official_intake_service import (
    commit_project_official_intake,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    Customer,
    CustomerStatus,
    OrganizationStatus,
    PreliminaryProjectLifecycleCommandReceipt,
    Project,
    ProjectAssetImportBatch,
    ProjectOfficialIntakeCommit,
    UserStatus,
)
from tests.test_pr01_official_intake_service import _seed


@pytest.fixture
def lifecycle_db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _seed_case(db: Session, *, unbound: bool = True) -> dict:
    seeded = _seed(db, suffix=f"g11b-{uuid.uuid4().hex[:8]}")
    seeded["role"].permissions = ["project:update", "project:official_intake:commit"]
    seeded["project"].current_preliminary_import_batch_id = seeded["batch"].id
    if unbound:
        seeded["project"].customer_id = None
        proposal = db.get(ColumnMappingDecision, seeded["decision"].proposal_decision_id)
        assert proposal is not None
        for fact in (
            proposal, seeded["decision"], seeded["usage"], seeded["snapshot"], seeded["artifact"]
        ):
            fact.customer_id = None
        manifest = copy.deepcopy(seeded["artifact"].lineage_manifest)
        manifest["customer_id"] = None
        seeded["artifact"].lineage_manifest = manifest
    db.commit()
    return seeded


def _bind(db: Session, seeded: dict, *, version: int, key: str = "g11b-bind", **changes):
    kwargs = {
        "actor": seeded["actor"], "org_id": seeded["org"].id,
        "project_id": seeded["project"].id, "customer_id": seeded["customer"].id,
        "expected_project_version": version, "idempotency_key": key,
        "correlation_id": "g11b-bind-correlation",
    }
    kwargs.update(changes)
    return service.bind_preliminary_project_customer(db, **kwargs)


def _batch(db: Session, seeded: dict) -> ProjectAssetImportBatch:
    batch = ProjectAssetImportBatch(
        organization_id=seeded["org"].id,
        project_id=seeded["project"].id,
        source_filename=f"another-{uuid.uuid4().hex[:6]}.xlsx",
        status="created", total_rows=0, valid_rows=0, invalid_rows=0, warning_rows=0,
        created_by_user_id=seeded["actor"].id,
    )
    db.add(batch)
    db.commit()
    return batch


def _switch(
    db: Session, seeded: dict, target: ProjectAssetImportBatch,
    *, version: int, old_id: uuid.UUID | None, key: str = "g11b-switch", **changes,
):
    kwargs = {
        "actor": seeded["actor"], "org_id": seeded["org"].id,
        "project_id": seeded["project"].id, "target_import_batch_id": target.id,
        "expected_current_import_batch_id": old_id,
        "expected_project_version": version, "idempotency_key": key,
        "correlation_id": "g11b-switch-correlation",
    }
    kwargs.update(changes)
    return service.switch_current_preliminary_import_batch(db, **kwargs)


def _intake(db: Session, seeded: dict, *, version: int, key: str = "g11b-intake"):
    return commit_project_official_intake(
        db, actor=seeded["actor"], org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        preliminary_result_artifact_id=seeded["artifact"].id,
        expected_project_version=version, expected_preliminary_result_version=1,
        idempotency_key=key, confirmed=True,
    )


def _assert_error(exc: pytest.ExceptionInfo[HTTPException], status: int, code: str) -> None:
    assert exc.value.status_code == status
    assert exc.value.detail["error_code"] == code


def _count(db: Session, model, **filters) -> int:
    return db.query(model).filter_by(**filters).count()


def test_bind_commits_one_version_receipt_audit_and_replays_without_restamping(lifecycle_db):
    seeded = _seed_case(lifecycle_db)
    project = seeded["project"]
    before = project.row_version
    analysis = evaluate_preliminary_analysis_provider(
        lifecycle_db, org_id=seeded["org"].id, project_id=project.id
    )
    assert analysis.result == "COMPLETE"
    assert evaluate_preliminary_ready_provider(
        lifecycle_db, org_id=seeded["org"].id, project_id=project.id,
        analysis_provider_result=analysis,
    ).result == "COMPLETE"

    receipt = _bind(lifecycle_db, seeded, version=before)
    assert receipt.command_type == service.BIND_COMMAND
    assert receipt.committed_project_version == before + 1
    assert project.customer_id == seeded["customer"].id
    assert project.row_version == before + 1
    assert seeded["artifact"].customer_id is None
    assert seeded["snapshot"].customer_id is None
    assert seeded["decision"].customer_id is None
    assert seeded["usage"].customer_id is None
    assert _count(lifecycle_db, PreliminaryProjectLifecycleCommandReceipt) == 1
    assert _count(lifecycle_db, AuditEvent, event_name="PreliminaryProjectCustomerBound") == 1

    replay = _bind(lifecycle_db, seeded, version=before)
    assert replay.id == receipt.id
    assert replay.committed_project_version == receipt.committed_project_version
    assert project.row_version == before + 1
    assert _count(lifecycle_db, PreliminaryProjectLifecycleCommandReceipt) == 1
    assert _count(lifecycle_db, AuditEvent, event_name="PreliminaryProjectCustomerBound") == 1
    with pytest.raises(HTTPException) as exc:
        _bind(lifecycle_db, seeded, version=before + 1, key="g11b-bind")
    _assert_error(exc, 409, "idempotency_key_reused")
    with pytest.raises(HTTPException) as exc:
        _bind(lifecycle_db, seeded, version=before + 1, key="g11b-bind-new")
    _assert_error(exc, 409, "project_already_bound")
    different = Customer(
        organization_id=seeded["org"].id, legal_name="Different Customer",
        status=CustomerStatus.ACTIVE, created_by=seeded["actor"].id,
    )
    lifecycle_db.add(different)
    lifecycle_db.commit()
    with pytest.raises(HTTPException) as exc:
        _bind(
            lifecycle_db, seeded, version=before + 1,
            key="g11b-bind-different", customer_id=different.id,
        )
    _assert_error(exc, 409, "project_already_bound")


def test_replay_rechecks_project_update_permission(lifecycle_db):
    seeded = _seed_case(lifecycle_db)
    before = seeded["project"].row_version
    _bind(lifecycle_db, seeded, version=before)
    seeded["role"].permissions = ["project:official_intake:commit"]
    lifecycle_db.commit()
    with pytest.raises(HTTPException) as exc:
        _bind(lifecycle_db, seeded, version=before)
    _assert_error(exc, 403, "preliminary_lifecycle_forbidden")
    assert _count(lifecycle_db, PreliminaryProjectLifecycleCommandReceipt) == 1
    assert _count(lifecycle_db, AuditEvent, event_name="PreliminaryProjectCustomerBound") == 1
    seeded["role"].permissions = ["project:update", "project:official_intake:commit"]
    seeded["customer"].status = CustomerStatus.INACTIVE
    lifecycle_db.commit()
    replay = _bind(lifecycle_db, seeded, version=before)
    assert replay.committed_project_version == before + 1
    assert _count(lifecycle_db, AuditEvent, event_name="PreliminaryProjectCustomerBound") == 1


def test_bind_rejects_missing_inactive_cross_tenant_stale_and_unauthorized(lifecycle_db):
    seeded = _seed_case(lifecycle_db)
    version = seeded["project"].row_version
    with pytest.raises(HTTPException) as exc:
        _bind(lifecycle_db, seeded, version=version - 1)
    _assert_error(exc, 409, "project_version_conflict")
    with pytest.raises(HTTPException) as exc:
        _bind(lifecycle_db, seeded, version=version, customer_id=uuid.uuid4())
    _assert_error(exc, 404, "customer_not_found")

    other = _seed_case(lifecycle_db)
    with pytest.raises(HTTPException) as exc:
        _bind(lifecycle_db, seeded, version=version, customer_id=other["customer"].id)
    _assert_error(exc, 404, "customer_not_found")
    seeded["customer"].status = CustomerStatus.INACTIVE
    lifecycle_db.commit()
    with pytest.raises(HTTPException) as exc:
        _bind(lifecycle_db, seeded, version=version)
    _assert_error(exc, 409, "customer_not_active")
    seeded["customer"].status = CustomerStatus.ACTIVE
    seeded["role"].permissions = []
    lifecycle_db.commit()
    with pytest.raises(HTTPException) as exc:
        _bind(lifecycle_db, seeded, version=version)
    _assert_error(exc, 403, "preliminary_lifecycle_forbidden")
    seeded["role"].permissions = ["project:update", "project:official_intake:commit"]
    seeded["actor"].status = UserStatus.INACTIVE
    lifecycle_db.commit()
    with pytest.raises(HTTPException) as exc:
        _bind(lifecycle_db, seeded, version=version)
    _assert_error(exc, 403, "preliminary_lifecycle_forbidden")
    seeded["actor"].status = UserStatus.ACTIVE
    seeded["org"].status = OrganizationStatus.INACTIVE
    lifecycle_db.commit()
    with pytest.raises(HTTPException) as exc:
        _bind(lifecycle_db, seeded, version=version)
    _assert_error(exc, 403, "preliminary_lifecycle_forbidden")
    assert seeded["project"].customer_id is None
    assert _count(lifecycle_db, PreliminaryProjectLifecycleCommandReceipt) == 0


def test_bind_rollback_on_receipt_audit_and_commit_failure(lifecycle_db, monkeypatch):
    seeded = _seed_case(lifecycle_db)
    before = seeded["project"].row_version

    def fail_receipt(_mapper, _connection, _receipt):
        raise RuntimeError("forced receipt failure")

    event.listen(PreliminaryProjectLifecycleCommandReceipt, "before_insert", fail_receipt)
    try:
        with pytest.raises(RuntimeError, match="forced receipt failure"):
            _bind(lifecycle_db, seeded, version=before)
    finally:
        event.remove(PreliminaryProjectLifecycleCommandReceipt, "before_insert", fail_receipt)

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("forced audit failure")

    with monkeypatch.context() as patch:
        patch.setattr(service, "log_audit_event", fail_audit)
        with pytest.raises(RuntimeError, match="forced audit failure"):
            _bind(lifecycle_db, seeded, version=before)

    original_commit = lifecycle_db.commit

    def fail_commit():
        raise RuntimeError("forced commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(lifecycle_db, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="forced commit failure"):
            _bind(lifecycle_db, seeded, version=before)
    assert lifecycle_db.commit == original_commit
    lifecycle_db.expire_all()
    assert seeded["project"].customer_id is None
    assert seeded["project"].row_version == before
    assert _count(lifecycle_db, PreliminaryProjectLifecycleCommandReceipt) == 0
    assert _count(lifecycle_db, AuditEvent, event_name="PreliminaryProjectCustomerBound") == 0


def test_switch_updates_only_pointer_and_replay_is_historical(lifecycle_db):
    seeded = _seed_case(lifecycle_db, unbound=False)
    second = _batch(lifecycle_db, seeded)
    project = seeded["project"]
    old_id = seeded["batch"].id
    before = project.row_version
    historical = (
        seeded["snapshot"].id, seeded["snapshot"].source_artifact_id,
        seeded["artifact"].id, seeded["artifact"].source_snapshot_sha256,
    )
    receipt = _switch(lifecycle_db, seeded, second, version=before, old_id=old_id)
    assert receipt.previous_import_batch_id == old_id
    assert receipt.target_import_batch_id == second.id
    assert receipt.committed_project_version == before + 1
    assert project.current_preliminary_import_batch_id == second.id
    assert project.row_version == before + 1
    assert historical == (
        seeded["snapshot"].id, seeded["snapshot"].source_artifact_id,
        seeded["artifact"].id, seeded["artifact"].source_snapshot_sha256,
    )
    assert _count(lifecycle_db, AuditEvent, event_name="CurrentPreliminaryImportBatchSwitched") == 1

    replay = _switch(lifecycle_db, seeded, second, version=before, old_id=old_id)
    assert replay.id == receipt.id
    assert project.row_version == before + 1
    assert _count(lifecycle_db, PreliminaryProjectLifecycleCommandReceipt) == 1
    assert _count(lifecycle_db, AuditEvent, event_name="CurrentPreliminaryImportBatchSwitched") == 1
    with pytest.raises(HTTPException) as exc:
        _switch(lifecycle_db, seeded, second, version=before + 1, old_id=old_id)
    _assert_error(exc, 409, "idempotency_key_reused")
    with pytest.raises(HTTPException) as exc:
        _switch(
            lifecycle_db, seeded, second, version=before + 1,
            old_id=second.id, key="g11b-switch-new",
        )
    _assert_error(exc, 409, "target_import_batch_already_current")


def test_switch_rejects_stale_wrong_scope_and_unresolved_pointer(lifecycle_db):
    seeded = _seed_case(lifecycle_db, unbound=False)
    second = _batch(lifecycle_db, seeded)
    version = seeded["project"].row_version
    old_id = seeded["batch"].id
    with pytest.raises(HTTPException) as exc:
        _switch(lifecycle_db, seeded, second, version=version - 1, old_id=old_id)
    _assert_error(exc, 409, "project_version_conflict")
    with pytest.raises(HTTPException) as exc:
        _switch(lifecycle_db, seeded, second, version=version, old_id=uuid.uuid4())
    _assert_error(exc, 409, "current_import_batch_conflict")
    other = _seed_case(lifecycle_db, unbound=False)
    with pytest.raises(HTTPException) as exc:
        _switch(lifecycle_db, seeded, other["batch"], version=version, old_id=old_id)
    _assert_error(exc, 404, "import_batch_not_found")
    sibling = Project(
        organization_id=seeded["org"].id, customer_id=seeded["customer"].id,
        code=f"G11B-SIBLING-{uuid.uuid4().hex[:6]}", name="Sibling",
        created_by=seeded["actor"].id,
    )
    lifecycle_db.add(sibling)
    lifecycle_db.flush()
    sibling_batch = ProjectAssetImportBatch(
        organization_id=seeded["org"].id, project_id=sibling.id,
        source_filename="sibling.xlsx", status="created", total_rows=0, valid_rows=0,
        invalid_rows=0, warning_rows=0, created_by_user_id=seeded["actor"].id,
    )
    lifecycle_db.add(sibling_batch)
    lifecycle_db.commit()
    with pytest.raises(HTTPException) as exc:
        _switch(lifecycle_db, seeded, sibling_batch, version=version, old_id=old_id)
    _assert_error(exc, 404, "import_batch_not_found")
    seeded["project"].current_preliminary_import_batch_id = None
    lifecycle_db.commit()
    with pytest.raises(HTTPException) as exc:
        _switch(
            lifecycle_db, seeded, second, version=seeded["project"].row_version,
            old_id=None,
        )
    _assert_error(exc, 409, "current_import_batch_unresolved")


def test_switch_audit_failure_rolls_back_pointer_and_receipt(lifecycle_db, monkeypatch):
    seeded = _seed_case(lifecycle_db, unbound=False)
    target = _batch(lifecycle_db, seeded)
    before = seeded["project"].row_version
    old_id = seeded["batch"].id

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("forced switch audit failure")

    monkeypatch.setattr(service, "log_audit_event", fail_audit)
    with pytest.raises(RuntimeError, match="forced switch audit failure"):
        _switch(lifecycle_db, seeded, target, version=before, old_id=old_id)
    lifecycle_db.expire_all()
    assert seeded["project"].row_version == before
    assert seeded["project"].current_preliminary_import_batch_id == old_id
    assert _count(lifecycle_db, PreliminaryProjectLifecycleCommandReceipt) == 0
    assert _count(lifecycle_db, AuditEvent, event_name="CurrentPreliminaryImportBatchSwitched") == 0


def test_official_intake_accepts_historical_null_artifact_and_replay_after_deactivation(lifecycle_db):
    seeded = _seed_case(lifecycle_db)
    unbound_version = seeded["project"].row_version
    with pytest.raises(HTTPException) as exc:
        _intake(lifecycle_db, seeded, version=unbound_version)
    _assert_error(exc, 409, "project_customer_unbound")
    _bind(lifecycle_db, seeded, version=unbound_version)
    bound_version = seeded["project"].row_version
    committed = _intake(lifecycle_db, seeded, version=bound_version)
    assert committed.customer_id == seeded["customer"].id
    assert seeded["artifact"].customer_id is None
    assert _count(lifecycle_db, ProjectOfficialIntakeCommit) == 1
    seeded["customer"].status = CustomerStatus.INACTIVE
    lifecycle_db.commit()
    replay = _intake(lifecycle_db, seeded, version=bound_version)
    assert replay.id == committed.id
    assert _count(lifecycle_db, AuditEvent, event_name="ProjectOfficialIntakeCommitted") == 1
    with pytest.raises(HTTPException) as exc:
        _bind(
            lifecycle_db, seeded, version=bound_version,
            key="g11b-new-bind-post-intake",
        )
    _assert_error(exc, 409, "official_intake_already_committed")


def test_official_intake_requires_active_customer_before_first_commit(lifecycle_db):
    seeded = _seed_case(lifecycle_db, unbound=False)
    seeded["customer"].status = CustomerStatus.INACTIVE
    lifecycle_db.commit()
    with pytest.raises(HTTPException) as exc:
        _intake(lifecycle_db, seeded, version=seeded["project"].row_version)
    _assert_error(exc, 409, "customer_not_active")
    assert _count(lifecycle_db, ProjectOfficialIntakeCommit) == 0


def test_official_intake_rejects_artifact_from_other_project_and_tenant(lifecycle_db):
    seeded = _seed_case(lifecycle_db, unbound=False)
    other = _seed_case(lifecycle_db, unbound=False)
    with pytest.raises(HTTPException) as exc:
        commit_project_official_intake(
            lifecycle_db, actor=seeded["actor"], org_id=seeded["org"].id,
            project_id=seeded["project"].id,
            preliminary_result_artifact_id=other["artifact"].id,
            expected_project_version=seeded["project"].row_version,
            expected_preliminary_result_version=1,
            idempotency_key="g11b-foreign-artifact", confirmed=True,
        )
    _assert_error(exc, 404, "preliminary_result_not_found")
    assert _count(lifecycle_db, ProjectOfficialIntakeCommit) == 0


def test_switch_is_closed_after_intake(lifecycle_db):
    seeded = _seed_case(lifecycle_db, unbound=False)
    intake = _intake(lifecycle_db, seeded, version=seeded["project"].row_version)
    assert intake is not None
    second = _batch(lifecycle_db, seeded)
    with pytest.raises(HTTPException) as exc:
        _switch(
            lifecycle_db, seeded, second, version=seeded["project"].row_version,
            old_id=seeded["batch"].id, key="g11b-new-switch-post-intake",
        )
    _assert_error(exc, 409, "official_intake_already_committed")
