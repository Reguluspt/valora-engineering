"""Durable evidence, provenance, negative holds and coherent UTC freshness."""
from dataclasses import dataclass, field
from datetime import timezone
from decimal import Decimal, localcontext

from app.db.mixins import utc_now
from app.modules.project_master_data.application.asset_review_authority import canonical_digest
from app.modules.project_master_data.application.asset_workbench_authority import content_binding as workbench_binding, request_digest, record_digest
from app.modules.project_master_data.models import AuditEvent, Project, ProjectAssetLine
from app.modules.project_master_data.price_evidence_models import (
    PriceEvidenceReceipt, ProjectPriceEvidenceSource as Source, ProjectPriceEvidenceDecision as Decision,
    ProjectPriceEvidenceConfirmation as Confirmation, ProjectPriceEvidenceWithdrawal as Withdrawal, FACT_MODELS,
)
from app.modules.project_master_data.price_evidence_schemas import COMMAND_SCHEMAS, PriceEvidenceResult, SourceMaterial

CONTRACT = "price-evidence-confirmation-v1"
CONTRACT_MANIFEST = {"contract": CONTRACT, "coverage": "each-exact-sealed-line",
    "sources": ["internet_survey", "unit_price_explanation", "prior_appraisal_result"],
    "human": "exact-relationship-and-revision", "confirmation": "whole-set",
    "currentness": "upstream-content-proof-revision-negative-generation-utc-deadline",
    "working_price": "optional-no-write", "downstream": "no-authorized-downstream-action"}
EVENTS = {
    "price-evidence-registration-v1": ("ProjectPriceEvidenceRegistered", "RegisterProjectPriceEvidence"),
    "price-evidence-relevance-v1": ("ProjectPriceEvidenceRelevanceDecided", "DecideProjectPriceEvidenceRelevance"),
    "price-evidence-withdrawal-v1": ("ProjectPriceEvidenceWithdrawn", "WithdrawProjectPriceEvidence"),
    CONTRACT: ("ProjectPriceEvidenceConfirmed", "ConfirmProjectPriceEvidence"),
    "price-evidence-confirmation-withdrawal-v1": ("ProjectPriceEvidenceConfirmationWithdrawn", "WithdrawProjectPriceEvidenceConfirmation"),
}


def contract_digest():
    return canonical_digest(CONTRACT_MANIFEST)


def scaled_sum(terms):
    # Two bounded 26-digit operands and at most 50 inputs fit without rounding.
    with localcontext() as context:
        context.prec = 80
        return sum((amount * coefficient for amount, coefficient in terms), Decimal(0))


def line_binding(snapshot, line_id):
    members = workbench_binding(snapshot)["members"]
    return next((member for member in members if member["line_id"] == str(line_id)), None)


def upstream_binding(snapshot):
    return {"workbench_confirmation_id": str(snapshot.workbench.latest.id) if snapshot.workbench.latest else None,
            "workbench": workbench_binding(snapshot)}


def audit_binding(record, receipt):
    return {"command_id": str(receipt.command_id), "receipt_id": str(receipt.id),
        "audit_id": str(record.audit_id),
        "record_id": str(record.id), "project_id": str(record.project_id), "session_id": str(record.session_id),
        "seal_id": str(record.seal_id), "contract_version": receipt.contract_version,
        "content_sha256": record.content_sha256, "record_sha256": record_digest(record),
        "request_sha256": receipt.request_sha256, "pre_row_version": record.pre_row_version,
        "post_row_version": record.post_row_version, "confirmed": True,
        "reason_present": record.invocation_binding.get("reason_note") is not None}


def receipt_integrity(record, receipt, audits):
    try:
        if receipt is None:
            return False
        request = COMMAND_SCHEMAS[receipt.contract_version].model_validate(record.invocation_binding)
        result = PriceEvidenceResult.model_validate(receipt.response_metadata)
        expected_result = dict(command_id=str(receipt.command_id), receipt_id=str(receipt.id),
            project_id=str(record.project_id), contract_version=receipt.contract_version, record_id=str(record.id),
            relationship_id=str(record.relationship_id) if isinstance(record, Decision) else None,
            project_row_version=record.post_row_version, created_at=record.created_at)
        if (result != PriceEvidenceResult.model_validate(expected_result)
                or any(getattr(record, key) != getattr(receipt, key) for key in
                       ("organization_id", "project_id", "actor_user_id", "session_id", "created_at"))
                or request.command_id != receipt.command_id
                or request.expected_seal_id != record.seal_id
                or request.expected_project_row_version != record.pre_row_version
                or record.post_row_version != record.pre_row_version + 1
                or receipt.request_sha256 != request_digest(org_id=record.organization_id, actor_id=record.actor_user_id,
                    project_id=record.project_id, request=request.model_dump(mode="json"))
                or record.content_sha256 != canonical_digest(record.content_binding)):
            return False
        if isinstance(record, Source):
            if (request.source_id != record.source_id or request.predecessor_revision_id != record.predecessor_id
                    or request.material.model_dump(mode="json") != record.content_binding["material"]
                    or request.material.category != record.category or request.material.expires_at != record.expires_at):
                return False
        elif isinstance(record, Decision):
            if (request.evidence_revision_id != record.evidence_revision_id or request.line_id != record.line_id
                    or request.prior_decision_id != record.predecessor_id or request.outcome != record.outcome
                    or request.disposition != record.disposition or request.review_due_at != record.review_due_at
                    or request.expected_line_proof_sha256 != canonical_digest(record.content_binding["line"])
                    or record.content_binding["relationship_id"] != str(record.relationship_id)):
                return False
        elif isinstance(record, Confirmation):
            if (request.supersedes_confirmation_id != record.predecessor_id
                    or request.expected_workbench_confirmation_id != record.workbench_confirmation_id):
                return False
        elif isinstance(record, Withdrawal):
            if record.target_kind == "confirmation":
                if request.expected_confirmation_id != record.target_id:
                    return False
            elif request.target_kind != record.target_kind or request.target_id != record.target_id:
                return False
        event_name, command_name = EVENTS[receipt.contract_version]
        matches = [a for a in audits if a.id == record.audit_id and a.event_name == event_name and a.command_name == command_name
            and a.organization_id == record.organization_id and a.actor_user_id == record.actor_user_id
            and a.entity_type == "Project" and a.entity_id == record.project_id and a.payload == audit_binding(record, receipt)]
        return len(matches) == 1
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


@dataclass
class PriceEvidenceAuthority:
    sources: dict = field(default_factory=dict)
    source_heads: dict = field(default_factory=dict)
    decisions: dict = field(default_factory=dict)
    decision_heads: dict = field(default_factory=dict)
    withdrawals: dict = field(default_factory=dict)
    confirmations: list = field(default_factory=list)
    receipts: dict = field(default_factory=dict)
    records: dict = field(default_factory=dict)
    intact: bool = True
    stale: list = field(default_factory=list)
    holds: list = field(default_factory=list)
    qualifying: dict = field(default_factory=dict)
    manifest: dict = field(default_factory=dict)
    facts: dict = field(default_factory=dict)
    earliest_deadline: object = None
    latest: object = None
    withdrawn: bool = False
    content_current: bool = False

    def retired(self, record):
        if isinstance(record, Source):
            return ("source", record.id) in self.withdrawals
        return (("decision", record.id) in self.withdrawals
                or ("relationship", record.relationship_id) in self.withdrawals
                or ("source", record.evidence_revision_id) in self.withdrawals)


def source_eligible(db, snapshot, state, source, now, visiting=None, cache=None):
    """No IO/network/provider admission. Retained text is the registered source material."""
    cache = {} if cache is None else cache
    if source.id not in cache:
        cache[source.id] = _source_eligible(db, snapshot, state, source, now, visiting, cache)
    return cache[source.id]


def _source_eligible(db, snapshot, state, source, now, visiting, cache):
    visiting = set() if visiting is None else visiting
    if source.id in visiting or state.source_heads.get(source.source_id) is not source or state.retired(source):
        return False
    if source.expires_at and now >= source.expires_at:
        return False
    try:
        material = SourceMaterial.model_validate(source.content_binding["material"])
        if material.value is None:
            return False
        if material.historical:
            historical = material.historical
            owned = db.query(Project.id).filter_by(id=historical.project_id,
                organization_id=snapshot.project.organization_id).first()
            line = db.query(ProjectAssetLine.id).filter_by(id=historical.line_id, project_id=historical.project_id).first()
            if not owned or not line or historical.project_id == snapshot.project.id:
                return False
        if material.explanation:
            visiting = visiting | {source.id}
            terms = []
            for item in material.explanation.inputs:
                dependency = state.sources.get(item.evidence_revision_id)
                if not dependency or not source_eligible(db, snapshot, state, dependency, now, visiting, cache):
                    return False
                value = SourceMaterial.model_validate(dependency.content_binding["material"]).value
                if (value.range_upper is not None or value.currency != material.value.currency
                        or value.unit_basis != material.value.unit_basis):
                    return False
                terms.append((value.amount, item.coefficient))
            if scaled_sum(terms) != material.explanation.proposed_basis_value:
                return False
        return True
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def resolve_price_evidence_authority(db, snapshot, *, now=None):
    now = now or utc_now()
    state = PriceEvidenceAuthority()
    org_id, project_id = snapshot.project.organization_id, snapshot.project.id

    def scoped(model):
        return db.query(model).filter_by(organization_id=org_id, project_id=project_id).populate_existing()

    receipts = scoped(PriceEvidenceReceipt).all()
    state.receipts = {r.id: r for r in receipts}
    records = sorted([r for model in FACT_MODELS for r in scoped(model).all()], key=lambda r: (r.post_row_version, str(r.id)))
    state.records = {r.receipt_id: r for r in records}
    audits = db.query(AuditEvent).filter(AuditEvent.organization_id == org_id, AuditEvent.entity_id == project_id,
        AuditEvent.event_name.in_([pair[0] for pair in EVENTS.values()])).populate_existing().all()
    state.intact = (len(records) == len(state.records) == len(receipts) == len(audits)
                    and len({r.post_row_version for r in records}) == len(records))
    for record in records:
        state.intact = receipt_integrity(record, state.receipts.get(record.receipt_id), audits) and state.intact
        if isinstance(record, Source):
            prior = state.source_heads.get(record.source_id)
            state.intact = state.intact and record.predecessor_id == (prior.id if prior else None)
            state.intact = state.intact and record.revision == (prior.revision + 1 if prior else 1)
            state.sources[record.id] = record
            state.source_heads[record.source_id] = record
        elif isinstance(record, Decision):
            source = state.sources.get(record.evidence_revision_id)
            prior = state.decision_heads.get((record.line_id, record.source_id))
            state.intact = state.intact and bool(source and source.source_id == record.source_id
                and record.predecessor_id == (prior.id if prior else None)
                and record.invocation_binding.get("predecessor_relationship_id") == (str(prior.relationship_id) if prior else None))
            state.decisions[record.id] = record
            state.decision_heads[(record.line_id, record.source_id)] = record
        elif isinstance(record, Confirmation):
            state.intact = state.intact and record.predecessor_id == (state.latest.id if state.latest else None)
            state.latest = record
            state.confirmations.append(record)
        else:
            target = (state.sources.get(record.target_id) if record.target_kind == "source" else
                      state.decisions.get(record.target_id) if record.target_kind == "decision" else
                      next((d for d in state.decisions.values() if d.relationship_id == record.target_id), None)
                      if record.target_kind == "relationship" else
                      next((c for c in state.confirmations if c.id == record.target_id), None))
            state.intact = state.intact and bool(target and (record.target_kind, record.target_id) not in state.withdrawals)
            state.withdrawals[(record.target_kind, record.target_id)] = record
    state.withdrawn = bool(state.latest and ("confirmation", state.latest.id) in state.withdrawals)
    deadlines = []
    relevant_sources = set()

    def bind_source_deadlines(source):
        if source is None or source.id in relevant_sources:
            return
        relevant_sources.add(source.id)
        if source.expires_at:
            deadlines.append(source.expires_at)
            if now >= source.expires_at:
                state.stale.append("source_expired")
        try:
            explanation = SourceMaterial.model_validate(source.content_binding["material"]).explanation
            for item in explanation.inputs if explanation else []:
                bind_source_deadlines(state.sources.get(item.evidence_revision_id))
        except (ValueError, TypeError, KeyError, AttributeError):
            state.intact = False
    for decision in state.decision_heads.values():
        if decision.disposition == "unresolved_concern":
            state.holds.append(decision.line_id)
        if state.retired(decision) or decision.disposition != "qualifying_basis":
            continue
        source = state.sources.get(decision.evidence_revision_id)
        bind_source_deadlines(source)
        deadlines.append(decision.review_due_at)
        current = bool(source and source_eligible(db, snapshot, state, source, now)
            and decision.content_binding.get("upstream") == upstream_binding(snapshot)
            and decision.content_binding.get("line") == line_binding(snapshot, decision.line_id)
            and decision.content_binding.get("contract_sha256") == contract_digest()
            and now < decision.review_due_at)
        if current:
            state.qualifying.setdefault(decision.line_id, []).append(decision)
        else:
            state.stale.append("evidence_currentness_conflict")
    state.earliest_deadline = min(deadlines) if deadlines else None
    state.manifest = {"contract": CONTRACT, "contract_sha256": contract_digest(), "upstream": upstream_binding(snapshot),
        "sources": sorted([str(s.id) + ":" + record_digest(s) for s in state.source_heads.values()]),
        "decisions": sorted([str(d.id) + ":" + record_digest(d) for d in state.decision_heads.values()]),
        "withdrawals": sorted([str(w.id) + ":" + record_digest(w) for w in state.withdrawals.values() if w.target_kind != "confirmation"]),
        "qualifying": sorted([str(d.line_id) + ":" + str(d.relationship_id) + ":" + str(d.id) + ":" + str(d.evidence_revision_id)
                              for decisions in state.qualifying.values() for d in decisions])}
    state.content_current = bool(state.intact and not state.stale and not state.holds and state.latest
        and not state.withdrawn and snapshot.workbench.content_current and snapshot.seal_current
        and snapshot.lines and all(state.qualifying.get(line.id) for line in snapshot.lines)
        and state.latest.content_binding == state.manifest)
    state.facts = {"contract_sha256": contract_digest(), "manifest": state.manifest,
        "confirmation": record_digest(state.latest) if state.latest else None, "withdrawn": state.withdrawn,
        "history": [record_digest(record) for record in records], "intact": state.intact,
        "receipts": sorted([str(r.id) + ":" + r.request_sha256 + ":" + canonical_digest(r.response_metadata) for r in receipts]),
        "audit": sorted([str(a.id) + ":" + canonical_digest(a.payload) for a in audits]),
        "freshness": sorted(set(state.stale)),
        "earliest_deadline": state.earliest_deadline.astimezone(timezone.utc).isoformat() if state.earliest_deadline else None}
    return state
