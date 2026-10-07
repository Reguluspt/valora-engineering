"""Read-derived quote heads, receipt integrity, exact coverage and currentness."""
from dataclasses import dataclass, field
from collections import Counter
import uuid
from datetime import timezone
from decimal import Decimal, localcontext
from sqlalchemy import or_

from app.db.mixins import utc_now
from app.modules.project_master_data.models import AuditEvent, Supplier, Currency
from app.modules.project_master_data.supplier_quote_models import SupplierQuoteFact as Fact, SupplierQuoteItem as Item, SupplierQuoteReceipt as Receipt
from app.modules.project_master_data.supplier_quote_schemas import COMMAND_SCHEMAS, QuoteTerms, QuoteItemInput
from app.modules.project_master_data.application.asset_review_authority import canonical_digest
from app.modules.project_master_data.application.asset_workbench_authority import request_digest
from app.modules.project_master_data.application.price_evidence_authority import line_binding
from app.modules.project_master_data.application.supplier_quote_source import retained_source

EVENTS = {key: ("SupplierQuote" + name, command) for key, name, command in (
    ("supplier-quote-registration-v1", "Registered", "RegisterSupplierQuote"),
    ("supplier-quote-line-registration-v1", "LineRegistered", "RegisterSupplierQuoteLine"),
    ("supplier-quote-revision-v1", "Revised", "ReviseSupplierQuote"),
    ("supplier-quote-confirmation-v1", "Confirmed", "ConfirmSupplierQuote"),
    ("supplier-quote-withdrawal-v1", "Withdrawn", "WithdrawSupplierQuote"),
    ("supplier-quote-rejection-v1", "Rejected", "RejectSupplierQuote"))}


def check(condition):
    if not condition:
        raise ValueError("Quotation journal integrity conflict")


def item_json(item):
    return QuoteItemInput(line_id=item.line_id, quantity=item.quantity, unit=item.unit,
        unit_price=item.unit_price, source_locator=item.source_locator).model_dump(mode="json")


def comparison_warnings(quoted, working, *, comparable):
    if not comparable or working is None or working <= 0:
        return []
    with localcontext() as context:
        context.prec = 80
        codes = ["below_working_price"] if quoted < working else []
        if abs(quoted - working) * Decimal(100) > working * Decimal(15):
            codes.append("difference_exceeds_15_percent")
        return codes


def supplier_binding(supplier):
    return dict(id=str(supplier.id), organization_id=str(supplier.organization_id), row_version=supplier.row_version,
        legal_name=supplier.legal_name, display_name=supplier.display_name, tax_code=supplier.tax_code,
        status=str(getattr(supplier.status, "value", supplier.status)), merged_into=str(supplier.merged_into_supplier_id) if supplier.merged_into_supplier_id else None,
        identity_sha256=canonical_digest({f: getattr(supplier, f) for f in ("legal_name", "tax_code")}))


def legal_supplier_id(suppliers, supplier_id):
    seen = set()
    while supplier_id not in seen:
        seen.add(supplier_id)
        supplier = suppliers.get(supplier_id)
        if not supplier:
            return None
        if not supplier.merged_into_supplier_id:
            return supplier.id
        supplier_id = supplier.merged_into_supplier_id
    return None


def currency_binding(currency):
    return dict(id=str(currency.id), code=currency.code, status=str(getattr(currency.status, "value", currency.status)), decimal_places=currency.decimal_places)


def upstream_binding(snapshot):
    return dict(seal_id=str(snapshot.seal.id) if snapshot.seal else None,
        membership_sha256=snapshot.seal.authoritative_set_sha256 if snapshot.seal else None,
        price_confirmation_id=str(snapshot.price_evidence.latest.id) if snapshot.price_evidence.latest else None,
        price_content_sha256=snapshot.price_evidence.latest.content_sha256 if snapshot.price_evidence.latest else None)


def audit_binding(fact, receipt):
    return dict(command_id=str(receipt.command_id), receipt_id=str(receipt.id), record_id=str(fact.id),
        project_id=str(fact.project_id), session_id=str(fact.session_id), contract_version=receipt.contract_version,
        pre_row_version=fact.pre_row_version, post_row_version=fact.post_row_version,
        content_sha256=fact.content_sha256, request_sha256=receipt.request_sha256,
        record_sha256=canonical_digest(dict(kind=fact.kind, quote_id=str(fact.quote_id), supplier_id=str(fact.supplier_id),
            revision_id=str(fact.revision_id) if fact.revision_id else None, revision_number=fact.revision_number,
            predecessor_id=str(fact.predecessor_id) if fact.predecessor_id else None, source_revision_id=str(fact.source_revision_id),
            seal_id=str(fact.seal_id), actor_id=str(fact.actor_user_id), created_at=fact.created_at.astimezone(timezone.utc).isoformat())))


@dataclass
class QuoteAuthority:
    facts: dict = field(default_factory=dict)
    records: dict = field(default_factory=dict)
    receipts: dict = field(default_factory=dict)
    heads: dict = field(default_factory=dict)
    revisions: dict = field(default_factory=dict)
    items: dict = field(default_factory=dict)
    status: dict = field(default_factory=dict)
    versions: dict = field(default_factory=dict)
    eligible: dict = field(default_factory=dict)
    reasons: dict = field(default_factory=dict)
    coverage: dict = field(default_factory=dict)
    warnings: dict = field(default_factory=dict)
    intact: bool = True
    complete: bool = False
    holds: list = field(default_factory=list)
    suppliers: dict = field(default_factory=dict)
    confirmed_heads: dict = field(default_factory=dict)
    concerns: dict = field(default_factory=dict)


def resolve_supplier_quote_authority(db, snapshot, *, locked=False):
    state = QuoteAuthority()
    org_id, project_id = snapshot.project.organization_id, snapshot.project.id
    records = db.query(Fact).filter_by(organization_id=org_id, project_id=project_id).order_by(Fact.post_row_version, Fact.id).populate_existing().all()
    receipts = db.query(Receipt).filter_by(organization_id=org_id, project_id=project_id).populate_existing().all()
    state.receipts = {r.id: r for r in receipts}
    all_items = db.query(Item).filter_by(organization_id=org_id, project_id=project_id).populate_existing().all()
    items_by_fact = {}
    for item in all_items:
        items_by_fact.setdefault(item.fact_id, []).append(item)
    audits = {a.id: a for a in db.query(AuditEvent).filter(or_(AuditEvent.id.in_([r.audit_id for r in records]),
        (AuditEvent.organization_id == org_id) & (AuditEvent.entity_id == project_id) & AuditEvent.event_name.in_([e[0] for e in EVENTS.values()]))).populate_existing().all()}
    suppliers_query = db.query(Supplier).filter(Supplier.organization_id == org_id).order_by(Supplier.id).populate_existing()
    if locked:
        suppliers_query = suppliers_query.with_for_update(read=True)
    suppliers = {s.id: s for s in suppliers_query.all()}
    state.suppliers = suppliers
    def legal_key(supplier):
        if supplier.tax_code:
            return "tax:" + "".join(supplier.tax_code.upper().split())
        return "unidentified:" + " ".join(supplier.legal_name.casefold().split())
    legal_counts = Counter(legal_key(s) for s in suppliers.values() if not s.merged_into_supplier_id)
    ambiguous = {key for key, count in legal_counts.items() if count > 1}
    record_tokens = []
    try:
        for fact in records:
            receipt, audit = state.receipts[fact.receipt_id], audits[fact.audit_id]
            request = COMMAND_SCHEMAS[receipt.contract_version].model_validate(fact.invocation_binding)
            response = dict(command_id=str(receipt.command_id), receipt_id=str(receipt.id), record_id=str(fact.id),
                project_id=str(project_id), quote_id=str(fact.quote_id), revision_id=str(fact.id if fact.revision_id is None else fact.revision_id),
                project_row_version=fact.post_row_version, contract_version=receipt.contract_version, created_at=fact.created_at.astimezone(timezone.utc).isoformat())
            expected_items = sorted(fact.content_binding.get("written_items", []), key=lambda i: i["line_id"])
            actual_items = sorted([item_json(i) for i in items_by_fact.get(fact.id, [])], key=lambda i: i["line_id"])
            # Numeric persistence may add trailing zeros; compare validated Decimals.
            check([QuoteItemInput.model_validate(i) for i in expected_items] == [QuoteItemInput.model_validate(i) for i in actual_items])
            check(receipt.response_metadata == response)
            check(all(getattr(fact, f) == getattr(receipt, f) for f in ("organization_id", "project_id", "actor_user_id", "session_id", "created_at")))
            check(request.command_id == receipt.command_id and request.quote_id == fact.quote_id and request.supplier_id == fact.supplier_id)
            check(request.expected_project_row_version == fact.pre_row_version and request.expected_seal_id == fact.seal_id)
            check(fact.post_row_version == fact.pre_row_version + 1 and request.expected_session_id == fact.session_id)
            check(fact.content_sha256 == canonical_digest(fact.content_binding))
            check(receipt.request_sha256 == request_digest(org_id=org_id, actor_id=fact.actor_user_id, project_id=project_id, request=request.model_dump(mode="json")))
            event_name, command_name = EVENTS[receipt.contract_version]
            check(audit.organization_id == org_id and audit.actor_user_id == fact.actor_user_id and audit.entity_id == project_id)
            check(audit.entity_type == "Project" and audit.event_name == event_name and audit.command_name == command_name and audit.payload == audit_binding(fact, receipt))
            check(fact.kind == receipt.contract_version.removeprefix("supplier-quote-").removesuffix("-v1"))
            prior = state.heads.get(fact.quote_id)
            check(request.expected_revision_id == (prior.id if prior else None))
            check(request.expected_quote_head_version == state.versions.get(fact.quote_id, 0))
            if fact.kind in ("registration", "revision"):
                check((fact.kind == "registration") == (prior is None))
                check(fact.predecessor_id == (prior.id if prior else None))
                check(fact.revision_number == (prior.revision_number + 1 if prior else 1))
                check(request.source_revision_id == fact.source_revision_id and fact.content_binding["terms"] == request.terms.model_dump(mode="json"))
                # Issuer continuity was explicitly resolved by the revision command and pinned in its audit digest.
                check(not prior or fact.content_binding["prior_supplier_id"] == str(prior.supplier_id))
                check(fact.kind != "revision" or [QuoteItemInput.model_validate(i) for i in expected_items] == sorted(request.items, key=lambda i: str(i.line_id)))
                if fact.kind == "revision":
                    active = state.confirmed_heads.get(fact.quote_id)
                    withdrawn_id = str(active.id) if active and request.revision_reason != "negotiation" else None
                    check(fact.content_binding["withdraws_revision_id"] == withdrawn_id)
                    check(fact.content_binding["resolves_concern_ids"] == [str(c) for c in request.resolves_concern_ids])
                    check(fact.content_binding["resolution_evidence"] == request.resolution_evidence)
                    if withdrawn_id:
                        state.status[active.id] = "withdrawn"
                        state.confirmed_heads.pop(fact.quote_id)
                state.heads[fact.quote_id] = fact
                state.revisions[fact.id] = fact
                state.items[fact.id] = {i.line_id: i for i in items_by_fact.get(fact.id, [])}
                state.status[fact.id] = "draft"
            else:
                target = state.revisions.get(fact.revision_id)
                check(prior and target and (fact.kind == "withdrawal" or target.id == prior.id))
                check(fact.source_revision_id == target.source_revision_id and fact.supplier_id == target.supplier_id)
                check(fact.content_binding["revision_sha256"] == target.content_sha256)
                status = state.status[target.id]
                if fact.kind == "line-registration":
                    check(status == "draft" and len(actual_items) == 1)
                    check(QuoteItemInput.model_validate(actual_items[0]) == request.item)
                    state.items[prior.id].update({i.line_id: i for i in items_by_fact[fact.id]})
                elif fact.kind == "confirmation":
                    check(status == "draft" and state.items[prior.id])
                    check(fact.content_binding["confirmed_items"] == [str(i.id) for i in sorted(state.items[prior.id].values(), key=lambda i: str(i.line_id))])
                    state.status[prior.id] = "confirmed"
                    former = state.confirmed_heads.get(fact.quote_id)
                    if former:
                        state.status[former.id] = "superseded"
                    state.confirmed_heads[fact.quote_id] = prior
                    resolution_ids = prior.content_binding.get("resolves_concern_ids", [])
                    for concern_id in resolution_ids:
                        concern = state.concerns.pop(uuid.UUID(concern_id))
                        check(concern.quote_id == fact.quote_id and prior.content_binding.get("resolution_evidence"))
                elif fact.kind == "withdrawal":
                    check(status == "confirmed" and state.confirmed_heads[fact.quote_id].id == target.id and request.target_revision_id == target.id)
                    state.status[target.id] = "withdrawn"
                    state.confirmed_heads.pop(fact.quote_id)
                else:
                    check(status == "draft")
                    state.status[prior.id] = "rejected"
                if fact.kind in ("withdrawal", "rejection") and request.concern_code:
                    state.concerns[fact.id] = fact
            state.records[fact.id] = fact
            state.versions[fact.quote_id] = fact.post_row_version
            record_tokens.append(fact.content_sha256)
        check(len(receipts) == len(records) == len(audits) and set(items_by_fact).issubset(state.records))
    except (AssertionError, KeyError, ValueError, TypeError, AttributeError):
        state.intact = False
    now = utc_now()
    dependencies = []
    current_revisions = {r.id: r for r in (*state.heads.values(), *state.confirmed_heads.values())}
    state.holds.extend(f.invocation_binding["concern_code"] for f in state.concerns.values())
    currency_codes = [r.content_binding["terms"]["currency"] for r in current_revisions.values()]
    currencies_query = db.query(Currency).filter(Currency.code.in_(currency_codes)).order_by(Currency.id).populate_existing()
    if locked:
        currencies_query = currencies_query.with_for_update(read=True)
    currencies = {c.code: c for c in currencies_query.all()}
    source_cache = {}
    from app.modules.project_master_data.application.price_evidence_provider import evaluate_price_evidence_provider
    upstream_current = evaluate_price_evidence_provider(snapshot, effective_permissions={"workbench:edit"}, has_active_session=True).result == "COMPLETE"
    for revision in sorted(current_revisions.values(), key=lambda r: (str(r.quote_id), r.revision_number)):
        quote_id = revision.quote_id
        supplier = suppliers.get(revision.supplier_id)
        source_key = (quote_id, revision.source_revision_id)
        if source_key not in source_cache:
            source_cache[source_key] = retained_source(db, org_id=org_id, project_id=project_id, document_id=quote_id,
                revision_id=revision.source_revision_id, locked=locked)
        source, available = source_cache[source_key]
        terms = QuoteTerms.model_validate(revision.content_binding["terms"])
        reasons = []
        currency = currencies.get(terms.currency)
        if not currency or currency_binding(currency) != revision.content_binding["currency"] or currency_binding(currency)["status"] != "active":
            reasons.append("currency_not_current")
        if not source or not available or source != revision.content_binding["source"]:
            reasons.append("source_not_current")
        if not supplier or supplier_binding(supplier) != revision.content_binding["supplier"] or supplier_binding(supplier)["status"] != "active" or supplier.merged_into_supplier_id:
            reasons.append("supplier_not_current")
        if upstream_binding(snapshot) != revision.content_binding["upstream"]:
            reasons.append("upstream_not_current")
        if not upstream_current:
            reasons.append("price_evidence_not_current")
        if now < terms.effective_at:
            reasons.append("not_effective")
        if now >= min(d for d in (terms.expires_at, terms.review_due_at) if d is not None):
            reasons.append("quote_expired")
        items = state.items[revision.id]
        if supplier and (legal_key(supplier) in ambiguous or not supplier.legal_name.strip()):
            reasons.append("supplier_identity_ambiguous")
            if state.status[revision.id] not in ("withdrawn", "rejected"):
                state.holds.append("supplier_identity_ambiguous")
        if len({i.source_locator for i in items.values()}) != len(items):
            state.intact = False
        for item in items.values():
            if revision.content_binding["lines"].get(str(item.line_id)) != line_binding(snapshot, item.line_id):
                reasons.append("line_not_current")
        eligible = bool(state.intact and not reasons and state.status[revision.id] == "confirmed" and items and state.confirmed_heads.get(quote_id) is revision)
        state.eligible[revision.id], state.reasons[revision.id] = eligible, sorted(set(reasons))
        dependencies.append(dict(quote_id=str(quote_id), supplier=supplier_binding(supplier) if supplier else None,
            source=source, currency=currency_binding(currency) if currency else None, available=available, reasons=state.reasons[revision.id], status=state.status[revision.id]))
        for item in items.values():
            if eligible:
                state.coverage.setdefault(item.line_id, set()).add(revision.supplier_id)
            line = next((line for line in snapshot.lines if line.id == item.line_id), None)
            # Exact comparable basis only; warning values never enter public Case State.
            comparable = bool(terms.comparison_basis == "same_working_unit_basis" and line and line.appraised_currency
                and line.unit and terms.currency == line.appraised_currency.code and item.unit == line.unit.code and item.quantity == line.quantity)
            state.warnings[item.id] = comparison_warnings(item.unit_price, Decimal(line.appraised_unit_price) if line and line.appraised_unit_price is not None else None, comparable=comparable)
    state.complete = bool(state.intact and not state.holds and snapshot.lines and all(state.coverage.get(line.id) for line in snapshot.lines))
    state.facts = dict(contract="supplier_quotes_v1", records=record_tokens, intact=state.intact, dependencies=dependencies,
        complete=state.complete, holds=sorted(set(state.holds)), coverage={str(k): sorted(str(s) for s in v) for k, v in state.coverage.items()})
    return state
