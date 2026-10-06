"""Thin confirmed preparation commands and snapshot receipt reconciliation."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user
from app.db import get_db
from app.db.session import get_case_state_db
from app.modules.project_master_data.models import User
from app.modules.project_master_data.asset_workbench_schemas import (
    ConfirmProjectAssetWorkbenchRequest, WithdrawProjectAssetWorkbenchConfirmationRequest, WorkbenchCommandResponse,
    WorkbenchPreparationSnapshot,
)
from app.modules.project_master_data.application.asset_workbench_commands import (
    confirm_project_asset_workbench, withdraw_project_asset_workbench_confirmation, read_asset_workbench_receipt,
)


class WorkbenchCommandRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def validate_contract(request: Request):
            try:
                return await handler(request)
            except RequestValidationError:
                raise HTTPException(400, detail="Invalid Asset Workbench command contract") from None

        return validate_contract


router = APIRouter(route_class=WorkbenchCommandRoute)


@router.get("/{project_id}/asset-workbench/preparation", response_model=WorkbenchPreparationSnapshot)
def read_preparation(project_id: uuid.UUID, db: Session = Depends(get_case_state_db),
                     actor: User = Depends(get_current_user)):
    # A7/#122 authorizes this scoped read when Case State cannot supply command metadata.
    from app.modules.project_master_data.application.asset_review_authority import resolve_authority
    from app.modules.project_master_data.application.asset_review_line_commands import require_line_access
    from app.modules.project_master_data.application.asset_review_provider import evaluate_asset_review_provider
    from app.modules.project_master_data.application.asset_workbench_authority import description_ready
    from app.modules.project_master_data.application.asset_line_validation_rules import value

    with db.no_autoflush:
        snapshot = resolve_authority(db, org_id=actor.organization_id, project_id=project_id)
        require_line_access(db, actor=actor, org_id=actor.organization_id, project_id=project_id)
        state = snapshot.workbench
        draft = value(snapshot.project.status) == "draft"
        coherent = bool(snapshot.seal and snapshot.seal_current and snapshot.lineage_current
                        and state.intact and snapshot.lines and all(p.result == "COMPLETE" for p in snapshot.prefix))
        upstream = evaluate_asset_review_provider(snapshot, effective_permissions={"workbench:edit"},
                                                  has_active_session=True)
        return dict(project_id=project_id, case_version=snapshot.case_version,
                    project_row_version=snapshot.project.row_version,
                    seal_id=snapshot.seal.id if coherent else None,
                    authoritative_set_sha256=snapshot.seal.authoritative_set_sha256 if coherent else None,
                    membership_version=snapshot.seal.membership_version if coherent else None,
                    line_versions=[dict(line_id=line.id, row_version=line.row_version) for line in snapshot.lines]
                    if coherent else [], prior_confirmation_id=state.latest.id if state.intact and state.latest else None,
                    withdrawn=state.withdrawn, can_edit_description=draft,
                    can_confirm=bool(coherent and draft and not state.content_current and upstream.result == "COMPLETE"
                                     and all(description_ready(line) for line in snapshot.lines)),
                    can_withdraw=bool(coherent and draft and state.latest and not state.withdrawn))


def _mutate(command, db, actor, project_id, payload):
    try:
        result = command(db, actor=actor, org_id=actor.organization_id, project_id=project_id, request=payload)
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(500, detail="Asset Workbench command failed; reconcile its receipt before retry") from None


@router.post("/{project_id}/asset-workbench/confirm", response_model=WorkbenchCommandResponse)
def confirm_workbench(project_id: uuid.UUID, payload: ConfirmProjectAssetWorkbenchRequest,
                      db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return _mutate(confirm_project_asset_workbench, db, actor, project_id, payload)


@router.post("/{project_id}/asset-workbench/withdraw", response_model=WorkbenchCommandResponse)
def withdraw_workbench(project_id: uuid.UUID, payload: WithdrawProjectAssetWorkbenchConfirmationRequest,
                       db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return _mutate(withdraw_project_asset_workbench_confirmation, db, actor, project_id, payload)


@router.get("/{project_id}/asset-workbench/command-receipts/{command_id}", response_model=WorkbenchCommandResponse)
def read_receipt(project_id: uuid.UUID, command_id: uuid.UUID,
                 db: Session = Depends(get_case_state_db), actor: User = Depends(get_current_user)):
    return read_asset_workbench_receipt(db, actor=actor, org_id=actor.organization_id,
                                      project_id=project_id, command_id=command_id)
