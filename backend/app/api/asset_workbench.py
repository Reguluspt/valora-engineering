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
