"""G1.1G public mapping commands and ADR 0046 service boundaries."""

from __future__ import annotations

import io
import hashlib
import uuid
from copy import deepcopy
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.modules.excel_import.application.column_mapping_service import (
    confirm_column_mapping,
    materialize_confirmed_mapping_to_staging,
    propose_column_mapping,
    reject_column_mapping,
)
from app.modules.excel_import.application.mapping_recovery_service import get_mapping_recovery_state
from app.modules.excel_import.application.source_artifact_service import reconcile_source_artifacts
from app.modules.excel_import.infrastructure.object_storage import (
    FakeObjectStorage,
    set_object_storage_override,
)
from app.modules.excel_import.models import (
    ColumnMappingDecision,
    ColumnMappingProfile,
    ColumnMappingProfileUsage,
    ImportSourceArtifact,
    ProjectColumnMappingAuthority,
    WorkbookStructureSnapshot,
)
from app.modules.project_master_data.application.preliminary_project_lifecycle_service import (
    bind_preliminary_project_customer,
    switch_current_preliminary_import_batch,
)
from app.modules.project_master_data.application.preliminary_analysis_service import (
    finalize_preliminary_analysis,
)
from app.modules.project_master_data.application.preliminary_analysis_currentness import (
    select_current_analysis,
)
from app.modules.project_master_data.application.preliminary_result_service import (
    generate_preliminary_result_artifact,
    validate_stored_v2_manifest,
)
from app.modules.project_master_data.application.preliminary_result_currentness import (
    select_current_result,
)
from app.modules.project_master_data.application.official_intake_service import (
    commit_project_official_intake,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    OrganizationStatus,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    ProjectOfficialIntakeCommit,
    Role,
    UserRole,
    UserStatus,
)
from tests.test_s13_pr_004_column_mapping import _propose, _seed
from tests.test_s13_pr_002_source_artifacts import _make_xlsx_bytes
from tests.test_pr01_preliminary_analysis_service import _line


@pytest.fixture
def mapping_db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    try:
        yield db
    finally:
        set_object_storage_override(None)
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def api_client(mapping_db):
    app.dependency_overrides[get_db] = lambda: mapping_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        set_object_storage_override(None)


def _api_seed(db, *, unbound: bool = True):
    storage = FakeObjectStorage()
    seeded = _seed(db, storage=storage)
    role = Role(
        code=f"g11g-{uuid.uuid4().hex[:12]}",
        display_name="Mapping operator",
        permissions=[
            "workbench:edit", "project:read", "project:update",
            "project:preliminary_analysis:finalize",
            "project:preliminary_result:generate", "project:official_intake:commit",
        ],
    )
    db.add(role)
    db.flush()
    db.add(UserRole(user_id=seeded["user"].id, role_id=role.id, is_active=True))
    seeded["project"].current_preliminary_import_batch_id = seeded["batch"].id
    if unbound:
        seeded["project"].customer_id = None
    db.commit()
    seeded["role"] = role
    seeded["storage"] = storage
    set_object_storage_override(storage)
    return seeded


def _path(seeded, action):
    return (
        f"/api/v1/projects/{seeded['project'].id}/asset-imports/"
        f"{seeded['batch'].id}/column-mapping/{action}"
    )


def _headers(seeded):
    return {"X-User-Id": str(seeded["user"].id), "X-Correlation-Id": "g11g-api"}


def _pending_reconcile_source(db, seeded, batch, *, generation):
    content = _make_xlsx_bytes()
    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    key = f"mapping/reconcile-{uuid.uuid4()}.xlsx"
    seeded["storage"].put_stream(key, io.BytesIO(content), content_type=content_type)
    pending = ImportSourceArtifact(
        organization_id=seeded["org"].id,
        project_id=seeded["project"].id,
        import_batch_id=batch.id,
        generation=generation,
        original_filename="reconcile.xlsx",
        detected_format="xlsx",
        content_type=content_type,
        file_size_bytes=len(content),
        checksum_sha256=hashlib.sha256(content).hexdigest(),
        storage_object_key=key,
        state="pending",
        adapter_metadata={},
        created_by_user_id=seeded["user"].id,
    )
    db.add(pending)
    db.commit()
    return pending


def _proposal_payload(seeded, *, command_id=None):
    return {
        "source_artifact_id": str(seeded["artifact"].id),
        "structure_snapshot_id": str(seeded["snapshot"].id),
        "candidate_index": 0,
        "command_id": str(command_id or uuid.uuid4()),
    }


def _confirm(db, seeded, proposal, *, scope="none", command_id=None):
    existing = db.query(ColumnMappingDecision).filter_by(
        organization_id=seeded["org"].id, command_id=command_id,
    ).first() if command_id is not None else None
    from app.modules.excel_import.application.mapping_authority import authority_slot
    slot = authority_slot(
        db, org_id=seeded["org"].id, project_id=seeded["project"].id,
    )
    expected_revision = (
        existing.before_summary.get("expected_selection_revision", 0)
        if existing is not None else (slot.selection_revision if slot else 0)
    )
    return confirm_column_mapping(
        db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, batch_id=seeded["batch"].id,
        proposal_decision_id=proposal.id, mapping_snapshot=proposal.mapping_snapshot,
        memory_scope=scope, command_id=command_id or uuid.uuid4(),
        expected_selection_revision=expected_revision,
    )


def _materialize(db, seeded, confirmation, *, command_id=None):
    existing = db.query(ColumnMappingProfileUsage).filter_by(
        organization_id=seeded["org"].id, command_id=command_id,
    ).first() if command_id is not None else None
    from app.modules.excel_import.application.mapping_authority import authority_slot
    slot = authority_slot(
        db, org_id=seeded["org"].id, project_id=seeded["project"].id,
    )
    expected_revision = (
        existing.expected_selection_revision
        if existing is not None else (slot.selection_revision if slot else 0)
    )
    return materialize_confirmed_mapping_to_staging(
        db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, batch_id=seeded["batch"].id,
        confirmation_decision_id=confirmation.id,
        command_id=command_id or uuid.uuid4(), storage=seeded["storage"],
        expected_selection_revision=expected_revision,
    )


def _error_code(exc, status, code):
    assert exc.value.status_code == status
    assert exc.value.detail["error_code"] == code


def test_authoritative_get_recovers_lost_confirmation_and_materialization(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    headers = _headers(seeded)
    state_url = _path(seeded, "state")
    initial = api_client.get(state_url, headers=headers)
    assert initial.status_code == 200, initial.text
    assert initial.json()["status"] == "no_selection"
    assert initial.json()["selection_revision"] == 0

    proposed = api_client.post(
        _path(seeded, "proposals"), headers=headers,
        json=_proposal_payload(seeded),
    )
    assert proposed.status_code == 201, proposed.text
    proposal = proposed.json()
    confirmation_key = uuid.uuid4()
    confirmation_payload = {
        "proposal_decision_id": proposal["decision_id"],
        "mapping_snapshot": proposal["mapping_snapshot"],
        "memory_scope": "none", "command_id": str(confirmation_key),
        "expected_selection_revision": 0,
    }
    assert api_client.post(
        _path(seeded, "confirmations"), headers=headers, json=confirmation_payload,
    ).status_code == 201
    recovered = api_client.get(state_url, headers=headers)
    assert recovered.status_code == 200, recovered.text
    selected = recovered.json()
    assert selected["status"] == "selected_unmaterialized"
    assert selected["selection_revision"] == 1
    assert selected["selected_command_id"] == str(confirmation_key)
    assert selected["selected_confirmation_decision_id"]
    assert selected["selected_usage_id"] is None
    assert api_client.post(
        _path(seeded, "confirmations"), headers=headers, json=confirmation_payload,
    ).status_code == 201
    assert api_client.post(
        _path(seeded, "materializations"), headers=headers,
        json={"confirmation_decision_id": selected["selected_confirmation_decision_id"],
              "command_id": str(uuid.uuid4()), "expected_selection_revision": 0},
    ).json()["detail"]["error_code"] == "mapping_selection_revision_conflict"

    usage_key = uuid.uuid4()
    materialization_payload = {
        "confirmation_decision_id": selected["selected_confirmation_decision_id"],
        "command_id": str(usage_key), "expected_selection_revision": 1,
    }
    assert api_client.post(
        _path(seeded, "materializations"), headers=headers,
        json=materialization_payload,
    ).status_code == 201
    recovered_usage = api_client.get(state_url, headers=headers)
    assert recovered_usage.status_code == 200, recovered_usage.text
    materialized = recovered_usage.json()
    assert materialized["status"] == "materialized"
    assert materialized["selection_revision"] == 2
    assert materialized["selected_usage_id"] == materialized["current_staging_usage_id"]
    assert materialized["materialized_asset_row_count"] == 3
    assert api_client.post(
        _path(seeded, "materializations"), headers=headers,
        json=materialization_payload,
    ).status_code == 201
    assert api_client.get(state_url, headers=headers).json()["selection_revision"] == 2


def test_legacy_history_requires_explicit_selection(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    confirmation = _confirm(mapping_db, seeded, proposal)
    slot = mapping_db.query(ProjectColumnMappingAuthority).one()
    mapping_db.delete(slot)
    mapping_db.commit()
    headers = _headers(seeded)
    state = api_client.get(_path(seeded, "state"), headers=headers)
    assert state.status_code == 200
    assert state.json()["status"] == "unresolved_legacy_history"
    assert state.json()["selected_confirmation_decision_id"] is None
    selected = api_client.post(
        _path(seeded, "legacy-selections"), headers=headers,
        json={"confirmation_decision_id": str(confirmation.id),
              "expected_selection_revision": 0, "command_id": str(uuid.uuid4())},
    )
    assert selected.status_code == 201, selected.text
    assert selected.json()["selection_revision"] == 1
    assert api_client.get(_path(seeded, "state"), headers=headers).json()["status"] == "selected_unmaterialized"
    again = api_client.post(
        _path(seeded, "legacy-selections"), headers=headers,
        json={"confirmation_decision_id": str(confirmation.id),
              "expected_selection_revision": 1, "command_id": str(uuid.uuid4())},
    )
    assert again.status_code == 409
    assert again.json()["detail"]["error_code"] == "mapping_selection_exists"


def test_legacy_selection_rejects_occupied_usage(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    confirmation = _confirm(mapping_db, seeded, proposal)
    _materialize(mapping_db, seeded, confirmation)
    mapping_db.delete(mapping_db.query(ProjectColumnMappingAuthority).one())
    mapping_db.commit()
    response = api_client.post(
        _path(seeded, "legacy-selections"), headers=_headers(seeded),
        json={"confirmation_decision_id": str(confirmation.id),
              "expected_selection_revision": 0, "command_id": str(uuid.uuid4())},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "mapping_legacy_selection_ineligible"
    assert mapping_db.query(ProjectColumnMappingAuthority).count() == 0


def test_legacy_selection_rejects_contradictory_outcome(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    confirmation = _confirm(mapping_db, seeded, proposal)
    mapping_db.delete(mapping_db.query(ProjectColumnMappingAuthority).one())
    mapping_db.add(ColumnMappingDecision(
        organization_id=seeded["org"].id,
        customer_id=confirmation.customer_id,
        project_id=seeded["project"].id,
        import_batch_id=seeded["batch"].id,
        source_artifact_id=seeded["artifact"].id,
        structure_snapshot_id=seeded["snapshot"].id,
        decision_kind="rejection", outcome="rejected", memory_scope="none",
        proposal_decision_id=proposal.id, actor_user_id=seeded["user"].id,
        command_id=uuid.uuid4(), proposal_source_kind="human",
        proposal_source_version=confirmation.proposal_source_version,
        mapping_contract_version=confirmation.mapping_contract_version,
        template_fingerprint_sha256=confirmation.template_fingerprint_sha256,
        mapping_snapshot=deepcopy(confirmation.mapping_snapshot),
        mapping_digest_sha256=confirmation.mapping_digest_sha256,
        before_summary={}, after_summary={}, reason_code="legacy_conflict",
    ))
    mapping_db.commit()
    response = api_client.post(
        _path(seeded, "legacy-selections"), headers=_headers(seeded),
        json={"confirmation_decision_id": str(confirmation.id),
              "expected_selection_revision": 0, "command_id": str(uuid.uuid4())},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "mapping_legacy_selection_ineligible"
    assert mapping_db.query(ProjectColumnMappingAuthority).count() == 0


def test_legacy_selection_rejects_cross_tenant_and_stale_source(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    confirmation = _confirm(mapping_db, seeded, proposal)
    mapping_db.delete(mapping_db.query(ProjectColumnMappingAuthority).one())
    mapping_db.commit()
    other = _api_seed(mapping_db)
    payload = {"confirmation_decision_id": str(confirmation.id),
               "expected_selection_revision": 0, "command_id": str(uuid.uuid4())}
    assert api_client.post(
        _path(seeded, "legacy-selections"), headers=_headers(other), json=payload,
    ).status_code == 404
    seeded["batch"].current_source_artifact_id = None
    mapping_db.commit()
    stale = api_client.post(
        _path(seeded, "legacy-selections"), headers=_headers(seeded), json=payload,
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["error_code"] == "mapping_source_not_current"
    assert mapping_db.query(ProjectColumnMappingAuthority).count() == 0


def test_source_replacement_invalidates_selection_atomically(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    confirmation = _confirm(mapping_db, seeded, proposal)
    headers = _headers(seeded)
    before = api_client.get(_path(seeded, "state"), headers=headers).json()
    assert before["status"] == "selected_unmaterialized"
    uploaded = api_client.post(
        f"/api/v1/projects/{seeded['project'].id}/asset-imports/"
        f"{seeded['batch'].id}/source-artifacts",
        headers=headers,
        files={"file": (
            "replacement.xlsx", io.BytesIO(_make_xlsx_bytes()),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
    )
    assert uploaded.status_code == 201, uploaded.text
    after = api_client.get(_path(seeded, "state"), headers=headers).json()
    assert after["current_source_artifact_id"] == uploaded.json()["id"]
    assert after["selected_confirmation_decision_id"] is None
    assert after["status"] == "no_selection"
    assert after["selection_revision"] == before["selection_revision"] + 1
    denied = api_client.post(
        _path(seeded, "materializations"), headers=headers,
        json={"confirmation_decision_id": str(confirmation.id),
              "command_id": str(uuid.uuid4()),
              "expected_selection_revision": after["selection_revision"]},
    )
    assert denied.status_code == 409


def test_reconciled_current_source_replacement_invalidates_selection(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    _confirm(mapping_db, seeded, proposal)
    before = api_client.get(_path(seeded, "state"), headers=_headers(seeded)).json()
    pending = _pending_reconcile_source(
        mapping_db, seeded, seeded["batch"], generation=2,
    )
    stats = reconcile_source_artifacts(
        mapping_db, storage=seeded["storage"], max_items=10,
        actor_id=seeded["user"].id, org_id=seeded["org"].id,
    )
    assert stats["errors"] == 0
    after = api_client.get(_path(seeded, "state"), headers=_headers(seeded)).json()
    assert after["current_source_artifact_id"] == str(pending.id)
    assert after["selected_confirmation_decision_id"] is None
    assert after["selection_revision"] == before["selection_revision"] + 1


def test_noncurrent_batch_source_replacement_preserves_current_selection(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    confirmation = _confirm(mapping_db, seeded, proposal)
    retained = ProjectAssetImportBatch(
        organization_id=seeded["org"].id, project_id=seeded["project"].id,
        source_filename="retained.xlsx", status="created",
        created_by_user_id=seeded["user"].id,
    )
    mapping_db.add(retained)
    mapping_db.commit()
    headers = _headers(seeded)
    before = api_client.get(_path(seeded, "state"), headers=headers).json()
    invalidations_before = mapping_db.query(AuditEvent).filter(
        AuditEvent.event_name == "ProjectColumnMappingAuthorityInvalidated",
    ).count()
    for index in (1, 2):
        uploaded = api_client.post(
            f"/api/v1/projects/{seeded['project'].id}/asset-imports/"
            f"{retained.id}/source-artifacts",
            headers=headers,
            files={"file": (
                f"retained-{index}.xlsx", io.BytesIO(_make_xlsx_bytes()),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )},
        )
        assert uploaded.status_code == 201, uploaded.text
    pending = _pending_reconcile_source(mapping_db, seeded, retained, generation=3)
    stats = reconcile_source_artifacts(
        mapping_db, storage=seeded["storage"], max_items=10,
        actor_id=seeded["user"].id, org_id=seeded["org"].id,
    )
    assert stats["errors"] == 0
    mapping_db.refresh(retained)
    assert retained.current_source_artifact_id == pending.id
    after = api_client.get(_path(seeded, "state"), headers=headers).json()
    assert after["status"] == "selected_unmaterialized"
    assert after["selected_confirmation_decision_id"] == str(confirmation.id)
    assert after["selection_revision"] == before["selection_revision"]
    assert after["current_source_artifact_id"] == before["current_source_artifact_id"]
    assert mapping_db.query(AuditEvent).filter(
        AuditEvent.event_name == "ProjectColumnMappingAuthorityInvalidated",
    ).count() == invalidations_before


def test_recovery_read_does_not_expose_current_usage_to_retained_batch(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    confirmation = _confirm(mapping_db, seeded, proposal)
    usage = _materialize(mapping_db, seeded, confirmation)
    retained = ProjectAssetImportBatch(
        organization_id=seeded["org"].id, project_id=seeded["project"].id,
        source_filename="retained.xlsx", status="created",
        created_by_user_id=seeded["user"].id,
    )
    mapping_db.add(retained)
    mapping_db.commit()
    response = api_client.get(
        f"/api/v1/projects/{seeded['project'].id}/asset-imports/"
        f"{retained.id}/column-mapping/state", headers=_headers(seeded),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "stale_lineage"
    assert response.json()["selected_confirmation_decision_id"] is None
    assert response.json()["selected_usage_id"] is None
    assert response.json()["current_staging_usage_id"] is None
    current = api_client.get(_path(seeded, "state"), headers=_headers(seeded))
    assert current.json()["status"] == "materialized"
    assert current.json()["selected_usage_id"] == str(usage.id)


def test_batch_switch_back_does_not_resurrect_selection(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    _confirm(mapping_db, seeded, proposal)
    other = ProjectAssetImportBatch(
        organization_id=seeded["org"].id, project_id=seeded["project"].id,
        source_filename="other.xlsx", status="created",
        created_by_user_id=seeded["user"].id,
    )
    mapping_db.add(other)
    mapping_db.commit()
    switch_current_preliminary_import_batch(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, target_import_batch_id=other.id,
        expected_current_import_batch_id=seeded["batch"].id,
        expected_project_version=seeded["project"].row_version,
        idempotency_key=f"f0-switch-away-{uuid.uuid4()}",
    )
    slot = mapping_db.query(ProjectColumnMappingAuthority).one()
    assert slot.confirmation_decision_id is None
    assert slot.selection_revision == 2
    switch_current_preliminary_import_batch(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        target_import_batch_id=seeded["batch"].id,
        expected_current_import_batch_id=other.id,
        expected_project_version=seeded["project"].row_version,
        idempotency_key=f"f0-switch-back-{uuid.uuid4()}",
    )
    state = api_client.get(_path(seeded, "state"), headers=_headers(seeded))
    assert state.status_code == 200
    assert state.json()["selection_revision"] == 3
    assert state.json()["selected_confirmation_decision_id"] is None
    assert state.json()["status"] == "unresolved_legacy_history"


def test_recovery_read_is_project_scoped_and_requires_read_permission(api_client, mapping_db):
    first = _api_seed(mapping_db)
    second = _api_seed(mapping_db)
    path = _path(first, "state")
    wrong_batch_path = (
        f"/api/v1/projects/{first['project'].id}/asset-imports/"
        f"{second['batch'].id}/column-mapping/state"
    )
    assert api_client.get(wrong_batch_path, headers=_headers(first)).status_code == 404
    assert api_client.get(path, headers=_headers(second)).status_code == 404
    first["role"].permissions = ["workbench:edit"]
    mapping_db.commit()
    assert api_client.get(path, headers=_headers(first)).status_code == 403


def test_selection_replacement_rejection_and_used_structure_boundary(mapping_db):
    seeded = _api_seed(mapping_db)
    first_proposal = _propose(mapping_db, seeded).decision
    second_proposal = _propose(mapping_db, seeded).decision
    first_key = uuid.uuid4()
    first_confirmation = _confirm(mapping_db, seeded, first_proposal, command_id=first_key)
    second_confirmation = _confirm(mapping_db, seeded, second_proposal)
    slot = mapping_db.query(ProjectColumnMappingAuthority).one()
    assert slot.confirmation_decision_id == second_confirmation.id
    assert slot.selection_revision == 2
    assert _confirm(mapping_db, seeded, first_proposal, command_id=first_key).id == first_confirmation.id
    assert slot.confirmation_decision_id == second_confirmation.id
    assert slot.selection_revision == 2
    with pytest.raises(HTTPException) as exc:
        _materialize(mapping_db, seeded, first_confirmation)
    _error_code(exc, 409, "mapping_selection_not_current")
    mapping_db.rollback()
    third_proposal = _propose(mapping_db, seeded).decision
    reject_column_mapping(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, batch_id=seeded["batch"].id,
        proposal_decision_id=third_proposal.id, command_id=uuid.uuid4(),
    )
    mapping_db.refresh(slot)
    assert slot.confirmation_decision_id == second_confirmation.id
    assert slot.selection_revision == 2
    _materialize(mapping_db, seeded, second_confirmation)
    assert slot.selection_revision == 3
    fourth_proposal = _propose(mapping_db, seeded).decision
    with pytest.raises(HTTPException) as exc:
        _confirm(mapping_db, seeded, fourth_proposal)
    _error_code(exc, 409, "mapping_usage_conflict")


def test_new_materialization_displaces_analysis_result_and_new_intake(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    first_proposal = _propose(mapping_db, seeded).decision
    first_confirmation = _confirm(mapping_db, seeded, first_proposal)
    first_usage_key = uuid.uuid4()
    first_usage = _materialize(
        mapping_db, seeded, first_confirmation, command_id=first_usage_key,
    )
    bind_preliminary_project_customer(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, customer_id=seeded["customer"].id,
        expected_project_version=seeded["project"].row_version,
        idempotency_key=f"f0-bind-{uuid.uuid4()}",
    )
    analysis = finalize_preliminary_analysis(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        expected_project_version=seeded["project"].row_version,
        import_batch_id=seeded["batch"].id,
        source_artifact_id=seeded["artifact"].id,
        structure_snapshot_id=seeded["snapshot"].id,
        mapping_decision_id=first_confirmation.id,
        mapping_profile_usage_id=first_usage.id,
        mapping_decision_digest_sha256=first_confirmation.mapping_digest_sha256,
        profile_usage_mapping_digest_sha256=first_usage.mapping_digest_sha256,
        line_manifest=[_line(source_row_number=7)],
        idempotency_key=f"f0-analysis-{uuid.uuid4()}", confirmed=True,
    )
    result = generate_preliminary_result_artifact(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        preliminary_analysis_snapshot_id=analysis.id,
        expected_project_version=seeded["project"].row_version,
        idempotency_key=f"f0-result-{uuid.uuid4()}", confirmed=True,
    )
    slot = mapping_db.query(ProjectColumnMappingAuthority).one()
    slot.selected_usage_id = None
    slot.current_staging_usage_id = None
    slot.selection_revision += 1
    mapping_db.commit()
    assert select_current_analysis(
        mapping_db, org_id=seeded["org"].id, project_id=seeded["project"].id,
        valid_manifest=validate_stored_v2_manifest,
    ) is None
    slot.selected_usage_id = first_usage.id
    slot.current_staging_usage_id = first_usage.id
    slot.selection_revision += 1
    mapping_db.commit()
    original = seeded["snapshot"]
    alternative = WorkbookStructureSnapshot(
        organization_id=seeded["org"].id, project_id=seeded["project"].id,
        import_batch_id=seeded["batch"].id,
        source_artifact_id=seeded["artifact"].id,
        snapshot_version=2,
        source_checksum_sha256=original.source_checksum_sha256,
        rule_version=original.rule_version,
        adapter_name=original.adapter_name,
        adapter_version=original.adapter_version,
        disposition=original.disposition,
        candidate_count=original.candidate_count,
        structure_payload=deepcopy(original.structure_payload),
        analysis_digest_sha256=original.analysis_digest_sha256,
        created_by_user_id=seeded["user"].id,
    )
    mapping_db.add(alternative)
    mapping_db.flush()
    mapping_db.add(AuditEvent(
        organization_id=seeded["org"].id,
        actor_user_id=seeded["user"].id,
        event_name="WorkbookStructureAnalyzed",
        entity_type="WorkbookStructureSnapshot",
        entity_id=alternative.id,
        command_name="AnalyzeWorkbookStructure",
        payload={
            "import_batch_id": str(seeded["batch"].id),
            "source_artifact_id": str(seeded["artifact"].id),
            "source_generation": seeded["artifact"].generation,
            "snapshot_version": 2,
            "rule_version": alternative.rule_version,
            "disposition": alternative.disposition,
            "candidate_count": alternative.candidate_count,
            "analysis_digest_sha256": alternative.analysis_digest_sha256,
        },
    ))
    mapping_db.commit()
    seeded["snapshot"] = alternative
    prior_state = get_mapping_recovery_state(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, batch_id=seeded["batch"].id,
    )
    assert prior_state["status"] == "materialized"
    assert prior_state["selected_structure_snapshot_id"] == original.id
    second_proposal = _propose(mapping_db, seeded).decision
    second_confirmation = _confirm(mapping_db, seeded, second_proposal)
    selected = api_client.get(_path(seeded, "state"), headers=_headers(seeded))
    assert selected.status_code == 200, selected.text
    assert selected.json()["status"] == "selected_unmaterialized"
    assert selected.json()["selected_confirmation_decision_id"] == str(second_confirmation.id)
    assert selected.json()["selected_usage_id"] is None
    assert selected.json()["current_staging_usage_id"] == str(first_usage.id)
    slot_revision = slot.selection_revision
    audit_count = mapping_db.query(AuditEvent).filter(
        AuditEvent.event_name == "ConfirmedMappingMaterialized",
    ).count()
    assert _materialize(
        mapping_db, seeded, first_confirmation, command_id=first_usage_key,
    ).id == first_usage.id
    mapping_db.refresh(slot)
    assert slot.confirmation_decision_id == second_confirmation.id
    assert slot.selected_usage_id is None
    assert slot.current_staging_usage_id == first_usage.id
    assert slot.selection_revision == slot_revision
    assert mapping_db.query(AuditEvent).filter(
        AuditEvent.event_name == "ConfirmedMappingMaterialized",
    ).count() == audit_count
    current_before = select_current_analysis(
        mapping_db, org_id=seeded["org"].id, project_id=seeded["project"].id,
        valid_manifest=validate_stored_v2_manifest,
    )
    assert current_before is not None and current_before.id == analysis.id
    assert select_current_result(
        mapping_db, org_id=seeded["org"].id, project_id=seeded["project"].id,
        current_analysis=current_before,
    ).id == result.id
    _materialize(mapping_db, seeded, second_confirmation)
    current_after = select_current_analysis(
        mapping_db, org_id=seeded["org"].id, project_id=seeded["project"].id,
        valid_manifest=validate_stored_v2_manifest,
    )
    assert current_after is None
    assert select_current_result(
        mapping_db, org_id=seeded["org"].id, project_id=seeded["project"].id,
        current_analysis=current_after,
    ) is None
    with pytest.raises(HTTPException) as exc:
        commit_project_official_intake(
            mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
            project_id=seeded["project"].id,
            preliminary_result_artifact_id=result.id,
            expected_project_version=seeded["project"].row_version,
            expected_preliminary_result_version=result.version,
            idempotency_key=f"f0-intake-{uuid.uuid4()}", confirmed=True,
        )
    _error_code(exc, 409, "preliminary_result_not_current")


def test_non_mapping_staging_replacement_closes_for_selected_lineage(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    confirmation = _confirm(mapping_db, seeded, proposal)
    usage = _materialize(mapping_db, seeded, confirmation)
    before_count = mapping_db.query(ProjectAssetImportStagingRow).count()
    response = api_client.post(
        f"/api/v1/projects/{seeded['project'].id}/asset-imports/"
        f"{seeded['batch'].id}/upload",
        headers=_headers(seeded),
        files={"file": (
            "other.xlsx", io.BytesIO(_make_xlsx_bytes()),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
    )
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["error_code"] == "mapping_staging_owned"
    assert mapping_db.query(ProjectAssetImportStagingRow).count() == before_count
    slot = mapping_db.query(ProjectColumnMappingAuthority).one()
    assert slot.selected_usage_id == usage.id
    assert slot.current_staging_usage_id == usage.id
    assert slot.selection_revision == 2


def test_non_mapping_staging_replacement_closes_for_unresolved_legacy_usage(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    confirmation = _confirm(mapping_db, seeded, proposal)
    _materialize(mapping_db, seeded, confirmation)
    slot = mapping_db.query(ProjectColumnMappingAuthority).one()
    mapping_db.delete(slot)
    mapping_db.commit()
    before_count = mapping_db.query(ProjectAssetImportStagingRow).count()
    response = api_client.post(
        f"/api/v1/projects/{seeded['project'].id}/asset-imports/"
        f"{seeded['batch'].id}/upload",
        headers=_headers(seeded),
        files={"file": (
            "other.xlsx", io.BytesIO(_make_xlsx_bytes()),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
    )
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["error_code"] == "mapping_legacy_staging_unresolved"
    assert mapping_db.query(ProjectAssetImportStagingRow).count() == before_count


def test_recovery_get_never_promotes_historical_usage_from_missing_owner(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    confirmation = _confirm(mapping_db, seeded, proposal)
    _materialize(mapping_db, seeded, confirmation)
    slot = mapping_db.query(ProjectColumnMappingAuthority).one()
    slot.selected_usage_id = None
    slot.current_staging_usage_id = None
    slot.selection_revision += 1
    mapping_db.commit()
    state = api_client.get(_path(seeded, "state"), headers=_headers(seeded))
    assert state.status_code == 200, state.text
    assert state.json()["status"] == "selected_recovery_required"
    assert state.json()["selected_usage_id"] is None
    assert state.json()["current_staging_usage_id"] is None


def test_recovery_get_fails_closed_on_stale_source_pointer(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    confirmation = _confirm(mapping_db, seeded, proposal)
    _materialize(mapping_db, seeded, confirmation)
    seeded["batch"].current_source_artifact_id = None
    mapping_db.commit()
    state = api_client.get(_path(seeded, "state"), headers=_headers(seeded))
    assert state.status_code == 200, state.text
    assert state.json()["status"] == "stale_lineage"
    assert state.json()["selected_confirmation_decision_id"] is not None
    assert state.json()["selected_usage_id"] is None
    assert state.json()["current_staging_usage_id"] is None


def test_recovery_get_hides_unverified_usage_link(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    confirmation = _confirm(mapping_db, seeded, proposal)
    usage = _materialize(mapping_db, seeded, confirmation)
    usage.mapping_digest_sha256 = "0" * 64
    mapping_db.commit()
    state = api_client.get(_path(seeded, "state"), headers=_headers(seeded))
    assert state.status_code == 200, state.text
    assert state.json()["status"] == "stale_lineage"
    assert state.json()["selected_usage_id"] is None
    assert state.json()["current_staging_usage_id"] is None


def test_recovery_get_requires_available_current_source(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    confirmation = _confirm(mapping_db, seeded, proposal)
    _materialize(mapping_db, seeded, confirmation)
    seeded["artifact"].state = "orphaned"
    mapping_db.commit()
    state = api_client.get(_path(seeded, "state"), headers=_headers(seeded))
    assert state.status_code == 200, state.text
    assert state.json()["status"] == "stale_lineage"
    assert state.json()["selected_usage_id"] is None
    assert state.json()["current_staging_usage_id"] is None


def test_public_mapping_round_trip_unbound_replay_and_rbac(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    headers = _headers(seeded)
    proposal_payload = _proposal_payload(seeded)
    proposal_url = _path(seeded, "proposals")
    assert api_client.post(proposal_url, headers=headers, json={
        **proposal_payload, "actor_id": str(seeded["user"].id),
    }).status_code == 422
    assert api_client.post(proposal_url, headers=headers, json={
        **proposal_payload, "candidate_index": True,
    }).status_code == 422
    seeded["role"].permissions = ["project:read"]
    mapping_db.commit()
    assert api_client.post(proposal_url, headers=headers, json=proposal_payload).status_code == 403
    seeded["role"].permissions = [
        "workbench:edit", "project:read", "project:update",
        "project:preliminary_analysis:finalize",
        "project:preliminary_result:generate", "project:official_intake:commit",
    ]
    mapping_db.commit()

    proposed = api_client.post(proposal_url, headers=headers, json=proposal_payload)
    assert proposed.status_code == 201, proposed.text
    body = proposed.json()
    assert body["review_required"] is True
    assert body["exact_profile_id"] is None
    assert body["similar_profile_ids"] == []
    assert body["mapping_snapshot"]["source"]["source_artifact_id"] == str(seeded["artifact"].id)
    assert api_client.post(proposal_url, headers=headers, json=proposal_payload).json() == body
    assert api_client.post(proposal_url, headers=headers, json={
        **proposal_payload, "candidate_index": 1,
    }).status_code == 409

    confirm_url = _path(seeded, "confirmations")
    confirm_payload = {
        "proposal_decision_id": body["decision_id"],
        "mapping_snapshot": body["mapping_snapshot"],
        "memory_scope": "none", "command_id": str(uuid.uuid4()),
        "expected_selection_revision": 0,
    }
    assert api_client.post(confirm_url, headers=headers, json={
        **confirm_payload, "memory_scope": "organization",
    }).status_code == 422
    assert api_client.post(confirm_url, headers=headers, json={
        **confirm_payload, "mapping_snapshot": {"fields": []},
    }).status_code == 422
    confirmed = api_client.post(confirm_url, headers=headers, json=confirm_payload)
    assert confirmed.status_code == 201, confirmed.text
    assert confirmed.json()["profile_id"] is None
    assert confirmed.json()["memory_scope"] == "none"
    assert api_client.post(confirm_url, headers=headers, json=confirm_payload).json() == confirmed.json()
    assert api_client.post(confirm_url, headers=headers, json={
        **confirm_payload, "memory_scope": "customer",
    }).status_code == 409

    materialize_url = _path(seeded, "materializations")
    materialize_payload = {
        "confirmation_decision_id": confirmed.json()["decision_id"],
        "command_id": str(uuid.uuid4()),
        "expected_selection_revision": 1,
    }
    materialized = api_client.post(materialize_url, headers=headers, json=materialize_payload)
    assert materialized.status_code == 201, materialized.text
    assert materialized.json()["materialized_asset_row_count"] == 3
    assert api_client.post(materialize_url, headers=headers, json=materialize_payload).json() == materialized.json()
    assert api_client.post(materialize_url, headers=headers, json={
        **materialize_payload, "confirmation_decision_id": str(uuid.uuid4()),
    }).status_code == 409
    assert mapping_db.query(ColumnMappingDecision).count() == 2
    assert mapping_db.query(ColumnMappingProfile).count() == 0
    assert mapping_db.query(ColumnMappingProfileUsage).one().customer_id is None


def test_service_current_batch_and_customer_memory_fail_closed(mapping_db):
    seeded = _api_seed(mapping_db)
    project = seeded["project"]
    project.current_preliminary_import_batch_id = None
    mapping_db.commit()
    with pytest.raises(HTTPException) as exc:
        _propose(mapping_db, seeded)
    _error_code(exc, 409, "mapping_batch_not_current")

    other_batch = ProjectAssetImportBatch(
        organization_id=seeded["org"].id, project_id=project.id,
        source_filename="other.xlsx", status="created", created_by_user_id=seeded["user"].id,
    )
    mapping_db.add(other_batch)
    mapping_db.flush()
    project.current_preliminary_import_batch_id = other_batch.id
    mapping_db.commit()
    with pytest.raises(HTTPException) as exc:
        _propose(mapping_db, seeded)
    _error_code(exc, 409, "mapping_batch_not_current")

    project.current_preliminary_import_batch_id = seeded["batch"].id
    mapping_db.commit()
    proposal = _propose(mapping_db, seeded).decision
    with pytest.raises(HTTPException) as exc:
        _confirm(mapping_db, seeded, proposal, scope="customer")
    _error_code(exc, 409, "mapping_customer_required")
    assert mapping_db.query(ColumnMappingDecision).count() == 1
    assert mapping_db.query(ColumnMappingProfile).count() == 0
    assert mapping_db.query(AuditEvent).filter_by(event_name="ColumnMappingConfirmed").count() == 0

    project.current_preliminary_import_batch_id = other_batch.id
    mapping_db.commit()
    with pytest.raises(HTTPException) as exc:
        _confirm(mapping_db, seeded, proposal)
    _error_code(exc, 409, "mapping_batch_not_current")
    with pytest.raises(HTTPException) as exc:
        reject_column_mapping(
            mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
            project_id=project.id, batch_id=seeded["batch"].id,
            proposal_decision_id=proposal.id, command_id=uuid.uuid4(),
        )
    _error_code(exc, 409, "mapping_batch_not_current")


def test_historical_null_customer_and_true_replay_survive_binding_and_intake(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    proposal_key, confirmation_key, usage_key = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    proposal = propose_column_mapping(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, batch_id=seeded["batch"].id,
        artifact_id=seeded["artifact"].id, snapshot_id=seeded["snapshot"].id,
        candidate_index=0, command_id=proposal_key,
    ).decision
    confirmation = _confirm(mapping_db, seeded, proposal, command_id=confirmation_key)
    usage = _materialize(mapping_db, seeded, confirmation, command_id=usage_key)
    bind_preliminary_project_customer(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, customer_id=seeded["customer"].id,
        expected_project_version=seeded["project"].row_version,
        idempotency_key="g11g-bind-after-mapping",
    )
    mapping_db.expire_all()
    assert mapping_db.get(ColumnMappingDecision, proposal.id).customer_id is None
    assert mapping_db.get(ColumnMappingDecision, confirmation.id).customer_id is None
    assert mapping_db.get(ColumnMappingProfileUsage, usage.id).customer_id is None
    analysis = finalize_preliminary_analysis(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        expected_project_version=seeded["project"].row_version,
        import_batch_id=seeded["batch"].id,
        source_artifact_id=seeded["artifact"].id,
        structure_snapshot_id=seeded["snapshot"].id,
        mapping_decision_id=confirmation.id,
        mapping_profile_usage_id=usage.id,
        mapping_decision_digest_sha256=confirmation.mapping_digest_sha256,
        profile_usage_mapping_digest_sha256=usage.mapping_digest_sha256,
        line_manifest=[_line(source_row_number=7)],
        idempotency_key="g11g-analysis-after-bind", confirmed=True,
    )
    assert analysis.customer_id == seeded["customer"].id
    assert analysis.mapping_profile_usage_id == usage.id
    result = generate_preliminary_result_artifact(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        preliminary_analysis_snapshot_id=analysis.id,
        expected_project_version=seeded["project"].row_version,
        idempotency_key="g11g-result-after-bind", confirmed=True,
    )
    pending_source = _pending_reconcile_source(
        mapping_db, seeded, seeded["batch"], generation=2,
    )
    commit_project_official_intake(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id,
        preliminary_result_artifact_id=result.id,
        expected_project_version=seeded["project"].row_version,
        expected_preliminary_result_version=result.version,
        idempotency_key="g11g-intake-after-bind", confirmed=True,
    )
    assert mapping_db.query(ProjectOfficialIntakeCommit).count() == 1
    frozen_source_id = seeded["batch"].current_source_artifact_id
    source_count_before = mapping_db.query(ImportSourceArtifact).count()
    denied_source = api_client.post(
        f"/api/v1/projects/{seeded['project'].id}/asset-imports/"
        f"{seeded['batch'].id}/source-artifacts",
        headers=_headers(seeded),
        files={"file": (
            "after-intake.xlsx", io.BytesIO(_make_xlsx_bytes()),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
    )
    assert denied_source.status_code == 409, denied_source.text
    assert denied_source.json()["detail"]["error_code"] == "source_official_intake_closed"
    assert mapping_db.query(ImportSourceArtifact).count() == source_count_before
    stats = reconcile_source_artifacts(
        mapping_db, storage=seeded["storage"], max_items=10,
        actor_id=seeded["user"].id, org_id=seeded["org"].id,
    )
    assert stats["errors"] == 0
    assert mapping_db.get(ImportSourceArtifact, pending_source.id).state == "orphaned"
    assert seeded["batch"].current_source_artifact_id == frozen_source_id
    management = api_client.get(
        "/api/v1/projects/preliminary-requests", headers=_headers(seeded),
    )
    assert management.status_code == 200, management.text
    assert management.json()["total"] == 0
    assert all(
        item["project_id"] != str(seeded["project"].id)
        for item in management.json()["items"]
    )
    state_after_intake = get_mapping_recovery_state(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, batch_id=seeded["batch"].id,
    )
    assert state_after_intake["official_intake_closed"] is True
    assert state_after_intake["status"] == "materialized"

    assert propose_column_mapping(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, batch_id=seeded["batch"].id,
        artifact_id=seeded["artifact"].id, snapshot_id=seeded["snapshot"].id,
        candidate_index=0, command_id=proposal_key,
    ).decision.id == proposal.id
    assert _confirm(mapping_db, seeded, proposal, command_id=confirmation_key).id == confirmation.id
    assert _materialize(mapping_db, seeded, confirmation, command_id=usage_key).id == usage.id
    with pytest.raises(HTTPException) as exc:
        _propose(mapping_db, seeded)
    _error_code(exc, 409, "mapping_official_intake_closed")
    with pytest.raises(HTTPException) as exc:
        _confirm(mapping_db, seeded, proposal)
    _error_code(exc, 409, "mapping_official_intake_closed")
    with pytest.raises(HTTPException) as exc:
        _materialize(mapping_db, seeded, confirmation)
    _error_code(exc, 409, "mapping_official_intake_closed")
    with pytest.raises(HTTPException) as exc:
        reject_column_mapping(
            mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
            project_id=seeded["project"].id, batch_id=seeded["batch"].id,
            proposal_decision_id=proposal.id, command_id=uuid.uuid4(),
        )
    _error_code(exc, 409, "mapping_official_intake_closed")
    assert mapping_db.query(ColumnMappingDecision).count() == 2
    assert mapping_db.query(ColumnMappingProfileUsage).count() == 1


@pytest.mark.parametrize("scope", ["none", "customer"])
def test_unbound_proposals_remain_current_after_customer_binding(mapping_db, scope):
    seeded = _api_seed(mapping_db)
    confirmed_proposal = _propose(mapping_db, seeded).decision
    rejected_proposal = _propose(mapping_db, seeded).decision
    bind_preliminary_project_customer(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, customer_id=seeded["customer"].id,
        expected_project_version=seeded["project"].row_version,
        idempotency_key=f"g11g-bind-before-decision-{scope}",
    )
    confirmation = _confirm(mapping_db, seeded, confirmed_proposal, scope=scope)
    rejection = reject_column_mapping(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, batch_id=seeded["batch"].id,
        proposal_decision_id=rejected_proposal.id, command_id=uuid.uuid4(),
    )
    mapping_db.expire_all()
    assert mapping_db.get(ColumnMappingDecision, confirmed_proposal.id).customer_id is None
    assert mapping_db.get(ColumnMappingDecision, rejected_proposal.id).customer_id is None
    assert confirmation.customer_id == seeded["customer"].id
    assert rejection.customer_id == seeded["customer"].id
    assert (confirmation.profile_id is not None) == (scope == "customer")


def test_null_customer_confirmation_materializes_after_customer_binding(mapping_db):
    seeded = _api_seed(mapping_db)
    proposal = _propose(mapping_db, seeded).decision
    confirmation = _confirm(mapping_db, seeded, proposal)
    bind_preliminary_project_customer(
        mapping_db, actor=seeded["user"], org_id=seeded["org"].id,
        project_id=seeded["project"].id, customer_id=seeded["customer"].id,
        expected_project_version=seeded["project"].row_version,
        idempotency_key="g11g-bind-before-materialization",
    )
    command_id = uuid.uuid4()
    usage = _materialize(mapping_db, seeded, confirmation, command_id=command_id)
    assert _materialize(mapping_db, seeded, confirmation, command_id=command_id).id == usage.id
    mapping_db.expire_all()
    assert mapping_db.get(ColumnMappingDecision, confirmation.id).customer_id is None
    assert mapping_db.get(ColumnMappingProfileUsage, usage.id).customer_id == seeded["customer"].id


def test_public_mapping_rejects_inactive_and_cross_tenant(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    other = _api_seed(mapping_db)
    url = _path(seeded, "proposals")
    payload = _proposal_payload(seeded)
    headers = _headers(seeded)
    assert api_client.post(_path(other, "proposals"), headers=headers, json=payload).status_code == 404
    foreign_batch_url = (
        f"/api/v1/projects/{seeded['project'].id}/asset-imports/"
        f"{other['batch'].id}/column-mapping/proposals"
    )
    assert api_client.post(foreign_batch_url, headers=headers, json=payload).status_code == 404
    assert api_client.post(url, headers=headers, json={
        **payload, "source_artifact_id": str(other["artifact"].id),
    }).status_code == 404
    assert api_client.post(url, headers=headers, json={
        **payload, "structure_snapshot_id": str(other["snapshot"].id),
    }).status_code == 404
    seeded["batch"].current_source_artifact_id = None
    mapping_db.commit()
    source_stale = api_client.post(url, headers=headers, json=payload)
    assert source_stale.status_code == 409
    assert source_stale.json()["detail"]["error_code"] == "mapping_source_not_current"
    seeded["batch"].current_source_artifact_id = seeded["artifact"].id
    mapping_db.commit()
    seeded["user"].status = UserStatus.INACTIVE
    mapping_db.commit()
    assert api_client.post(url, headers=headers, json=payload).status_code in (401, 403)
    seeded["user"].status = UserStatus.ACTIVE
    seeded["org"].status = OrganizationStatus.INACTIVE
    mapping_db.commit()
    assert api_client.post(url, headers=headers, json=payload).status_code in (401, 403)


def test_public_rejection_requires_proposal_and_preserves_reason(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    headers = _headers(seeded)
    proposal = api_client.post(
        _path(seeded, "proposals"), headers=headers, json=_proposal_payload(seeded),
    )
    assert proposal.status_code == 201, proposal.text
    reject_url = _path(seeded, "rejections")
    payload = {
        "proposal_decision_id": proposal.json()["decision_id"],
        "command_id": str(uuid.uuid4()),
        "reason_code": "wrong_columns", "reason_text": "Cần chọn lại cột tài sản.",
    }
    rejected = api_client.post(reject_url, headers=headers, json=payload)
    assert rejected.status_code == 201, rejected.text
    assert rejected.json()["outcome"] == "rejected"
    assert api_client.post(reject_url, headers=headers, json=payload).json() == rejected.json()
    assert api_client.post(reject_url, headers=headers, json={
        **payload, "reason_code": "other",
    }).status_code == 409
    stored = mapping_db.get(ColumnMappingDecision, uuid.UUID(rejected.json()["decision_id"]))
    assert stored.reason_code == "wrong_columns"
    assert stored.reason_text == "Cần chọn lại cột tài sản."
    assert api_client.post(_path(seeded, "materializations"), headers=headers, json={
        "confirmation_decision_id": rejected.json()["decision_id"],
        "command_id": str(uuid.uuid4()),
        "expected_selection_revision": 0,
    }).status_code == 409
    assert mapping_db.query(ColumnMappingProfileUsage).count() == 0


def test_unbound_project_can_use_approved_organization_template(mapping_db):
    first = _api_seed(mapping_db, unbound=False)
    proposal = _propose(mapping_db, first).decision
    confirmation = _confirm(mapping_db, first, proposal, scope="customer")
    template = mapping_db.get(ColumnMappingProfile, confirmation.profile_id)
    user_id = first["user"].id
    template.approved_by_user_id = user_id
    template.approved_at = datetime.now(timezone.utc)
    template.scope_type = "organization_template"
    template.customer_id = None
    mapping_db.commit()

    second = _seed(
        mapping_db, org=first["org"], user=first["user"], customer=first["customer"],
    )
    second["project"].customer_id = None
    mapping_db.commit()
    result = _propose(mapping_db, second)
    assert result.organization_template_id == template.id
    assert result.exact_profile_id is None
    assert result.similar_profile_ids == ()
    assert result.decision.customer_id is None
