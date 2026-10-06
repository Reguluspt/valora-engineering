"""A11 bounded presentation of A10 facts; no persistence or completion authority."""
from app.db.mixins import utc_now
from app.modules.project_master_data.application.price_evidence_authority import source_eligible
from app.modules.project_master_data.price_evidence_schemas import SourceMaterial


def source_projection(db, snapshot, source, *, line_id, writable, can_register, can_decide, now):
    state = snapshot.price_evidence
    material = SourceMaterial.model_validate(source.content_binding["material"])
    head = state.source_heads.get(source.source_id) is source
    retired = state.retired(source)
    eligible = state.intact and source_eligible(db, snapshot, state, source, now)
    decision = state.decision_heads.get((line_id, source.source_id)) if line_id else None
    qualifying = bool(decision and decision in state.qualifying.get(line_id, []))
    decision_retired = bool(decision and state.retired(decision))
    return dict(
        source_id=source.source_id, evidence_revision_id=source.id, revision=source.revision,
        predecessor_revision_id=source.predecessor_id, category=source.category,
        origin=material.origin, effective_date=material.effective_date,
        date_unknown=material.effective_date is None, captured_at=material.captured_at,
        expires_at=source.expires_at, expired=bool(source.expires_at and now >= source.expires_at),
        current=head, withdrawn=retired, eligible=eligible,
        can_correct=bool(can_register and head), can_withdraw=bool(writable and head and not retired),
        can_accept=bool(line_id and can_decide and eligible),
        can_reject=bool(line_id and writable and head),
        explanation_input_eligible=bool(eligible and material.value and material.value.range_upper is None),
        decision=None if not decision else dict(
            decision_id=decision.id, relationship_id=decision.relationship_id,
            evidence_revision_id=decision.evidence_revision_id, line_id=decision.line_id,
            outcome=decision.outcome, disposition=decision.disposition, qualifying=qualifying,
            withdrawn=decision_retired, review_due_at=decision.review_due_at,
            review_expired=now >= decision.review_due_at,
            unresolved_concern=decision.disposition == "unresolved_concern",
            can_withdraw=bool(writable and not decision_retired),
        ),
    )


def workspace_projection(db, snapshot, preparation, *, line_id=None, offset=0, limit=50):
    state = snapshot.price_evidence
    now = utc_now()
    # The resolver owns qualifying coverage and holds. Do not recompute them here.
    covered = sum(bool(state.qualifying.get(line.id)) for line in snapshot.lines)
    sources = sorted(state.source_heads.values(), key=lambda s: (s.created_at, str(s.id))) if state.intact else []
    return dict(
        project_id=snapshot.project.id, case_version=snapshot.case_version,
        line_id=line_id, covered_count=covered if state.intact else None,
        sealed_count=len(snapshot.lines), confirmation_id=state.latest.id if state.latest else None,
        confirmation_withdrawn=state.withdrawn, confirmation_current=state.content_current,
        can_withdraw_confirmation=bool(preparation["can_withdraw"] and state.latest and not state.withdrawn),
        line_covered=bool(state.qualifying.get(line_id)) if state.intact and line_id else None,
        line_hold=bool(line_id in state.holds), reason_codes=sorted(set(state.stale)),
        sources=[source_projection(db, snapshot, source, line_id=line_id,
            writable=preparation["can_withdraw"], can_register=preparation["can_register"],
            can_decide=preparation["can_decide"], now=now) for source in sources[offset:offset + limit]],
        offset=offset, total=len(sources), next_offset=offset + limit if offset + limit < len(sources) else None,
    )
