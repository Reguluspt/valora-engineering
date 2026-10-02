"""Thin A4 endpoints with scoped command-contract HTTP 400 validation."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user
from app.db import get_db
from app.db.session import get_case_state_db
from app.modules.project_master_data.models import User
from app.modules.project_master_data.asset_review_line_schemas import (
    ValidateProjectAssetLineRequest, DecideProjectAssetLineReviewRequest, LineCommandResponse,
)
from app.modules.project_master_data.application.asset_review_line_commands import (
    validate_project_asset_line, decide_project_asset_line_review, read_asset_review_receipt,
)


class LineCommandRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def validate_contract(request: Request):
            try:
                return await handler(request)
            except RequestValidationError:
                raise HTTPException(400, detail="Invalid Asset Review command contract") from None

        return validate_contract


router = APIRouter(route_class=LineCommandRoute)


def _mutate(command, db, actor, project_id, line_id, payload):
    try:
        result = command(db, actor=actor, org_id=actor.organization_id,
                         project_id=project_id, line_id=line_id, request=payload)
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(500, detail="Asset Review command failed; reconcile its receipt before retry") from None


@router.post("/{project_id}/asset-lines/{line_id}/validate", response_model=LineCommandResponse)
def validate_line(project_id: uuid.UUID, line_id: uuid.UUID, payload: ValidateProjectAssetLineRequest,
                  db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return _mutate(validate_project_asset_line, db, actor, project_id, line_id, payload)


@router.post("/{project_id}/asset-lines/{line_id}/review-decision", response_model=LineCommandResponse)
def decide_line(project_id: uuid.UUID, line_id: uuid.UUID, payload: DecideProjectAssetLineReviewRequest,
                db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return _mutate(decide_project_asset_line_review, db, actor, project_id, line_id, payload)


@router.get("/{project_id}/asset-lines/{line_id}/command-receipts/{command_id}", response_model=LineCommandResponse)
def read_receipt(project_id: uuid.UUID, line_id: uuid.UUID, command_id: uuid.UUID,
                 db: Session = Depends(get_case_state_db), actor: User = Depends(get_current_user)):
    return read_asset_review_receipt(db, actor=actor, org_id=actor.organization_id,
        project_id=project_id, line_id=line_id, command_id=command_id)
