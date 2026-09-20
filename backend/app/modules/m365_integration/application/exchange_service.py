"""Offline-safe OneDrive App Folder Exchange write orchestration."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.mixins import utc_now
from app.modules.m365_integration.application.connection_service import (
    get_connection_capabilities,
)
from app.modules.m365_integration.domain.graph_gateway import (
    GraphExchangeItem,
    GraphMutationStatus,
    M365GraphGateway,
)
from app.modules.m365_integration.models import (
    M365ExchangeArtifact,
    M365ExchangeOperation,
    OneDriveConnection,
)
from app.modules.project_master_data.models import Project


MAX_EXCHANGE_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class ExchangeNamespace:
    drive_id: str
    app_root_item_id: str
    valora_item_id: str
    exchange_item_id: str
    inbox_item_id: str
    working_item_id: str
    exports_item_id: str


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _abort(db: Session, status: int, code: str, detail: str) -> None:
    db.rollback()
    raise _error(status, code, detail)


def _require_write_connection(
    db: Session,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    connection_id: uuid.UUID,
) -> OneDriveConnection:
    project = db.query(Project.id).filter(
        Project.organization_id == organization_id, Project.id == project_id
    ).first()
    connection = db.query(OneDriveConnection).filter(
        OneDriveConnection.organization_id == organization_id,
        OneDriveConnection.id == connection_id,
        OneDriveConnection.status == "active",
    ).first()
    if project is None or connection is None:
        _abort(db, 404, "exchange_not_found", "Không tìm thấy tài nguyên Exchange.")
    read_available, write_available = get_connection_capabilities(
        db, organization_id=organization_id, connection_id=connection_id
    )
    if not read_available or not write_available:
        _abort(db, 409, "exchange_reconsent_required", "Cần cấp quyền Exchange.")
    return connection


def _verified_folder(
    *,
    result,
    graph_gateway: M365GraphGateway,
    access_token: str,
    drive_id: str,
    parent_item_id: str,
    exact_name: str,
) -> GraphExchangeItem:
    item = result.item
    if result.status in {
        GraphMutationStatus.OUTCOME_UNKNOWN,
        GraphMutationStatus.COLLISION,
    }:
        matches = graph_gateway.resolve_child_by_exact_name(
            access_token=access_token,
            drive_id=drive_id,
            parent_item_id=parent_item_id,
            exact_name=exact_name,
        )
        item = matches[0] if len(matches) == 1 else None
    if (
        item is None
        or item.kind != "folder"
        or item.drive_id != drive_id
        or item.parent_item_id != parent_item_id
        or item.name != exact_name
    ):
        raise _error(
            409,
            "exchange_namespace_collision",
            "Không thể xác minh thư mục Exchange.",
        )
    return item


def provision_exchange_namespace(
    *, graph_gateway: M365GraphGateway, access_token: str
) -> ExchangeNamespace:
    """Resolve approot and provision only the frozen exact child chain."""
    app_root = graph_gateway.get_app_root(access_token=access_token)
    if app_root.kind != "folder" or not app_root.drive_id or not app_root.drive_item_id:
        raise _error(409, "exchange_app_root_invalid", "Không thể xác minh App Folder.")
    parent = app_root
    resolved: dict[str, str] = {}
    for name, key in (
        ("VALORA", "valora"),
        ("Exchange", "exchange"),
        ("Inbox", "inbox"),
    ):
        item = _verified_folder(
            result=graph_gateway.ensure_child_folder(
                access_token=access_token,
                drive_id=app_root.drive_id,
                parent_item_id=parent.drive_item_id,
                exact_name=name,
            ),
            graph_gateway=graph_gateway,
            access_token=access_token,
            drive_id=app_root.drive_id,
            parent_item_id=parent.drive_item_id,
            exact_name=name,
        )
        resolved[key] = item.drive_item_id
        parent = item
        if name == "Exchange":
            exchange_parent = item
    for name, key in (("Working", "working"), ("Exports", "exports")):
        item = _verified_folder(
            result=graph_gateway.ensure_child_folder(
                access_token=access_token,
                drive_id=app_root.drive_id,
                parent_item_id=exchange_parent.drive_item_id,
                exact_name=name,
            ),
            graph_gateway=graph_gateway,
            access_token=access_token,
            drive_id=app_root.drive_id,
            parent_item_id=exchange_parent.drive_item_id,
            exact_name=name,
        )
        resolved[key] = item.drive_item_id
    return ExchangeNamespace(
        drive_id=app_root.drive_id,
        app_root_item_id=app_root.drive_item_id,
        valora_item_id=resolved["valora"],
        exchange_item_id=resolved["exchange"],
        inbox_item_id=resolved["inbox"],
        working_item_id=resolved["working"],
        exports_item_id=resolved["exports"],
    )


def _digest_request(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def prepare_exchange_create(
    db: Session,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    connection_id: uuid.UUID,
    idempotency_key: str,
    operation_kind: str,
    target_role: str,
    media: str,
    drive_id: str,
    destination_parent_item_id: str,
    destination_name: str,
    content: bytes,
) -> M365ExchangeOperation:
    connection = _require_write_connection(
        db,
        organization_id=organization_id,
        project_id=project_id,
        connection_id=connection_id,
    )
    if drive_id != connection.drive_id or operation_kind not in {
        "CREATE_WORKING",
        "CREATE_EXPORT",
    }:
        _abort(db, 409, "exchange_target_escape", "Đích Exchange không hợp lệ.")
    extension = ".docx" if media == "docx" else ".xlsx" if media == "xlsx" else None
    normalized_key = idempotency_key.strip()
    expected_role = "working" if operation_kind == "CREATE_WORKING" else "export"
    if (
        extension is None
        or target_role != expected_role
        or not destination_name.lower().endswith(extension)
        or "/" in destination_name
        or "\\" in destination_name
        or not normalized_key
        or len(normalized_key) > 128
        or len(content) > MAX_EXCHANGE_BYTES
    ):
        _abort(db, 422, "exchange_request_invalid", "Yêu cầu Exchange không hợp lệ.")
    content_sha256 = hashlib.sha256(content).hexdigest()
    request_digest = _digest_request(
        {
            "organization_id": str(organization_id),
            "project_id": str(project_id),
            "connection_id": str(connection_id),
            "operation_kind": operation_kind,
            "target_role": target_role,
            "media": media,
            "drive_id": drive_id,
            "parent_item_id": destination_parent_item_id,
            "destination_name": destination_name,
            "sha256": content_sha256,
            "byte_length": len(content),
        }
    )
    existing = db.query(M365ExchangeOperation).filter(
        M365ExchangeOperation.organization_id == organization_id,
        M365ExchangeOperation.idempotency_key == normalized_key,
    ).first()
    if existing is not None:
        if existing.request_digest_sha256 != request_digest:
            _abort(db, 409, "idempotency_key_reused", "Khóa yêu cầu đã được dùng.")
        db.commit()
        return existing
    operation = M365ExchangeOperation(
        organization_id=organization_id,
        project_id=project_id,
        connection_id=connection_id,
        idempotency_key=normalized_key,
        request_digest_sha256=request_digest,
        operation_kind=operation_kind,
        target_role=target_role,
        media=media,
        drive_id=drive_id,
        destination_parent_item_id=destination_parent_item_id,
        destination_name=destination_name,
        pre_sha256=content_sha256,
        pre_byte_length=len(content),
        state="PREPARED",
    )
    db.add(operation)
    try:
        db.commit()
        return operation
    except IntegrityError as exc:
        db.rollback()
        raced = db.query(M365ExchangeOperation).filter(
            M365ExchangeOperation.organization_id == organization_id,
            M365ExchangeOperation.idempotency_key == normalized_key,
        ).first()
        if raced is not None and raced.request_digest_sha256 == request_digest:
            return raced
        raise _error(409, "exchange_operation_conflict", "Yêu cầu Exchange xung đột.") from exc


def _reconcile_created_item(
    *,
    graph_gateway: M365GraphGateway,
    access_token: str,
    operation: M365ExchangeOperation,
    content: bytes,
) -> GraphExchangeItem | None:
    matches = graph_gateway.resolve_child_by_exact_name(
        access_token=access_token,
        drive_id=operation.drive_id,
        parent_item_id=operation.destination_parent_item_id,
        exact_name=operation.destination_name,
    )
    if not matches:
        return None
    if len(matches) != 1:
        raise _error(409, "exchange_provider_ambiguous", "Kết quả OneDrive không rõ ràng.")
    item = matches[0]
    if (
        item.kind != "file"
        or item.drive_id != operation.drive_id
        or item.parent_item_id != operation.destination_parent_item_id
        or item.name != operation.destination_name
        or item.size_bytes != len(content)
    ):
        raise _error(409, "exchange_provider_mismatch", "Tệp OneDrive không khớp yêu cầu.")
    observed = graph_gateway.get_drive_item_content(
        access_token=access_token,
        drive_id=operation.drive_id,
        drive_item_id=item.drive_item_id,
    )
    if len(observed) != len(content) or hashlib.sha256(observed).hexdigest() != hashlib.sha256(content).hexdigest():
        raise _error(409, "exchange_provider_mismatch", "Nội dung OneDrive không khớp yêu cầu.")
    return item


def execute_exchange_create(
    db: Session,
    *,
    organization_id: uuid.UUID,
    operation_id: uuid.UUID,
    content: bytes,
    graph_gateway: M365GraphGateway,
    access_token: str,
    source_authority_type: str,
    document_id: uuid.UUID | None = None,
    document_revision_id: uuid.UUID | None = None,
    excel_import_batch_id: uuid.UUID | None = None,
    excel_source_artifact_id: uuid.UUID | None = None,
) -> M365ExchangeArtifact | None:
    operation = db.query(M365ExchangeOperation).filter(
        M365ExchangeOperation.organization_id == organization_id,
        M365ExchangeOperation.id == operation_id,
    ).first()
    if operation is None:
        _abort(db, 404, "exchange_operation_not_found", "Không tìm thấy yêu cầu Exchange.")
    if hashlib.sha256(content).hexdigest() != operation.pre_sha256 or len(content) != operation.pre_byte_length:
        _abort(db, 409, "exchange_content_mismatch", "Nội dung Exchange đã thay đổi.")
    if operation.state == "FINALIZED":
        return db.get(M365ExchangeArtifact, operation.artifact_id)
    if operation.state == "PROVIDER_VERIFIED":
        artifact = db.get(M365ExchangeArtifact, operation.artifact_id)
        if artifact is None:
            _abort(
                db,
                409,
                "exchange_operation_state_conflict",
                "Bằng chứng Exchange không đầy đủ.",
            )
        operation.state = "FINALIZED"
        operation.finalized_at = utc_now()
        db.commit()
        return artifact
    if operation.state == "FAILED_ACTION_REQUIRED":
        return None
    db.commit()

    # Resolve the authorized App Folder namespace again at the actual
    # mutation/recovery boundary. A caller-provided parent item ID is never
    # sufficient evidence that the destination is inside Exchange.
    namespace = provision_exchange_namespace(
        graph_gateway=graph_gateway, access_token=access_token
    )
    expected_parent_item_id = (
        namespace.working_item_id
        if operation.operation_kind == "CREATE_WORKING"
        and operation.target_role == "working"
        else namespace.exports_item_id
        if operation.operation_kind == "CREATE_EXPORT"
        and operation.target_role == "export"
        else None
    )
    if (
        expected_parent_item_id is None
        or operation.drive_id != namespace.drive_id
        or operation.destination_parent_item_id != expected_parent_item_id
    ):
        _abort(db, 409, "exchange_target_escape", "Đích Exchange không hợp lệ.")

    item: GraphExchangeItem | None = None
    if operation.state == "PREPARED":
        result = graph_gateway.create_file(
            access_token=access_token,
            drive_id=operation.drive_id,
            parent_item_id=operation.destination_parent_item_id,
            exact_name=operation.destination_name,
            content=content,
        )
        if result.status == GraphMutationStatus.CREATED:
            item = result.item
        elif result.status in {GraphMutationStatus.OUTCOME_UNKNOWN, GraphMutationStatus.COLLISION}:
            persisted = db.get(M365ExchangeOperation, operation_id)
            persisted.state = "PROVIDER_UNKNOWN"
            persisted.provider_request_id = result.provider_request_id
            db.commit()
        elif result.status == GraphMutationStatus.UNAVAILABLE:
            return None
        else:
            persisted = db.get(M365ExchangeOperation, operation_id)
            persisted.state = "FAILED_ACTION_REQUIRED"
            persisted.failure_code = result.status.value
            db.commit()
            return None
    operation = db.get(M365ExchangeOperation, operation_id)
    try:
        item = _reconcile_created_item(
            graph_gateway=graph_gateway,
            access_token=access_token,
            operation=operation,
            content=content,
        )
    except HTTPException:
        operation.state = "FAILED_ACTION_REQUIRED"
        operation.failure_code = "provider_ambiguous_or_mismatch"
        db.commit()
        raise
    if item is None:
        return None

    persisted = (
        db.query(M365ExchangeOperation)
        .filter(
            M365ExchangeOperation.organization_id == organization_id,
            M365ExchangeOperation.id == operation_id,
        )
        .populate_existing()
        .with_for_update()
        .first()
    )
    if persisted is None:
        _abort(db, 404, "exchange_operation_not_found", "Không tìm thấy yêu cầu Exchange.")
    if persisted.state in {"PROVIDER_VERIFIED", "FINALIZED"}:
        artifact = db.get(M365ExchangeArtifact, persisted.artifact_id)
        if artifact is None:
            _abort(
                db,
                409,
                "exchange_operation_state_conflict",
                "Bằng chứng Exchange không đầy đủ.",
            )
        if persisted.state == "PROVIDER_VERIFIED":
            persisted.state = "FINALIZED"
            persisted.finalized_at = utc_now()
        db.commit()
        return artifact
    if persisted.state not in {"PREPARED", "PROVIDER_UNKNOWN"}:
        _abort(db, 409, "exchange_operation_state_conflict", "Trạng thái Exchange đã thay đổi.")
    observed_sha256 = hashlib.sha256(content).hexdigest()
    artifact = M365ExchangeArtifact(
        organization_id=organization_id,
        project_id=persisted.project_id,
        connection_id=persisted.connection_id,
        role=persisted.target_role,
        media=persisted.media,
        state="AVAILABLE",
        drive_id=persisted.drive_id,
        drive_item_id=item.drive_item_id,
        logical_namespace=f"VALORA/Exchange/{'Working' if persisted.target_role == 'working' else 'Exports'}",
        display_name=item.name,
        e_tag=item.e_tag,
        c_tag=item.c_tag,
        provider_version_id=item.graph_version_id,
        observed_sha256=observed_sha256,
        observed_byte_length=len(content),
        source_authority_type=source_authority_type,
        document_id=document_id,
        document_revision_id=document_revision_id,
        excel_import_batch_id=excel_import_batch_id,
        excel_source_artifact_id=excel_source_artifact_id,
    )
    db.add(artifact)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raced = (
            db.query(M365ExchangeOperation)
            .filter(
                M365ExchangeOperation.organization_id == organization_id,
                M365ExchangeOperation.id == operation_id,
            )
            .populate_existing()
            .first()
        )
        if (
            raced is not None
            and raced.artifact_id is not None
            and raced.state in {"PROVIDER_VERIFIED", "FINALIZED"}
        ):
            return execute_exchange_create(
                db,
                organization_id=organization_id,
                operation_id=operation_id,
                content=content,
                graph_gateway=graph_gateway,
                access_token=access_token,
                source_authority_type=source_authority_type,
                document_id=document_id,
                document_revision_id=document_revision_id,
                excel_import_batch_id=excel_import_batch_id,
                excel_source_artifact_id=excel_source_artifact_id,
            )
        raise _error(
            409,
            "exchange_operation_state_conflict",
            "Trạng thái Exchange đã thay đổi.",
        )
    persisted.state = "PROVIDER_VERIFIED"
    persisted.expected_drive_item_id = item.drive_item_id
    persisted.expected_e_tag = item.e_tag
    persisted.post_sha256 = observed_sha256
    persisted.post_byte_length = len(content)
    persisted.provider_verified_at = utc_now()
    persisted.artifact_id = artifact.id
    db.commit()
    return execute_exchange_create(
        db,
        organization_id=organization_id,
        operation_id=operation_id,
        content=content,
        graph_gateway=graph_gateway,
        access_token=access_token,
        source_authority_type=source_authority_type,
        document_id=document_id,
        document_revision_id=document_revision_id,
        excel_import_batch_id=excel_import_batch_id,
        excel_source_artifact_id=excel_source_artifact_id,
    )
