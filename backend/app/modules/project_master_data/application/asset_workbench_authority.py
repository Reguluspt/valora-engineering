"""Shared immutable preparation bindings and receipt/audit integrity on every read."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.modules.project_master_data.application.asset_review_authority import canonical_digest
from app.modules.project_master_data.application.asset_review_provider import _membership
from app.modules.project_master_data.application.asset_line_validation_rules import rule_digest
from app.modules.project_master_data.asset_workbench_schemas import (
    ConfirmProjectAssetWorkbenchRequest, WithdrawProjectAssetWorkbenchConfirmationRequest,
    WorkbenchCommandResult,
)
from app.modules.project_master_data.models import (
    AssetWorkbenchCommandReceipt, ProjectAssetWorkbenchConfirmation,
    ProjectAssetWorkbenchWithdrawal, AuditEvent,
)

CONFIRM_CONTRACT = "asset-workbench-confirmation-v1"
WITHDRAW_CONTRACT = "asset-workbench-withdrawal-v1"
PREPARATION_MANIFEST = {
    "contract": CONFIRM_CONTRACT, "membership": "exact-asset-review-seal-v1",
    "description": {"type": "string", "trimmed_nonblank": True, "max_length": 5000},
    "appraised_unit_price": "optional-working-data", "proof": "current-accepted-valid-adr0049",
    "downstream": "no-authorized-downstream-action",
}


def description_ready(line):
    return isinstance(line.description, str) and bool(line.description.strip()) and len(line.description) <= 5000


def preparation_digest():
    return canonical_digest(PREPARATION_MANIFEST)


def content_binding(snapshot):
    valid, lines = _membership(snapshot)
    seal = snapshot.seal
    members = []
    for line in lines:
        proof = snapshot.line_proofs[line.id]
        gen, decision = proof["generation"], proof["decision"]
        members.append({"line_id": str(line.id), "staging_row_id": str(line.source_staging_row_id),
            **{key: proof[key] for key in ("official_input_sha256", "reference_sha256", "rule_sha256")},
            "validation_generation_id": str(gen.id) if gen else None,
            "validation_generation": gen.generation if gen else None,
            "positive_decision_id": str(decision.id) if decision else None,
            "decision_version": decision.decision_version if decision else None})
    return {"contract": CONFIRM_CONTRACT, "preparation_sha256": preparation_digest(),
        "rule_sha256": rule_digest(), "organization_id": str(snapshot.project.organization_id),
        "project_id": str(snapshot.project.id), "membership_proved": valid,
        "seal_id": str(seal.id) if seal else None,
        "authoritative_set_sha256": seal.authoritative_set_sha256 if seal else None,
        "membership_version": seal.membership_version if seal else None,
        "entry_lineage_sha256": canonical_digest(snapshot.entry_manifest), "members": members}


def request_digest(*, org_id, actor_id, project_id, request):
    return canonical_digest({"organization_id": str(org_id), "actor_user_id": str(actor_id),
        "project_id": str(project_id), "request": request})


def record_digest(record):
    # Full provenance, including protected invocation/reason, is pinned by digest only in audit.
    return canonical_digest({column.name: (None if value is None else
        value.astimezone(timezone.utc).isoformat() if isinstance(value, datetime) else str(value)
        if column.name.endswith("_id") or column.name == "id" else value)
        for column in record.__table__.columns for value in [getattr(record, column.name)]})


def audit_binding(record, receipt):
    confirmation = isinstance(record, ProjectAssetWorkbenchConfirmation)
    return {"command_id": str(receipt.command_id), "receipt_id": str(receipt.id),
        "confirmation_id": str(record.id if confirmation else record.confirmation_id),
        "reversal_id": None if confirmation else str(record.id),
        "project_id": str(record.project_id), "session_id": str(record.session_id),
        "seal_id": str(record.seal_id), "authoritative_set_sha256": record.authoritative_set_sha256,
        "membership_version": record.membership_version, "contract_version": record.contract_version,
        "content_sha256": record.content_sha256, "record_sha256": record_digest(record),
        "request_sha256": receipt.request_sha256,
        "pre_row_version": record.pre_row_version, "post_row_version": record.post_row_version,
        "confirmed": True, "reason_present": record.reason_note is not None}


def receipt_integrity(record, receipt, audits):
    if receipt is None:
        return False
    try:
        confirming = isinstance(record, ProjectAssetWorkbenchConfirmation)
        schema = ConfirmProjectAssetWorkbenchRequest if confirming else WithdrawProjectAssetWorkbenchConfirmationRequest
        request = schema.model_validate(record.invocation_binding)
        result = WorkbenchCommandResult.model_validate(receipt.response_metadata)
        scope = ("organization_id", "project_id", "actor_user_id", "session_id")
        if (not all(getattr(record, field) == getattr(receipt, field) for field in scope)
                or record.contract_version != request.contract_version or receipt.contract_version != request.contract_version
                or receipt.command_id != request.command_id or not record.confirmed
                or receipt.request_sha256 != request_digest(org_id=record.organization_id,
                    actor_id=record.actor_user_id, project_id=record.project_id,
                    request=request.model_dump(mode="json"))
                or record.content_sha256 != canonical_digest(record.content_binding)
                or request.expected_project_row_version != record.pre_row_version
                or record.post_row_version != record.pre_row_version + 1
                or request.expected_seal_id != record.seal_id
                or request.expected_membership_version != record.membership_version
                or request.expected_authoritative_set_sha256 != record.authoritative_set_sha256
                or request.reason_note != record.reason_note
                or result.command_id != receipt.command_id or result.receipt_id != receipt.id
                or result.project_id != record.project_id or result.contract_version != record.contract_version
                or result.confirmation_id != (record.id if confirming else record.confirmation_id)
                or result.reversal_id != (None if confirming else record.id)
                or result.project_row_version != record.post_row_version
                or result.created_at != record.created_at):
            return False
        if confirming and request.supersedes_confirmation_id != record.supersedes_confirmation_id:
            return False
        if not confirming and request.expected_confirmation_id != record.confirmation_id:
            return False
        event = "ProjectAssetWorkbenchConfirmed" if confirming else "ProjectAssetWorkbenchConfirmationWithdrawn"
        command = "ConfirmProjectAssetWorkbench" if confirming else "WithdrawProjectAssetWorkbenchConfirmation"
        bindings = audit_binding(record, receipt)
        matching = [a for a in audits if a.event_name == event and a.command_name == command
            and a.entity_type == "Project" and a.entity_id == record.project_id
            and a.organization_id == record.organization_id and a.actor_user_id == record.actor_user_id
            and a.payload == bindings]
        return len(matching) == 1
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


@dataclass
class WorkbenchAuthority:
    latest: object | None
    reversal: object | None
    withdrawn: bool
    intact: bool
    content_current: bool
    receipts: dict
    records: dict
    facts: dict


def resolve_workbench_authority(db, snapshot):
    org_id, project_id = snapshot.project.organization_id, snapshot.project.id

    def scoped(model):
        return db.query(model).filter_by(organization_id=org_id, project_id=project_id).populate_existing()

    confirmations = scoped(ProjectAssetWorkbenchConfirmation).order_by(
        ProjectAssetWorkbenchConfirmation.confirmation_version, ProjectAssetWorkbenchConfirmation.id).all()
    withdrawals = scoped(ProjectAssetWorkbenchWithdrawal).order_by(
        ProjectAssetWorkbenchWithdrawal.pre_row_version, ProjectAssetWorkbenchWithdrawal.id).all()
    receipts = {r.id: r for r in scoped(AssetWorkbenchCommandReceipt).all()}
    audits = db.query(AuditEvent).filter(AuditEvent.organization_id == org_id,
        AuditEvent.entity_id == project_id, AuditEvent.event_name.in_(
            ("ProjectAssetWorkbenchConfirmed", "ProjectAssetWorkbenchConfirmationWithdrawn"))).populate_existing().all()
    records = {r.receipt_id: r for r in [*confirmations, *withdrawals]}
    latest = confirmations[-1] if confirmations else None
    reversal = withdrawals[-1] if withdrawals else None
    by_confirmation = {r.confirmation_id: r for r in withdrawals}
    intact = len(records) == len(receipts) == len(audits) and len(by_confirmation) == len(withdrawals)
    for index, confirmation in enumerate(confirmations):
        prior = confirmations[index - 1] if index else None
        prior_reversal = by_confirmation.get(prior.id) if prior else None
        intact = intact and bool(
            confirmation.confirmation_version == index + 1
            and confirmation.supersedes_confirmation_id == (prior.id if prior else None)
            and confirmation.prior_reversal_id == (prior_reversal.id if prior_reversal else None)
            and (not prior or confirmation.pre_row_version >= prior.post_row_version)
            and (not prior_reversal or confirmation.pre_row_version >= prior_reversal.post_row_version)
            and receipt_integrity(confirmation, receipts.get(confirmation.receipt_id), audits))
    by_id = {r.id: r for r in confirmations}
    for withdrawal in withdrawals:
        prior = by_id.get(withdrawal.confirmation_id)
        intact = intact and bool(prior and withdrawal.pre_row_version >= prior.post_row_version
            and receipt_integrity(withdrawal, receipts.get(withdrawal.receipt_id), audits))
    withdrawn = bool(latest and latest.id in by_confirmation)
    current = bool(intact and latest and not withdrawn and snapshot.seal_current and snapshot.lineage_current
        and latest.content_binding == content_binding(snapshot)
        and latest.content_sha256 == canonical_digest(content_binding(snapshot))
        and all(snapshot.line_proofs[line.id]["positive_current"] and description_ready(line)
                for line in snapshot.lines))
    def fact(record):
        return {"id": str(record.id), "digest": record_digest(record)} if record else None
    facts = {"contract": CONFIRM_CONTRACT, "preparation_sha256": preparation_digest(),
        "confirmation": fact(latest), "reversal": fact(reversal), "withdrawn": withdrawn,
        "intact": intact, "content_current": current,
        "receipts": sorted([str(r.id) + ":" + canonical_digest(r.response_metadata) + ":" + r.request_sha256
                            for r in receipts.values()]),
        "audit": sorted([str(a.id) + ":" + canonical_digest(a.payload) for a in audits])}
    return WorkbenchAuthority(latest, reversal, withdrawn, intact, current, receipts, records, facts)
