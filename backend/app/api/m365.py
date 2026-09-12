"""Internal OAuth bridge for the OneDrive Personal PR-05 foundation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.auth import get_correlation_id, get_current_session
from app.core.config import get_settings
from app.core.rbac import require_permission
from app.db import get_db
from app.modules.m365_integration.application.connection_service import (
    begin_onedrive_authorization,
    complete_onedrive_authorization,
    require_onedrive_actor,
)
from app.modules.m365_integration.application.provision_document_service import (
    provision_onedrive_document,
)
from app.modules.m365_integration.application.revalidation_service import (
    RevalidationReadiness,
    get_revalidation_readiness,
    revalidate_document,
    resolve_managed_region_definition_set,
    seal_existing_binding_baseline,
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


class M365RevalidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_document_revision_id: uuid.UUID
    expected_document_revision: int = Field(ge=1)
    trigger: Literal["explicit_refresh", "freshness_required_action", "reconnect"]
    idempotency_key: str = Field(min_length=1, max_length=128)


class M365BaselineEnrollmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_document_revision_id: uuid.UUID
    expected_document_revision: int = Field(ge=1)
    binding_id: uuid.UUID
    generated_document_id: uuid.UUID
    idempotency_key: str = Field(min_length=1, max_length=128)


class M365DocumentProvisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_version_id: uuid.UUID
    connection_id: uuid.UUID
    drive_item_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    data_snapshot: dict[str, object]
    idempotency_key: str = Field(min_length=1, max_length=128)


class M365DocumentProvisionResponse(BaseModel):
    document_id: uuid.UUID
    document_revision_id: uuid.UUID
    document_revision: int
    render_job_id: uuid.UUID
    generated_document_id: uuid.UUID
    binding_id: uuid.UUID
    baseline_id: uuid.UUID
    document_type: str
    title: str
    file_name: str
    web_url: str


class M365BaselineEnrollmentResponse(BaseModel):
    baseline_id: uuid.UUID
    document_id: uuid.UUID
    document_revision_id: uuid.UUID
    binding_id: uuid.UUID
    authority_ref: str
    parser_contract_version: str
    fingerprint_contract_version: str
    created_at: datetime


class M365RevalidationResponse(BaseModel):
    observation_id: uuid.UUID
    document_id: uuid.UUID
    document_revision_id: uuid.UUID
    binding_id: uuid.UUID
    classification: str
    affected_region_keys: list[str]
    completed_at: datetime
    reason_category: str | None
    retryable: bool


class M365RevalidationReadinessResponse(BaseModel):
    document_id: uuid.UUID
    document_revision_id: uuid.UUID
    document_revision: int
    binding_id: uuid.UUID
    drive_id: str
    drive_item_id: str
    file_name: str
    file_path: str | None
    web_url: str
    baseline_eligible: bool
    classification: str | None
    completed_at: datetime | None
    affected_region_keys: list[str]
    is_fresh: bool
    is_safe_for_freshness_required_action: bool
    stale_reason: str | None
    blocking_reason: str | None
    next_action: str | None
    retryable: bool


def _components(db: Session):
    settings = get_settings()
    keys, active_version = parse_keyring(
        settings.m365_vault_keys_json.get_secret_value(),
        settings.m365_vault_active_key_version,
    )
    vault = DatabaseCredentialVault(db, keys=keys, active_key_version=active_version)
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


def _readiness_response(
    readiness: RevalidationReadiness,
) -> M365RevalidationReadinessResponse:
    return M365RevalidationReadinessResponse(
        document_id=readiness.document_id,
        document_revision_id=readiness.document_revision_id,
        document_revision=readiness.document_revision,
        binding_id=readiness.binding_id,
        drive_id=readiness.drive_id,
        drive_item_id=readiness.drive_item_id,
        file_name=readiness.file_name,
        file_path=readiness.file_path,
        web_url=readiness.web_url,
        baseline_eligible=readiness.baseline_eligible,
        classification=readiness.classification,
        completed_at=readiness.completed_at,
        affected_region_keys=list(readiness.affected_region_keys),
        is_fresh=readiness.is_fresh,
        is_safe_for_freshness_required_action=(readiness.is_safe_for_freshness_required_action),
        stale_reason=readiness.stale_reason,
        blocking_reason=readiness.blocking_reason,
        next_action=readiness.next_action,
        retryable=readiness.retryable,
    )


@router.post(
    "/projects/{project_id}/documents/provision",
    response_model=M365DocumentProvisionResponse,
    status_code=201,
)
def provision_canonical_onedrive_document(
    project_id: uuid.UUID,
    payload: M365DocumentProvisionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update")),
) -> M365DocumentProvisionResponse:
    vault, oauth, graph = _components(db)
    provisioned = provision_onedrive_document(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        project_id=project_id,
        template_version_id=payload.template_version_id,
        connection_id=payload.connection_id,
        drive_item_id=payload.drive_item_id,
        title=payload.title,
        data_snapshot=payload.data_snapshot,
        idempotency_key=payload.idempotency_key,
        oauth_client=oauth,
        graph_gateway=graph,
        credential_vault=vault,
        correlation_id=get_correlation_id(request),
    )
    return M365DocumentProvisionResponse(**provisioned.__dict__)


@router.post(
    "/projects/{project_id}/documents/{document_id}/revalidation/baseline",
    response_model=M365BaselineEnrollmentResponse,
    status_code=201,
)
def enroll_document_revalidation_baseline(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: M365BaselineEnrollmentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update")),
) -> M365BaselineEnrollmentResponse:
    definition_set = resolve_managed_region_definition_set(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        project_id=project_id,
        document_id=document_id,
        expected_document_revision_id=payload.expected_document_revision_id,
        expected_document_revision=payload.expected_document_revision,
        binding_id=payload.binding_id,
        generated_document_id=payload.generated_document_id,
    )
    vault, oauth, graph = _components(db)
    baseline = seal_existing_binding_baseline(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        project_id=project_id,
        document_id=document_id,
        expected_document_revision_id=payload.expected_document_revision_id,
        expected_document_revision=payload.expected_document_revision,
        binding_id=payload.binding_id,
        definition_set=definition_set,
        idempotency_key=payload.idempotency_key,
        oauth_client=oauth,
        graph_gateway=graph,
        credential_vault=vault,
        correlation_id=get_correlation_id(request),
    )
    return M365BaselineEnrollmentResponse(
        baseline_id=baseline.id,
        document_id=baseline.document_id,
        document_revision_id=baseline.document_revision_id,
        binding_id=baseline.binding_id,
        authority_ref=baseline.authority_ref,
        parser_contract_version=baseline.parser_contract_version,
        fingerprint_contract_version=baseline.fingerprint_contract_version,
        created_at=baseline.created_at,
    )


@router.get(
    "/projects/{project_id}/documents/{document_id}/revalidation",
    response_model=M365RevalidationReadinessResponse,
)
def read_document_revalidation(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read")),
) -> M365RevalidationReadinessResponse:
    readiness = get_revalidation_readiness(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        project_id=project_id,
        document_id=document_id,
    )
    return _readiness_response(readiness)


@router.post(
    "/projects/{project_id}/documents/{document_id}/revalidation",
    response_model=M365RevalidationResponse,
)
def revalidate_onedrive_document(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: M365RevalidationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read")),
) -> M365RevalidationResponse:
    vault, oauth, graph = _components(db)
    observation = revalidate_document(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        project_id=project_id,
        document_id=document_id,
        expected_document_revision_id=payload.expected_document_revision_id,
        expected_document_revision=payload.expected_document_revision,
        trigger=payload.trigger,
        idempotency_key=payload.idempotency_key,
        oauth_client=oauth,
        graph_gateway=graph,
        credential_vault=vault,
        correlation_id=get_correlation_id(request),
    )
    return M365RevalidationResponse(
        observation_id=observation.id,
        document_id=observation.document_id,
        document_revision_id=observation.document_revision_id,
        binding_id=observation.binding_id,
        classification=observation.classification,
        affected_region_keys=list(observation.affected_region_keys),
        completed_at=observation.completed_at,
        reason_category=observation.reason_category,
        retryable=observation.retryable,
    )
