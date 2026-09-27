"""Runtime authority and credential resolution for explicit Exchange commands."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.m365_integration.application.connection_service import (
    get_connection_capabilities,
    require_onedrive_actor,
)
from app.modules.m365_integration.application.revalidation_service import (
    definition_set_from_template_manifest,
)
from app.modules.m365_integration.domain.credential_vault import M365CredentialVault
from app.modules.m365_integration.domain.graph_gateway import M365OAuthClient
from app.modules.m365_integration.domain.managed_regions import ManagedRegionDefinitionSet
from app.modules.m365_integration.models import OneDriveConnection
from app.modules.project_master_data.models import (
    DocumentTemplate,
    DocumentTemplateStatus,
    Project,
    TemplateVersion,
    TemplateVersionStatus,
    User,
)


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


@dataclass(frozen=True)
class ExchangeRuntime:
    connection: OneDriveConnection
    access_token: str


def acquire_exchange_runtime(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    connection_id: uuid.UUID,
    oauth_client: M365OAuthClient,
    credential_vault: M365CredentialVault,
) -> ExchangeRuntime:
    """Resolve exact AppFolder capability and a short-lived delegated token."""
    actor = require_onedrive_actor(
        db, organization_id=organization_id, user_id=actor.id
    )
    connection = (
        db.query(OneDriveConnection)
        .filter(
            OneDriveConnection.organization_id == organization_id,
            OneDriveConnection.id == connection_id,
            OneDriveConnection.user_id == actor.id,
            OneDriveConnection.status == "active",
        )
        .first()
    )
    if connection is None:
        db.rollback()
        raise _error(404, "exchange_connection_not_found", "Không tìm thấy kết nối OneDrive.")
    read_available, write_available = get_connection_capabilities(
        db, organization_id=organization_id, connection_id=connection_id
    )
    if not read_available or not write_available:
        db.rollback()
        raise _error(409, "exchange_reconsent_required", "Cần cấp quyền Exchange.")
    try:
        old_cache = credential_vault.load(
            organization_id=organization_id,
            user_id=actor.id,
            credential_id=connection.credential_id,
            purpose="token_cache",
        )
        token = oauth_client.acquire_access_token(
            token_cache=old_cache,
            scope_profile="exchange_write",
        )
        if token.token_cache != old_cache:
            credential_vault.replace(
                organization_id=organization_id,
                user_id=actor.id,
                credential_id=connection.credential_id,
                purpose="token_cache",
                plaintext=token.token_cache,
            )
        db.commit()
        return ExchangeRuntime(connection=connection, access_token=token.access_token)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise _error(
            502,
            "exchange_token_unavailable",
            "Không thể làm mới quyền truy cập Exchange.",
        ) from exc


def resolve_exchange_definition_set(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    template_version_id: uuid.UUID,
    document_type: str | None = None,
) -> tuple[str, ManagedRegionDefinitionSet]:
    """Resolve an active server-owned DOCX template manifest for Exchange."""
    actor = require_onedrive_actor(
        db, organization_id=organization_id, user_id=actor.id
    )
    del actor
    project = db.query(Project.id).filter(
        Project.organization_id == organization_id,
        Project.id == project_id,
    ).first()
    authority = (
        db.query(TemplateVersion, DocumentTemplate)
        .join(
            DocumentTemplate,
            TemplateVersion.document_template_id == DocumentTemplate.id,
        )
        .filter(
            TemplateVersion.id == template_version_id,
            TemplateVersion.template_format == "docx",
            TemplateVersion.status == TemplateVersionStatus.ACTIVE,
            DocumentTemplate.organization_id == organization_id,
            DocumentTemplate.status == DocumentTemplateStatus.ACTIVE,
        )
        .first()
    )
    if project is None or authority is None:
        db.rollback()
        raise _error(
            404,
            "exchange_template_authority_not_found",
            "Không tìm thấy mẫu DOCX đã phê duyệt.",
        )
    template_version, template = authority
    if document_type is not None and template.document_type != document_type:
        db.rollback()
        raise _error(
            409,
            "exchange_template_authority_mismatch",
            "Loại tài liệu không khớp mẫu đã phê duyệt.",
        )
    try:
        definition_set = definition_set_from_template_manifest(
            template_version_id=template_version.id,
            manifest=template_version.placeholder_manifest,
        )
    except ValueError as exc:
        db.rollback()
        raise _error(
            409,
            "exchange_template_authority_required",
            "Mẫu DOCX chưa có vùng quản lý đã phê duyệt.",
        ) from exc
    return template.document_type, definition_set
