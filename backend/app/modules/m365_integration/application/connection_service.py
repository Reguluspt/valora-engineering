"""Single-use OneDrive Personal authorization and connection activation."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Mapping

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.audit import log_audit_event
from app.core.rbac import derive_effective_permissions
from app.modules.m365_integration.domain.credential_vault import M365CredentialVault
from app.modules.m365_integration.domain.graph_gateway import M365GraphGateway, M365OAuthClient
from app.modules.m365_integration.models import M365OAuthState, OneDriveConnection
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserRole,
    UserSession,
    UserStatus,
)


ONEDRIVE_CONNECT_PERMISSION = "project:update"
EVENT_ONEDRIVE_AUTHORIZATION_STARTED = "ONEDRIVE_AUTHORIZATION_STARTED"
EVENT_ONEDRIVE_CONNECTION_ACTIVATED = "ONEDRIVE_CONNECTION_ACTIVATED"


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _abort(db: Session, status: int, code: str, detail: str) -> None:
    db.rollback()
    raise _error(status, code, detail)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _state_hash(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def require_onedrive_actor(
    db: Session, *, organization_id: uuid.UUID, user_id: uuid.UUID
) -> User:
    actor = (
        db.query(User)
        .options(
            selectinload(User.organization),
            selectinload(User.roles).selectinload(UserRole.role),
        )
        .filter(User.id == user_id, User.organization_id == organization_id)
        .populate_existing()
        .first()
    )
    organization = db.get(OrganizationProfile, organization_id)
    if (
        actor is None
        or organization is None
        or str(getattr(actor.status, "value", actor.status)) != UserStatus.ACTIVE.value
        or str(getattr(organization.status, "value", organization.status))
        != OrganizationStatus.ACTIVE.value
        or ONEDRIVE_CONNECT_PERMISSION not in derive_effective_permissions(actor, db)
    ):
        _abort(db, 403, "onedrive_forbidden", "Không thể thực hiện thao tác này.")
    return actor


def begin_onedrive_authorization(
    db: Session,
    *,
    actor: User,
    user_session: UserSession,
    oauth_client: M365OAuthClient,
    credential_vault: M365CredentialVault,
    correlation_id: str | None = None,
) -> str:
    """Create a single-use state and return the Microsoft authorization URL."""
    organization_id = actor.organization_id
    if (
        user_session.user_id != actor.id
        or user_session.organization_id != organization_id
        or user_session.status != "active"
    ):
        _abort(db, 403, "onedrive_session_mismatch", "Phiên làm việc không hợp lệ.")
    actor = require_onedrive_actor(
        db, organization_id=organization_id, user_id=actor.id
    )
    try:
        start = oauth_client.begin()
    except Exception as exc:
        db.rollback()
        raise _error(
            503, "onedrive_oauth_unavailable", "Không thể kết nối Microsoft."
        ) from exc

    flow_credential_id = credential_vault.store(
        organization_id=organization_id,
        user_id=actor.id,
        purpose="oauth_flow",
        plaintext=start.flow_material,
    )
    authorization_state = M365OAuthState(
        organization_id=organization_id,
        user_id=actor.id,
        user_session_id=user_session.id,
        state_hash=_state_hash(start.state),
        flow_credential_id=flow_credential_id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(authorization_state)
    log_audit_event(
        db,
        event_name=EVENT_ONEDRIVE_AUTHORIZATION_STARTED,
        entity_type="M365OAuthState",
        entity_id=authorization_state.id,
        organization_id=organization_id,
        actor_user_id=actor.id,
        command_name="BeginOneDriveAuthorization",
        correlation_id=correlation_id,
        payload={"provider": "microsoft", "account_type": "personal"},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _error(
            409, "onedrive_authorization_conflict", "Không thể bắt đầu kết nối Microsoft."
        ) from exc
    return start.authorization_url


def _consume_authorization_state(
    db: Session,
    *,
    state: str,
    credential_vault: M365CredentialVault,
) -> tuple[uuid.UUID, uuid.UUID, bytes]:
    authorization_state = (
        db.query(M365OAuthState)
        .filter(M365OAuthState.state_hash == _state_hash(state))
        .with_for_update()
        .populate_existing()
        .first()
    )
    now = datetime.now(timezone.utc)
    if (
        authorization_state is None
        or authorization_state.consumed_at is not None
        or _utc(authorization_state.expires_at) <= now
        or authorization_state.flow_credential_id is None
    ):
        _abort(db, 400, "onedrive_oauth_state_invalid", "Kết nối Microsoft đã hết hạn.")

    session = (
        db.query(UserSession)
        .filter(
            UserSession.id == authorization_state.user_session_id,
            UserSession.user_id == authorization_state.user_id,
            UserSession.organization_id == authorization_state.organization_id,
            UserSession.status == "active",
        )
        .first()
    )
    if session is None or _utc(session.absolute_expires_at) <= now:
        _abort(db, 400, "onedrive_oauth_session_invalid", "Phiên kết nối đã hết hạn.")

    credential_id = authorization_state.flow_credential_id
    material = credential_vault.load(
        organization_id=authorization_state.organization_id,
        user_id=authorization_state.user_id,
        credential_id=credential_id,
        purpose="oauth_flow",
    )
    organization_id = authorization_state.organization_id
    user_id = authorization_state.user_id
    authorization_state.consumed_at = now
    authorization_state.flow_credential_id = None
    db.flush()
    credential_vault.delete(
        organization_id=organization_id,
        user_id=user_id,
        credential_id=credential_id,
        purpose="oauth_flow",
    )
    db.commit()
    return organization_id, user_id, material


def complete_onedrive_authorization(
    db: Session,
    *,
    auth_response: Mapping[str, str],
    oauth_client: M365OAuthClient,
    graph_gateway: M365GraphGateway,
    credential_vault: M365CredentialVault,
    correlation_id: str | None = None,
) -> OneDriveConnection:
    """Consume callback state, verify the personal drive, then activate the connection."""
    state = auth_response.get("state")
    if not isinstance(state, str) or not state:
        _abort(db, 400, "onedrive_oauth_state_missing", "Thiếu trạng thái kết nối Microsoft.")

    organization_id, user_id, flow_material = _consume_authorization_state(
        db, state=state, credential_vault=credential_vault
    )
    try:
        authorization = oauth_client.complete(
            flow_material=flow_material, auth_response=auth_response
        )
        drive = graph_gateway.get_default_drive(access_token=authorization.access_token)
    except Exception as exc:
        raise _error(
            502, "onedrive_authorization_failed", "Không thể xác minh OneDrive Personal."
        ) from exc
    if drive.drive_type != "personal":
        raise _error(
            409, "onedrive_account_type_mismatch", "Tài khoản không phải OneDrive Personal."
        )

    actor = require_onedrive_actor(db, organization_id=organization_id, user_id=user_id)
    connection = (
        db.query(OneDriveConnection)
        .filter(
            OneDriveConnection.organization_id == organization_id,
            OneDriveConnection.user_id == user_id,
        )
        .with_for_update()
        .populate_existing()
        .first()
    )
    if connection is None:
        credential_id = credential_vault.store(
            organization_id=organization_id,
            user_id=user_id,
            purpose="token_cache",
            plaintext=authorization.token_cache,
        )
        connection = OneDriveConnection(
            organization_id=organization_id,
            user_id=user_id,
            consumer_issuer=authorization.consumer_issuer,
            microsoft_account_subject=authorization.microsoft_account_subject,
            drive_id=drive.drive_id,
            credential_id=credential_id,
            status="active",
            last_verified_at=datetime.now(timezone.utc),
        )
        db.add(connection)
    else:
        if (
            connection.consumer_issuer != authorization.consumer_issuer
            or connection.microsoft_account_subject
            != authorization.microsoft_account_subject
            or connection.drive_id != drive.drive_id
        ):
            _abort(
                db,
                409,
                "onedrive_account_switch_forbidden",
                "Tài khoản Microsoft không khớp kết nối hiện tại.",
            )
        credential_vault.replace(
            organization_id=organization_id,
            user_id=user_id,
            credential_id=connection.credential_id,
            purpose="token_cache",
            plaintext=authorization.token_cache,
        )
        connection.status = "active"
        connection.last_verified_at = datetime.now(timezone.utc)

    db.flush()
    log_audit_event(
        db,
        event_name=EVENT_ONEDRIVE_CONNECTION_ACTIVATED,
        entity_type="OneDriveConnection",
        entity_id=connection.id,
        organization_id=organization_id,
        actor_user_id=actor.id,
        command_name="CompleteOneDriveAuthorization",
        correlation_id=correlation_id,
        payload={"drive_id": drive.drive_id, "account_type": "personal"},
    )
    try:
        db.commit()
        db.refresh(connection)
        return connection
    except IntegrityError as exc:
        db.rollback()
        raise _error(
            409, "onedrive_connection_conflict", "Kết nối OneDrive đã thay đổi đồng thời."
        ) from exc
