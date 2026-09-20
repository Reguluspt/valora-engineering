"""Durable local orchestration for app-owned immutable document storage."""
from __future__ import annotations

import hashlib
import re
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.db.mixins import utc_now
from app.modules.document_workspace.application.document_revision_service import _reload_actor
from app.modules.document_workspace.domain.document_blob_store import (
    ChecksumVerificationStatus,
    CreateImmutableStatus,
    DocumentBlobStore,
    ObjectObservationStatus,
)
from app.modules.document_workspace.models import (
    DocumentRecord,
    DocumentRevision,
    DocumentRevisionCurrentHead,
    DocumentStorageCandidate,
    DocumentStorageExecutionEvent,
    DocumentStorageExecutionIntent,
    DocumentStorageExecutionState,
    StorageObjectBinding,
)
from app.modules.project_master_data.models import Project, User


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TERMINAL_CLEANUP_STATES = {"SUPERSEDED", "ABANDONED", "RECONCILIATION_REQUIRED"}
_TERMINAL_STATES = _TERMINAL_CLEANUP_STATES | {"FINALIZED"}
_ALLOWED_TRANSITIONS = {
    "PREPARED": {"CANDIDATE_GENERATED"},
    "CANDIDATE_GENERATED": {"CREATE_DISPATCHED"},
    "CREATE_DISPATCHED": {
        "CANDIDATE_GENERATED",
        "CREATE_OUTCOME_UNKNOWN",
        "OBJECT_OBSERVED",
        "STORAGE_UNAVAILABLE",
        "RECONCILIATION_REQUIRED",
    },
    "CREATE_OUTCOME_UNKNOWN": {
        "CANDIDATE_GENERATED",
        "OBJECT_OBSERVED",
        "STORAGE_UNAVAILABLE",
        "RECONCILIATION_REQUIRED",
    },
    "STORAGE_UNAVAILABLE": {
        "CANDIDATE_GENERATED",
        "OBJECT_OBSERVED",
        "STORAGE_UNAVAILABLE",
        "RECONCILIATION_REQUIRED",
    },
    "OBJECT_OBSERVED": {
        "OBJECT_VERIFIED",
        "STORAGE_UNAVAILABLE",
        "RECONCILIATION_REQUIRED",
    },
    "OBJECT_VERIFIED": {"FINALIZING", "SUPERSEDED"},
    "FINALIZING": {"FINALIZED"},
    "RECONCILIATION_REQUIRED": {"RECONCILIATION_REQUIRED"},
    "SUPERSEDED": {"SUPERSEDED"},
    "ABANDONED": {"ABANDONED"},
    "FINALIZED": set(),
}


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _abort(db: Session, status: int, code: str, detail: str) -> None:
    db.rollback()
    raise _error(status, code, detail)


def _require_sha256(db: Session, value: str, field: str) -> str:
    if not _SHA256_RE.fullmatch(value):
        _abort(db, 422, "invalid_sha256", f"{field} is invalid.")
    return value


def _require_matching_provider(
    db: Session,
    *,
    candidate: DocumentStorageCandidate,
    blob_store: DocumentBlobStore,
) -> None:
    if blob_store.provider_kind != candidate.provider_kind:
        _abort(
            db,
            409,
            "storage_provider_mismatch",
            "Configured storage provider does not match the persisted candidate.",
        )


def _intent_by_key(
    db: Session, *, organization_id: uuid.UUID, idempotency_key: str
) -> DocumentStorageExecutionIntent | None:
    return (
        db.query(DocumentStorageExecutionIntent)
        .filter(
            DocumentStorageExecutionIntent.organization_id == organization_id,
            DocumentStorageExecutionIntent.idempotency_key == idempotency_key,
        )
        .first()
    )


def _state(db: Session, *, intent: DocumentStorageExecutionIntent, lock: bool) -> DocumentStorageExecutionState:
    query = db.query(DocumentStorageExecutionState).filter(
        DocumentStorageExecutionState.execution_intent_id == intent.id,
        DocumentStorageExecutionState.organization_id == intent.organization_id,
    )
    state = query.with_for_update().first() if lock else query.first()
    if state is None:
        _abort(db, 409, "storage_state_missing", "Storage execution state is unavailable.")
    return state


def _append_transition(
    db: Session,
    *,
    intent: DocumentStorageExecutionIntent,
    state: DocumentStorageExecutionState,
    next_state: str,
    event_code: str,
    reason_code: str | None = None,
    provider_request_id: str | None = None,
    observed_object_version: str | None = None,
    observed_etag: str | None = None,
    observed_object_created_at: datetime | None = None,
    observed_content_sha256: str | None = None,
    observed_byte_length: int | None = None,
    recorded_by_user_id: uuid.UUID | None = None,
) -> None:
    if next_state not in _ALLOWED_TRANSITIONS.get(state.current_state, set()):
        _abort(
            db,
            409,
            "storage_transition_invalid",
            f"Storage transition {state.current_state} -> {next_state} is not allowed.",
        )
    sequence = state.last_event_sequence + 1
    db.add(
        DocumentStorageExecutionEvent(
            organization_id=intent.organization_id,
            execution_intent_id=intent.id,
            sequence=sequence,
            event_code=event_code,
            reason_code=reason_code,
            provider_request_id=provider_request_id,
            observed_object_version=observed_object_version,
            observed_etag=observed_etag,
            observed_object_created_at=observed_object_created_at,
            observed_content_sha256=observed_content_sha256,
            observed_byte_length=observed_byte_length,
            recorded_by_user_id=recorded_by_user_id or intent.requested_by_user_id,
        )
    )
    state.current_state = next_state
    state.last_event_sequence = sequence
    state.state_version += 1
    state.updated_at = utc_now()


def prepare_storage_intent(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    document_id: uuid.UUID,
    idempotency_key: str,
    request_digest_sha256: str,
    plan_digest_sha256: str,
    decision_digest_sha256: str,
    correlation_id: str | None = None,
) -> DocumentStorageExecutionIntent:
    """Freeze the current head and atomically create the first event/projection."""
    normalized_key = idempotency_key.strip()
    if not normalized_key or len(normalized_key) > 128:
        _abort(db, 422, "invalid_idempotency_key", "Storage idempotency key is invalid.")
    for value, field in (
        (request_digest_sha256, "request digest"),
        (plan_digest_sha256, "plan digest"),
        (decision_digest_sha256, "decision digest"),
    ):
        _require_sha256(db, value, field)
    actor = _reload_actor(db, actor=actor, organization_id=organization_id)
    existing = _intent_by_key(db, organization_id=organization_id, idempotency_key=normalized_key)
    if existing is not None:
        if existing.request_digest_sha256 != request_digest_sha256:
            _abort(db, 409, "idempotency_key_reused", "Storage key was used for another request.")
        db.commit()
        return existing
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == organization_id)
        .with_for_update()
        .first()
    )
    if project is None:
        _abort(db, 404, "project_not_found", "Project was not found.")
    document = (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.id == document_id,
            DocumentRecord.organization_id == organization_id,
            DocumentRecord.project_id == project_id,
        )
        .with_for_update()
        .first()
    )
    head = (
        db.query(DocumentRevisionCurrentHead)
        .filter(
            DocumentRevisionCurrentHead.organization_id == organization_id,
            DocumentRevisionCurrentHead.project_id == project_id,
            DocumentRevisionCurrentHead.document_id == document_id,
        )
        .with_for_update()
        .first()
    )
    if document is None or head is None:
        _abort(db, 404, "document_revision_not_found", "Document revision was not found.")
    revision = db.get(DocumentRevision, head.current_revision_id)
    if revision is None or revision.document_revision != head.document_revision:
        _abort(db, 409, "document_revision_conflict", "Document head is inconsistent.")
    intent = DocumentStorageExecutionIntent(
        organization_id=organization_id,
        project_id=project_id,
        document_id=document_id,
        expected_revision_id=revision.id,
        expected_document_revision=revision.document_revision,
        expected_content_sha256=revision.content_checksum_sha256,
        idempotency_key=normalized_key,
        request_digest_sha256=request_digest_sha256,
        plan_digest_sha256=plan_digest_sha256,
        decision_digest_sha256=decision_digest_sha256,
        requested_by_user_id=actor.id,
        correlation_id=correlation_id,
    )
    db.add(intent)
    db.flush()
    state = DocumentStorageExecutionState(
        execution_intent_id=intent.id,
        organization_id=organization_id,
        project_id=project_id,
        document_id=document_id,
        current_state="PREPARED",
        state_version=1,
        last_event_sequence=1,
    )
    db.add(state)
    db.add(
        DocumentStorageExecutionEvent(
            organization_id=organization_id,
            execution_intent_id=intent.id,
            sequence=1,
            event_code="PREPARED",
            recorded_by_user_id=actor.id,
        )
    )
    log_audit_event(
        db,
        event_name="DOCUMENT_STORAGE_INTENT_PREPARED",
        entity_type="DocumentStorageExecutionIntent",
        entity_id=intent.id,
        organization_id=organization_id,
        actor_user_id=actor.id,
        command_name="PrepareDocumentStorageIntent",
        correlation_id=correlation_id,
        payload={"document_id": str(document_id), "expected_revision": revision.document_revision},
    )
    try:
        db.commit()
        return intent
    except IntegrityError as exc:
        db.rollback()
        raced = _intent_by_key(db, organization_id=organization_id, idempotency_key=normalized_key)
        if raced is not None and raced.request_digest_sha256 == request_digest_sha256:
            return raced
        raise _error(409, "storage_intent_conflict", "Storage intent conflicts with another run.") from exc


def record_storage_candidate(
    db: Session,
    *,
    organization_id: uuid.UUID,
    intent_id: uuid.UUID,
    content: bytes,
    provider_kind: Literal["fake", "local"],
    storage_profile_id: str,
    container_name: str,
    object_key: str,
    media_type: str,
    generator_version: str,
) -> DocumentStorageCandidate:
    """Persist only deterministic candidate metadata after exact local hashing."""
    intent = db.get(DocumentStorageExecutionIntent, intent_id)
    if intent is None or intent.organization_id != organization_id:
        _abort(db, 404, "storage_intent_not_found", "Storage intent was not found.")
    if provider_kind not in {"fake", "local"}:
        _abort(db, 422, "storage_candidate_invalid", "Storage provider is invalid.")
    content_sha256 = hashlib.sha256(content).hexdigest()
    normalized_fields = tuple(
        value.strip()
        for value in (storage_profile_id, container_name, object_key, media_type, generator_version)
    )
    if any(not value for value in normalized_fields):
        _abort(db, 422, "storage_candidate_invalid", "Storage candidate identity is invalid.")
    normalized_profile, normalized_container, normalized_key, normalized_media, normalized_generator = (
        normalized_fields
    )
    existing = (
        db.query(DocumentStorageCandidate)
        .filter(
            DocumentStorageCandidate.organization_id == organization_id,
            DocumentStorageCandidate.execution_intent_id == intent_id,
        )
        .first()
    )
    if existing is not None:
        persisted_identity = (
            existing.provider_kind,
            existing.storage_profile_id,
            existing.container_name,
            existing.object_key,
            existing.media_type,
            existing.generator_version,
        )
        if (
            existing.content_sha256 != content_sha256
            or existing.byte_length != len(content)
            or persisted_identity != (provider_kind, *normalized_fields)
        ):
            _abort(db, 409, "storage_candidate_conflict", "Storage candidate differs from replay.")
        db.commit()
        return existing
    state = _state(db, intent=intent, lock=True)
    if state.current_state != "PREPARED":
        _abort(db, 409, "storage_transition_invalid", "Storage candidate cannot be recorded now.")
    candidate = DocumentStorageCandidate(
        organization_id=organization_id,
        execution_intent_id=intent_id,
        storage_profile_id=normalized_profile,
        provider_kind=provider_kind,
        container_name=normalized_container,
        object_key=normalized_key,
        content_sha256=content_sha256,
        byte_length=len(content),
        media_type=normalized_media,
        generator_version=normalized_generator,
    )
    db.add(candidate)
    _append_transition(
        db,
        intent=intent,
        state=state,
        next_state="CANDIDATE_GENERATED",
        event_code="CANDIDATE_GENERATED",
        observed_content_sha256=content_sha256,
        observed_byte_length=len(content),
    )
    db.commit()
    return candidate


async def _bytes_once(content: bytes) -> AsyncIterator[bytes]:
    yield content


def _transition_after_io(
    db: Session,
    *,
    intent: DocumentStorageExecutionIntent,
    next_state: str,
    event_code: str,
    reason_code: str | None = None,
    provider_request_id: str | None = None,
    observed_object_version: str | None = None,
    observed_etag: str | None = None,
    observed_object_created_at: datetime | None = None,
    observed_content_sha256: str | None = None,
    observed_byte_length: int | None = None,
) -> DocumentStorageExecutionState:
    state = _state(db, intent=intent, lock=True)
    _append_transition(
        db,
        intent=intent,
        state=state,
        next_state=next_state,
        event_code=event_code,
        reason_code=reason_code,
        provider_request_id=provider_request_id,
        observed_object_version=observed_object_version,
        observed_etag=observed_etag,
        observed_object_created_at=observed_object_created_at,
        observed_content_sha256=observed_content_sha256,
        observed_byte_length=observed_byte_length,
    )
    db.commit()
    return state


async def create_or_recover_storage_object(
    db: Session,
    *,
    organization_id: uuid.UUID,
    intent_id: uuid.UUID,
    content: bytes,
    blob_store: DocumentBlobStore,
) -> DocumentStorageExecutionState:
    """Create, observe and verify outside DB locks; never blindly retry an unknown write."""
    intent = db.get(DocumentStorageExecutionIntent, intent_id)
    candidate = (
        db.query(DocumentStorageCandidate)
        .filter_by(organization_id=organization_id, execution_intent_id=intent_id)
        .first()
    )
    if intent is None or candidate is None or intent.organization_id != organization_id:
        _abort(db, 404, "storage_candidate_not_found", "Storage candidate was not found.")
    _require_matching_provider(db, candidate=candidate, blob_store=blob_store)
    object_key = candidate.object_key
    content_sha256 = candidate.content_sha256
    byte_length = candidate.byte_length
    if hashlib.sha256(content).hexdigest() != content_sha256 or len(content) != byte_length:
        _abort(db, 409, "storage_content_mismatch", "Generated content differs from the candidate.")
    state = _state(db, intent=intent, lock=False)
    if state.current_state in _TERMINAL_STATES or state.current_state == "OBJECT_VERIFIED":
        return state
    if state.current_state != "OBJECT_OBSERVED":
        if state.current_state in {
            "CREATE_DISPATCHED",
            "CREATE_OUTCOME_UNKNOWN",
            "STORAGE_UNAVAILABLE",
        }:
            db.commit()
            observation = await blob_store.observe(object_key=object_key)
        else:
            if state.current_state != "CANDIDATE_GENERATED":
                _abort(
                    db,
                    409,
                    "storage_transition_invalid",
                    "Storage create cannot run from this state.",
                )
            _transition_after_io(
                db, intent=intent, next_state="CREATE_DISPATCHED", event_code="CREATE_DISPATCHED"
            )
            created = await blob_store.create_immutable(
                object_key=object_key,
                content=_bytes_once(content),
                byte_length=byte_length,
                expected_sha256=content_sha256,
            )
            if created.status == CreateImmutableStatus.UNAVAILABLE:
                return _transition_after_io(
                    db,
                    intent=intent,
                    next_state="STORAGE_UNAVAILABLE",
                    event_code="STORAGE_UNAVAILABLE",
                )
            if created.status == CreateImmutableStatus.REJECTED:
                return _transition_after_io(
                    db,
                    intent=intent,
                    next_state="RECONCILIATION_REQUIRED",
                    event_code="CREATE_REJECTED",
                )
            if created.status == CreateImmutableStatus.OUTCOME_UNKNOWN:
                _transition_after_io(
                    db,
                    intent=intent,
                    next_state="CREATE_OUTCOME_UNKNOWN",
                    event_code="CREATE_OUTCOME_UNKNOWN",
                    provider_request_id=created.provider_request_id,
                    observed_object_version=created.provider_object_version,
                )
            observation = await blob_store.observe(object_key=object_key)
        if observation.status == ObjectObservationStatus.UNAVAILABLE:
            return _transition_after_io(
                db, intent=intent, next_state="STORAGE_UNAVAILABLE", event_code="STORAGE_UNAVAILABLE"
            )
        if observation.status == ObjectObservationStatus.ABSENT:
            # Observation settled the prior outcome; a later explicit command may recreate safely.
            return _transition_after_io(
                db,
                intent=intent,
                next_state="CANDIDATE_GENERATED",
                event_code="OBJECT_ABSENT_AFTER_CREATE",
            )
        if observation.status == ObjectObservationStatus.AMBIGUOUS:
            return _transition_after_io(
                db,
                intent=intent,
                next_state="RECONCILIATION_REQUIRED",
                event_code="OBJECT_UNVERIFIABLE",
            )
        _transition_after_io(
            db,
            intent=intent,
            next_state="OBJECT_OBSERVED",
            event_code="OBJECT_OBSERVED",
            provider_request_id=observation.provider_request_id,
            observed_object_version=observation.provider_object_version,
            observed_etag=observation.observed_etag,
            observed_object_created_at=observation.object_created_at,
            observed_byte_length=observation.byte_length,
        )
    else:
        db.commit()
    verified = await blob_store.verify_checksum(
        object_key=object_key,
        expected_sha256=content_sha256,
        expected_byte_length=byte_length,
    )
    if verified.status == ChecksumVerificationStatus.MATCH:
        return _transition_after_io(
            db,
            intent=intent,
            next_state="OBJECT_VERIFIED",
            event_code="OBJECT_VERIFIED",
            observed_content_sha256=verified.observed_sha256,
            observed_byte_length=verified.observed_byte_length,
        )
    if verified.status == ChecksumVerificationStatus.UNAVAILABLE:
        return _transition_after_io(
            db, intent=intent, next_state="STORAGE_UNAVAILABLE", event_code="STORAGE_UNAVAILABLE"
        )
    return _transition_after_io(
        db,
        intent=intent,
        next_state="RECONCILIATION_REQUIRED",
        event_code="CHECKSUM_NOT_VERIFIED",
        observed_content_sha256=verified.observed_sha256,
        observed_byte_length=verified.observed_byte_length,
    )


def finalize_storage_revision(
    db: Session,
    *,
    organization_id: uuid.UUID,
    intent_id: uuid.UUID,
    retention_policy_code: str,
    retention_anchor_at: datetime,
    minimum_retain_until: datetime,
) -> StorageObjectBinding:
    """Publish one N+1 revision, binding and head CAS in one short transaction."""
    intent = db.get(DocumentStorageExecutionIntent, intent_id)
    if intent is None or intent.organization_id != organization_id:
        _abort(db, 404, "storage_intent_not_found", "Storage intent was not found.")
    existing = (
        db.query(StorageObjectBinding)
        .filter_by(organization_id=organization_id, execution_intent_id=intent_id)
        .first()
    )
    if existing is not None:
        db.commit()
        return existing
    candidate = (
        db.query(DocumentStorageCandidate)
        .filter_by(organization_id=organization_id, execution_intent_id=intent_id)
        .first()
    )
    state = _state(db, intent=intent, lock=True)
    if state.current_state == "FINALIZED":
        finalized = (
            db.query(StorageObjectBinding)
            .filter_by(organization_id=organization_id, execution_intent_id=intent_id)
            .first()
        )
        if finalized is not None:
            db.commit()
            return finalized
        _abort(db, 409, "storage_binding_missing", "Finalized storage binding is unavailable.")
    if candidate is None or state.current_state != "OBJECT_VERIFIED":
        _abort(db, 409, "storage_not_verified", "Storage object is not verified.")
    try:
        ten_year_floor = retention_anchor_at.replace(year=retention_anchor_at.year + 10)
    except ValueError:
        ten_year_floor = retention_anchor_at.replace(
            year=retention_anchor_at.year + 10, day=28
        )
    if not retention_policy_code.strip() or minimum_retain_until < ten_year_floor:
        _abort(db, 422, "storage_retention_invalid", "Retention snapshot is invalid.")
    observation = (
        db.query(DocumentStorageExecutionEvent)
        .filter(
            DocumentStorageExecutionEvent.organization_id == organization_id,
            DocumentStorageExecutionEvent.execution_intent_id == intent_id,
            DocumentStorageExecutionEvent.event_code == "OBJECT_OBSERVED",
        )
        .order_by(DocumentStorageExecutionEvent.sequence.desc())
        .first()
    )
    if observation is None or observation.observed_object_created_at is None:
        _abort(db, 409, "storage_observation_missing", "Verified object identity is incomplete.")
    head = (
        db.query(DocumentRevisionCurrentHead)
        .filter(
            DocumentRevisionCurrentHead.organization_id == organization_id,
            DocumentRevisionCurrentHead.project_id == intent.project_id,
            DocumentRevisionCurrentHead.document_id == intent.document_id,
        )
        .with_for_update()
        .first()
    )
    previous = db.get(DocumentRevision, intent.expected_revision_id)
    if (
        head is None
        or previous is None
        or head.current_revision_id != intent.expected_revision_id
        or head.document_revision != intent.expected_document_revision
    ):
        _append_transition(
            db,
            intent=intent,
            state=state,
            next_state="SUPERSEDED",
            event_code="SUPERSEDED",
            reason_code="CURRENT_HEAD_CHANGED",
        )
        db.commit()
        raise _error(409, "storage_head_superseded", "Document head changed before finalization.")
    _append_transition(
        db, intent=intent, state=state, next_state="FINALIZING", event_code="FINALIZING"
    )
    revision = DocumentRevision(
        organization_id=organization_id,
        project_id=intent.project_id,
        document_id=intent.document_id,
        document_revision=intent.expected_document_revision + 1,
        data_snapshot_digest_sha256=previous.data_snapshot_digest_sha256,
        content_checksum_sha256=candidate.content_sha256,
        idempotency_key=intent.idempotency_key,
        request_digest_sha256=intent.request_digest_sha256,
        created_by_user_id=intent.requested_by_user_id,
    )
    db.add(revision)
    db.flush()
    now = utc_now()
    binding = StorageObjectBinding(
        organization_id=organization_id,
        project_id=intent.project_id,
        document_id=intent.document_id,
        document_revision_id=revision.id,
        execution_intent_id=intent.id,
        storage_candidate_id=candidate.id,
        storage_profile_id=candidate.storage_profile_id,
        provider_kind=candidate.provider_kind,
        container_name=candidate.container_name,
        object_key=candidate.object_key,
        provider_object_version=observation.observed_object_version,
        checksum_algorithm="SHA256",
        content_sha256=candidate.content_sha256,
        byte_length=candidate.byte_length,
        observed_etag=observation.observed_etag,
        object_created_at=observation.observed_object_created_at,
        verified_at=now,
        retention_policy_code=retention_policy_code.strip(),
        retention_anchor_at=retention_anchor_at,
        minimum_retain_until=minimum_retain_until,
    )
    db.add(binding)
    cas = db.execute(
        update(DocumentRevisionCurrentHead)
        .where(
            DocumentRevisionCurrentHead.organization_id == organization_id,
            DocumentRevisionCurrentHead.project_id == intent.project_id,
            DocumentRevisionCurrentHead.document_id == intent.document_id,
            DocumentRevisionCurrentHead.current_revision_id == intent.expected_revision_id,
            DocumentRevisionCurrentHead.document_revision == intent.expected_document_revision,
        )
        .values(current_revision_id=revision.id, document_revision=revision.document_revision)
    )
    if cas.rowcount != 1:
        db.rollback()
        persisted_intent = db.get(DocumentStorageExecutionIntent, intent_id)
        if persisted_intent is not None:
            persisted_state = _state(db, intent=persisted_intent, lock=True)
            _append_transition(
                db,
                intent=persisted_intent,
                state=persisted_state,
                next_state="SUPERSEDED",
                event_code="SUPERSEDED",
                reason_code="CURRENT_HEAD_CAS_LOST",
            )
            db.commit()
        raise _error(409, "storage_head_superseded", "Document head changed before finalization.")
    _append_transition(db, intent=intent, state=state, next_state="FINALIZED", event_code="FINALIZED")
    log_audit_event(
        db,
        event_name="DOCUMENT_STORAGE_REVISION_FINALIZED",
        entity_type="StorageObjectBinding",
        entity_id=binding.id,
        organization_id=organization_id,
        actor_user_id=intent.requested_by_user_id,
        command_name="FinalizeDocumentStorageRevision",
        correlation_id=intent.correlation_id,
        payload={
            "document_id": str(intent.document_id),
            "document_revision_id": str(revision.id),
            "byte_length": candidate.byte_length,
        },
    )
    try:
        db.commit()
        return binding
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(StorageObjectBinding)
            .filter_by(organization_id=organization_id, execution_intent_id=intent_id)
            .first()
        )
        if raced is not None:
            return raced
        raise _error(409, "storage_finalize_conflict", "Storage finalization conflicts.") from exc


async def cleanup_uncommitted_candidate(
    db: Session,
    *,
    actor: User,
    organization_id: uuid.UUID,
    intent_id: uuid.UUID,
    blob_store: DocumentBlobStore,
    cleanup_policy_code: str,
    policy_allows_cleanup: bool,
    legal_hold_active: bool,
) -> DocumentStorageExecutionState:
    """Clean only an unbound terminal candidate; finalized objects have no path here."""
    actor = _reload_actor(db, actor=actor, organization_id=organization_id)
    normalized_policy = cleanup_policy_code.strip()
    if not normalized_policy or not policy_allows_cleanup or legal_hold_active:
        _abort(db, 409, "storage_cleanup_policy_blocked", "Storage cleanup is not permitted.")
    intent = db.get(DocumentStorageExecutionIntent, intent_id)
    if intent is None or intent.organization_id != organization_id:
        _abort(db, 404, "storage_intent_not_found", "Storage intent was not found.")
    candidate = (
        db.query(DocumentStorageCandidate)
        .filter_by(organization_id=organization_id, execution_intent_id=intent_id)
        .first()
    )
    if candidate is not None:
        _require_matching_provider(db, candidate=candidate, blob_store=blob_store)
    state = _state(db, intent=intent, lock=False)
    bound = (
        db.query(StorageObjectBinding.id)
        .filter_by(organization_id=organization_id, execution_intent_id=intent_id)
        .first()
    )
    if candidate is None or bound is not None or state.current_state not in _TERMINAL_CLEANUP_STATES:
        _abort(db, 409, "storage_cleanup_forbidden", "Storage candidate is not eligible for cleanup.")
    object_key = candidate.object_key
    content_sha256 = candidate.content_sha256
    candidate_id = candidate.id
    actor_id = actor.id
    terminal_state = state.current_state
    db.commit()
    result = await blob_store.delete_uncommitted_or_expire(
        object_key=object_key, expected_sha256=content_sha256
    )
    event_code = "CANDIDATE_CLEANED" if result.status.value in {"DELETED", "ABSENT"} else "CLEANUP_DEFERRED"
    persisted_intent = db.get(DocumentStorageExecutionIntent, intent_id)
    if persisted_intent is None:
        _abort(db, 409, "storage_intent_missing", "Storage intent disappeared during cleanup.")
    persisted_state = _state(db, intent=persisted_intent, lock=True)
    if persisted_state.current_state != terminal_state:
        _abort(db, 409, "storage_cleanup_state_changed", "Storage cleanup state changed concurrently.")
    _append_transition(
        db,
        intent=persisted_intent,
        state=persisted_state,
        next_state=terminal_state,
        event_code=event_code,
        reason_code=result.status.value,
        recorded_by_user_id=actor_id,
    )
    log_audit_event(
        db,
        event_name="DOCUMENT_STORAGE_CANDIDATE_CLEANUP_RECORDED",
        entity_type="DocumentStorageCandidate",
        entity_id=candidate_id,
        organization_id=organization_id,
        actor_user_id=actor_id,
        command_name="CleanupUncommittedDocumentStorageCandidate",
        correlation_id=persisted_intent.correlation_id,
        payload={
            "execution_intent_id": str(intent_id),
            "cleanup_policy_code": normalized_policy,
            "outcome": result.status.value,
        },
    )
    db.commit()
    return persisted_state
