"""Internal OAuth bridge for the OneDrive Personal PR-05 foundation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.auth import get_correlation_id, get_current_session
from app.core.config import get_settings
from app.core.rbac import get_current_user, require_permission
from app.db import get_db
from app.modules.m365_integration.application.connection_service import (
    begin_onedrive_authorization,
    complete_onedrive_authorization,
    get_connection_capabilities,
    require_onedrive_actor,
)
from app.modules.m365_integration.application.exchange_import_service import (
    create_docx_export,
    create_docx_working_copy,
    import_inbox_docx,
    import_inbox_xlsx,
    reimport_working_docx,
)
from app.modules.m365_integration.application.exchange_runtime_service import (
    acquire_exchange_runtime,
    resolve_exchange_definition_set,
)
from app.modules.m365_integration.application.provision_document_service import (
    provision_onedrive_document,
)
from app.modules.m365_integration.application.operational_entry_service import (
    AdoptionOptions,
    OperationalDocument,
    get_adoption_options,
    list_operational_documents,
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
from app.modules.document_workspace.infrastructure.document_blob_store_factory import (
    build_document_blob_store,
)
from app.modules.m365_integration.models import M365ExchangeArtifact, OneDriveConnection
from app.modules.project_master_data.models import Project, User, UserSession


router = APIRouter(prefix="/api/v1/m365/onedrive", tags=["m365-internal"])


class OneDriveAuthorizationResponse(BaseModel):
    authorization_url: str


class OneDriveConnectionStatusResponse(BaseModel):
    connection_id: uuid.UUID | None
    drive_id: str | None
    status: Literal["not_connected", "active", "error", "revoked"]
    last_verified_at: datetime | None
    capability_state: Literal[
        "read-only", "exchange-write-ready", "reconsent-required"
    ]
    read_available: bool
    appfolder_write_available: bool


class M365AdoptionTemplateResponse(BaseModel):
    template_version_id: uuid.UUID
    template_name: str
    document_type: str
    version_number: int


class M365DriveEntryResponse(BaseModel):
    drive_item_id: str
    kind: Literal["folder", "docx"]
    name: str
    size_bytes: int | None
    last_modified_at: datetime | None
    web_url: str | None


class M365AdoptionOptionsResponse(BaseModel):
    project_id: uuid.UUID
    project_code: str
    project_name: str
    connection_id: uuid.UUID
    drive_id: str
    parent_item_id: str | None
    data_snapshot: dict[str, object]
    templates: list[M365AdoptionTemplateResponse]
    items: list[M365DriveEntryResponse]
    truncated: bool


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
    recovery_code: str | None
    classification: str | None
    completed_at: datetime | None
    affected_region_keys: list[str]
    is_fresh: bool
    is_safe_for_freshness_required_action: bool
    stale_reason: str | None
    blocking_reason: str | None
    next_action: str | None
    retryable: bool


class M365OperationalDocumentResponse(BaseModel):
    document_id: uuid.UUID
    title: str
    document_type: str
    readiness: M365RevalidationReadinessResponse


class M365ExchangeArtifactResponse(BaseModel):
    artifact_id: uuid.UUID
    connection_id: uuid.UUID
    role: Literal["inbox", "working", "export"]
    media: Literal["docx", "xlsx"]
    state: str
    display_name: str
    document_id: uuid.UUID | None
    document_revision_id: uuid.UUID | None
    excel_import_batch_id: uuid.UUID | None
    excel_source_artifact_id: uuid.UUID | None


class M365ExchangeDocxImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_id: uuid.UUID
    drive_item_id: str = Field(min_length=1, max_length=255)
    template_version_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=1, max_length=128)


class M365ExchangeXlsxImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_id: uuid.UUID
    drive_item_id: str = Field(min_length=1, max_length=255)
    batch_id: uuid.UUID


class M365ExchangeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_id: uuid.UUID
    destination_name: str = Field(min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=1, max_length=128)


class M365ExchangeReimportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_version_id: uuid.UUID | None = None


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


def _exchange_artifact_response(
    artifact: M365ExchangeArtifact,
) -> M365ExchangeArtifactResponse:
    return M365ExchangeArtifactResponse(
        artifact_id=artifact.id,
        connection_id=artifact.connection_id,
        role=artifact.role,
        media=artifact.media,
        state=artifact.state,
        display_name=artifact.display_name,
        document_id=artifact.document_id,
        document_revision_id=artifact.document_revision_id,
        excel_import_batch_id=artifact.excel_import_batch_id,
        excel_source_artifact_id=artifact.excel_source_artifact_id,
    )


def _retention_window() -> tuple[datetime, datetime]:
    anchor = datetime.now(timezone.utc)
    try:
        minimum = anchor.replace(year=anchor.year + 10)
    except ValueError:
        minimum = anchor.replace(year=anchor.year + 10, day=28)
    return anchor, minimum


@router.post("/authorize", response_model=OneDriveAuthorizationResponse)
def authorize_onedrive(
    request: Request,
    scope_profile: Literal["read_only", "exchange_write"] = "read_only",
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
        scope_profile=scope_profile,
        correlation_id=get_correlation_id(request),
    )
    return OneDriveAuthorizationResponse(authorization_url=authorization_url)


def _frontend_return_uri(result: str, reason: str | None = None) -> str:
    settings = get_settings()
    target = urlsplit(settings.m365_frontend_return_uri)
    if (
        target.scheme not in {"http", "https"}
        or not target.hostname
        or target.username is not None
        or target.password is not None
    ):
        raise RuntimeError("M365_FRONTEND_RETURN_URI is invalid.")
    target_origin = f"{target.scheme}://{target.netloc}"
    allowed_origins = {origin.rstrip("/") for origin in settings.parsed_cors_origins}
    if target_origin not in allowed_origins:
        raise RuntimeError("M365_FRONTEND_RETURN_URI origin is not allowed.")
    parameters = {"m365": result}
    if reason:
        parameters["reason"] = reason
    if target.fragment:
        route, separator, existing_query = target.fragment.partition("?")
        fragment_query = dict(parse_qsl(existing_query)) if separator else {}
        fragment_query.update(parameters)
        fragment = f"{route}?{urlencode(fragment_query)}"
        return urlunsplit((target.scheme, target.netloc, target.path, target.query, fragment))
    query = dict(parse_qsl(target.query))
    query.update(parameters)
    return urlunsplit((target.scheme, target.netloc, target.path, urlencode(query), ""))


def _callback_reason(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        candidate = detail.get("error_code")
        if isinstance(candidate, str) and candidate.startswith("onedrive_"):
            return candidate[:64]
    return "onedrive_callback_failed"


@router.get("/oauth/callback", response_class=RedirectResponse)
def onedrive_oauth_callback(
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    success_location = _frontend_return_uri("connected")
    vault, oauth, graph = _components(db)
    try:
        complete_onedrive_authorization(
            db,
            auth_response=dict(request.query_params),
            oauth_client=oauth,
            graph_gateway=graph,
            credential_vault=vault,
            correlation_id=get_correlation_id(request),
        )
        location = success_location
    except HTTPException as exc:
        location = _frontend_return_uri("failed", _callback_reason(exc))
    return RedirectResponse(location, status_code=303)


@router.get("/connection", response_model=OneDriveConnectionStatusResponse)
def read_onedrive_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OneDriveConnectionStatusResponse:
    connection = (
        db.query(OneDriveConnection)
        .filter(
            OneDriveConnection.organization_id == current_user.organization_id,
            OneDriveConnection.user_id == current_user.id,
        )
        .first()
    )
    if connection is None:
        return OneDriveConnectionStatusResponse(
            connection_id=None,
            drive_id=None,
            status="not_connected",
            last_verified_at=None,
            capability_state="reconsent-required",
            read_available=False,
            appfolder_write_available=False,
        )
    read_available, appfolder_write_available = get_connection_capabilities(
        db,
        organization_id=current_user.organization_id,
        connection_id=connection.id,
    )
    if connection.status != "active":
        read_available = False
        appfolder_write_available = False
    if read_available and appfolder_write_available:
        capability_state = "exchange-write-ready"
    elif read_available:
        capability_state = "read-only"
    else:
        capability_state = "reconsent-required"
    return OneDriveConnectionStatusResponse(
        connection_id=connection.id,
        drive_id=connection.drive_id,
        status=connection.status,
        last_verified_at=connection.last_verified_at,
        capability_state=capability_state,
        read_available=read_available,
        appfolder_write_available=appfolder_write_available,
    )


@router.get(
    "/projects/{project_id}/exchange/artifacts",
    response_model=list[M365ExchangeArtifactResponse],
)
def read_exchange_artifacts(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update")),
) -> list[M365ExchangeArtifactResponse]:
    project_exists = (
        db.query(Project.id)
        .filter(
            Project.id == project_id,
            Project.organization_id == current_user.organization_id,
        )
        .first()
    )
    if project_exists is None:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "project_not_found", "detail": "Không tìm thấy hồ sơ."},
        )
    artifacts = (
        db.query(M365ExchangeArtifact)
        .filter(
            M365ExchangeArtifact.organization_id == current_user.organization_id,
            M365ExchangeArtifact.project_id == project_id,
        )
        .order_by(M365ExchangeArtifact.observed_at.desc(), M365ExchangeArtifact.id)
        .all()
    )
    return [_exchange_artifact_response(artifact) for artifact in artifacts]


@router.post(
    "/projects/{project_id}/exchange/import-docx",
    response_model=M365ExchangeArtifactResponse,
    status_code=201,
)
async def import_exchange_docx(
    project_id: uuid.UUID,
    payload: M365ExchangeDocxImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update")),
) -> M365ExchangeArtifactResponse:
    document_type, definition_set = resolve_exchange_definition_set(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        project_id=project_id,
        template_version_id=payload.template_version_id,
    )
    vault, oauth, graph = _components(db)
    runtime = acquire_exchange_runtime(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        connection_id=payload.connection_id,
        oauth_client=oauth,
        credential_vault=vault,
    )
    blob_store = build_document_blob_store(get_settings())
    anchor, minimum = _retention_window()
    _, _, artifact = await import_inbox_docx(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        project_id=project_id,
        connection_id=runtime.connection.id,
        drive_item_id=payload.drive_item_id,
        document_type=document_type,
        title=payload.title,
        definition_set=definition_set,
        idempotency_key=payload.idempotency_key,
        graph_gateway=graph,
        access_token=runtime.access_token,
        blob_store=blob_store,
        storage_profile_id=f"exchange-{blob_store.provider_kind}",
        container_name="valora-document-blobs",
        retention_policy_code="official-document-10y",
        retention_anchor_at=anchor,
        minimum_retain_until=minimum,
    )
    return _exchange_artifact_response(artifact)


@router.post(
    "/projects/{project_id}/exchange/import-xlsx",
    response_model=M365ExchangeArtifactResponse,
    status_code=201,
)
def import_exchange_xlsx(
    project_id: uuid.UUID,
    payload: M365ExchangeXlsxImportRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update")),
) -> M365ExchangeArtifactResponse:
    vault, oauth, graph = _components(db)
    runtime = acquire_exchange_runtime(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        connection_id=payload.connection_id,
        oauth_client=oauth,
        credential_vault=vault,
    )
    artifact = import_inbox_xlsx(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        project_id=project_id,
        connection_id=runtime.connection.id,
        batch_id=payload.batch_id,
        drive_item_id=payload.drive_item_id,
        graph_gateway=graph,
        access_token=runtime.access_token,
        request=request,
    )
    return _exchange_artifact_response(artifact)


async def _create_exchange_copy(
    *,
    role: Literal["working", "export"],
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: M365ExchangeCreateRequest,
    db: Session,
    current_user: User,
) -> M365ExchangeArtifactResponse:
    vault, oauth, graph = _components(db)
    runtime = acquire_exchange_runtime(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        connection_id=payload.connection_id,
        oauth_client=oauth,
        credential_vault=vault,
    )
    blob_store = build_document_blob_store(get_settings())
    command = create_docx_working_copy if role == "working" else create_docx_export
    artifact = await command(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        project_id=project_id,
        connection_id=runtime.connection.id,
        document_id=document_id,
        destination_name=payload.destination_name,
        idempotency_key=payload.idempotency_key,
        graph_gateway=graph,
        access_token=runtime.access_token,
        blob_store=blob_store,
    )
    if artifact is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "exchange_provider_unavailable",
                "detail": "OneDrive Exchange tạm thời không khả dụng.",
            },
        )
    return _exchange_artifact_response(artifact)


@router.post(
    "/projects/{project_id}/documents/{document_id}/exchange/working",
    response_model=M365ExchangeArtifactResponse,
    status_code=201,
)
async def create_exchange_working_copy(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: M365ExchangeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update")),
) -> M365ExchangeArtifactResponse:
    return await _create_exchange_copy(
        role="working",
        project_id=project_id,
        document_id=document_id,
        payload=payload,
        db=db,
        current_user=current_user,
    )


@router.post(
    "/projects/{project_id}/documents/{document_id}/exchange/export",
    response_model=M365ExchangeArtifactResponse,
    status_code=201,
)
async def create_exchange_export(
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: M365ExchangeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update")),
) -> M365ExchangeArtifactResponse:
    return await _create_exchange_copy(
        role="export",
        project_id=project_id,
        document_id=document_id,
        payload=payload,
        db=db,
        current_user=current_user,
    )


@router.post(
    "/projects/{project_id}/exchange/artifacts/{artifact_id}/reimport",
    response_model=M365ExchangeArtifactResponse,
)
async def reimport_exchange_artifact(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    payload: M365ExchangeReimportRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update")),
) -> M365ExchangeArtifactResponse:
    artifact = (
        db.query(M365ExchangeArtifact)
        .filter(
            M365ExchangeArtifact.id == artifact_id,
            M365ExchangeArtifact.organization_id == current_user.organization_id,
            M365ExchangeArtifact.project_id == project_id,
            M365ExchangeArtifact.role.in_(("inbox", "working")),
        )
        .first()
    )
    if artifact is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "exchange_artifact_not_found",
                "detail": "Không tìm thấy tệp Exchange.",
            },
        )
    vault, oauth, graph = _components(db)
    runtime = acquire_exchange_runtime(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        connection_id=artifact.connection_id,
        oauth_client=oauth,
        credential_vault=vault,
    )
    if artifact.media == "xlsx":
        if artifact.excel_import_batch_id is None:
            raise HTTPException(status_code=409, detail="Exchange XLSX lineage is incomplete.")
        updated = import_inbox_xlsx(
            db,
            actor=current_user,
            organization_id=current_user.organization_id,
            project_id=project_id,
            connection_id=runtime.connection.id,
            batch_id=artifact.excel_import_batch_id,
            drive_item_id=artifact.drive_item_id,
            graph_gateway=graph,
            access_token=runtime.access_token,
            request=request,
            reimport=True,
        )
        return _exchange_artifact_response(updated)
    if payload.template_version_id is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "exchange_template_authority_required",
                "detail": "Cần chọn mẫu DOCX đã phê duyệt.",
            },
        )
    _, definition_set = resolve_exchange_definition_set(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        project_id=project_id,
        template_version_id=payload.template_version_id,
    )
    blob_store = build_document_blob_store(get_settings())
    anchor, minimum = _retention_window()
    result = await reimport_working_docx(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        project_id=project_id,
        artifact_id=artifact.id,
        definition_set=definition_set,
        idempotency_key=f"exchange-reimport-{artifact.id}-{artifact.e_tag}"[:128],
        graph_gateway=graph,
        access_token=runtime.access_token,
        blob_store=blob_store,
        storage_profile_id=f"exchange-{blob_store.provider_kind}",
        container_name="valora-document-blobs",
        retention_policy_code="official-document-10y",
        retention_anchor_at=anchor,
        minimum_retain_until=minimum,
    )
    return _exchange_artifact_response(result.artifact)


def _adoption_options_response(options: AdoptionOptions) -> M365AdoptionOptionsResponse:
    return M365AdoptionOptionsResponse(
        project_id=options.project_id,
        project_code=options.project_code,
        project_name=options.project_name,
        connection_id=options.connection_id,
        drive_id=options.drive_id,
        parent_item_id=options.parent_item_id,
        data_snapshot=options.data_snapshot,
        templates=[M365AdoptionTemplateResponse(**item.__dict__) for item in options.templates],
        items=[M365DriveEntryResponse(**item.__dict__) for item in options.items],
        truncated=options.truncated,
    )


@router.get(
    "/projects/{project_id}/adoption-options",
    response_model=M365AdoptionOptionsResponse,
)
def read_adoption_options(
    project_id: uuid.UUID,
    parent_item_id: str | None = Query(default=None, min_length=1, max_length=255),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update")),
) -> M365AdoptionOptionsResponse:
    vault, oauth, graph = _components(db)
    options = get_adoption_options(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        project_id=project_id,
        parent_item_id=parent_item_id,
        oauth_client=oauth,
        graph_gateway=graph,
        credential_vault=vault,
    )
    return _adoption_options_response(options)


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
        recovery_code=readiness.recovery_code,
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


def _operational_document_response(
    document: OperationalDocument,
) -> M365OperationalDocumentResponse:
    return M365OperationalDocumentResponse(
        document_id=document.document_id,
        title=document.title,
        document_type=document.document_type,
        readiness=_readiness_response(document.readiness),
    )


@router.get(
    "/projects/{project_id}/documents",
    response_model=list[M365OperationalDocumentResponse],
)
def read_operational_documents(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read")),
) -> list[M365OperationalDocumentResponse]:
    documents = list_operational_documents(
        db,
        actor=current_user,
        organization_id=current_user.organization_id,
        project_id=project_id,
    )
    return [_operational_document_response(document) for document in documents]


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
