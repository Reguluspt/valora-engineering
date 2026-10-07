"""One confirmed independent Supplier per exact inherited line, computed on read."""
from dataclasses import dataclass

from app.modules.project_master_data.application.asset_line_validation_rules import value
from app.modules.project_master_data.application.price_evidence_provider import evaluate_price_evidence_provider


@dataclass(frozen=True)
class SupplierQuoteProviderResult:
    result: str
    blockers: list
    stale: list
    next_action: dict
    provider_key: str = "supplier_quotes_v1"


def evaluate_supplier_quote_provider(snapshot, *, effective_permissions, has_active_session=False, available=True):
    def action(kind, key=None, context=None):
        return dict(kind=kind, stage=None if kind == "NO_AUTHORIZED_DOWNSTREAM_ACTION" else "SUPPLIER_QUOTES",
            semantic_route_key=key, validation_issue_id=None, context=context)
    upstream = evaluate_price_evidence_provider(snapshot, effective_permissions=effective_permissions, has_active_session=has_active_session)
    if not available or upstream.result != "COMPLETE":
        return SupplierQuoteProviderResult("NOT_AVAILABLE", [], [], action("UNAVAILABLE"))
    state = snapshot.supplier_quotes
    if not state.intact:
        return SupplierQuoteProviderResult("STALE", [], [dict(stage="SUPPLIER_QUOTES", reason_code="quote_integrity_conflict")], action("UNAVAILABLE"))
    if state.holds:
        return SupplierQuoteProviderResult("BLOCKED", [dict(stage="SUPPLIER_QUOTES", reason_code=code) for code in sorted(set(state.holds))], [], action("BLOCKER"))
    if state.complete:
        return SupplierQuoteProviderResult("COMPLETE", [], [], action("NO_AUTHORIZED_DOWNSTREAM_ACTION"))
    if value(snapshot.project.status) != "draft":
        return SupplierQuoteProviderResult("BLOCKED", [dict(stage="SUPPLIER_QUOTES", reason_code="project_not_draft")], [], action("UNAVAILABLE"))
    stale = [dict(stage="SUPPLIER_QUOTES", reason_code=reason) for revision in state.confirmed_heads.values()
        if state.status[revision.id] == "confirmed" for reason in state.reasons[revision.id]
        if any(not state.coverage.get(i.line_id) for i in state.items[revision.id].values())]
    if stale:
        return SupplierQuoteProviderResult("STALE", [], stale, action("UNAVAILABLE", context=dict(kind="supplier_quotes_diagnostic",
            project_id=str(snapshot.project.id), case_version=snapshot.case_version, reload_required=True)))
    context = dict(kind="supplier_quotes_preparation", project_id=str(snapshot.project.id), case_version=snapshot.case_version,
        project_row_version=snapshot.project.row_version, seal_id=str(snapshot.seal.id), membership_version=snapshot.seal.membership_version,
        authoritative_set_sha256=snapshot.seal.authoritative_set_sha256, contract_version="supplier-quote-registration-v1")
    next_action = action("PENDING", "supplier_quotes_prepare_required", context)
    if "workbench:edit" not in effective_permissions or not has_active_session:
        next_action = action("UNAVAILABLE")
    return SupplierQuoteProviderResult("INCOMPLETE", [], [], next_action)
