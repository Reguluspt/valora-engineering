"""A10 official commands; the caller owns the single outer commit/rollback."""
import uuid

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.db.mixins import utc_now
from app.modules.project_master_data.application.asset_review_authority import canonical_digest, lock_project, resolve_authority, require_mutation_actor
from app.modules.project_master_data.application.asset_review_line_commands import require_line_access, conflict
from app.modules.project_master_data.application.asset_line_validation_rules import value
from app.modules.project_master_data.application.asset_workbench_provider import evaluate_asset_workbench_provider
from app.modules.project_master_data.application.asset_workbench_authority import request_digest
from app.modules.project_master_data.application.price_evidence_authority import (
    EVENTS, contract_digest, audit_binding, line_binding, upstream_binding, source_eligible, scaled_sum,
)
from app.modules.project_master_data.price_evidence_models import (
    PriceEvidenceReceipt, ProjectPriceEvidenceSource as Source, ProjectPriceEvidenceDecision as Decision,
    ProjectPriceEvidenceConfirmation as Confirmation, ProjectPriceEvidenceWithdrawal as Withdrawal,
)
from app.modules.project_master_data.price_evidence_schemas import (
    RegisterProjectPriceEvidenceRequest, DecideProjectPriceEvidenceRelevanceRequest,
    WithdrawProjectPriceEvidenceRequest, ConfirmProjectPriceEvidenceRequest,
    WithdrawProjectPriceEvidenceConfirmationRequest, PriceEvidenceResult,
)


def _response(snapshot, receipt, *, replayed):
    if not snapshot.price_evidence.intact or receipt.id not in snapshot.price_evidence.records:
        conflict("price_evidence_integrity_conflict")
    return dict(result=PriceEvidenceResult.model_validate(receipt.response_metadata).model_dump(mode="json"),
                replayed=replayed, historical=True, current_case_version=snapshot.case_version)


def read_price_evidence_receipt(db, *, actor, org_id, project_id, command_id):
    require_mutation_actor(db, actor=actor, org_id=org_id, permission="project:read")
    snapshot = resolve_authority(db, org_id=org_id, project_id=project_id)
    receipt = db.query(PriceEvidenceReceipt).filter_by(organization_id=org_id, project_id=project_id,
        actor_user_id=actor.id, command_id=command_id).first()
    if not receipt:
        raise HTTPException(404, detail="Command receipt not found")
    return _response(snapshot, receipt, replayed=False)


@event.listens_for(Session, "before_commit")
def _revalidate_commit(db):
    if db.in_nested_transaction():
        return
    pending = db.info.get("price_evidence_commit_checks", {})
    if not pending:
        return
    db.flush()
    for project_id, (actor, org_id, expected, deadline) in pending.items():
        require_line_access(db, actor=actor, org_id=org_id, project_id=project_id, locked=True)
        fresh = resolve_authority(db, org_id=org_id, project_id=project_id, locked=True)
        if (fresh.case_version != expected or value(fresh.project.status) != "draft"
                or (deadline is not None and utc_now() >= deadline)):
            conflict("price_evidence_commit_currentness_conflict")


@event.listens_for(Session, "after_transaction_end")
def _clear_commit_checks(db, transaction):
    if transaction.parent is None:
        db.info.pop("price_evidence_commit_checks", None)


def _scoped_target(state, request):
    if request.target_kind == "source":
        target = state.sources.get(request.target_id)
        current = target and state.source_heads.get(target.source_id) is target and not state.retired(target)
    elif request.target_kind == "decision":
        target = state.decisions.get(request.target_id)
        current = target and state.decision_heads.get((target.line_id, target.source_id)) is target and not state.retired(target)
    else:
        target = next((d for d in state.decisions.values() if d.relationship_id == request.target_id), None)
        current = target and state.decision_heads.get((target.line_id, target.source_id)) is target and not state.retired(target)
    if not target:
        raise HTTPException(404, detail="Evidence target not found")
    if not current:
        conflict("price_evidence_active_target_required")
    return target


def _execute(db, *, actor, org_id, project_id, request):
    lock_project(db, org_id=org_id, project_id=project_id)
    persisted, session = require_line_access(db, actor=actor, org_id=org_id, project_id=project_id, locked=True)
    snapshot = resolve_authority(db, org_id=org_id, project_id=project_id, locked=True)
    state = snapshot.price_evidence
    invocation = request.model_dump(mode="json")
    digest = request_digest(org_id=org_id, actor_id=persisted.id, project_id=project_id, request=invocation)
    receipt = db.query(PriceEvidenceReceipt).filter_by(command_id=request.command_id).first()
    if receipt:
        if (receipt.organization_id != org_id or receipt.project_id != project_id
                or receipt.actor_user_id != persisted.id or receipt.request_sha256 != digest):
            conflict("price_evidence_command_reuse_conflict")
        return _response(snapshot, receipt, replayed=True)
    if value(snapshot.project.status) != "draft":
        raise HTTPException(400, detail="Project must be DRAFT")
    if (request.expected_project_row_version != snapshot.project.row_version
            or request.expected_case_version != snapshot.case_version
            or not snapshot.seal_current or not snapshot.lineage_current or not snapshot.seal
            or request.expected_seal_id != snapshot.seal.id
            or request.expected_authoritative_set_sha256 != snapshot.seal.authoritative_set_sha256
            or request.expected_membership_version != snapshot.seal.membership_version
            or {item.line_id: item.row_version for item in request.expected_line_versions} != {line.id: line.row_version for line in snapshot.lines}
            or request.expected_workbench_confirmation_id != (snapshot.workbench.latest.id if snapshot.workbench.latest else None)):
        conflict("price_evidence_authority_version_conflict")
    if not state.intact:
        conflict("price_evidence_integrity_conflict")
    registration = isinstance(request, RegisterProjectPriceEvidenceRequest)
    deciding = isinstance(request, DecideProjectPriceEvidenceRelevanceRequest)
    confirming = isinstance(request, ConfirmProjectPriceEvidenceRequest)
    if registration or confirming or (deciding and request.outcome == "accepted"):
        upstream = evaluate_asset_workbench_provider(snapshot, effective_permissions={"workbench:edit"}, has_active_session=True)
        if upstream.result != "COMPLETE":
            conflict("price_evidence_upstream_required")
    receipt_id, record_id, now = uuid.uuid4(), uuid.uuid4(), utc_now()
    relationship_id, deadline = None, None
    binding = {"contract_sha256": contract_digest(), "upstream": upstream_binding(snapshot)}
    fields = {}
    if registration:
        prior = state.source_heads.get(request.source_id)
        other_scope = db.query(Source.id).filter(Source.source_id == request.source_id,
            Source.project_id != project_id).first()
        if other_scope:
            raise HTTPException(404, detail="Source identity not found")
        if request.predecessor_revision_id != (prior.id if prior else None):
            conflict("price_evidence_source_version_conflict")
        material = request.material
        if prior and not state.retired(prior) and prior.content_binding["material"] == material.model_dump(mode="json"):
            conflict("price_evidence_same_state_conflict")
        if material.captured_at > now or (material.expires_at and material.expires_at <= now):
            raise HTTPException(400, detail="Invalid source dates")
        # Retained historical result transcription binds an owned prior Project and exact asset.
        if material.historical:
            from app.modules.project_master_data.models import Project, ProjectAssetLine
            historical = material.historical
            prior_project = db.query(Project).filter_by(id=historical.project_id, organization_id=org_id).first()
            prior_line = db.query(ProjectAssetLine).filter_by(id=historical.line_id, project_id=historical.project_id).first()
            if not prior_project or not prior_line or historical.project_id == project_id:
                raise HTTPException(404, detail="Historical source not found")
        if material.explanation:
            from app.modules.project_master_data.price_evidence_schemas import SourceMaterial
            terms = []
            for item in material.explanation.inputs:
                source = state.sources.get(item.evidence_revision_id)
                if not source:
                    raise HTTPException(404, detail="Explanation source not found")
                if source.source_id == request.source_id or not source_eligible(db, snapshot, state, source, now):
                    conflict("price_evidence_explanation_source_required")
                observed = SourceMaterial.model_validate(source.content_binding["material"]).value
                if (observed.range_upper is not None or observed.currency != material.value.currency
                        or observed.unit_basis != material.value.unit_basis):
                    raise HTTPException(400, detail="Explanation units or currency mismatch")
                terms.append((observed.amount, item.coefficient))
            if scaled_sum(terms) != material.explanation.proposed_basis_value:
                raise HTTPException(400, detail="Explanation calculation mismatch")
        binding["material"] = material.model_dump(mode="json")
        model = Source
        fields = dict(source_id=request.source_id, revision=prior.revision + 1 if prior else 1,
            predecessor_id=prior.id if prior else None, category=material.category, expires_at=material.expires_at)
        deadline = material.expires_at
    elif deciding:
        source = state.sources.get(request.evidence_revision_id)
        if source is None or request.line_id not in {line.id for line in snapshot.lines}:
            raise HTTPException(404, detail="Evidence or line not found")
        if state.source_heads.get(source.source_id) is not source or (state.retired(source) and request.outcome == "accepted"):
            conflict("price_evidence_source_version_conflict")
        prior = state.decision_heads.get((request.line_id, source.source_id))
        if (request.prior_decision_id != (prior.id if prior else None)
                or request.predecessor_relationship_id != (prior.relationship_id if prior else None)
                or request.expected_line_proof_sha256 != canonical_digest(line_binding(snapshot, request.line_id))):
            conflict("price_evidence_decision_version_conflict")
        if request.review_due_at <= now or (request.outcome == "accepted" and source.expires_at and request.review_due_at > source.expires_at):
            raise HTTPException(400, detail="Invalid suitability review deadline")
        if request.outcome == "accepted" and not source_eligible(db, snapshot, state, source, now):
            conflict("price_evidence_qualifying_source_required")
        required_priorities = {"internet_survey"} if source.category == "unit_price_explanation" else (
            {"internet_survey", "unit_price_explanation"} if source.category == "prior_appraisal_result" else set())
        if set(request.higher_priorities_considered) != required_priorities:
            raise HTTPException(400, detail="Explicit source priority consideration required")
        if prior and not state.retired(prior):
            old = dict(prior.invocation_binding)
            compare = ("evidence_revision_id", "source_portion", "relevance_rationale", "suitability_rationale", "limitations",
                       "applicability_date", "temporal_applicability", "source_priority_rationale", "higher_priorities_considered",
                       "outcome", "disposition", "review_due_at", "expected_line_proof_sha256")
            if all(old[key] == invocation[key] for key in compare) and prior.content_binding["upstream"] == binding["upstream"]:
                conflict("price_evidence_same_state_conflict")
        relationship_id = uuid.uuid4()
        binding.update(relationship_id=str(relationship_id), line=line_binding(snapshot, request.line_id), source_sha256=source.content_sha256)
        model = Decision
        fields = dict(relationship_id=relationship_id, source_id=source.source_id, evidence_revision_id=source.id,
            line_id=request.line_id, predecessor_id=prior.id if prior else None,
            outcome=request.outcome, disposition=request.disposition, review_due_at=request.review_due_at)
        deadline = (min(request.review_due_at, source.expires_at)
                    if request.outcome == "accepted" and source.expires_at else request.review_due_at)
    elif confirming:
        if request.supersedes_confirmation_id != (state.latest.id if state.latest else None):
            conflict("price_evidence_confirmation_version_conflict")
        if state.content_current:
            conflict("price_evidence_same_state_conflict")
        if state.stale or state.holds or not all(state.qualifying.get(line.id) for line in snapshot.lines):
            conflict("price_evidence_coverage_required")
        binding = state.manifest
        model = Confirmation
        fields = dict(predecessor_id=state.latest.id if state.latest else None, workbench_confirmation_id=snapshot.workbench.latest.id)
        deadline = state.earliest_deadline
    else:
        model = Withdrawal
        if isinstance(request, WithdrawProjectPriceEvidenceRequest):
            _scoped_target(state, request)
            fields = dict(target_kind=request.target_kind, target_id=request.target_id)
        else:
            if not state.latest or state.withdrawn or request.expected_confirmation_id != state.latest.id:
                conflict("price_evidence_active_confirmation_required")
            fields = dict(target_kind="confirmation", target_id=state.latest.id)

    result = PriceEvidenceResult(command_id=request.command_id, receipt_id=receipt_id, project_id=project_id,
        contract_version=request.contract_version, record_id=record_id, relationship_id=relationship_id,
        project_row_version=snapshot.project.row_version + 1, created_at=now).model_dump(mode="json")
    receipt = PriceEvidenceReceipt(id=receipt_id, organization_id=org_id, project_id=project_id,
        actor_user_id=persisted.id, session_id=session.id, created_at=now, command_id=request.command_id,
        contract_version=request.contract_version, request_sha256=digest, response_metadata=result)
    try:
        with db.begin_nested():
            db.add(receipt)
            db.flush()
    except IntegrityError as exc:
        if getattr(getattr(exc.orig, "diag", None), "constraint_name", None) == "uq_pe_command":
            conflict("price_evidence_command_reuse_conflict")
        raise
    record = model(id=record_id, organization_id=org_id, project_id=project_id, actor_user_id=persisted.id,
        session_id=session.id, created_at=now, receipt_id=receipt_id, audit_id=uuid.uuid4(), seal_id=snapshot.seal.id,
        pre_row_version=snapshot.project.row_version, post_row_version=snapshot.project.row_version + 1,
        content_sha256=canonical_digest(binding), content_binding=binding, invocation_binding=invocation, **fields)
    snapshot.project.row_version += 1
    event_name, command_name = EVENTS[request.contract_version]
    log_audit_event(db, event_name=event_name, command_name=command_name, entity_type="Project", entity_id=project_id,
        organization_id=org_id, actor_user_id=persisted.id, payload=audit_binding(record, receipt), audit_event_id=record.audit_id)
    db.add(record)
    db.flush()
    after = resolve_authority(db, org_id=org_id, project_id=project_id, locked=True)
    db.info.setdefault("price_evidence_commit_checks", {})[project_id] = (persisted, org_id, after.case_version, deadline)
    return _response(after, receipt, replayed=False)


def _command(schema, db, *, actor, org_id, project_id, request):
    try:
        request = schema.model_validate(request.model_dump(mode="json") if isinstance(request, schema) else request)
    except ValidationError:
        raise HTTPException(400, detail="Invalid PRICE_EVIDENCE command contract") from None
    return _execute(db, actor=actor, org_id=org_id, project_id=project_id, request=request)


def register_project_price_evidence(db, **kwargs):
    return _command(RegisterProjectPriceEvidenceRequest, db, **kwargs)


def decide_project_price_evidence_relevance(db, **kwargs):
    return _command(DecideProjectPriceEvidenceRelevanceRequest, db, **kwargs)


def withdraw_project_price_evidence(db, **kwargs):
    return _command(WithdrawProjectPriceEvidenceRequest, db, **kwargs)


def confirm_project_price_evidence(db, **kwargs):
    return _command(ConfirmProjectPriceEvidenceRequest, db, **kwargs)


def withdraw_project_price_evidence_confirmation(db, **kwargs):
    return _command(WithdrawProjectPriceEvidenceConfirmationRequest, db, **kwargs)
