"""Read-only orchestration for the operational OneDrive Personal frontend."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.document_workspace.models import (
    DocumentRecord,
    DocumentRevision,
    DocumentRevisionCurrentHead,
)
from app.modules.m365_integration.application.bind_document_service import (
    _connection_access_token,
)
from app.modules.m365_integration.application.revalidation_service import (
    RevalidationReadiness,
    _definition_set_from_template_manifest,
    _require_actor,
    get_revalidation_readiness,
)
from app.modules.m365_integration.domain.credential_vault import M365CredentialVault
from app.modules.m365_integration.domain.graph_gateway import (
    GraphDriveEntry,
    M365GraphGateway,
    M365OAuthClient,
)
from app.modules.m365_integration.infrastructure.graph_adapter import MicrosoftGraphError
from app.modules.m365_integration.models import M365RevisionBinding, OneDriveConnection
from app.modules.project_master_data.models import (
    DocumentTemplate,
    DocumentTemplateStatus,
    Project,
    TemplateVersion,
    TemplateVersionStatus,
    User,
)


ADOPTION_SNAPSHOT_CONTRACT = "valora-operational-adoption-v1"
MAX_VISIBLE_CHILDREN = 100


@dataclass(frozen=True)
class AdoptionTemplate:
    template_version_id: uuid.UUID
    template_name: str
    document_type: str
    version_number: int


@dataclass(frozen=True)
class AdoptionOptions:
    project_id: uuid.UUID
    project_code: str
    project_name: str
    connection_id: uuid.UUID
    drive_id: str
    parent_item_id: str | None
    data_snapshot: dict[str, object]
    templates: tuple[AdoptionTemplate, ...]
    items: tuple[GraphDriveEntry, ...]
    truncated: bool


@dataclass(frozen=True)
class OperationalDocument:
    document_id: uuid.UUID
    title: str
    document_type: str
    readiness: RevalidationReadiness


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _abort(db: Session, status: int, code: str, detail: str) -> None:
    db.rollback()
    raise _error(status, code, detail)


def build_operational_adoption_snapshot(project: Project) -> dict[str, object]:
    """Return the exact bounded lineage envelope accepted from this frontend."""
    return {
        "contract_version": ADOPTION_SNAPSHOT_CONTRACT,
        "project_id": str(project.id),
        "project_code": project.code,
        "project_name": project.name,
        "project_row_version": project.row_version,
    }


def get_adoption_options(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    parent_item_id: str | None,
    oauth_client: M365OAuthClient,
    graph_gateway: M365GraphGateway,
    credential_vault: M365CredentialVault,
) -> AdoptionOptions:
    actor = _require_actor(
        db,
        organization_id=organization_id,
        actor_id=actor.id,
        permission="project:update",
    )
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == organization_id)
        .first()
    )
    if project is None:
        _abort(db, 404, "project_not_found", "Không tìm thấy hồ sơ.")
    connection = (
        db.query(OneDriveConnection)
        .filter(
            OneDriveConnection.organization_id == organization_id,
            OneDriveConnection.user_id == actor.id,
            OneDriveConnection.status == "active",
        )
        .first()
    )
    if connection is None:
        _abort(
            db,
            409,
            "onedrive_connection_required",
            "Vui lòng kết nối OneDrive Personal trước.",
        )

    candidates = (
        db.query(TemplateVersion, DocumentTemplate)
        .join(DocumentTemplate, TemplateVersion.document_template_id == DocumentTemplate.id)
        .filter(
            DocumentTemplate.organization_id == organization_id,
            DocumentTemplate.status == DocumentTemplateStatus.ACTIVE,
            DocumentTemplate.current_version_id == TemplateVersion.id,
            TemplateVersion.status == TemplateVersionStatus.ACTIVE,
            TemplateVersion.template_format == "docx",
        )
        .order_by(DocumentTemplate.name, TemplateVersion.version_number)
        .all()
    )
    templates: list[AdoptionTemplate] = []
    for version, template in candidates:
        try:
            _definition_set_from_template_manifest(
                template_version_id=version.id,
                manifest=version.placeholder_manifest,
            )
        except ValueError:
            continue
        templates.append(
            AdoptionTemplate(
                template_version_id=version.id,
                template_name=template.name,
                document_type=template.document_type,
                version_number=version.version_number,
            )
        )

    connection, access_token = _connection_access_token(
        db,
        organization_id=organization_id,
        actor_id=actor.id,
        connection_id=connection.id,
        oauth_client=oauth_client,
        credential_vault=credential_vault,
    )
    try:
        children = graph_gateway.list_drive_children(
            access_token=access_token,
            drive_id=connection.drive_id,
            parent_item_id=parent_item_id,
            limit=MAX_VISIBLE_CHILDREN,
        )
    except MicrosoftGraphError as exc:
        db.rollback()
        raise _error(
            502,
            "onedrive_folder_unavailable",
            "Không thể đọc thư mục OneDrive.",
        ) from exc
    except Exception as exc:
        db.rollback()
        raise _error(
            502,
            "onedrive_folder_unavailable",
            "Không thể đọc thư mục OneDrive.",
        ) from exc

    items = tuple(sorted(children.entries, key=lambda item: (item.kind != "folder", item.name.casefold())))
    return AdoptionOptions(
        project_id=project.id,
        project_code=project.code,
        project_name=project.name,
        connection_id=connection.id,
        drive_id=connection.drive_id,
        parent_item_id=parent_item_id,
        data_snapshot=build_operational_adoption_snapshot(project),
        templates=tuple(templates),
        items=items,
        truncated=children.truncated,
    )


def list_operational_documents(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
) -> tuple[OperationalDocument, ...]:
    actor = _require_actor(
        db,
        organization_id=organization_id,
        actor_id=actor.id,
        permission="project:read",
    )
    project = (
        db.query(Project.id)
        .filter(Project.id == project_id, Project.organization_id == organization_id)
        .first()
    )
    if project is None:
        _abort(db, 404, "project_not_found", "Không tìm thấy hồ sơ.")
    documents = (
        db.query(DocumentRecord)
        .join(
            DocumentRevisionCurrentHead,
            (DocumentRevisionCurrentHead.organization_id == DocumentRecord.organization_id)
            & (DocumentRevisionCurrentHead.project_id == DocumentRecord.project_id)
            & (DocumentRevisionCurrentHead.document_id == DocumentRecord.id),
        )
        .join(
            DocumentRevision,
            (DocumentRevision.id == DocumentRevisionCurrentHead.current_revision_id)
            & (DocumentRevision.organization_id == DocumentRecord.organization_id),
        )
        .join(
            M365RevisionBinding,
            (M365RevisionBinding.document_revision_id == DocumentRevision.id)
            & (M365RevisionBinding.organization_id == DocumentRecord.organization_id),
        )
        .filter(
            DocumentRecord.organization_id == organization_id,
            DocumentRecord.project_id == project_id,
        )
        .order_by(DocumentRecord.created_at.desc(), DocumentRecord.id)
        .all()
    )
    return tuple(
        OperationalDocument(
            document_id=document.id,
            title=document.title,
            document_type=document.document_type,
            readiness=get_revalidation_readiness(
                db,
                actor=actor,
                organization_id=organization_id,
                project_id=project_id,
                document_id=document.id,
            ),
        )
        for document in documents
    )
