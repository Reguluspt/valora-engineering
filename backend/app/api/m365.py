"""Internal OAuth bridge for the OneDrive Personal PR-05 foundation."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_correlation_id, get_current_session
from app.core.config import get_settings
from app.db import get_db
from app.modules.m365_integration.application.connection_service import (
    begin_onedrive_authorization,
    complete_onedrive_authorization,
    require_onedrive_actor,
)
from app.modules.m365_integration.infrastructure.credential_vault import (
    DatabaseCredentialVault,
    parse_keyring,
)
from app.modules.m365_integration.infrastructure.graph_adapter import MicrosoftGraphGateway
from app.modules.m365_integration.infrastructure.microsoft_oauth import (
    MicrosoftPersonalOAuthClient,
)
from app.modules.project_master_data.models import User, UserSession


router = APIRouter(prefix="/api/v1/m365/onedrive", tags=["m365-internal"])


class OneDriveAuthorizationResponse(BaseModel):
    authorization_url: str


class OneDriveConnectionResponse(BaseModel):
    connection_id: str
    drive_id: str
    status: str


def _components(db: Session):
    settings = get_settings()
    keys, active_version = parse_keyring(
        settings.m365_vault_keys_json.get_secret_value(),
        settings.m365_vault_active_key_version,
    )
    vault = DatabaseCredentialVault(
        db, keys=keys, active_key_version=active_version
    )
    oauth = MicrosoftPersonalOAuthClient(
        client_id=settings.m365_client_id,
        client_secret=settings.m365_client_secret.get_secret_value(),
        redirect_uri=settings.m365_redirect_uri,
    )
    return vault, oauth, MicrosoftGraphGateway()


@router.post("/authorize", response_model=OneDriveAuthorizationResponse)
def authorize_onedrive(
    request: Request,
    db: Session = Depends(get_db),
    session: UserSession = Depends(get_current_session),
) -> OneDriveAuthorizationResponse:
    actor = db.get(User, session.user_id)
    if actor is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "onedrive_user_not_found",
                "detail": "Phiên làm việc không hợp lệ.",
            },
        )
    actor = require_onedrive_actor(
        db,
        organization_id=session.organization_id,
        user_id=actor.id,
    )
    vault, oauth, _ = _components(db)
    authorization_url = begin_onedrive_authorization(
        db,
        actor=actor,
        user_session=session,
        oauth_client=oauth,
        credential_vault=vault,
        correlation_id=get_correlation_id(request),
    )
    return OneDriveAuthorizationResponse(authorization_url=authorization_url)


@router.get("/oauth/callback", response_model=OneDriveConnectionResponse)
def onedrive_oauth_callback(
    request: Request,
    db: Session = Depends(get_db),
) -> OneDriveConnectionResponse:
    vault, oauth, graph = _components(db)
    connection = complete_onedrive_authorization(
        db,
        auth_response=dict(request.query_params),
        oauth_client=oauth,
        graph_gateway=graph,
        credential_vault=vault,
        correlation_id=get_correlation_id(request),
    )
    return OneDriveConnectionResponse(
        connection_id=str(connection.id),
        drive_id=connection.drive_id,
        status=connection.status,
    )
