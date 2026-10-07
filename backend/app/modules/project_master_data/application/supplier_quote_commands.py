"""Project-first commands, one caller-owned transaction, historical receipts."""
import uuid

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.db.mixins import utc_now
from app.modules.project_master_data.models import Supplier, Currency
from app.modules.project_master_data.supplier_quote_models import SupplierQuoteFact as Fact, SupplierQuoteItem as Item, SupplierQuoteReceipt as Receipt
from app.modules.project_master_data.supplier_quote_schemas import COMMAND_SCHEMAS, QuoteTerms
from app.modules.project_master_data.application.asset_review_authority import canonical_digest, lock_project, resolve_authority, require_mutation_actor
from app.modules.project_master_data.application.asset_review_line_commands import require_line_access, conflict
from app.modules.project_master_data.application.asset_workbench_authority import request_digest
from app.modules.project_master_data.application.asset_line_validation_rules import value
from app.modules.project_master_data.application.price_evidence_authority import line_binding
from app.modules.project_master_data.application.price_evidence_provider import evaluate_price_evidence_provider
from app.modules.project_master_data.application.supplier_quote_authority import EVENTS, supplier_binding, upstream_binding, audit_binding, legal_supplier_id, currency_binding
from app.modules.project_master_data.application.supplier_quote_source import retained_source


def response(snapshot, receipt, replayed=False):
    if not snapshot.supplier_quotes.intact or receipt.id not in snapshot.supplier_quotes.receipts:
        conflict("supplier_quote_integrity_conflict")
    return dict(result=receipt.response_metadata, replayed=replayed, historical=True, current_case_version=snapshot.case_version)


def read_receipt(db, *, actor, org_id, project_id, command_id):
    require_mutation_actor(db, actor=actor, org_id=org_id, permission="project:read")
    snapshot = resolve_authority(db, org_id=org_id, project_id=project_id)
    receipt = db.query(Receipt).filter_by(organization_id=org_id, project_id=project_id, actor_user_id=actor.id, command_id=command_id).first()
    if not receipt:
        raise HTTPException(404, detail="Quotation receipt not found")
    return response(snapshot, receipt)


@event.listens_for(Session, "before_commit")
def revalidate_commit(db):
    if db.in_nested_transaction():
        return
    checks = db.info.get("supplier_quote_commit_checks", {})
    if not checks:
        return
    db.flush()
    for project_id, (actor, org_id, expected, session_id, deadline, requires_upstream, revision_id, kind) in checks.items():
        _, session = require_line_access(db, actor=actor, org_id=org_id, project_id=project_id, locked=True)
        fresh = resolve_authority(db, org_id=org_id, project_id=project_id, locked=True)
        if (fresh.case_version != expected or value(fresh.project.status) != "draft" or session.id != session_id
                or not fresh.supplier_quotes.intact or (deadline is not None and utc_now() >= deadline)
                or (requires_upstream and evaluate_price_evidence_provider(fresh, effective_permissions={"workbench:edit"}, has_active_session=True).result != "COMPLETE")):
            conflict("supplier_quote_commit_currentness_conflict")
        if requires_upstream and (set(fresh.supplier_quotes.reasons.get(revision_id, ["revision_missing"])) - ({"not_effective"} if kind != "confirmation" else set())):
            conflict("supplier_quote_commit_source_dependency_conflict")
        if kind == "confirmation" and not fresh.supplier_quotes.eligible.get(revision_id):
            conflict("supplier_quote_commit_confirmation_conflict")


@event.listens_for(Session, "after_transaction_end")
def clear_checks(db, transaction):
    if transaction.parent is None:
        db.info.pop("supplier_quote_commit_checks", None)


def execute(db, *, actor, org_id, project_id, request):
    try:
        invocation = request.model_dump(mode="json") if hasattr(request, "model_dump") else request
        request = COMMAND_SCHEMAS[invocation["contract_version"]].model_validate(invocation)
    except (ValidationError, KeyError, TypeError):
        raise HTTPException(400, detail="Invalid SUPPLIER_QUOTES command contract") from None
    invocation = request.model_dump(mode="json")
    kind = request.contract_version.removeprefix("supplier-quote-").removesuffix("-v1")
    requires_upstream = kind not in ("withdrawal", "rejection")
    lock_project(db, org_id=org_id, project_id=project_id)
    persisted, session = require_line_access(db, actor=actor, org_id=org_id, project_id=project_id, locked=True)
    snapshot = resolve_authority(db, org_id=org_id, project_id=project_id, locked=True)
    state = snapshot.supplier_quotes
    digest = request_digest(org_id=org_id, actor_id=persisted.id, project_id=project_id, request=invocation)
    receipt = db.query(Receipt).filter_by(command_id=request.command_id).first()
    if receipt:
        if (receipt.organization_id != org_id or receipt.project_id != project_id or receipt.actor_user_id != persisted.id or receipt.request_sha256 != digest):
            conflict("supplier_quote_command_reuse_conflict")
        return response(snapshot, receipt, True)
    if value(snapshot.project.status) != "draft":
        raise HTTPException(400, detail="Project must be DRAFT")
    prior = state.heads.get(request.quote_id)
    if (not state.intact or not snapshot.lineage_current or not snapshot.seal_current or not snapshot.seal
            or request.expected_project_row_version != snapshot.project.row_version or request.expected_case_version != snapshot.case_version
            or request.expected_seal_id != snapshot.seal.id or request.expected_authoritative_set_sha256 != snapshot.seal.authoritative_set_sha256
            or request.expected_membership_version != snapshot.seal.membership_version or request.expected_session_id != session.id
            or {i.line_id: i.row_version for i in request.expected_line_versions} != {line.id: line.row_version for line in snapshot.lines}
            or request.expected_price_evidence_confirmation_id != (snapshot.price_evidence.latest.id if snapshot.price_evidence.latest else None)
            or request.expected_revision_id != (prior.id if prior else None)
            or request.expected_quote_head_version != state.versions.get(request.quote_id, 0)):
        conflict("supplier_quote_authority_version_conflict")
    target = state.revisions.get(request.target_revision_id) if kind == "withdrawal" else prior
    if kind == "withdrawal" and (not target or target.quote_id != request.quote_id):
        raise HTTPException(404, detail="Quotation withdrawal target not found")
    supplier = db.query(Supplier).filter_by(organization_id=org_id, id=request.supplier_id).populate_existing().with_for_update(read=True).first()
    if not supplier:
        raise HTTPException(404, detail="Supplier not found")
    if supplier.row_version != request.expected_supplier_row_version or (requires_upstream and (supplier_binding(supplier)["status"] != "active" or supplier.merged_into_supplier_id)):
        conflict("supplier_quote_supplier_version_conflict")
    if requires_upstream and evaluate_price_evidence_provider(snapshot, effective_permissions={"workbench:edit"}, has_active_session=True).result != "COMPLETE":
        conflict("supplier_quote_price_evidence_required")
    if (kind == "registration") != (prior is None):
        conflict("supplier_quote_revision_required")
    if target and target.supplier_id != supplier.id and (kind != "revision" or request.revision_reason != "correction"):
        conflict("supplier_quote_supplier_identity_conflict")
    revision_id = request.source_revision_id if kind in ("registration", "revision") else target.source_revision_id
    source, available = retained_source(db, org_id=org_id, project_id=project_id, document_id=request.quote_id, revision_id=revision_id, locked=True)
    if source is None:
        raise HTTPException(404, detail="Retained source not found")
    if request.expected_source_generation != source["generation"]:
        conflict("supplier_quote_source_version_conflict")
    if requires_upstream and not available:
        conflict("supplier_quote_retained_source_required")
    if requires_upstream and any(r.quote_id != request.quote_id and state.status[r.id] in ("draft", "confirmed")
            and legal_supplier_id(state.suppliers, r.supplier_id) != supplier.id and r.content_binding["source"]["sha256"] == source["sha256"]
            for r in (*state.heads.values(), *state.confirmed_heads.values())):
        conflict("supplier_quote_source_attribution_conflict")
    now, fact_id, receipt_id, audit_id = utc_now(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    written_items, deadline = [], None
    if kind in ("registration", "revision"):
        terms = request.terms
        currency = db.query(Currency).filter_by(code=terms.currency, status="active").populate_existing().with_for_update(read=True).first()
        if not currency:
            raise HTTPException(400, detail="Resolved active currency required")
        if terms.quote_date > now.date() or min(d for d in (terms.expires_at, terms.review_due_at) if d is not None) <= now:
            raise HTTPException(400, detail="Invalid quotation dates")
        written_items = request.items if kind == "revision" else []
        binding = dict(terms=terms.model_dump(mode="json"), source=source, supplier=supplier_binding(supplier), currency=currency_binding(currency), upstream=upstream_binding(snapshot),
            lines={str(line.id): line_binding(snapshot, line.id) for line in snapshot.lines}, prior_supplier_id=str(prior.supplier_id) if prior else None)
        if kind == "revision":
            active = state.confirmed_heads.get(request.quote_id)
            binding["withdraws_revision_id"] = str(active.id) if active and request.revision_reason != "negotiation" else None
            for concern_id in request.resolves_concern_ids:
                if concern_id not in state.concerns or state.concerns[concern_id].quote_id != request.quote_id:
                    raise HTTPException(404, detail="Quotation concern not found")
            binding["resolves_concern_ids"] = [str(c) for c in request.resolves_concern_ids]
            binding["resolution_evidence"] = request.resolution_evidence
        fields = dict(revision_id=None, revision_number=prior.revision_number + 1 if prior else 1, predecessor_id=prior.id if prior else None)
        deadline = min(d for d in (terms.expires_at, terms.review_due_at) if d is not None)
    else:
        status = state.status[target.id]
        fields = dict(revision_id=target.id, revision_number=None, predecessor_id=None)
        binding = dict(revision_sha256=target.content_sha256)
        if requires_upstream:
            terms = QuoteTerms.model_validate(target.content_binding["terms"])
            deadline = min(d for d in (terms.expires_at, terms.review_due_at) if d is not None)
        if kind == "line-registration":
            if status != "draft" or set(state.reasons[prior.id]) - {"not_effective"}:
                conflict("supplier_quote_current_draft_required")
            written_items = [request.item]
            if any(i.line_id != request.item.line_id and i.source_locator == request.item.source_locator for i in state.items[prior.id].values()):
                conflict("supplier_quote_repeated_source_allocation")
        elif kind == "confirmation":
            resolved_ids = {uuid.UUID(c) for c in prior.content_binding.get("resolves_concern_ids", [])}
            unresolved = [c for c, fact in state.concerns.items() if fact.quote_id == request.quote_id and c not in resolved_ids]
            if status != "draft" or state.reasons[prior.id] or unresolved or not state.items[prior.id]:
                conflict("supplier_quote_confirmable_revision_required")
            binding["confirmed_items"] = [str(i.id) for i in sorted(state.items[prior.id].values(), key=lambda i: str(i.line_id))]
        elif kind == "withdrawal":
            if status != "confirmed" or state.confirmed_heads.get(request.quote_id) is not target:
                conflict("supplier_quote_confirmed_revision_required")
        elif status != "draft":
            conflict("supplier_quote_draft_rejection_required")
    if any(item.line_id not in {line.id for line in snapshot.lines} for item in written_items):
        raise HTTPException(404, detail="Exact sealed line not found")
    lines = {line.id: line for line in snapshot.lines}
    if any(not lines[i.line_id].unit or i.unit != lines[i.line_id].unit.code or i.quantity != lines[i.line_id].quantity for i in written_items):
        raise HTTPException(400, detail="Quoted quantity and resolved unit must match the exact sealed line")
    binding["written_items"] = [item.model_dump(mode="json") for item in written_items]
    result = dict(command_id=str(request.command_id), receipt_id=str(receipt_id), record_id=str(fact_id), project_id=str(project_id),
        quote_id=str(request.quote_id), revision_id=str(fact_id if fields["revision_id"] is None else fields["revision_id"]),
        contract_version=request.contract_version, project_row_version=snapshot.project.row_version + 1, created_at=now.isoformat())
    receipt = Receipt(id=receipt_id, organization_id=org_id, project_id=project_id, actor_user_id=persisted.id, session_id=session.id,
        created_at=now, command_id=request.command_id, contract_version=request.contract_version, request_sha256=digest, response_metadata=result)
    try:
        with db.begin_nested():
            db.add(receipt)
            db.flush()
    except IntegrityError as exc:
        if getattr(getattr(exc.orig, "diag", None), "constraint_name", None) == "uq_sq_command":
            conflict("supplier_quote_command_reuse_conflict")
        raise
    fact = Fact(id=fact_id, organization_id=org_id, project_id=project_id, actor_user_id=persisted.id, session_id=session.id, created_at=now,
        quote_id=request.quote_id, supplier_id=supplier.id, kind=kind, source_revision_id=revision_id, receipt_id=receipt_id, audit_id=audit_id,
        seal_id=snapshot.seal.id, pre_row_version=snapshot.project.row_version, post_row_version=snapshot.project.row_version + 1,
        content_sha256=canonical_digest(binding), content_binding=binding, invocation_binding=invocation, **fields)
    snapshot.project.row_version += 1
    event_name, command_name = EVENTS[request.contract_version]
    log_audit_event(db, event_name=event_name, command_name=command_name, entity_type="Project", entity_id=project_id,
        organization_id=org_id, actor_user_id=persisted.id, payload=audit_binding(fact, receipt), audit_event_id=audit_id)
    db.add(fact)
    db.flush()
    for item in written_items:
        db.add(Item(organization_id=org_id, project_id=project_id, fact_id=fact_id, **item.model_dump()))
    db.flush()
    after = resolve_authority(db, org_id=org_id, project_id=project_id, locked=True)
    checks = db.info.setdefault("supplier_quote_commit_checks", {})
    prior_check = checks.get(project_id)
    if prior_check:
        deadline = min((d for d in (deadline, prior_check[4]) if d is not None), default=None)
        requires_upstream = requires_upstream or prior_check[5]
    checks[project_id] = (persisted, org_id, after.case_version, session.id, deadline, requires_upstream, fact_id if fields["revision_id"] is None else fields["revision_id"], kind)
    return response(after, receipt)


def command_for(contract):
    def command(db, **kwargs):
        request = kwargs["request"]
        raw = request.model_dump(mode="json") if hasattr(request, "model_dump") else request
        if not isinstance(raw, dict) or raw.get("contract_version") != contract:
            raise HTTPException(400, detail="Wrong quotation command contract")
        return execute(db, **kwargs)
    return command


register_supplier_quote = command_for("supplier-quote-registration-v1")
register_supplier_quote_line = command_for("supplier-quote-line-registration-v1")
revise_supplier_quote = command_for("supplier-quote-revision-v1")
confirm_supplier_quote = command_for("supplier-quote-confirmation-v1")
withdraw_supplier_quote = command_for("supplier-quote-withdrawal-v1")
reject_supplier_quote = command_for("supplier-quote-rejection-v1")
