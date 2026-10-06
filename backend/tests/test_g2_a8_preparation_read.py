import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from pydantic import ValidationError
from app.api.asset_workbench import read_preparation
from app.modules.project_master_data.application.asset_workbench_commands import (
    confirm_project_asset_workbench, withdraw_project_asset_workbench_confirmation,
)
from tests.test_g2_asset_workbench import entry_db as _entry_db, line_db as _line_db, workbench_db as _workbench_db, counts, request_for, execute, snapshot
from tests.test_g2_asset_workbench import human_commit, commit_saved, accept_all
from app.modules.project_master_data.schemas import CaseStateStageResponse

entry_db, line_db, workbench_db = _entry_db, _line_db, _workbench_db


def read(db, entry):
    with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as reader:
        return read_preparation(entry["project"].id, reader, entry["user"])


def from_read(preparation, withdrawal=False):
    return dict(command_id=str(uuid.uuid4()), confirm=True,
                contract_version="asset-workbench-withdrawal-v1" if withdrawal else "asset-workbench-confirmation-v1",
                expected_project_row_version=preparation["project_row_version"],
                expected_case_version=preparation["case_version"], expected_seal_id=preparation["seal_id"],
                expected_authoritative_set_sha256=preparation["authoritative_set_sha256"],
                expected_membership_version=preparation["membership_version"],
                expected_line_versions=preparation["line_versions"],
                reason_note="Synthetic explicit reason" if preparation["prior_confirmation_id"] else None,
                **({"expected_confirmation_id": preparation["prior_confirmation_id"]} if withdrawal
                   else {"supersedes_confirmation_id": preparation["prior_confirmation_id"]}))


def test_public_read_constructs_full_set_commands_without_read_writes(workbench_db):
    db, entry = workbench_db
    before = counts(db)
    preparation = read(db, entry)
    assert counts(db) == before and preparation["can_confirm"] and not preparation["can_withdraw"]
    assert {item["line_id"] for item in preparation["line_versions"]} == {line.id for line in snapshot(db, entry).lines}
    confirm_project_asset_workbench(db, actor=entry["user"], org_id=entry["org"].id,
                                   project_id=entry["project"].id, request=from_read(preparation))
    db.commit()
    current = read(db, entry)
    assert not current["can_confirm"] and current["can_withdraw"]
    withdraw_project_asset_workbench_confirmation(db, actor=entry["user"], org_id=entry["org"].id,
                                                 project_id=entry["project"].id, request=from_read(current, True))
    db.commit()
    withdrawn = read(db, entry)
    assert withdrawn["can_confirm"] and not withdrawn["can_withdraw"] and withdrawn["withdrawn"]
    assert withdrawn["prior_confirmation_id"] == current["prior_confirmation_id"]


def test_non_draft_read_does_not_offer_writes_or_erase_completion(workbench_db):
    db, entry = workbench_db
    execute(db, entry, request_for(db, entry))
    snapshot(db, entry).project.status = "archived"
    db.commit()
    preparation = read(db, entry)
    assert not any(preparation[key] for key in ("can_confirm", "can_withdraw", "can_edit_description"))
    assert snapshot(db, entry).workbench.content_current


@pytest.mark.parametrize("mode", ["permission", "session", "tenant"])
def test_read_preserves_command_access_boundary(workbench_db, mode):
    db, entry = workbench_db
    if mode == "permission":
        entry["role"].permissions = ["project:read"]
    elif mode == "session":
        entry["session"].status = "closed"
    db.commit()
    with pytest.raises(HTTPException) as denied:
        if mode == "tenant":
            with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as reader:
                read_preparation(uuid.uuid4(), reader, entry["user"])
        else:
            read(db, entry)
    assert denied.value.status_code in (403, 404)


def test_stale_read_and_public_case_state_support_proof_renewal_and_reconfirm(workbench_db):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.rbac import get_current_user
    from app.db.session import get_case_state_db

    db, entry = workbench_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    version = human_commit(db, entry, "description", "Changed official description")
    commit_saved(db, entry, "description", version)
    db.commit()

    def override_read():
        with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as reader:
            yield reader
    app.dependency_overrides[get_case_state_db] = override_read
    app.dependency_overrides[get_current_user] = lambda: entry["user"]
    try:
        with TestClient(app) as client:
            response = client.get(f'/api/v1/projects/{entry["project"].id}/case-state')
            assert response.status_code == 200
            stage = next(s for s in response.json()["stages"] if s["stage"] == "ASSET_WORKBENCH")
            assert stage["result"] == "STALE"
            assert any(d["reason_code"] == "reconfirmation_required" for d in stage["diagnostics"])
            preparation = client.get(f'/api/v1/projects/{entry["project"].id}/asset-workbench/preparation')
            assert preparation.status_code == 200
            assert not preparation.json()["can_confirm"] and preparation.json()["can_withdraw"]
    finally:
        app.dependency_overrides.pop(get_case_state_db, None)
        app.dependency_overrides.pop(get_current_user, None)
    accept_all(db, entry)
    preparation = read(db, entry)
    assert preparation["can_confirm"] and preparation["prior_confirmation_id"]
    execute(db, entry, from_read(preparation))
    db.commit()
    assert snapshot(db, entry).workbench.content_current


@pytest.mark.parametrize("stage,reason", [
    ("ASSET_REVIEW", "review_rejected"), ("ASSET_WORKBENCH", "review_rejected"),
    ("ASSET_WORKBENCH", "seal_mismatch"), ("ASSET_WORKBENCH", "reconfirmation_required"),
    ("ASSET_WORKBENCH", "confirmation_integrity_conflict"),
])
def test_existing_provider_diagnostics_serialize(stage, reason):
    response = CaseStateStageResponse.model_validate(dict(stage=stage, result="STALE", provider_key=None,
        diagnostics=[dict(stage=stage, reason_code=reason)]))
    assert response.model_dump()["diagnostics"][0]["reason_code"] == reason


@pytest.mark.parametrize("stage,reason", [
    ("ASSET_REVIEW", "reconfirmation_required"), ("PRICE_EVIDENCE", "seal_mismatch"),
    ("ASSET_WORKBENCH", "invented_reason"),
])
def test_diagnostic_schema_does_not_expand_provider_authority(stage, reason):
    with pytest.raises(ValidationError):
        CaseStateStageResponse.model_validate(dict(stage=stage, result="STALE", provider_key=None,
            diagnostics=[dict(stage=stage, reason_code=reason)]))
