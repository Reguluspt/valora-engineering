"""Read-only ASSET_WORKBENCH predicates with the accepted downstream hold."""
from dataclasses import dataclass

from app.modules.project_master_data.application.asset_review_provider import (
    evaluate_asset_review_provider, _membership,
)
from app.modules.project_master_data.application.asset_line_validation_rules import value
from app.modules.project_master_data.application.asset_workbench_authority import CONFIRM_CONTRACT, description_ready

PROVIDER_KEY = "asset_workbench_confirmation_v1"
STAGE = "ASSET_WORKBENCH"


@dataclass(frozen=True)
class AssetWorkbenchProviderResult:
    result: str
    blockers: list
    stale: list
    next_action: dict
    provider_key: str = PROVIDER_KEY


def evaluate_asset_workbench_provider(snapshot, *, effective_permissions, has_active_session=False, available=True):
    def action(kind, key=None, context=None):
        return {"kind": kind, "stage": STAGE if kind != "NO_AUTHORIZED_DOWNSTREAM_ACTION" else None,
                "semantic_route_key": key, "validation_issue_id": None, "context": context}

    upstream = evaluate_asset_review_provider(snapshot, effective_permissions=effective_permissions,
                                              has_active_session=has_active_session)
    if not available or not snapshot.intake or any(p.result != "COMPLETE" for p in snapshot.prefix):
        return AssetWorkbenchProviderResult("NOT_AVAILABLE", [], [], action("UNAVAILABLE"))
    state = snapshot.workbench
    blockers = [{**item, "stage": STAGE} for item in upstream.blockers]
    stale = [{**item, "stage": STAGE} for item in upstream.stale]
    if (snapshot.seal and snapshot.seal.correspondence == []
            and not snapshot.lines):
        blockers.append({"stage": STAGE, "reason_code": "empty_selection"})
    if not state.intact:
        stale.append({"stage": STAGE, "reason_code": "confirmation_integrity_conflict"})
    elif state.latest and not state.withdrawn and not state.content_current:
        stale.append({"stage": STAGE, "reason_code": "reconfirmation_required"})
    if value(snapshot.project.status) != "draft" and not state.content_current:
        blockers.append({"stage": STAGE, "reason_code": "project_not_draft"})
    if blockers:
        if upstream.blockers:
            next_action = upstream.next_action
        else:
            next_action = action("BLOCKER", "asset_review_entry_blocked", {
                "kind": "entry", "project_id": str(snapshot.project.id),
                "case_version": snapshot.case_version, "reason_code": blockers[0]["reason_code"]})
        return AssetWorkbenchProviderResult("BLOCKED", blockers, stale, next_action)
    if stale:
        if upstream.stale:
            next_action = upstream.next_action
        else:
            next_action = action("UNAVAILABLE", "asset_workbench_prepare_required", {
                "kind": "asset_workbench_diagnostic", "project_id": str(snapshot.project.id),
                "case_version": snapshot.case_version, "reason_code": stale[0]["reason_code"],
                "reload_required": True})
        if "workbench:edit" not in effective_permissions or not has_active_session:
            next_action = action("UNAVAILABLE")
        return AssetWorkbenchProviderResult("STALE", [], stale, next_action)
    if upstream.result != "COMPLETE":
        return AssetWorkbenchProviderResult("INCOMPLETE", [], [], upstream.next_action)
    if state.content_current:
        return AssetWorkbenchProviderResult("COMPLETE", [], [], action("NO_AUTHORIZED_DOWNSTREAM_ACTION"))
    valid, ordered = _membership(snapshot)
    if not valid:
        return AssetWorkbenchProviderResult("STALE", [], [{"stage": STAGE, "reason_code": "seal_mismatch"}],
                                            action("UNAVAILABLE"))
    deficient = next((line for line in ordered if not description_ready(line)), None)
    context = {"kind": "asset_workbench_preparation", "project_id": str(snapshot.project.id),
        "case_version": snapshot.case_version, "project_row_version": snapshot.project.row_version,
        "seal_id": str(snapshot.seal.id), "authoritative_set_sha256": snapshot.seal.authoritative_set_sha256,
        "membership_version": snapshot.seal.membership_version, "contract_version": CONFIRM_CONTRACT,
        "confirmation_required": True, "prior_confirmation_id": str(state.latest.id) if state.latest else None,
        "reason_code": "description_required" if deficient else "reconfirmation_required" if state.latest
                       else "confirmation_required"}
    if deficient:
        context.update(line_id=str(deficient.id), line_row_version=deficient.row_version)
    next_action = action("PENDING", "asset_workbench_prepare_required", context)
    if "workbench:edit" not in effective_permissions or not has_active_session:
        next_action = action("UNAVAILABLE", context={"kind": "permission", "project_id": str(snapshot.project.id),
            "case_version": snapshot.case_version,
            "reason_code": "permission_required" if "workbench:edit" not in effective_permissions else "session_required"})
    return AssetWorkbenchProviderResult("INCOMPLETE", [], [], next_action)
