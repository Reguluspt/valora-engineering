"""Current proof facts shared by Case State, command CAS and receipt recovery."""
from __future__ import annotations

from app.modules.project_master_data.application.asset_review_authority import canonical_digest
from app.modules.project_master_data.application.asset_line_validation_rules import (
    REFERENCE_FIELDS, RULE_CONTRACT, input_digest, line_reference_facts, rule_digest, value,
)
from app.modules.project_master_data.models import (
    Unit, Currency, Brand, Manufacturer, AuditEvent, AssetReviewCommandReceipt,
    AssetLineValidationGeneration, AssetLineHumanDecision, AssetLineDecisionReversal,
)

REFERENCE_MODELS = {"Unit": Unit, "Currency": Currency, "Brand": Brand, "Manufacturer": Manufacturer}


def load_references(db, lines, *, locked):
    references = {}
    # Global rows: fixed type order, then UUID, after every official line lock.
    for kind, fields in REFERENCE_FIELDS.items():
        ids = sorted({getattr(line, f) for line in lines for f in fields
                      if getattr(line, f) is not None}, key=str)
        model = REFERENCE_MODELS[kind]
        if ids:
            query = db.query(model).filter(model.id.in_(ids)).order_by(model.id).populate_existing()
            if locked:
                query = query.with_for_update(read=True)
            for reference in query.all():
                references[kind, reference.id] = reference
    return references


def receipt_integrity(receipt, proof, audits):
    expected_event = ("ProjectAssetLineValidated" if isinstance(proof, AssetLineValidationGeneration)
                      else "ProjectAssetLineReviewDecided")
    expected_contract = ("asset-line-validation-v1" if isinstance(proof, AssetLineValidationGeneration)
                         else "asset-line-human-review-v1")
    command = ("ValidateProjectAssetLine" if isinstance(proof, AssetLineValidationGeneration)
               else "DecideProjectAssetLineReview")
    bindings = {"command_id": str(receipt.command_id), "proof_id": str(proof.id),
        "receipt_id": str(receipt.id), "project_id": str(proof.project_id),
        "session_id": str(proof.session_id), "seal_id": str(proof.seal_id),
        "membership_version": proof.membership_version, "confirmed": True,
        "pre_row_version": proof.pre_row_version, "post_row_version": proof.post_row_version,
        "official_input_sha256": proof.official_input_sha256, "reference_sha256": proof.reference_sha256,
        "rule_sha256": proof.rule_sha256, "contract_version": expected_contract}
    matching = [a for a in audits if a.event_name == expected_event
                and a.entity_id == receipt.line_id and a.actor_user_id == receipt.actor_user_id
                and a.organization_id == receipt.organization_id
                and a.entity_type == "ProjectAssetLine" and a.command_name == command
                and a.payload and all(a.payload.get(f) == v for f, v in bindings.items())]
    result = receipt.response_metadata
    metadata_matches = all(result.get(f) == str(getattr(receipt, f)) for f in
                           ("command_id", "project_id", "line_id"))
    if isinstance(proof, AssetLineValidationGeneration):
        metadata_matches = (metadata_matches and result.get("validation_outcome") == proof.outcome
            and result.get("validation_generation") == proof.generation and result.get("findings") == proof.findings)
    else:
        metadata_matches = (metadata_matches and result.get("target_review_status") == proof.target_review_status
                            and result.get("decision_version") == proof.decision_version)
    return bool(receipt.contract_version == expected_contract and proof.confirmed
                and metadata_matches and result.get("receipt_id") == str(receipt.id)
                and result.get("contract_version") == expected_contract
                and all(getattr(receipt, f) == getattr(proof, f) for f in
                        ("organization_id", "project_id", "line_id", "actor_user_id", "session_id"))
                and result.get("proof_id") == str(proof.id)
                and result.get("line_row_version") == proof.post_row_version
                and len(matching) == 1)


def resolve_line_proofs(db, *, org_id, project_id, lines, references, seal, seal_current):
    def scoped(model):
        return db.query(model).filter_by(organization_id=org_id, project_id=project_id).populate_existing()

    generations = scoped(AssetLineValidationGeneration).order_by(AssetLineValidationGeneration.generation).all()
    decisions = scoped(AssetLineHumanDecision).order_by(AssetLineHumanDecision.decision_version).all()
    reversals = scoped(AssetLineDecisionReversal).all()
    receipts = {r.id: r for r in scoped(AssetReviewCommandReceipt).all()}
    audits = db.query(AuditEvent).filter(AuditEvent.organization_id == org_id,
        AuditEvent.entity_id.in_([line.id for line in lines]),
        AuditEvent.event_name.in_(("ProjectAssetLineValidated", "ProjectAssetLineReviewDecided"))).all()
    result, facts = {}, []
    for line in lines:
        gens = [g for g in generations if g.line_id == line.id]
        human = [d for d in decisions if d.line_id == line.id]
        gen = gens[-1] if gens else None
        decision = human[-1] if human else None
        reversal = next((r for r in reversals if decision and r.successor_decision_id == decision.id), None)
        digests = {"official_input_sha256": input_digest(line),
                   "reference_sha256": canonical_digest(line_reference_facts(line, references)),
                   "rule_sha256": rule_digest()}

        def evidence_current(proof):
            receipt = receipts.get(proof.receipt_id) if proof else None
            return bool(proof and receipt and receipt_integrity(receipt, proof, audits)
                        and seal_current and proof.seal_id == seal.id
                        and proof.membership_version == seal.membership_version
                        and all(getattr(proof, f) == digest for f, digest in digests.items()))

        validation_current = bool(evidence_current(gen) and gen.rule_contract == RULE_CONTRACT
                                  and value(line.validation_status) == gen.outcome)
        reversal_current = bool(decision and (
            len(human) == 1 and reversal is None or len(human) > 1 and reversal
            and reversal.prior_decision_id == human[-2].id
            and reversal.organization_id == org_id and reversal.project_id == project_id
            and reversal.line_id == line.id and reversal.actor_user_id == decision.actor_user_id
            and reversal.session_id == decision.session_id and bool(decision.reason_note)))
        positive_current = bool(decision and reversal_current and evidence_current(decision)
            and decision.target_review_status == "accepted" and value(line.review_status) == "accepted"
            and validation_current and gen.outcome == "valid" and decision.validation_generation_id == gen.id)
        # Human negative holds outlive input/rule/reference changes and revalidation.
        negative = (decision.target_review_status if decision
                    and decision.target_review_status in ("flagged", "rejected") else None)
        # Historical negative strings fail closed, but never manufacture positive proof.
        if value(line.review_status) in ("flagged", "rejected"):
            negative = value(line.review_status)
        result[line.id] = {**digests, "generation": gen, "decision": decision,
            "reversal": reversal, "validation_current": validation_current,
            "positive_current": positive_current, "negative_hold": negative,
            "reversal_current": reversal_current}

        def proof_fact(proof):
            if not proof:
                return None
            return {"id": str(proof.id), "receipt_id": str(proof.receipt_id),
                    "seal_id": str(proof.seal_id), "membership_version": proof.membership_version,
                    "pre_row_version": proof.pre_row_version, "post_row_version": proof.post_row_version,
                    **{f: getattr(proof, f) for f in digests}}

        facts.append({"line_id": str(line.id), **digests,
            "generation": {**proof_fact(gen), "generation": gen.generation, "outcome": gen.outcome,
                "rule_contract": gen.rule_contract, "findings_sha256": canonical_digest(gen.findings)} if gen else None,
            "validation_current": validation_current,
            "decision": {**proof_fact(decision), "version": decision.decision_version,
                "target": decision.target_review_status,
                "generation_id": str(decision.validation_generation_id) if decision.validation_generation_id else None} if decision else None,
            "positive_current": positive_current, "negative_hold": negative,
            "reversal": {"id": str(reversal.id), "prior": str(reversal.prior_decision_id),
                "successor": str(reversal.successor_decision_id)} if reversal else None,
            "reversal_current": reversal_current})
    return result, facts
