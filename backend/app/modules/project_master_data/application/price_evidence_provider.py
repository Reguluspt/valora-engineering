"""PRICE_EVIDENCE readiness remains computed from current durable facts."""
from dataclasses import dataclass

from app.modules.project_master_data.application.asset_workbench_provider import evaluate_asset_workbench_provider
from app.modules.project_master_data.application.asset_review_provider import _membership
from app.modules.project_master_data.application.asset_line_validation_rules import value
from app.modules.project_master_data.application.price_evidence_authority import CONTRACT


@dataclass(frozen=True)
class PriceEvidenceProviderResult:
    result: str
    blockers: list
    stale: list
    next_action: dict
    provider_key: str = "price_evidence_confirmation_v1"


def evaluate_price_evidence_provider(snapshot, *, effective_permissions, has_active_session=False, available=True):
    def action(kind, key=None, context=None):
        return dict(kind=kind, stage=None if kind == "NO_AUTHORIZED_DOWNSTREAM_ACTION" else "PRICE_EVIDENCE",
                    semantic_route_key=key, validation_issue_id=None, context=context)

    upstream = evaluate_asset_workbench_provider(snapshot, effective_permissions=effective_permissions,
                                                  has_active_session=has_active_session)
    if not available or not snapshot.intake or not snapshot.seal or any(p.result != "COMPLETE" for p in snapshot.prefix):
        return PriceEvidenceProviderResult("NOT_AVAILABLE", [], [], action("UNAVAILABLE"))
    state = snapshot.price_evidence
    blockers = [{**item, "stage": "PRICE_EVIDENCE"} for item in upstream.blockers]
    stale = [{**item, "stage": "PRICE_EVIDENCE"} for item in upstream.stale]
    if state.holds:
        blockers.append(dict(stage="PRICE_EVIDENCE", reason_code="suitability_hold"))
    if value(snapshot.project.status) != "draft" and not state.content_current:
        blockers.append(dict(stage="PRICE_EVIDENCE", reason_code="project_not_draft"))
    reasons = ["evidence_integrity_conflict"] if not state.intact else sorted(set(state.stale))
    if state.latest and not state.withdrawn and not state.content_current:
        reasons.append("reconfirmation_required")
    stale.extend(dict(stage="PRICE_EVIDENCE", reason_code=reason) for reason in reasons)
    if blockers:
        return PriceEvidenceProviderResult("BLOCKED", blockers, stale,
            upstream.next_action if upstream.blockers else action("BLOCKER"))
    if stale:
        context = dict(kind="price_evidence_diagnostic", project_id=str(snapshot.project.id),
                       case_version=snapshot.case_version, reason_code="evidence_currentness_conflict", reload_required=True)
        if not state.intact:
            context["reason_code"] = "evidence_integrity_conflict"
        return PriceEvidenceProviderResult("STALE", [], stale, action("UNAVAILABLE", context=context))
    if upstream.result != "COMPLETE":
        return PriceEvidenceProviderResult("INCOMPLETE", [], [], upstream.next_action)
    if state.content_current:
        return PriceEvidenceProviderResult("COMPLETE", [], [], action("NO_AUTHORIZED_DOWNSTREAM_ACTION"))
    valid, ordered = _membership(snapshot)
    if not valid:
        return PriceEvidenceProviderResult("STALE", [], [dict(stage="PRICE_EVIDENCE", reason_code="seal_mismatch")], action("UNAVAILABLE"))
    deficient = next((line for line in ordered if not state.qualifying.get(line.id)), None)
    context = dict(kind="price_evidence_preparation", project_id=str(snapshot.project.id), case_version=snapshot.case_version,
        project_row_version=snapshot.project.row_version, seal_id=str(snapshot.seal.id),
        authoritative_set_sha256=snapshot.seal.authoritative_set_sha256, membership_version=snapshot.seal.membership_version,
        contract_version=CONTRACT, upstream_confirmation_id=str(snapshot.workbench.latest.id),
        prior_confirmation_id=str(state.latest.id) if state.latest else None, confirmation_required=True,
        reason_code="evidence_required" if deficient else "confirmation_required")
    if deficient:
        context.update(line_id=str(deficient.id), line_row_version=deficient.row_version)
    next_action = action("PENDING", "price_evidence_prepare_required", context)
    if "workbench:edit" not in effective_permissions or not has_active_session:
        next_action = action("UNAVAILABLE")
    return PriceEvidenceProviderResult("INCOMPLETE", [], [], next_action)
