"""Project-first whole-set confirmation/withdrawal; caller owns outer transaction."""
import uuid

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.audit import log_audit_event
from app.db.mixins import utc_now
from app.modules.project_master_data.application.asset_review_authority import lock_project, resolve_authority, canonical_digest
from app.modules.project_master_data.application.asset_review_line_commands import require_line_access, conflict
from app.modules.project_master_data.application.asset_review_provider import evaluate_asset_review_provider
from app.modules.project_master_data.application.asset_line_validation_rules import value
from app.modules.project_master_data.application.asset_workbench_authority import (
    content_binding, request_digest, audit_binding, description_ready,
)
from app.modules.project_master_data.asset_workbench_schemas import (
    ConfirmProjectAssetWorkbenchRequest, WithdrawProjectAssetWorkbenchConfirmationRequest, WorkbenchCommandResult,
)
from app.modules.project_master_data.models import (
    AssetWorkbenchCommandReceipt, ProjectAssetWorkbenchConfirmation, ProjectAssetWorkbenchWithdrawal,
)


def _response(snapshot, receipt, *, replayed):
    state = snapshot.workbench
    record = state.records.get(receipt.id)
    if not state.intact or record is None:
        conflict("asset_workbench_receipt_integrity_conflict")
    if isinstance(record, ProjectAssetWorkbenchConfirmation):
        current = bool(state.latest and state.latest.id == record.id and state.content_current)
    else:
        current = bool(state.withdrawn and state.reversal and state.reversal.id == record.id
                       and record.content_binding == content_binding(snapshot))
    return {"result": WorkbenchCommandResult.model_validate(receipt.response_metadata).model_dump(mode="json"),
            "replayed": replayed, "historical": not current, "current_case_version": snapshot.case_version}


def read_asset_workbench_receipt(db, *, actor, org_id, project_id, command_id):
    with db.no_autoflush:
        resolve_authority_snapshot = resolve_authority(db, org_id=org_id, project_id=project_id)
        require_line_access(db, actor=actor, org_id=org_id, project_id=project_id)
        receipt = db.query(AssetWorkbenchCommandReceipt).filter_by(organization_id=org_id,
            project_id=project_id, actor_user_id=actor.id, command_id=command_id).first()
        if not receipt:
            raise HTTPException(404, detail="Command receipt not found")
        return _response(resolve_authority_snapshot, receipt, replayed=False)


def _execute(db, *, actor, org_id, project_id, request):
    lock_project(db, org_id=org_id, project_id=project_id)
    require_line_access(db, actor=actor, org_id=org_id, project_id=project_id)
    snapshot = resolve_authority(db, org_id=org_id, project_id=project_id, locked=True)
    persisted, session = require_line_access(db, actor=actor, org_id=org_id, project_id=project_id, locked=True)
    invocation = request.model_dump(mode="json")
    digest = request_digest(org_id=org_id, actor_id=persisted.id, project_id=project_id, request=invocation)
    receipt = db.query(AssetWorkbenchCommandReceipt).filter_by(organization_id=org_id, command_id=request.command_id).first()
    if receipt:
        if receipt.project_id != project_id or receipt.actor_user_id != persisted.id or receipt.request_sha256 != digest:
            conflict("asset_workbench_command_reuse_conflict")
        return _response(snapshot, receipt, replayed=True)
    if value(snapshot.project.status) != "draft":
        raise HTTPException(400, detail="Project must be DRAFT")
    if (request.expected_project_row_version != snapshot.project.row_version
            or request.expected_case_version != snapshot.case_version
            or not snapshot.seal_current or not snapshot.lineage_current
            or not snapshot.seal or request.expected_seal_id != snapshot.seal.id
            or request.expected_authoritative_set_sha256 != snapshot.seal.authoritative_set_sha256
            or request.expected_membership_version != snapshot.seal.membership_version
            or {item.line_id: item.row_version for item in request.expected_line_versions}
               != {line.id: line.row_version for line in snapshot.lines}
            or any(p.result != "COMPLETE" for p in snapshot.prefix)):
        conflict("asset_workbench_authority_version_conflict")
    state = snapshot.workbench
    if not state.intact:
        conflict("asset_workbench_receipt_integrity_conflict")
    confirming = isinstance(request, ConfirmProjectAssetWorkbenchRequest)
    if confirming:
        if request.supersedes_confirmation_id != (state.latest.id if state.latest else None):
            conflict("asset_workbench_prior_confirmation_conflict")
        if state.content_current:
            conflict("asset_workbench_same_state_conflict")
        upstream = evaluate_asset_review_provider(snapshot, effective_permissions={"workbench:edit"}, has_active_session=True)
        if upstream.result != "COMPLETE" or not all(description_ready(line) for line in snapshot.lines):
            conflict("asset_workbench_preparation_required")
    elif not state.latest or state.withdrawn or request.expected_confirmation_id != state.latest.id:
        conflict("asset_workbench_current_confirmation_required")

    receipt_id, record_id, now = uuid.uuid4(), uuid.uuid4(), utc_now()
    binding = content_binding(snapshot)
    result = WorkbenchCommandResult(command_id=request.command_id, receipt_id=receipt_id,
        project_id=project_id, contract_version=request.contract_version,
        confirmation_id=record_id if confirming else state.latest.id,
        reversal_id=None if confirming else record_id,
        project_row_version=snapshot.project.row_version + 1, created_at=now).model_dump(mode="json")
    receipt = AssetWorkbenchCommandReceipt(id=receipt_id, organization_id=org_id, project_id=project_id,
        actor_user_id=persisted.id, session_id=session.id, created_at=now, command_id=request.command_id,
        contract_version=request.contract_version, request_sha256=digest, response_metadata=result)
    try:
        with db.begin_nested():
            db.add(receipt)
            db.flush()
    except IntegrityError as exc:
        if getattr(getattr(exc.orig, "diag", None), "constraint_name", None) == "uq_aw_receipt_command":
            conflict("asset_workbench_command_reuse_conflict")
        raise
    common = dict(id=record_id, organization_id=org_id, project_id=project_id, actor_user_id=persisted.id,
        session_id=session.id, created_at=now, receipt_id=receipt_id, seal_id=snapshot.seal.id,
        authoritative_set_sha256=snapshot.seal.authoritative_set_sha256, membership_version=snapshot.seal.membership_version,
        contract_version=request.contract_version, content_sha256=canonical_digest(binding), content_binding=binding,
        invocation_binding=invocation, pre_row_version=snapshot.project.row_version,
        post_row_version=snapshot.project.row_version + 1, confirmed=True, reason_note=request.reason_note)
    if confirming:
        record = ProjectAssetWorkbenchConfirmation(**common,
            confirmation_version=state.latest.confirmation_version + 1 if state.latest else 1,
            supersedes_confirmation_id=state.latest.id if state.latest else None,
            prior_reversal_id=state.reversal.id if state.withdrawn else None)
        event, command = "ProjectAssetWorkbenchConfirmed", "ConfirmProjectAssetWorkbench"
    else:
        record = ProjectAssetWorkbenchWithdrawal(**common, confirmation_id=state.latest.id)
        event, command = "ProjectAssetWorkbenchConfirmationWithdrawn", "WithdrawProjectAssetWorkbenchConfirmation"
    db.add(record)
    snapshot.project.row_version += 1
    db.flush()
    log_audit_event(db, event_name=event, command_name=command, entity_type="Project", entity_id=project_id,
        organization_id=org_id, actor_user_id=persisted.id, payload=audit_binding(record, receipt))
    require_line_access(db, actor=actor, org_id=org_id, project_id=project_id, locked=True)
    after = resolve_authority(db, org_id=org_id, project_id=project_id, locked=True)
    return _response(after, receipt, replayed=False)


def _validated_request(schema, request):
    try:
        return schema.model_validate(request)
    except ValidationError:
        raise HTTPException(400, detail="Invalid Asset Workbench command contract") from None


def confirm_project_asset_workbench(db, *, actor, org_id, project_id, request):
    return _execute(db, actor=actor, org_id=org_id, project_id=project_id,
                    request=_validated_request(ConfirmProjectAssetWorkbenchRequest, request))


def withdraw_project_asset_workbench_confirmation(db, *, actor, org_id, project_id, request):
    return _execute(db, actor=actor, org_id=org_id, project_id=project_id,
                    request=_validated_request(WithdrawProjectAssetWorkbenchConfirmationRequest, request))
