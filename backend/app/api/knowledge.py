import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.rbac import require_permission
from app.core.audit import log_audit_event
from app.modules.project_master_data.models import (
    User,
    TechnicalSpecification,
    TechnicalSpecificationVersion,
    TechnicalSpecificationVersionStatus,
    QuoteBatch,
    QuoteBatchStatus,
    QuoteLine,
    QuoteLineStatus,
    AppraisedPriceDecision,
    AppraisedPriceDecisionStatus,
    KnowledgeQueueItem,
    KnowledgeQueueItemStatus,
    KnowledgeConflict,
    KnowledgeConflictStatus,
)
from app.modules.project_master_data.knowledge_schemas import (
    TechnicalSpecificationResponse,
    TechnicalSpecificationVersionResponse,
    TechnicalSpecificationVersionUpdate,
    QuoteBatchResponse,
    QuoteBatchUpdate,
    AppraisedPriceDecisionResponse,
    AppraisedPriceDecisionUpdate,
    KnowledgeQueueItemResponse,
    KnowledgeConflictResponse,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


def sanitize_audit_payload(d: dict) -> dict:
    """Recursively convert UUIDs and non-primitive types in dict to string values for JSON serialization."""
    if not isinstance(d, dict):
        return d
    res = {}
    for k, v in d.items():
        if isinstance(v, uuid.UUID):
            res[k] = str(v)
        elif hasattr(v, "value"):  # Handle Enums
            res[k] = str(v.value)
        elif isinstance(v, dict):
            res[k] = sanitize_audit_payload(v)
        elif isinstance(v, list):
            res[k] = [
                str(x)
                if isinstance(x, uuid.UUID)
                else (sanitize_audit_payload(x) if isinstance(x, dict) else x)
                for x in v
            ]
        else:
            res[k] = v
    return res


# ==========================================
# TECHNICAL SPECIFICATIONS
# ==========================================


@router.get("/technical-specifications", response_model=List[TechnicalSpecificationResponse])
def list_technical_specifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read")),
):
    return db.query(TechnicalSpecification).all()


@router.get("/technical-specifications/{id}", response_model=TechnicalSpecificationResponse)
def get_technical_specification(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read")),
):
    spec = db.query(TechnicalSpecification).filter(TechnicalSpecification.id == id).first()
    if not spec:
        raise HTTPException(status_code=404, detail="TechnicalSpecification not found")
    return spec


@router.patch(
    "/technical-specifications/versions/{version_id}",
    response_model=TechnicalSpecificationVersionResponse,
)
def update_technical_specification_version(
    version_id: uuid.UUID,
    payload: TechnicalSpecificationVersionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:update")),
):
    ver = (
        db.query(TechnicalSpecificationVersion)
        .filter(TechnicalSpecificationVersion.id == version_id)
        .first()
    )
    if not ver:
        raise HTTPException(status_code=404, detail="TechnicalSpecificationVersion not found")

    # Immutable active/approved versions check
    if ver.status in [
        TechnicalSpecificationVersionStatus.ACTIVE,
        TechnicalSpecificationVersionStatus.SUPERSEDED,
    ]:
        raise HTTPException(status_code=422, detail="VAL_KNOW_PATCH_001")

    # Optimistic locking check
    if ver.row_version != payload.expected_row_version:
        raise HTTPException(status_code=409, detail="VAL_KNOW_CONFLICT_001")

    update_dict = payload.model_dump(exclude_unset=True, exclude={"expected_row_version"})
    for k, v in update_dict.items():
        setattr(ver, k, v)
    ver.row_version += 1
    db.commit()
    db.refresh(ver)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="TECHNICAL_SPECIFICATION_VERSION_UPDATE",
        entity_type="TechnicalSpecificationVersion",
        entity_id=ver.id,
        payload=sanitize_audit_payload(update_dict),
    )
    return ver


# ==========================================
# QUOTE BATCHES
# ==========================================


@router.get("/quote-batches", response_model=List[QuoteBatchResponse])
def list_quote_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read")),
):
    return db.query(QuoteBatch).all()


@router.get("/quote-batches/{quote_batch_id}", response_model=QuoteBatchResponse)
def get_quote_batch(
    quote_batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read")),
):
    batch = db.query(QuoteBatch).filter(QuoteBatch.id == quote_batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="QuoteBatch not found")
    return batch


@router.patch("/quote-batches/{quote_batch_id}", response_model=QuoteBatchResponse)
def update_quote_batch(
    quote_batch_id: uuid.UUID,
    payload: QuoteBatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:update")),
):
    batch = db.query(QuoteBatch).filter(QuoteBatch.id == quote_batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="QuoteBatch not found")

    # Active records are immutable check
    if batch.status in [QuoteBatchStatus.ACTIVE, QuoteBatchStatus.SUPERSEDED]:
        raise HTTPException(status_code=422, detail="VAL_KNOW_PATCH_001")

    # Optimistic locking check
    if batch.row_version != payload.expected_row_version:
        raise HTTPException(status_code=409, detail="VAL_KNOW_CONFLICT_001")

    update_dict = payload.model_dump(exclude_unset=True, exclude={"expected_row_version"})
    for k, v in update_dict.items():
        setattr(batch, k, v)
    batch.row_version += 1
    db.commit()
    db.refresh(batch)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="QUOTE_BATCH_UPDATE",
        entity_type="QuoteBatch",
        entity_id=batch.id,
        payload=sanitize_audit_payload(update_dict),
    )
    return batch


@router.post(
    "/quote-batches/{quote_batch_id}/revise", response_model=QuoteBatchResponse, status_code=201
)
def revise_quote_batch(
    quote_batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:update")),
):
    batch = db.query(QuoteBatch).filter(QuoteBatch.id == quote_batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="QuoteBatch not found")

    # Revision creates a new quote batch linked to previous_quote_batch_id
    rev_batch = QuoteBatch(
        canonical_asset_id=batch.canonical_asset_id,
        asset_variant_id=batch.asset_variant_id,
        created_by=current_user.id,
        status=QuoteBatchStatus.DRAFT,
        revision_number=batch.revision_number + 1,
        previous_quote_batch_id=batch.id,
    )
    db.add(rev_batch)
    db.commit()
    db.refresh(rev_batch)

    # Copy quote lines under draft status
    for line in batch.quote_lines:
        rev_line = QuoteLine(
            quote_batch_id=rev_batch.id,
            evidence_file_id=line.evidence_file_id,
            supplier_name=line.supplier_name,
            quoted_unit_price=line.quoted_unit_price,
            currency=line.currency,
            quantity=line.quantity,
            unit_of_measure=line.unit_of_measure,
            quote_label=line.quote_label,
            quote_date=line.quote_date,
            status=QuoteLineStatus.DRAFT,
        )
        db.add(rev_line)
    db.commit()
    db.refresh(rev_batch)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="QUOTE_BATCH_REVISE",
        entity_type="QuoteBatch",
        entity_id=rev_batch.id,
        payload={
            "previous_quote_batch_id": str(batch.id),
            "revision_number": rev_batch.revision_number,
        },
    )
    return rev_batch


# ==========================================
# APPRAISED PRICE DECISIONS
# ==========================================


@router.get("/appraised-price-decisions", response_model=List[AppraisedPriceDecisionResponse])
def list_appraised_price_decisions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read")),
):
    return db.query(AppraisedPriceDecision).all()


@router.get(
    "/appraised-price-decisions/{decision_id}", response_model=AppraisedPriceDecisionResponse
)
def get_appraised_price_decision(
    decision_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read")),
):
    dec = db.query(AppraisedPriceDecision).filter(AppraisedPriceDecision.id == decision_id).first()
    if not dec:
        raise HTTPException(status_code=404, detail="AppraisedPriceDecision not found")
    return dec


@router.patch(
    "/appraised-price-decisions/{decision_id}", response_model=AppraisedPriceDecisionResponse
)
def update_appraised_price_decision(
    decision_id: uuid.UUID,
    payload: AppraisedPriceDecisionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:update")),
):
    dec = db.query(AppraisedPriceDecision).filter(AppraisedPriceDecision.id == decision_id).first()
    if not dec:
        raise HTTPException(status_code=404, detail="AppraisedPriceDecision not found")

    # Immutable active/approved decisions check
    if dec.status in [AppraisedPriceDecisionStatus.ACTIVE, AppraisedPriceDecisionStatus.SUPERSEDED]:
        raise HTTPException(status_code=422, detail="VAL_KNOW_PATCH_001")

    # Optimistic locking check
    if dec.row_version != payload.expected_row_version:
        raise HTTPException(status_code=409, detail="VAL_KNOW_CONFLICT_001")

    update_dict = payload.model_dump(exclude_unset=True, exclude={"expected_row_version"})
    for k, v in update_dict.items():
        setattr(dec, k, v)
    dec.row_version += 1
    db.commit()
    db.refresh(dec)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="APPRAISED_PRICE_DECISION_UPDATE",
        entity_type="AppraisedPriceDecision",
        entity_id=dec.id,
        payload=sanitize_audit_payload(update_dict),
    )
    return dec


# ==========================================
# KNOWLEDGE QUEUE
# ==========================================


@router.get("/queue", response_model=List[KnowledgeQueueItemResponse])
def list_knowledge_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read")),
):
    return db.query(KnowledgeQueueItem).all()


@router.get("/queue/{queue_item_id}", response_model=KnowledgeQueueItemResponse)
def get_knowledge_queue_item(
    queue_item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read")),
):
    item = db.query(KnowledgeQueueItem).filter(KnowledgeQueueItem.id == queue_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="KnowledgeQueueItem not found")
    return item


@router.post("/queue/{queue_item_id}/claim", response_model=KnowledgeQueueItemResponse)
def claim_knowledge_queue_item(
    queue_item_id: uuid.UUID,
    expected_row_version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:update")),
):
    item = db.query(KnowledgeQueueItem).filter(KnowledgeQueueItem.id == queue_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="KnowledgeQueueItem not found")

    if item.row_version != expected_row_version:
        raise HTTPException(status_code=409, detail="VAL_KNOW_CONFLICT_001")

    item.status = KnowledgeQueueItemStatus.CLAIMED
    item.claimed_by = current_user.id
    item.claimed_at = datetime.now(timezone.utc)
    item.row_version += 1
    db.commit()
    db.refresh(item)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="KNOWLEDGE_QUEUE_CLAIM",
        entity_type="KnowledgeQueueItem",
        entity_id=item.id,
        payload={"status": "claimed"},
    )
    return item


@router.post("/queue/{queue_item_id}/release", response_model=KnowledgeQueueItemResponse)
def release_knowledge_queue_item(
    queue_item_id: uuid.UUID,
    expected_row_version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:update")),
):
    item = db.query(KnowledgeQueueItem).filter(KnowledgeQueueItem.id == queue_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="KnowledgeQueueItem not found")

    if item.row_version != expected_row_version:
        raise HTTPException(status_code=409, detail="VAL_KNOW_CONFLICT_001")

    item.status = KnowledgeQueueItemStatus.PENDING
    item.claimed_by = None
    item.claimed_at = None
    item.row_version += 1
    db.commit()
    db.refresh(item)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="KNOWLEDGE_QUEUE_RELEASE",
        entity_type="KnowledgeQueueItem",
        entity_id=item.id,
        payload={"status": "pending"},
    )
    return item


@router.post("/queue/{queue_item_id}/review", response_model=KnowledgeQueueItemResponse)
def review_knowledge_queue_item(
    queue_item_id: uuid.UUID,
    status_choice: KnowledgeQueueItemStatus,
    expected_row_version: int,
    reject_reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:approve")),
):
    item = db.query(KnowledgeQueueItem).filter(KnowledgeQueueItem.id == queue_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="KnowledgeQueueItem not found")

    if item.row_version != expected_row_version:
        raise HTTPException(status_code=409, detail="VAL_KNOW_CONFLICT_001")

    item.status = status_choice
    item.reviewer_id = current_user.id
    item.reviewed_at = datetime.now(timezone.utc)
    if status_choice == KnowledgeQueueItemStatus.REJECTED and reject_reason:
        item.auto_reject_reason = reject_reason
    item.row_version += 1
    db.commit()
    db.refresh(item)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="KNOWLEDGE_QUEUE_REVIEW",
        entity_type="KnowledgeQueueItem",
        entity_id=item.id,
        payload={"status": status_choice},
    )
    return item


# ==========================================
# KNOWLEDGE CONFLICTS
# ==========================================


@router.get("/conflicts", response_model=List[KnowledgeConflictResponse])
def list_knowledge_conflicts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read")),
):
    return db.query(KnowledgeConflict).all()


@router.get("/conflicts/{conflict_id}", response_model=KnowledgeConflictResponse)
def get_knowledge_conflict(
    conflict_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read")),
):
    conflict = db.query(KnowledgeConflict).filter(KnowledgeConflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="KnowledgeConflict not found")
    return conflict


@router.post("/conflicts/{conflict_id}/resolve", response_model=KnowledgeConflictResponse)
def resolve_knowledge_conflict(
    conflict_id: uuid.UUID,
    resolution_notes: str,
    expected_row_version: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:approve")),
):
    conflict = db.query(KnowledgeConflict).filter(KnowledgeConflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="KnowledgeConflict not found")

    if conflict.row_version != expected_row_version:
        raise HTTPException(status_code=409, detail="VAL_KNOW_CONFLICT_001")

    conflict.status = KnowledgeConflictStatus.RESOLVED
    conflict.resolution_notes = resolution_notes
    conflict.resolved_by = current_user.id
    conflict.resolved_at = datetime.now(timezone.utc)
    conflict.row_version += 1
    db.commit()
    db.refresh(conflict)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="KNOWLEDGE_CONFLICT_RESOLVE",
        entity_type="KnowledgeConflict",
        entity_id=conflict.id,
        payload={"status": "resolved"},
    )
    return conflict
