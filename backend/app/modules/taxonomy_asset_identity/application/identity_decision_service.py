"""S14-PR-003 Identity decision service and learning feedback generation."""
from __future__ import annotations

import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.excel_import.models import (
    AssetIdentityDecision,
    ContextualAssetAlias,
    LearningFeedbackEvent,
    RawAssetObservation,
)
from app.modules.taxonomy_asset_identity.domain.asset_matcher import normalize_asset_text


def confirm_identity_decision(
    db: Session,
    *,
    actor_id: uuid.UUID,
    org_id: uuid.UUID,
    customer_id: uuid.UUID | None = None,
    project_id: uuid.UUID,
    raw_observation_id: uuid.UUID,
    decision_type: str,  # "accepted", "corrected", "rejected", "deferred"
    chosen_canonical_asset_id: uuid.UUID | None = None,
    chosen_asset_variant_id: uuid.UUID | None = None,
    chosen_alias_id: uuid.UUID | None = None,
    create_contextual_alias: bool = False,
    rejection_reason: str | None = None,
    command_id: uuid.UUID,
) -> tuple[AssetIdentityDecision, LearningFeedbackEvent | None]:
    """Execute human identity decision (ADR 0031 §5 & §6).
    
    Invariants:
    1. Only committed human decisions generate LearningFeedbackEvents.
    2. Optional creation of ContextualAssetAlias when confirmed/corrected.
    3. Append-only decision record with command idempotency.
    """
    if decision_type not in {"accepted", "corrected", "rejected", "deferred"}:
        raise HTTPException(status_code=400, detail="Loại quyết định định danh không hợp lệ.")

    # Idempotency check
    existing = (
        db.query(AssetIdentityDecision)
        .filter(
            AssetIdentityDecision.organization_id == org_id,
            AssetIdentityDecision.command_id == command_id,
        )
        .first()
    )
    if existing:
        return existing, None

    obs = (
        db.query(RawAssetObservation)
        .filter(
            RawAssetObservation.organization_id == org_id,
            RawAssetObservation.id == raw_observation_id,
        )
        .first()
    )
    if not obs:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi quan sát tài sản gốc.")

    decision = AssetIdentityDecision(
        id=uuid.uuid4(),
        organization_id=org_id,
        customer_id=customer_id or obs.customer_id,
        project_id=project_id,
        raw_observation_id=raw_observation_id,
        decision_type=decision_type,
        chosen_canonical_asset_id=chosen_canonical_asset_id,
        chosen_asset_variant_id=chosen_asset_variant_id,
        chosen_alias_id=chosen_alias_id,
        rejection_reason=rejection_reason,
        actor_user_id=actor_id,
        command_id=command_id,
    )
    db.add(decision)

    feedback_event: LearningFeedbackEvent | None = None

    # ADR 0031 §6: Positive learning evidence is created only by a committed human decision
    if decision_type in {"accepted", "corrected"} and (chosen_canonical_asset_id or chosen_asset_variant_id):
        target_type = "CanonicalAsset" if chosen_canonical_asset_id else "AssetVariant"
        target_id = chosen_canonical_asset_id or chosen_asset_variant_id

        if create_contextual_alias and obs.raw_asset_name:
            ctx_alias = ContextualAssetAlias(
                id=uuid.uuid4(),
                organization_id=org_id,
                customer_id=customer_id or obs.customer_id,
                alias_name=obs.raw_asset_name,
                normalized_alias_name=normalize_asset_text(obs.raw_asset_name),
                canonical_asset_id=chosen_canonical_asset_id,
                asset_variant_id=chosen_asset_variant_id,
                status="active",
                source_decision_id=decision.id,
                created_by_user_id=actor_id,
            )
            db.add(ctx_alias)

        feedback_event = LearningFeedbackEvent(
            id=uuid.uuid4(),
            organization_id=org_id,
            customer_id=customer_id or obs.customer_id,
            source_decision_id=decision.id,
            event_type="positive_match",
            raw_wording=obs.raw_asset_name,
            target_type=target_type,
            target_id=target_id,
            feedback_metadata={
                "decision_type": decision_type,
                "created_contextual_alias": create_contextual_alias,
            },
        )
        db.add(feedback_event)

    elif decision_type == "rejected" and (chosen_canonical_asset_id or chosen_asset_variant_id):
        target_type = "CanonicalAsset" if chosen_canonical_asset_id else "AssetVariant"
        target_id = chosen_canonical_asset_id or chosen_asset_variant_id

        feedback_event = LearningFeedbackEvent(
            id=uuid.uuid4(),
            organization_id=org_id,
            customer_id=customer_id or obs.customer_id,
            source_decision_id=decision.id,
            event_type="negative_match",
            raw_wording=obs.raw_asset_name,
            target_type=target_type,
            target_id=target_id,
            feedback_metadata={"rejection_reason": rejection_reason},
        )
        db.add(feedback_event)

    db.commit()
    db.refresh(decision)
    if feedback_event:
        db.refresh(feedback_event)

    return decision, feedback_event
