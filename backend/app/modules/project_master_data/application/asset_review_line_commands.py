"""ADR 0049 commands; the caller owns commit/rollback of all effects and audit."""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError

from app.core.audit import log_audit_event
from app.db.mixins import utc_now
from app.modules.project_master_data.asset_review_line_schemas import (
    ValidateProjectAssetLineRequest, DecideProjectAssetLineReviewRequest, LineCommandResult,
)
from app.modules.project_master_data.application.asset_review_authority import (
    canonical_digest, lock_project, require_mutation_actor, resolve_authority,
)
from app.modules.project_master_data.application.asset_line_proofs import receipt_integrity
from app.modules.project_master_data.application.asset_line_validation_rules import RULE_CONTRACT, evaluate_rules, value
from app.modules.project_master_data.models import (
    User, UserRole, Role, OrganizationProfile, WorkbenchSession, AuditEvent,
    AssetReviewCommandReceipt, AssetLineValidationGeneration, AssetLineHumanDecision,
    AssetLineDecisionReversal,
)


def conflict(code):
    raise HTTPException(409, detail={"error_code": code})


def require_line_access(db, *, actor, org_id, project_id, locked=False):
    if not isinstance(actor, User) or actor.organization_id != org_id:
        raise HTTPException(403, detail="Active human account required")
    if locked:
        db.query(User).filter_by(id=actor.id, organization_id=org_id).with_for_update(read=True).all()
        db.query(OrganizationProfile).filter_by(id=org_id).with_for_update(read=True).all()
        grants = db.query(UserRole).filter_by(user_id=actor.id).order_by(UserRole.id).with_for_update(read=True).all()
        ids = sorted({g.role_id for g in grants}, key=str)
        if ids:
            db.query(Role).filter(Role.id.in_(ids)).order_by(Role.id).with_for_update(read=True).all()
    persisted = require_mutation_actor(db, actor=actor, org_id=org_id)
    query = db.query(WorkbenchSession).filter_by(project_id=project_id, user_id=persisted.id,
                                               status="active").populate_existing()
    if locked:
        query = query.with_for_update(read=True)
    session = query.first()
    if not session:
        raise HTTPException(404, detail="Active owned Workbench session not found")
    return persisted, session


def _line(snapshot, line_id):
    line = next((line for line in snapshot.lines if line.id == line_id), None)
    if line is None:
        raise HTTPException(404, detail="Asset line not found")
    return line


def _receipt_response(db, snapshot, receipt, *, replayed):
    proof_type = (AssetLineValidationGeneration if receipt.contract_version == "asset-line-validation-v1"
                  else AssetLineHumanDecision)
    proof = db.query(proof_type).filter_by(receipt_id=receipt.id,
        organization_id=receipt.organization_id, project_id=receipt.project_id, line_id=receipt.line_id).first()
    audits = db.query(AuditEvent).filter_by(organization_id=receipt.organization_id,
                                          entity_id=receipt.line_id).all()
    if not proof or not receipt_integrity(receipt, proof, audits):
        conflict("asset_review_receipt_integrity_conflict")
    reversal_id = receipt.response_metadata.get("reversal_id")
    if reversal_id:
        reversal = db.query(AssetLineDecisionReversal).filter_by(id=uuid.UUID(reversal_id),
            organization_id=receipt.organization_id, project_id=receipt.project_id,
            line_id=receipt.line_id, actor_user_id=receipt.actor_user_id, session_id=receipt.session_id,
            successor_decision_id=proof.id).first()
        if not reversal:
            conflict("asset_review_receipt_integrity_conflict")
    line = _line(snapshot, receipt.line_id)
    state = snapshot.line_proofs[line.id]
    latest = state["generation" if proof_type is AssetLineValidationGeneration else "decision"]
    current = state["validation_current" if proof_type is AssetLineValidationGeneration
                    else "positive_current"]
    if proof_type is AssetLineHumanDecision and proof.target_review_status in ("flagged", "rejected"):
        current = bool(latest and latest.id == proof.id and state["negative_hold"] == proof.target_review_status)
    # A receipt proves historical execution, never completion of the current set.
    historical = not (snapshot.seal_current and latest and latest.id == proof.id
                      and current and line.row_version == proof.post_row_version)
    return {"result": LineCommandResult.model_validate(receipt.response_metadata).model_dump(mode="json"),
            "replayed": replayed, "historical": historical, "current_case_version": snapshot.case_version}


def read_asset_review_receipt(db, *, actor, org_id, project_id, line_id, command_id):
    snapshot = resolve_authority(db, org_id=org_id, project_id=project_id)
    _line(snapshot, line_id)
    require_line_access(db, actor=actor, org_id=org_id, project_id=project_id)
    receipt = db.query(AssetReviewCommandReceipt).filter_by(organization_id=org_id,
        project_id=project_id, line_id=line_id, actor_user_id=actor.id, command_id=command_id).first()
    if not receipt:
        raise HTTPException(404, detail="Command receipt not found")
    return _receipt_response(db, snapshot, receipt, replayed=False)


def _execute(db, *, actor, org_id, project_id, line_id, request):
    lock_project(db, org_id=org_id, project_id=project_id)
    require_line_access(db, actor=actor, org_id=org_id, project_id=project_id)
    snapshot = resolve_authority(db, org_id=org_id, project_id=project_id, locked=True)
    line = _line(snapshot, line_id)
    persisted, session = require_line_access(db, actor=actor, org_id=org_id, project_id=project_id, locked=True)
    request_digest = canonical_digest(request.model_dump(mode="json"))
    receipt = db.query(AssetReviewCommandReceipt).filter_by(organization_id=org_id,
                                                          command_id=request.command_id).first()
    if receipt:
        if (receipt.project_id != project_id or receipt.line_id != line_id
                or receipt.actor_user_id != persisted.id or receipt.request_sha256 != request_digest):
            conflict("asset_review_command_reuse_conflict")
        return _receipt_response(db, snapshot, receipt, replayed=True)
    if value(snapshot.project.status) != "draft":
        raise HTTPException(400, detail="Project must be DRAFT")
    if request.expected_case_version != snapshot.case_version or request.expected_row_version != line.row_version:
        conflict("asset_review_version_conflict")
    if (not snapshot.seal_current or not snapshot.lineage_current
            or value(snapshot.batch.status) != "applied"
            or str(line.id) not in {item["line_id"] for item in snapshot.seal.correspondence}):
        conflict("asset_review_authority_conflict")

    state = snapshot.line_proofs[line.id]
    gen, prior = state["generation"], state["decision"]
    old_review, old_validation = value(line.review_status), value(line.validation_status)
    validation = isinstance(request, ValidateProjectAssetLineRequest)
    if not validation:
        if request.target_review_status in ("flagged", "rejected") and not request.reason_note:
            raise HTTPException(400, detail="Negative decision requires reason")
        if prior:
            if request.supersedes_decision_id != prior.id:
                conflict("asset_review_prior_decision_conflict")
            if not request.reason_note:
                raise HTTPException(400, detail="Superseding decision requires reason")
        elif request.supersedes_decision_id is not None:
            conflict("asset_review_prior_decision_conflict")
        effective = (state["negative_hold"] or ("accepted" if state["positive_current"] else "pending"))
        if effective == request.target_review_status:
            conflict("asset_review_same_target_conflict")
        if request.target_review_status == "accepted":
            if not state["validation_current"] or gen.outcome != "valid":
                conflict("asset_review_valid_proof_required")
            if any(value(i.status) == "open" and value(i.severity) == "blocking"
                   and i.target_id in (project_id, line_id) for i in snapshot.issues):
                conflict("asset_review_scoped_blocker")

    proof_id, receipt_id, reversal_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4() if not validation and prior else None
    now = utc_now()
    metadata = dict(command_id=request.command_id, receipt_id=receipt_id,
        project_id=project_id, line_id=line_id, proof_id=proof_id,
        contract_version=request.contract_version, line_row_version=line.row_version + 1, created_at=now)
    if validation:
        outcome, findings = evaluate_rules(line, snapshot.references)
        metadata.update(validation_outcome=outcome, validation_generation=gen.generation + 1 if gen else 1,
                        findings=findings)
    else:
        metadata.update(target_review_status=request.target_review_status,
                        decision_version=prior.decision_version + 1 if prior else 1, reversal_id=reversal_id)
    result = LineCommandResult(**metadata).model_dump(mode="json")
    receipt = AssetReviewCommandReceipt(id=receipt_id, organization_id=org_id,
        project_id=project_id, line_id=line_id, actor_user_id=persisted.id, session_id=session.id,
        created_at=now, command_id=request.command_id, contract_version=request.contract_version,
        request_sha256=request_digest, response_metadata=result)
    # The tenant-wide UUID may race on a different Project. Reserve it before any
    # line/proof/audit write; only the unique-command violation becomes a 409.
    try:
        with db.begin_nested():
            db.add(receipt)
            db.flush()
    except IntegrityError as exc:
        if getattr(getattr(exc.orig, "diag", None), "constraint_name", None) == "uq_ar_receipt_command":
            conflict("asset_review_command_reuse_conflict")
        raise
    proof_args = dict(id=proof_id, organization_id=org_id, project_id=project_id,
        line_id=line_id, actor_user_id=persisted.id, session_id=session.id,
        receipt_id=receipt_id, seal_id=snapshot.seal.id, membership_version=snapshot.seal.membership_version,
        **{f: state[f] for f in ("official_input_sha256", "reference_sha256", "rule_sha256")},
        pre_row_version=line.row_version, post_row_version=line.row_version + 1, confirmed=True, created_at=now)
    if validation:
        proof = AssetLineValidationGeneration(**proof_args, generation=result["validation_generation"],
            rule_contract=RULE_CONTRACT, outcome=outcome, findings=findings)
        line.validation_status = outcome
        if value(line.review_status) == "accepted":
            line.review_status = "pending"
        event, command = "ProjectAssetLineValidated", "ValidateProjectAssetLine"
    else:
        proof = AssetLineHumanDecision(**proof_args, decision_version=result["decision_version"],
            target_review_status=request.target_review_status, reason_note=request.reason_note,
            validation_generation_id=gen.id if gen else None)
        line.review_status = request.target_review_status
        event, command = "ProjectAssetLineReviewDecided", "DecideProjectAssetLineReview"
    db.add(proof)
    line.row_version += 1
    db.flush()
    if reversal_id:
        db.add(AssetLineDecisionReversal(id=reversal_id, organization_id=org_id, project_id=project_id,
            line_id=line_id, actor_user_id=persisted.id, session_id=session.id, created_at=now,
            prior_decision_id=prior.id, successor_decision_id=proof_id))
    log_audit_event(db, event_name=event, command_name=command, entity_type="ProjectAssetLine",
        entity_id=line_id, organization_id=org_id, actor_user_id=persisted.id,
        payload={"command_id": str(request.command_id), "receipt_id": str(receipt_id),
            "proof_id": str(proof_id), "project_id": str(project_id), "session_id": str(session.id),
            "pre_row_version": proof.pre_row_version, "post_row_version": proof.post_row_version,
            "seal_id": str(snapshot.seal.id), "membership_version": snapshot.seal.membership_version,
            "official_input_sha256": proof.official_input_sha256, "reference_sha256": proof.reference_sha256,
            "rule_sha256": proof.rule_sha256, "contract_version": request.contract_version,
            "validation_outcome": result["validation_outcome"], "target_review_status": result["target_review_status"],
            "confirmed": True, "old_review_status": old_review, "new_review_status": value(line.review_status),
            "old_validation_status": old_validation, "new_validation_status": value(line.validation_status),
            "validation_generation": result["validation_generation"], "decision_version": result["decision_version"],
            "finding_codes": [f["code"] for f in result["findings"]],
            "reason_present": bool(getattr(request, "reason_note", None)),
            "prior_decision_id": str(prior.id) if not validation and prior else None,
            "reversal_id": str(reversal_id) if reversal_id else None})
    require_line_access(db, actor=actor, org_id=org_id, project_id=project_id, locked=True)
    after = resolve_authority(db, org_id=org_id, project_id=project_id, locked=True)
    return _receipt_response(db, after, receipt, replayed=False)


def validate_project_asset_line(db, *, actor, org_id, project_id, line_id, request):
    request = _validated_request(ValidateProjectAssetLineRequest, request)
    return _execute(db, actor=actor, org_id=org_id, project_id=project_id, line_id=line_id, request=request)


def decide_project_asset_line_review(db, *, actor, org_id, project_id, line_id, request):
    request = _validated_request(DecideProjectAssetLineReviewRequest, request)
    return _execute(db, actor=actor, org_id=org_id, project_id=project_id, line_id=line_id, request=request)


def _validated_request(schema, request):
    try:
        return schema.model_validate(request)
    except ValidationError:
        raise HTTPException(400, detail="Invalid Asset Review command contract") from None
