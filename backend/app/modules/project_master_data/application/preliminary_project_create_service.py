"""Own one READ COMMITTED business transaction, independent of request auth bookkeeping."""

import hashlib
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.api.auth import expiry_as_utc, raise_401
from app.core.audit import log_audit_event
from app.core.rbac import derive_effective_permissions, require_permission
from app.db.session import SessionLocal, engine
from app.modules.project_master_data.models import (
    AuditEvent,
    OrganizationProfile,
    Project,
    PreliminaryProjectCreateReceipt,
    User,
    UserSession,
)
from app.modules.project_master_data.preliminary_project_create_schemas import (
    CreatePreliminaryRequest,
    VERSION,
    digest,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Principal:
    organization_id: uuid.UUID
    actor_user_id: uuid.UUID
    session_id: uuid.UUID


def unresolved(request_id, code, status=503):
    return HTTPException(
        status_code=status,
        detail={
            "code": code,
            "status": "UNRESOLVED",
            "request_id": str(request_id),
            "final": False,
        },
    )


def lock_key(principal: Principal, request_id: uuid.UUID) -> int:
    material = (
        b"valora:preliminary-create:v1\0"
        + principal.organization_id.bytes
        + principal.actor_user_id.bytes
        + request_id.bytes
    )
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big", signed=True)


def authorize(db, principal, permission):
    # Expire relationships too: a lock wait must not reuse cached role/session truth.
    db.expire_all()
    session = db.get(UserSession, principal.session_id)
    user = db.get(User, principal.actor_user_id)
    org = db.get(OrganizationProfile, principal.organization_id)
    now = datetime.now(timezone.utc)
    if (
        not session
        or not user
        or not org
        or session.status != "active"
        or session.user_id != principal.actor_user_id
        or session.organization_id != principal.organization_id
        or user.organization_id != principal.organization_id
        or user.status != "active"
        or org.status != "active"
        or any(
            expiry_as_utc(t) < now
            for t in (
                session.access_expires_at,
                session.idle_expires_at,
                session.absolute_expires_at,
            )
        )
    ):
        raise_401("Phiên làm việc không hợp lệ hoặc đã hết hạn.")
    if permission not in derive_effective_permissions(user, db):
        # Reuse the existing denial envelope and effective-permission implementation.
        require_permission(permission)(current_user=user, db=db)


def require_receipt_schema(db, request_id, code):
    # A catalog lookup is safe before D7; never query the absent receipt table.
    if db.scalar(text("SELECT pg_catalog.to_regclass('preliminary_project_create_receipts')")) is None:
        raise unresolved(request_id, code)


def find_receipt(db, principal, request_id):
    return db.scalar(
        select(PreliminaryProjectCreateReceipt).where(
            PreliminaryProjectCreateReceipt.organization_id == principal.organization_id,
            PreliminaryProjectCreateReceipt.actor_user_id == principal.actor_user_id,
            PreliminaryProjectCreateReceipt.request_id == request_id,
        )
    )


def receipt_dto(db, receipt):
    try:
        audit = db.get(AuditEvent, receipt.audit_event_id)
        valid = (
            receipt.canonical_version == VERSION
            and digest(bytes(receipt.canonical_payload)) == receipt.payload_digest
            and receipt.project_code == format(receipt.project_id.int, "039d")
            and audit is not None
            and (audit.organization_id, audit.actor_user_id, audit.entity_id)
            == (receipt.organization_id, receipt.actor_user_id, receipt.project_id)
            and (audit.event_name, audit.entity_type, audit.command_name)
            == ("ProjectCreated", "Project", "CreatePreliminaryRequest")
            and audit.payload
            == {
                "request_id": str(receipt.request_id),
                "receipt_id": str(receipt.id),
                "code": receipt.project_code,
            }
            and audit.created_at == receipt.recorded_at
        )
        if not valid:
            raise ValueError("Receipt integrity")
        return {
            "status": "COMMITTED",
            "request_id": str(receipt.request_id),
            "project": {"id": str(receipt.project_id), "code": receipt.project_code},
            "receipt": {
                "id": str(receipt.id),
                "canonical_version": VERSION,
                "recorded_at": receipt.recorded_at.astimezone(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            },
        }
    except (ValueError, TypeError, UnicodeError):
        raise unresolved(receipt.request_id, "RECEIPT_INTEGRITY_ERROR") from None


def create_preliminary_request(principal: Principal, payload: CreatePreliminaryRequest):
    request_id = uuid.UUID(payload.request_id)
    committing = False
    try:
        with SessionLocal(bind=engine.execution_options(isolation_level="READ COMMITTED")) as db:
            with db.begin():
                db.execute(text("SET LOCAL lock_timeout = '5s'"))
                db.execute(text("SET LOCAL statement_timeout = '15s'"))
                authorize(db, principal, "project:create")
                db.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_key)"),
                    {"lock_key": lock_key(principal, request_id)},
                )
                authorize(db, principal, "project:create")
                require_receipt_schema(db, request_id, "CREATE_UNRESOLVED")
                receipt = find_receipt(db, principal, request_id)
                canonical = payload.canonical_bytes()
                if receipt is not None:
                    result = receipt_dto(db, receipt)
                    if (
                        receipt.canonical_version != VERSION
                        or receipt.payload_digest != digest(canonical)
                        or bytes(receipt.canonical_payload) != canonical
                    ):
                        raise HTTPException(
                            409,
                            detail={
                                "code": "POST_CONFLICT",
                                "request_id": str(request_id),
                                "message": "Mã yêu cầu đã được sử dụng cho nội dung khác.",
                            },
                        )
                    status = 200
                else:
                    if os.environ.get("VALORA_PRELIMINARY_CREATE_ENABLED", "false") != "true":
                        raise unresolved(request_id, "CREATE_UNRESOLVED")
                    project_id, receipt_id, audit_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
                    code = format(project_id.int, "039d")
                    recorded_at = datetime.now(timezone.utc)
                    db.add(
                        Project(
                            id=project_id,
                            organization_id=principal.organization_id,
                            created_by=principal.actor_user_id,
                            name=payload.name,
                            description=payload.description,
                            code=code,
                            status="draft",
                            knowledge_status="pending",
                            customer_id=None,
                            current_preliminary_import_batch_id=None,
                            fee_amount=0,
                            fee_currency_id=None,
                            signer_profile_id=None,
                        )
                    )
                    db.flush()
                    log_audit_event(
                        db,
                        "ProjectCreated",
                        "Project",
                        project_id,
                        principal.organization_id,
                        principal.actor_user_id,
                        "CreatePreliminaryRequest",
                        payload={
                            "request_id": str(request_id),
                            "receipt_id": str(receipt_id),
                            "code": code,
                        },
                        audit_event_id=audit_id,
                        created_at=recorded_at,
                    )
                    receipt = PreliminaryProjectCreateReceipt(
                        id=receipt_id,
                        organization_id=principal.organization_id,
                        actor_user_id=principal.actor_user_id,
                        request_id=request_id,
                        project_id=project_id,
                        project_code=code,
                        audit_event_id=audit_id,
                        canonical_version=VERSION,
                        canonical_payload=canonical,
                        payload_digest=digest(canonical),
                        recorded_at=recorded_at,
                    )
                    db.add(receipt)
                    db.flush()
                    result, status = receipt_dto(db, receipt), 201
                committing = True
            return result, status
    except HTTPException:
        raise
    except Exception as exc:
        code = "COMMIT_OUTCOME_UNKNOWN" if committing else "CREATE_UNRESOLVED"
        if not committing and isinstance(exc, DBAPIError):
            state = getattr(exc.orig, "sqlstate", None)
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            if state == "55P03":
                code = "LOCK_TIMEOUT"
            elif state == "23505" and constraint in ("projects_pkey", "uq_project_code_org"):
                code = "IDENTITY_COLLISION"
        logger.warning("Preliminary create unresolved: %s", code)
        raise unresolved(request_id, code) from None


def recover_preliminary_request(principal: Principal, request_id: uuid.UUID):
    try:
        with SessionLocal(bind=engine.execution_options(isolation_level="READ COMMITTED")) as db:
            with db.begin():
                db.execute(text("SET LOCAL statement_timeout = '15s'"))
                authorize(db, principal, "project:read")
                require_receipt_schema(db, request_id, "RECOVERY_UNAVAILABLE")
                receipt = find_receipt(db, principal, request_id)
                if receipt is None:
                    raise unresolved(request_id, "UNRESOLVED", 404)
                return receipt_dto(db, receipt)
    except HTTPException:
        raise
    except Exception:
        logger.warning("Preliminary recovery unavailable")
        raise unresolved(request_id, "RECOVERY_UNAVAILABLE") from None
