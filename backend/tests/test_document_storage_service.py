"""Deterministic fake-provider contract tests for VALORA-STORAGE-FAKE-001."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.document_workspace.application.document_storage_service import (
    cleanup_uncommitted_candidate,
    create_or_recover_storage_object,
    finalize_storage_revision,
    prepare_storage_intent,
    record_storage_candidate,
)
from app.modules.document_workspace.domain.document_blob_store import (
    InjectedStorageCrash,
    InMemoryDocumentBlobStore,
)
from app.modules.document_workspace.models import (
    DocumentRevision,
    DocumentRevisionCurrentHead,
    DocumentStorageExecutionEvent,
    DocumentStorageExecutionIntent,
    DocumentStorageExecutionState,
    DocumentStorageCandidate,
    StorageObjectBinding,
)
from tests.test_pr05_m365_foundation import TABLES, _document, _seed


REQUEST_DIGEST = "1" * 64
PLAN_DIGEST = "2" * 64
DECISION_DIGEST = "3" * 64
RETENTION_ANCHOR = datetime(2026, 9, 19, tzinfo=timezone.utc)
RETENTION_UNTIL = datetime(2036, 9, 19, tzinfo=timezone.utc)
STORAGE_TABLES = [
    DocumentStorageExecutionIntent.__table__,
    DocumentStorageCandidate.__table__,
    DocumentStorageExecutionState.__table__,
    DocumentStorageExecutionEvent.__table__,
    StorageObjectBinding.__table__,
]


@pytest.fixture
def storage_context() -> dict[str, Any]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_foreign_keys(dbapi_connection, connection_record):
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine, tables=[*TABLES, *STORAGE_TABLES])
    db = Session(bind=engine)
    seeded = _seed(db, suffix="storage-fake")
    revision = _document(db, seeded)
    try:
        yield {"db": db, "engine": engine, "seeded": seeded, "revision": revision, "provider": InMemoryDocumentBlobStore()}
    finally:
        db.close()
        engine.dispose()


def _invoke(value: Any) -> Any:
    return asyncio.run(value) if inspect.isawaitable(value) else value


def _content(label: str) -> tuple[bytes, str]:
    content = f"PK\x03\x04 deterministic docx candidate {label}".encode()
    return content, hashlib.sha256(content).hexdigest()


def _prepare(ctx: dict[str, Any], *, key: str = "storage-intent-1") -> DocumentStorageExecutionIntent:
    seeded = ctx["seeded"]
    revision = ctx["revision"]
    return prepare_storage_intent(
        ctx["db"], actor=seeded["actor"], organization_id=seeded["organization"].id,
        project_id=seeded["project"].id, document_id=revision.document_id,
        idempotency_key=key, request_digest_sha256=REQUEST_DIGEST,
        plan_digest_sha256=PLAN_DIGEST, decision_digest_sha256=DECISION_DIGEST,
        correlation_id=f"corr-{key}",
    )


def _candidate(ctx: dict[str, Any], intent: DocumentStorageExecutionIntent, *, label: str = "A", object_key: str | None = None):
    content, checksum = _content(label)
    candidate = record_storage_candidate(
        ctx["db"], organization_id=intent.organization_id, intent_id=intent.id, content=content,
        storage_profile_id="fake-local", container_name="valora-test",
        object_key=object_key or f"tenant/{intent.organization_id}/intent/{intent.id}",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        generator_version="test-generator-v1",
    )
    assert candidate.content_sha256 == checksum
    return content, candidate


def _verify(ctx: dict[str, Any], intent: DocumentStorageExecutionIntent, content: bytes):
    return _invoke(create_or_recover_storage_object(
        ctx["db"], organization_id=intent.organization_id, intent_id=intent.id,
        content=content, blob_store=ctx["provider"],
    ))


def _finalize(ctx: dict[str, Any], intent: DocumentStorageExecutionIntent):
    return finalize_storage_revision(
        ctx["db"], organization_id=intent.organization_id, intent_id=intent.id,
        retention_policy_code="official-document-10y", retention_anchor_at=RETENTION_ANCHOR,
        minimum_retain_until=RETENTION_UNTIL,
    )


def _cleanup(
    ctx: dict[str, Any],
    intent: DocumentStorageExecutionIntent,
    *,
    policy_allows_cleanup: bool = True,
    legal_hold_active: bool = False,
):
    return _invoke(cleanup_uncommitted_candidate(
        ctx["db"], actor=ctx["seeded"]["actor"],
        organization_id=intent.organization_id, intent_id=intent.id,
        blob_store=ctx["provider"], cleanup_policy_code="UNCOMMITTED_ORPHAN_V1",
        policy_allows_cleanup=policy_allows_cleanup, legal_hold_active=legal_hold_active,
    ))


def _head(ctx: dict[str, Any]):
    return ctx["db"].query(DocumentRevisionCurrentHead).one()


def _state(ctx: dict[str, Any], intent_id: Any):
    return ctx["db"].query(DocumentStorageExecutionState).filter_by(execution_intent_id=intent_id).one()


def _event_codes(ctx: dict[str, Any], intent_id: Any) -> list[str]:
    return [row.event_code for row in ctx["db"].query(DocumentStorageExecutionEvent)
            .filter_by(execution_intent_id=intent_id).order_by(DocumentStorageExecutionEvent.sequence)]


def test_t1_normal_create_verifies_exact_checksum_and_publishes_one_revision(storage_context):
    intent = _prepare(storage_context)
    content, candidate = _candidate(storage_context, intent)
    state = _verify(storage_context, intent, content)
    assert state.current_state == "OBJECT_VERIFIED"
    binding = _finalize(storage_context, intent)
    assert storage_context["provider"].object_bytes(object_key=candidate.object_key) == content
    assert binding.content_sha256 == hashlib.sha256(content).hexdigest()
    assert binding.byte_length == len(content)
    assert binding.object_created_at is not None and binding.verified_at is not None
    assert binding.retention_policy_code == "official-document-10y"
    assert binding.minimum_retain_until.replace(tzinfo=timezone.utc) == RETENTION_UNTIL
    assert storage_context["db"].query(DocumentRevision).count() == 2
    assert _head(storage_context).current_revision_id == binding.document_revision_id
    assert _head(storage_context).document_revision == 2


def test_t2_duplicate_same_checksum_reuses_object_and_has_no_duplicate_effect(storage_context):
    intent = _prepare(storage_context, key="same-key")
    content, _ = _candidate(storage_context, intent)
    _verify(storage_context, intent, content)
    first = _finalize(storage_context, intent)
    creates = storage_context["provider"].calls["create"]
    replay = _prepare(storage_context, key="same-key")
    assert replay.id == intent.id
    _candidate(storage_context, replay, object_key=f"tenant/{intent.organization_id}/intent/{intent.id}")
    assert _verify(storage_context, replay, content).current_state == "FINALIZED"
    second = _finalize(storage_context, replay)
    assert second.id == first.id
    assert storage_context["provider"].calls["create"] == creates
    assert storage_context["db"].query(DocumentRevision).count() == 2


def test_t3_same_key_with_wrong_provider_bytes_requires_reconciliation(storage_context):
    intent = _prepare(storage_context, key="candidate-reuse")
    content, candidate = _candidate(storage_context, intent, label="original", object_key="same-key")
    wrong, _ = _content("different")
    storage_context["provider"].seed_object(object_key=candidate.object_key, content=wrong)
    assert _verify(storage_context, intent, content).current_state == "RECONCILIATION_REQUIRED"
    assert storage_context["provider"].calls["create"] == 1
    assert storage_context["provider"].object_bytes(object_key=candidate.object_key) == wrong
    assert storage_context["db"].query(DocumentRevision).count() == 1
    assert _head(storage_context).document_revision == 1


def test_t4_lost_success_response_observes_same_key_and_finalizes_without_blind_retry(storage_context):
    intent = _prepare(storage_context, key="lost-response")
    content, candidate = _candidate(storage_context, intent)
    storage_context["provider"].set_fault("create", "after_commit_before_response")
    assert _verify(storage_context, intent, content).current_state == "OBJECT_VERIFIED"
    binding = _finalize(storage_context, intent)
    assert storage_context["provider"].calls["create"] == 1
    assert storage_context["provider"].calls["observe"] >= 1
    assert storage_context["provider"].object_bytes(object_key=candidate.object_key) == content
    assert binding.document_revision_id == _head(storage_context).current_revision_id


def test_t5_crash_before_provider_commit_recovers_absent_then_explicit_create(storage_context):
    intent = _prepare(storage_context, key="before-create")
    content, candidate = _candidate(storage_context, intent)
    storage_context["provider"].set_fault("create", "before_commit_crash")
    with pytest.raises(InjectedStorageCrash):
        _verify(storage_context, intent, content)
    assert _state(storage_context, intent.id).current_state == "CREATE_DISPATCHED"
    assert storage_context["provider"].object_bytes(object_key=candidate.object_key) is None
    assert storage_context["db"].query(DocumentRevision).count() == 1
    storage_context["provider"].clear_fault("create")
    assert _verify(storage_context, intent, content).current_state == "CANDIDATE_GENERATED"
    assert storage_context["provider"].calls["create"] == 1
    assert _verify(storage_context, intent, content).current_state == "OBJECT_VERIFIED"
    assert storage_context["provider"].calls["create"] == 2
    assert _finalize(storage_context, intent).document_revision_id == _head(storage_context).current_revision_id


def test_t6_crash_after_provider_commit_recovers_present_object_and_finalizes_once(storage_context):
    intent = _prepare(storage_context, key="after-create")
    content, candidate = _candidate(storage_context, intent)
    storage_context["provider"].set_fault("create", "after_commit_crash")
    with pytest.raises(InjectedStorageCrash):
        _verify(storage_context, intent, content)
    assert _state(storage_context, intent.id).current_state == "CREATE_DISPATCHED"
    assert storage_context["provider"].object_bytes(object_key=candidate.object_key) == content
    storage_context["provider"].clear_fault("create")
    assert _verify(storage_context, intent, content).current_state == "OBJECT_VERIFIED"
    assert storage_context["provider"].calls["create"] == 1
    assert storage_context["provider"].calls["observe"] >= 1
    binding = _finalize(storage_context, intent)
    assert _finalize(storage_context, intent).id == binding.id
    assert storage_context["db"].query(DocumentRevision).count() == 2


def test_t7_database_finalization_failure_rolls_back_revision_head_binding_but_keeps_candidate(storage_context, monkeypatch):
    intent = _prepare(storage_context, key="db-failure")
    content, candidate = _candidate(storage_context, intent)
    _verify(storage_context, intent, content)
    real_commit = storage_context["db"].commit
    monkeypatch.setattr(storage_context["db"], "commit", lambda: (_ for _ in ()).throw(RuntimeError("database finalization failure")))
    with pytest.raises(RuntimeError, match="database finalization"):
        _finalize(storage_context, intent)
    storage_context["db"].rollback()
    assert storage_context["db"].query(DocumentRevision).count() == 1
    assert _head(storage_context).document_revision == 1
    assert storage_context["provider"].object_bytes(object_key=candidate.object_key) == content
    monkeypatch.setattr(storage_context["db"], "commit", real_commit)
    assert _finalize(storage_context, intent).document_revision_id == _head(storage_context).current_revision_id


def test_t10_wrong_content_rejects_finalization_and_replacement_create(storage_context):
    intent = _prepare(storage_context, key="wrong-content")
    content, candidate = _candidate(storage_context, intent)
    wrong, _ = _content("wrong")
    storage_context["provider"].seed_object(object_key=candidate.object_key, content=wrong)
    assert _verify(storage_context, intent, content).current_state == "RECONCILIATION_REQUIRED"
    assert storage_context["provider"].calls["create"] == 1
    assert storage_context["provider"].object_bytes(object_key=candidate.object_key) == wrong
    assert storage_context["db"].query(DocumentRevision).count() == 1
    assert _head(storage_context).document_revision == 1


def test_t11_temporary_storage_outage_is_recoverable_without_automatic_write_retry(storage_context):
    intent = _prepare(storage_context, key="storage-down")
    content, _ = _candidate(storage_context, intent)
    storage_context["provider"].set_fault("create", "unavailable")
    assert _verify(storage_context, intent, content).current_state == "STORAGE_UNAVAILABLE"
    assert storage_context["provider"].calls["create"] == 1
    assert storage_context["db"].query(DocumentRevision).count() == 1
    storage_context["provider"].clear_fault("create")
    assert _verify(storage_context, intent, content).current_state == "CANDIDATE_GENERATED"
    assert _verify(storage_context, intent, content).current_state == "OBJECT_VERIFIED"
    assert storage_context["provider"].calls["create"] == 2


def test_t11_observe_ambiguous_fails_closed_for_reconciliation(storage_context):
    intent = _prepare(storage_context, key="observe-ambiguous")
    content, _ = _candidate(storage_context, intent)
    storage_context["provider"].set_fault("create", "after_commit_before_response")
    storage_context["provider"].set_fault("observe", "ambiguous")
    assert _verify(storage_context, intent, content).current_state == "RECONCILIATION_REQUIRED"
    assert _event_codes(storage_context, intent.id)[-1] == "OBJECT_UNVERIFIABLE"


def test_t11_observe_unavailable_is_durable_and_recoverable(storage_context):
    intent = _prepare(storage_context, key="observe-unavailable")
    content, _ = _candidate(storage_context, intent)
    storage_context["provider"].set_fault("create", "after_commit_before_response")
    storage_context["provider"].set_fault("observe", "unavailable")
    assert _verify(storage_context, intent, content).current_state == "STORAGE_UNAVAILABLE"
    storage_context["provider"].clear_fault("observe")
    storage_context["provider"].clear_fault("create")
    assert _verify(storage_context, intent, content).current_state == "OBJECT_VERIFIED"


def test_t11_verify_unavailable_is_durable_and_recoverable(storage_context):
    intent = _prepare(storage_context, key="verify-unavailable")
    content, _ = _candidate(storage_context, intent)
    storage_context["provider"].set_fault("verify", "unavailable")
    assert _verify(storage_context, intent, content).current_state == "STORAGE_UNAVAILABLE"
    storage_context["provider"].clear_fault("verify")
    assert _verify(storage_context, intent, content).current_state == "OBJECT_VERIFIED"


def test_t11_verify_unverifiable_requires_reconciliation(storage_context):
    intent = _prepare(storage_context, key="verify-unverifiable")
    content, _ = _candidate(storage_context, intent)
    storage_context["provider"].set_fault("verify", "unverifiable")
    assert _verify(storage_context, intent, content).current_state == "RECONCILIATION_REQUIRED"
    assert _event_codes(storage_context, intent.id)[-1] == "CHECKSUM_NOT_VERIFIED"


def test_t12_cleanup_requires_terminal_unbound_candidate(storage_context):
    intent = _prepare(storage_context, key="orphan-cleanup")
    content, candidate = _candidate(storage_context, intent)
    _verify(storage_context, intent, content)
    _state(storage_context, intent.id).current_state = "SUPERSEDED"
    storage_context["db"].commit()
    cleaned = _cleanup(storage_context, intent)
    assert cleaned.current_state == "SUPERSEDED"
    assert storage_context["provider"].object_bytes(object_key=candidate.object_key) is None
    assert storage_context["provider"].calls["cleanup"] == 1


def test_t12_cleanup_deferred_is_durable_then_retries(storage_context):
    intent = _prepare(storage_context, key="cleanup-deferred")
    content, candidate = _candidate(storage_context, intent)
    _verify(storage_context, intent, content)
    _state(storage_context, intent.id).current_state = "SUPERSEDED"
    storage_context["db"].commit()
    storage_context["provider"].set_fault("cleanup", "unavailable")
    assert _cleanup(storage_context, intent).current_state == "SUPERSEDED"
    assert storage_context["provider"].object_bytes(object_key=candidate.object_key) == content
    assert _event_codes(storage_context, intent.id)[-1] == "CLEANUP_DEFERRED"
    storage_context["provider"].clear_fault("cleanup")
    _cleanup(storage_context, intent)
    assert storage_context["provider"].object_bytes(object_key=candidate.object_key) is None
    assert _event_codes(storage_context, intent.id)[-1] == "CANDIDATE_CLEANED"


def test_t12_cleanup_rejects_finalized_bound_candidate(storage_context):
    intent = _prepare(storage_context, key="cleanup-bound")
    content, candidate = _candidate(storage_context, intent)
    _verify(storage_context, intent, content)
    _finalize(storage_context, intent)
    with pytest.raises(HTTPException) as exc:
        _cleanup(storage_context, intent)
    assert exc.value.status_code == 409
    assert exc.value.detail["error_code"] == "storage_cleanup_forbidden"
    assert storage_context["provider"].calls["cleanup"] == 0
    assert storage_context["provider"].object_bytes(object_key=candidate.object_key) == content


def test_t12_cleanup_policy_and_legal_hold_block_provider_delete(storage_context):
    intent = _prepare(storage_context, key="cleanup-policy-blocked")
    content, candidate = _candidate(storage_context, intent)
    _verify(storage_context, intent, content)
    _state(storage_context, intent.id).current_state = "SUPERSEDED"
    storage_context["db"].commit()
    for kwargs in ({"policy_allows_cleanup": False}, {"legal_hold_active": True}):
        with pytest.raises(HTTPException) as exc:
            _cleanup(storage_context, intent, **kwargs)
        assert exc.value.status_code == 409
        assert exc.value.detail["error_code"] == "storage_cleanup_policy_blocked"
        assert storage_context["provider"].calls["cleanup"] == 0
        assert storage_context["provider"].object_bytes(object_key=candidate.object_key) == content


def test_t13_repeated_recovery_is_idempotent_and_audit_transition_sequence_is_append_only(storage_context):
    intent = _prepare(storage_context, key="recovery-replay")
    content, _ = _candidate(storage_context, intent)
    storage_context["provider"].set_fault("create", "after_commit_before_response")
    _verify(storage_context, intent, content)
    storage_context["provider"].clear_fault("create")
    assert _verify(storage_context, intent, content).current_state == "OBJECT_VERIFIED"
    assert _verify(storage_context, intent, content).current_state == "OBJECT_VERIFIED"
    _finalize(storage_context, intent)
    assert _event_codes(storage_context, intent.id) == [
        "PREPARED", "CANDIDATE_GENERATED", "CREATE_DISPATCHED", "CREATE_OUTCOME_UNKNOWN",
        "OBJECT_OBSERVED", "OBJECT_VERIFIED", "FINALIZING", "FINALIZED",
    ]
    assert sorted(event.sequence for event in storage_context["db"].query(DocumentStorageExecutionEvent).filter_by(execution_intent_id=intent.id)) == list(range(1, 9))


def test_t14_replayed_finalize_cannot_create_duplicate_document_revision(storage_context):
    intent = _prepare(storage_context, key="finalize-replay")
    content, _ = _candidate(storage_context, intent)
    _verify(storage_context, intent, content)
    first = _finalize(storage_context, intent)
    replay = _finalize(storage_context, intent)
    assert replay.id == first.id
    assert storage_context["db"].query(DocumentRevision).count() == 2
    assert _head(storage_context).current_revision_id == first.document_revision_id
