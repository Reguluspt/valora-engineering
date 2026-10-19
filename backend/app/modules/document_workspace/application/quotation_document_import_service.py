"""Human-confirmed TXT custody using the existing storage transaction owner."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import text, update

from app.core.audit import log_audit_event
from app.core.rbac import derive_effective_permissions
from app.db.session import SessionLocal, engine
from app.modules.document_workspace.application import document_storage_service as storage
from app.modules.document_workspace.models import (
    DocumentRevision, DocumentRevisionCurrentHead, DocumentStorageCandidate, DocumentStorageExecutionEvent,
    DocumentStorageExecutionIntent, DocumentStorageExecutionState, StorageObjectBinding,
    QuotationDocumentImportRequest as ImportRequest,
    QuotationDocumentImportReceipt as ImportReceipt,
)
from app.modules.document_workspace.quotation_document_import_schemas import (
    CONTRACT, MEDIA_TYPE, ImportCommand, OriginalTxt, RecoverCommand, reject,
)
from app.modules.project_master_data.application.asset_review_authority import resolve_authority
from app.modules.project_master_data.application.supplier_quote_source import retained_source, run_storage
from app.modules.project_master_data.models import (
    AuditEvent, OrganizationProfile, Project, Role, User, UserRole, UserSession,
)

POLICY_CODE = "quotation-txt-record-10y-v1"
POLICY = {
    "schema": "quotation-txt-retention-policy-v1",
    "policy_code": POLICY_CODE, "policy_version": 1,
    "business_authority": "issue208/comment6247157693",
    "document_type": "supplier_quotation_source", "media_type": MEDIA_TYPE,
    "initial_milestone_event": "QUOTATION_DOCUMENT_IMPORTED",
    "initial_milestone_clock": "postgresql-finalization-transaction-timestamp-v1",
    "initial_minimum_calendar_years": 10,
    "calendar_rule": "utc-same-month-day-time; feb29-clamp-to-feb28",
    "future_release_rule": "max(existing-floor, certified-project-release-at-plus-10-calendar-years)",
    "extension_fact_mode": "append-only; original-binding-immutable",
    "legal_hold_rule": "any-active-hold-denies-purge", "ordinary_finalized_delete": "forbidden",
    "uncertified_extension_enforcement": "no-purge-no-finalized-expiry",
}
TARGET = dict(storage_profile_id="exchange-local", provider_kind="local", container_name="valora-document-blobs")
RECOVERABLE_STATES = {"PREPARED", "CANDIDATE_GENERATED", "CREATE_DISPATCHED", "CREATE_OUTCOME_UNKNOWN", "STORAGE_UNAVAILABLE", "OBJECT_OBSERVED", "OBJECT_VERIFIED"}


def digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def ten_year_floor(value: datetime) -> datetime:
    value = value.astimezone(timezone.utc)
    try:
        return value.replace(year=value.year + 10)
    except ValueError:
        return value.replace(year=value.year + 10, day=28)


class ImportAlreadyFinalized(Exception):
    pass


def _fresh():
    return SessionLocal(autoflush=False, expire_on_commit=False)


def _limits(db):
    if db.get_bind().dialect.name != "postgresql":
        reject(503, "txt_postgresql_required")
    db.execute(text("SET LOCAL lock_timeout = '5s'"))
    db.execute(text("SET LOCAL statement_timeout = '15s'"))


def _actor(db, *, org_id, actor_id, session_id, lock=False, write=False):
    def read(model, **scope):
        q = db.query(model).filter_by(**scope).populate_existing()
        return (q.with_for_update(read=True) if lock else q).first()

    org = read(OrganizationProfile, id=org_id)
    user = read(User, id=actor_id, organization_id=org_id)
    session = read(UserSession, id=session_id, user_id=actor_id, organization_id=org_id)
    now = db.scalar(text("select clock_timestamp()"))
    if (not org or org.status != "active" or not user or user.status != "active"
            or not session or session.status != "active" or session.revoked_at is not None
            or any(v.astimezone(timezone.utc) <= now for v in (
                session.access_expires_at, session.idle_expires_at, session.absolute_expires_at))):
        reject(403, "txt_actor_unavailable")
    grants = db.query(UserRole).filter_by(user_id=actor_id).order_by(UserRole.id).populate_existing()
    grants = (grants.with_for_update(read=True) if lock else grants).all()
    role_ids = sorted({g.role_id for g in grants if g.is_active and g.revoked_at is None})
    roles = db.query(Role).filter(Role.id.in_(role_ids)).order_by(Role.id).populate_existing()
    (roles.with_for_update(read=True) if lock else roles).all()
    db.expire(user, ["roles", "organization"])
    permissions = derive_effective_permissions(user, db)
    if not {"project:read", *( ["project:update"] if write else [])}.issubset(permissions):
        reject(403, "txt_permission_required")
    return user, permissions


def _project(db, *, org_id, project_id, lock=False):
    q = db.query(Project).filter_by(id=project_id, organization_id=org_id).populate_existing()
    project = (q.with_for_update() if lock else q).first()
    if project is None:
        reject(404, "txt_project_not_found")
    return project


def import_context(*, org_id, actor_id, session_id, project_id, blob_store):
    with _fresh() as db:
        _, permissions = _actor(db, org_id=org_id, actor_id=actor_id, session_id=session_id)
    bind = engine.execution_options(isolation_level="REPEATABLE READ")
    with SessionLocal(bind=bind, autoflush=False) as db:
        db.info["supplier_quote_blob_store"] = blob_store
        snapshot = resolve_authority(db, org_id=org_id, project_id=project_id)
        project = snapshot.project
        blocked = []
        if "project:update" not in permissions:
            blocked.append("permission_required")
        if project.status != "draft":
            blocked.append("project_not_draft")
        if blob_store.provider_kind != "local":
            blocked.append("local_storage_required")
        return dict(contract_version=CONTRACT, project_id=str(project.id), project_code=project.code,
            project_name=project.name, case_version=snapshot.case_version, project_row_version=project.row_version,
            can_import=not blocked, blocked_codes=blocked, extension=".txt", encoding="utf-8", max_bytes=1048576,
            retention_policy_code=POLICY_CODE, policy_version=1)


def _manifests(command, original, *, org_id, project_id, actor_id, policy=None, target=None):
    policy = POLICY if policy is None else policy
    target = TARGET if target is None else target
    policy_sha = digest(policy)
    snapshot = digest(dict(schema="quotation-txt-source-snapshot-v1", org=str(org_id), project=str(project_id),
        document_type="supplier_quotation_source", filename=original.filename, media_type=MEDIA_TYPE,
        encoding="utf-8", content_sha256=original.sha256, byte_length=len(original.content)))
    plan = digest(dict(schema=policy["schema"], policy_code=policy["policy_code"], policy_version=policy["policy_version"],
        validation_manifest=policy, storage_profile=target["storage_profile_id"], container=target["container_name"], provider_kind=target["provider_kind"]))
    common = dict(org=str(org_id), project=str(project_id), actor=str(actor_id), command_id=str(command.command_id),
        confirm=True, snapshot=snapshot, plan=plan, expected_case_version=command.expected_case_version,
        expected_project_row_version=command.expected_project_row_version)
    decision = digest(dict(schema="quotation-txt-human-admission-v1", **common))
    request = digest(dict(schema="quotation-txt-import-request-v1", contract_version=CONTRACT, decision=decision, **common))
    return dict(snapshot_sha256=snapshot, plan_sha256=plan, decision_sha256=decision, request_sha256=request,
        policy_manifest_sha256=policy_sha)


def _request(db, *, org_id, project_id, actor_id, command_id):
    request = db.query(ImportRequest).filter_by(command_id=command_id).populate_existing().first()
    if request is not None and (request.organization_id, request.project_id, request.actor_user_id) != (org_id, project_id, actor_id):
        reject(404, "txt_import_not_found")
    return request


def _validate_envelope(db, request):
    intent = db.get(DocumentStorageExecutionIntent, request.execution_intent_id)
    audit = db.get(AuditEvent, request.prepared_audit_id)
    original = OriginalTxt(request.filename, b"", request.content_sha256)
    command = ImportCommand.model_validate_json(json.dumps(dict(contract_version=CONTRACT, command_id=str(request.command_id),
        confirm=True, expected_case_version=request.expected_case_version, expected_project_row_version=request.expected_project_row_version,
        expected_sha256=request.content_sha256, expected_byte_length=request.byte_length)))
    # Rebuild source manifest with the recorded byte count; raw bytes never enter the envelope.
    snapshot = digest(dict(schema="quotation-txt-source-snapshot-v1", org=str(request.organization_id), project=str(request.project_id),
        document_type="supplier_quotation_source", filename=request.filename, media_type=MEDIA_TYPE,
        encoding="utf-8", content_sha256=request.content_sha256, byte_length=request.byte_length))
    plan = digest(dict(schema=request.policy_manifest["schema"], policy_code=request.retention_policy_code, policy_version=request.policy_version,
        validation_manifest=request.policy_manifest, storage_profile=request.storage_profile_id,
        container=request.container_name, provider_kind=request.provider_kind))
    common = dict(org=str(request.organization_id), project=str(request.project_id), actor=str(request.actor_user_id),
        command_id=str(command.command_id), confirm=True, snapshot=snapshot, plan=plan,
        expected_case_version=request.expected_case_version, expected_project_row_version=request.expected_project_row_version)
    decision = digest(dict(schema="quotation-txt-human-admission-v1", **common))
    request_sha = digest(dict(schema="quotation-txt-import-request-v1", contract_version=request.contract_version, decision=decision, **common))
    if (request.contract_version != CONTRACT or request.media_type != MEDIA_TYPE
            or digest(request.policy_manifest) != request.policy_manifest_sha256
            or request.policy_version != 1 or request.policy_manifest.get("policy_code") != request.retention_policy_code
            or request.snapshot_sha256 != snapshot or request.plan_sha256 != plan or request.decision_sha256 != decision
            or request.request_sha256 != request_sha or not intent or not audit
            or audit.event_name != "QUOTATION_DOCUMENT_IMPORT_PREPARED"
            or (audit.organization_id, audit.actor_user_id, audit.entity_id) != (request.organization_id, request.actor_user_id, request.id)
            or audit.payload != dict(command_id=str(request.command_id), byte_length=request.byte_length)
            or (intent.project_id, intent.document_id, intent.requested_by_user_id, intent.intent_kind, intent.expected_revision_id,
                intent.expected_document_revision, intent.expected_content_sha256, intent.initial_data_snapshot_digest_sha256,
                intent.request_digest_sha256, intent.plan_digest_sha256, intent.decision_digest_sha256)
            != (request.project_id, request.document_id, request.actor_user_id, "INITIAL_REVISION", None, 0,
                original.sha256, snapshot, request_sha, plan, decision)
            or intent.idempotency_key != "txt-quote-import:" + str(request.command_id)):
        reject(409, "txt_envelope_integrity")
    return intent


def _historical(db, request):
    _validate_envelope(db, request)
    receipt = db.query(ImportReceipt).filter_by(request_id=request.id).first()
    if receipt is None:
        if db.query(StorageObjectBinding.id).filter_by(organization_id=request.organization_id, execution_intent_id=request.execution_intent_id).first():
            reject(409, "txt_receipt_missing")
        return None
    binding = db.get(StorageObjectBinding, receipt.binding_id)
    revision = db.get(DocumentRevision, receipt.revision_id)
    audit = db.get(AuditEvent, receipt.milestone_audit_id)
    state = db.get(DocumentStorageExecutionState, request.execution_intent_id)
    candidate = db.get(DocumentStorageCandidate, binding.storage_candidate_id) if binding else None
    if (not binding or not revision or not audit or not state or not candidate or state.current_state != "FINALIZED"
            or digest(receipt.snapshot) != receipt.receipt_sha256
            or receipt.snapshot != _receipt_snapshot(request, receipt, binding, audit.created_at)
            or audit.event_name != "QUOTATION_DOCUMENT_IMPORTED"
            or (audit.organization_id, audit.actor_user_id, audit.entity_id) != (request.organization_id, request.actor_user_id, receipt.id)
            or audit.payload.get("milestone_at") != stamp(receipt.finalized_at)
            or (receipt.organization_id, receipt.project_id, receipt.actor_user_id, receipt.execution_intent_id, receipt.document_id)
            != (request.organization_id, request.project_id, request.actor_user_id, request.execution_intent_id, request.document_id)
            or (binding.execution_intent_id, binding.document_revision_id, binding.content_sha256, binding.byte_length)
            != (request.execution_intent_id, revision.id, request.content_sha256, request.byte_length)
            or revision.document_revision != 1 or revision.document_id != request.document_id
            or receipt.policy_manifest != request.policy_manifest or receipt.policy_manifest_sha256 != request.policy_manifest_sha256
            or (receipt.content_sha256, receipt.byte_length, receipt.post_project_row_version) != (request.content_sha256, request.byte_length, request.expected_project_row_version + 1)
            or not (audit.created_at == receipt.finalized_at == receipt.retention_anchor_at == binding.retention_anchor_at == binding.bound_at)
            or binding.minimum_retain_until != ten_year_floor(audit.created_at)
            or binding.minimum_retain_until != receipt.minimum_retain_until):
        reject(409, "txt_receipt_integrity")
    if (binding.retention_policy_code != request.retention_policy_code
            or receipt.retention_policy_code != request.retention_policy_code
            or receipt.policy_version != request.policy_version
            or (binding.organization_id, binding.project_id, binding.document_id) != (request.organization_id, request.project_id, request.document_id)
            or (candidate.execution_intent_id, candidate.storage_profile_id, candidate.provider_kind, candidate.container_name)
            != (request.execution_intent_id, request.storage_profile_id, request.provider_kind, request.container_name)
            or (binding.storage_profile_id, binding.provider_kind, binding.container_name, binding.object_key)
            != (candidate.storage_profile_id, candidate.provider_kind, candidate.container_name, candidate.object_key)
            or binding.object_key != f"{request.organization_id.hex}/{request.project_id.hex}/{request.document_id.hex}/{request.execution_intent_id.hex}.txt"
            or audit.payload != dict(milestone_at=stamp(receipt.finalized_at), receipt_id=str(receipt.id),
                policy_code=receipt.retention_policy_code, policy_version=receipt.policy_version,
                minimum_retain_until=stamp(receipt.minimum_retain_until), byte_length=receipt.byte_length)):
        reject(409, "txt_receipt_integrity")
    storage_audit = db.query(AuditEvent).filter_by(organization_id=request.organization_id,
        entity_id=binding.id, event_name="DOCUMENT_STORAGE_REVISION_FINALIZED", actor_user_id=request.actor_user_id).first()
    event = db.query(DocumentStorageExecutionEvent).filter_by(organization_id=request.organization_id,
        execution_intent_id=request.execution_intent_id, sequence=state.last_event_sequence, event_code="FINALIZED").first()
    if not event or not storage_audit or storage_audit.payload != dict(document_id=str(request.document_id),
            document_revision_id=str(receipt.revision_id), byte_length=request.byte_length):
        reject(409, "txt_receipt_integrity")
    return receipt, binding, state


def _receipt_snapshot(request, receipt, binding, t):
    return dict(schema="quotation-txt-import-receipt-v1", command_id=str(request.command_id),
        organization_id=str(request.organization_id), project_id=str(request.project_id), actor_user_id=str(request.actor_user_id),
        request_id=str(request.id), intent_id=str(request.execution_intent_id), document_id=str(request.document_id),
        revision_id=str(receipt.revision_id), binding_id=str(binding.id), receipt_id=str(receipt.id),
        milestone_event_id=str(receipt.milestone_audit_id), request_digest=request.request_sha256,
        sha256=request.content_sha256, byte_length=request.byte_length, generation=1,
        retention_policy_code=receipt.retention_policy_code, policy_version=receipt.policy_version,
        policy_manifest_sha256=receipt.policy_manifest_sha256, policy_manifest=receipt.policy_manifest,
        finalized_at=stamp(t), retention_anchor_at=stamp(t),
        minimum_retain_until=stamp(receipt.minimum_retain_until), post_project_row_version=receipt.post_project_row_version)


def read_status(*, org_id, project_id, actor_id, session_id, command_id, blob_store):
    with _fresh() as db:
        _actor(db, org_id=org_id, actor_id=actor_id, session_id=session_id)
        _project(db, org_id=org_id, project_id=project_id)
        request = _request(db, org_id=org_id, project_id=project_id, actor_id=actor_id, command_id=command_id)
        if request is None:
            reject(404, "txt_import_not_found")
        historical = _historical(db, request)
        result = dict(contract_version=CONTRACT, command_id=str(command_id), project_id=str(project_id), request_id=str(request.id),
            intent_id=str(request.execution_intent_id), document_id=str(request.document_id), request_digest=request.request_sha256,
            sha256=request.content_sha256, byte_length=request.byte_length)
        if historical:
            receipt, binding, state = historical
            result.update(outcome="finalized", storage_state=state.current_state, storage_state_version=state.state_version,
                historical_receipt=receipt.snapshot, receipt_digest=receipt.receipt_sha256, **{k: v for k, v in receipt.snapshot.items() if k not in result})
            result.update(effective_minimum_retain_until=None, purge_allowed=False,
                purge_reason="release_extension_enforcement_not_certified", retention_disposition="NO_PURGE_EXTENSION_UNCERTIFIED")
            revision_id = binding.document_revision_id
            document_id = request.document_id
        else:
            state = db.get(DocumentStorageExecutionState, request.execution_intent_id)
            result.update(outcome="pending", storage_state=state.current_state, storage_state_version=state.state_version,
                recovery_permitted=state.current_state in RECOVERABLE_STATES)
            return result
    # Publication locks and their transaction have ended before current A13 object proof.
    with _fresh() as db:
        db.info["supplier_quote_blob_store"] = blob_store
        _, available = retained_source(db, org_id=org_id, project_id=project_id, document_id=document_id, revision_id=revision_id)
    result["source"] = dict(available=available, reason=None if available else "source_not_current_or_unavailable", observed_at=stamp(datetime.now(timezone.utc)))
    return result


def import_original(*, org_id, project_id, actor_id, session_id, command: ImportCommand, original: OriginalTxt, blob_store, recover=False):
    scope = dict(org_id=org_id, project_id=project_id, actor_id=actor_id, session_id=session_id)
    if (original.sha256, len(original.content)) != (command.expected_sha256, command.expected_byte_length):
        reject(409, "txt_original_mismatch")
    manifests = _manifests(command, original, org_id=org_id, project_id=project_id, actor_id=actor_id)
    with _fresh() as db:
        _, permissions = _actor(db, org_id=org_id, actor_id=actor_id, session_id=session_id)
        request = _request(db, org_id=org_id, project_id=project_id, actor_id=actor_id, command_id=command.command_id)
        if request:
            manifests = _manifests(command, original, org_id=org_id, project_id=project_id, actor_id=actor_id,
                policy=request.policy_manifest, target={key: getattr(request, key) for key in TARGET})
            if request.request_sha256 != manifests["request_sha256"]:
                reject(409, "txt_command_reused")
            if _historical(db, request):
                return read_status(**scope, command_id=command.command_id, blob_store=blob_store), False
            if blob_store.provider_kind != "local":
                reject(409, "txt_storage_target_changed")
            if "project:update" not in permissions:
                reject(403, "txt_permission_required")
            if not recover:
                return read_status(**scope, command_id=command.command_id, blob_store=blob_store), False
            state = db.get(DocumentStorageExecutionState, request.execution_intent_id)
            if not isinstance(command, RecoverCommand) or state.state_version != command.expected_storage_state_version or state.current_state not in RECOVERABLE_STATES:
                reject(409, "txt_recovery_stale")
            if request.policy_manifest != POLICY or request.policy_manifest_sha256 != digest(POLICY):
                reject(409, "txt_policy_changed")
            intent_id = request.execution_intent_id
        else:
            if blob_store.provider_kind != "local":
                reject(409, "txt_storage_target_changed")
            if "project:update" not in permissions:
                reject(403, "txt_permission_required")
            if recover:
                reject(404, "txt_import_not_found")
            intent_id = None
    if intent_id is None:
        context = import_context(**scope, blob_store=blob_store)
        if not context["can_import"]:
            reject(403, "txt_import_unavailable")
        if (context["case_version"], context["project_row_version"]) != (command.expected_case_version, command.expected_project_row_version):
            reject(409, "txt_preflight_stale")
        with _fresh() as db:
            try:
                _limits(db)
                project = _project(db, org_id=org_id, project_id=project_id, lock=True)
                actor, _ = _actor(db, org_id=org_id, actor_id=actor_id, session_id=session_id, lock=True, write=True)
                raced = _request(db, org_id=org_id, project_id=project_id, actor_id=actor_id, command_id=command.command_id)
                if raced:
                    if raced.request_sha256 != manifests["request_sha256"]:
                        reject(409, "txt_command_reused")
                    db.rollback()
                    return read_status(**scope, command_id=command.command_id, blob_store=blob_store), False
                if project.status != "draft" or project.row_version != command.expected_project_row_version:
                    reject(409, "txt_project_stale")

                def prepare_callback(session, intent):
                    envelope = ImportRequest(id=uuid.uuid4(), organization_id=org_id, project_id=project_id, actor_user_id=actor_id,
                        command_id=command.command_id, execution_intent_id=intent.id, document_id=intent.document_id,
                        contract_version=CONTRACT, filename=original.filename, media_type=MEDIA_TYPE, content_sha256=original.sha256,
                        byte_length=len(original.content), expected_case_version=command.expected_case_version,
                        expected_project_row_version=command.expected_project_row_version, retention_policy_code=POLICY_CODE,
                        policy_version=1, policy_manifest=POLICY, prepared_audit_id=uuid.uuid4(), **TARGET, **manifests)
                    log_audit_event(session, event_name="QUOTATION_DOCUMENT_IMPORT_PREPARED", entity_type="QuotationDocumentImportRequest",
                        entity_id=envelope.id, organization_id=org_id, actor_user_id=actor_id, command_name="ImportQuotationDocument",
                        audit_event_id=envelope.prepared_audit_id, payload=dict(command_id=str(command.command_id), byte_length=len(original.content)))
                    session.add(envelope)

                intent = storage.prepare_initial_storage_intent(db, actor=actor, organization_id=org_id, project_id=project_id,
                    document_type="supplier_quotation_source", title=original.filename, expected_content_sha256=original.sha256,
                    data_snapshot_digest_sha256=manifests["snapshot_sha256"], idempotency_key="txt-quote-import:" + str(command.command_id),
                    request_digest_sha256=manifests["request_sha256"], plan_digest_sha256=manifests["plan_sha256"],
                    decision_digest_sha256=manifests["decision_sha256"], preparation_callback=prepare_callback)
                intent_id = intent.id
            except BaseException:
                db.rollback()
                raise
    if recover:
        context = import_context(**scope, blob_store=blob_store)
        if not context["can_import"] or (context["case_version"], context["project_row_version"]) != (command.expected_case_version, command.expected_project_row_version):
            reject(409, "txt_recovery_context_stale")
    with _fresh() as db:
        request = _request(db, org_id=org_id, project_id=project_id, actor_id=actor_id, command_id=command.command_id)
        _validate_envelope(db, request)
        if {key: getattr(request, key) for key in TARGET} != TARGET:
            reject(409, "txt_storage_target_changed")
        candidate = storage.record_storage_candidate(db, organization_id=org_id, intent_id=intent_id, content=original.content,
            object_key=f"{org_id.hex}/{project_id.hex}/{request.document_id.hex}/{intent_id.hex}.txt", media_type=MEDIA_TYPE,
            generator_version="quotation-txt-original-v1", **TARGET)
        state = run_storage(storage.create_or_recover_storage_object(db, organization_id=org_id, intent_id=intent_id,
            content=original.content, blob_store=blob_store))
        state_name = state.current_state
        candidate_id, key, size, sha = candidate.id, candidate.object_key, candidate.byte_length, candidate.content_sha256
    if state_name != "OBJECT_VERIFIED":
        return read_status(**scope, command_id=command.command_id, blob_store=blob_store), False
    before = run_storage(blob_store.observe(object_key=key))
    verified = run_storage(blob_store.read_verified(object_key=key, expected_sha256=sha, expected_byte_length=size, max_bytes=1048576))
    after = run_storage(blob_store.observe(object_key=key))
    if (str(before.status) != "PRESENT" or before != after or before.byte_length != size or not before.provider_object_version
            or not before.object_created_at or str(verified.status) != "MATCH" or verified.observed_sha256 != sha
            or verified.observed_byte_length != size):
        reject(409, "txt_source_verification_failed")
    own_receipt_id = None
    try:
        with _fresh() as db:
            try:
                _limits(db)
                t = db.scalar(text("select transaction_timestamp()" )).astimezone(timezone.utc)
                floor = ten_year_floor(t)

                def guard(session):
                    project = _project(session, org_id=org_id, project_id=project_id, lock=True)
                    _actor(session, org_id=org_id, actor_id=actor_id, session_id=session_id, lock=True, write=True)
                    request = _request(session, org_id=org_id, project_id=project_id, actor_id=actor_id, command_id=command.command_id)
                    if _historical(session, request):
                        raise ImportAlreadyFinalized()
                    if project.status != "draft" or project.row_version != command.expected_project_row_version:
                        reject(409, "txt_project_stale")
                    if session.query(DocumentRevisionCurrentHead).filter_by(organization_id=org_id, project_id=project_id, document_id=request.document_id).first():
                        reject(409, "txt_initial_head_conflict")
                    if request.request_sha256 != manifests["request_sha256"] or request.policy_manifest != POLICY:
                        reject(409, "txt_envelope_integrity")
                    persisted = session.get(DocumentStorageCandidate, candidate_id)
                    observation = session.query(DocumentStorageExecutionEvent).filter_by(organization_id=org_id,
                        execution_intent_id=intent_id, event_code="OBJECT_OBSERVED").order_by(DocumentStorageExecutionEvent.sequence.desc()).first()
                    if (not persisted or not observation or persisted.execution_intent_id != intent_id
                            or (persisted.provider_kind, persisted.storage_profile_id, persisted.container_name) != ("local", "exchange-local", TARGET["container_name"])
                            or (persisted.object_key, persisted.content_sha256, persisted.byte_length) != (key, sha, size)
                            or (observation.observed_object_version, observation.observed_object_created_at, observation.observed_byte_length)
                            != (before.provider_object_version, before.object_created_at, size)):
                        reject(409, "txt_source_proof_stale")

                def finalize_callback(session, revision, binding):
                    nonlocal own_receipt_id
                    if (binding.organization_id, binding.project_id, binding.document_id, binding.storage_candidate_id,
                            binding.provider_object_version, binding.object_created_at, binding.content_sha256, binding.byte_length) != (
                            org_id, project_id, revision.document_id, candidate_id, before.provider_object_version,
                            before.object_created_at, sha, size):
                        reject(409, "txt_final_source_proof_changed")
                    binding.bound_at = t
                    session.flush()
                    cas = session.execute(update(Project).where(Project.organization_id == org_id, Project.id == project_id,
                        Project.status == "draft", Project.row_version == command.expected_project_row_version).values(
                            row_version=command.expected_project_row_version + 1, updated_by=actor_id), execution_options={"synchronize_session": False})
                    if cas.rowcount != 1:
                        reject(409, "txt_project_stale")
                    request = _request(session, org_id=org_id, project_id=project_id, actor_id=actor_id, command_id=command.command_id)
                    receipt = ImportReceipt(id=uuid.uuid4(), organization_id=org_id, project_id=project_id, actor_user_id=actor_id,
                        request_id=request.id, execution_intent_id=intent_id, document_id=request.document_id, revision_id=revision.id,
                        binding_id=binding.id, milestone_audit_id=uuid.uuid4(), content_sha256=sha, byte_length=size,
                        retention_policy_code=POLICY_CODE, policy_version=1, policy_manifest=POLICY, policy_manifest_sha256=digest(POLICY),
                        finalized_at=t, retention_anchor_at=t, minimum_retain_until=floor,
                        post_project_row_version=command.expected_project_row_version + 1)
                    own_receipt_id = receipt.id
                    receipt.snapshot = _receipt_snapshot(request, receipt, binding, t)
                    receipt.receipt_sha256 = digest(receipt.snapshot)
                    log_audit_event(session, event_name="QUOTATION_DOCUMENT_IMPORTED", entity_type="QuotationDocumentImportReceipt",
                        entity_id=receipt.id, organization_id=org_id, actor_user_id=actor_id, command_name="ImportQuotationDocument",
                        audit_event_id=receipt.milestone_audit_id, created_at=t,
                        payload=dict(milestone_at=stamp(t), receipt_id=str(receipt.id), policy_code=POLICY_CODE,
                            policy_version=1, minimum_retain_until=stamp(floor), byte_length=size))
                    session.add(receipt)
                    session.flush()
                    if not (binding.bound_at == binding.retention_anchor_at == receipt.retention_anchor_at == t
                            and binding.minimum_retain_until == receipt.minimum_retain_until == floor):
                        reject(409, "txt_retention_integrity")

                storage.finalize_storage_revision(db, organization_id=org_id, intent_id=intent_id,
                    retention_policy_code=POLICY_CODE, retention_anchor_at=t, minimum_retain_until=floor,
                    pre_finalization_guard=guard, finalization_callback=finalize_callback)
            except BaseException:
                db.rollback()
                raise
    except ImportAlreadyFinalized:
        return read_status(**scope, command_id=command.command_id, blob_store=blob_store), False
    result = read_status(**scope, command_id=command.command_id, blob_store=blob_store)
    return result, own_receipt_id is not None and result.get("receipt_id") == str(own_receipt_id)
