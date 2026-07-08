import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.modules.project_master_data.models import (
    TechnicalSpecificationVersionStatus, QuoteBatchStatus, QuoteLineStatus,
    AppraisedPriceDecisionStatus, KnowledgeQueueItemStatus, KnowledgeConflictSeverity, KnowledgeConflictStatus
)

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TechnicalSpecificationResponse(BaseSchema):
    id: uuid.UUID
    canonical_asset_id: Optional[uuid.UUID]
    asset_variant_id: Optional[uuid.UUID]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TechnicalSpecificationVersionUpdate(BaseSchema):
    status: Optional[TechnicalSpecificationVersionStatus] = None
    attribute_values: Optional[dict] = None
    confidence_score: Optional[float] = None
    expected_row_version: int


class TechnicalSpecificationVersionResponse(BaseSchema):
    id: uuid.UUID
    technical_specification_id: uuid.UUID
    version_number: int
    attribute_values: dict
    source_evidence_ids: List[str]
    source_project_id: Optional[uuid.UUID]
    confidence_score: Optional[float]
    status: TechnicalSpecificationVersionStatus
    created_by: uuid.UUID
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    row_version: int
    created_at: datetime
    updated_at: datetime


class QuoteBatchUpdate(BaseSchema):
    status: Optional[QuoteBatchStatus] = None
    override_blocking_conflict_reason: Optional[str] = None
    expected_row_version: int


class QuoteLineResponse(BaseSchema):
    id: uuid.UUID
    quote_batch_id: uuid.UUID
    evidence_file_id: Optional[uuid.UUID]
    supplier_name: str
    quoted_unit_price: float
    currency: str
    quantity: Optional[float]
    unit_of_measure: Optional[str]
    quote_label: Optional[str]
    quote_date: Optional[datetime]
    status: QuoteLineStatus
    created_at: datetime
    updated_at: datetime


class QuoteBatchResponse(BaseSchema):
    id: uuid.UUID
    canonical_asset_id: Optional[uuid.UUID]
    asset_variant_id: Optional[uuid.UUID]
    created_by: uuid.UUID
    status: QuoteBatchStatus
    revision_number: int
    previous_quote_batch_id: Optional[uuid.UUID]
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    override_blocking_conflict_reason: Optional[str]
    row_version: int
    created_at: datetime
    updated_at: datetime
    quote_lines: List[QuoteLineResponse] = []


class AppraisedPriceDecisionUpdate(BaseSchema):
    status: Optional[AppraisedPriceDecisionStatus] = None
    final_unit_price: Optional[float] = None
    currency: Optional[str] = None
    rationale: Optional[str] = None
    expected_row_version: int


class AppraisedPriceDecisionResponse(BaseSchema):
    id: uuid.UUID
    canonical_asset_id: Optional[uuid.UUID]
    asset_variant_id: Optional[uuid.UUID]
    quote_batch_id: Optional[uuid.UUID]
    final_unit_price: float
    currency: str
    rationale: str
    status: AppraisedPriceDecisionStatus
    created_by: uuid.UUID
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    row_version: int
    created_at: datetime
    updated_at: datetime


class KnowledgeQueueItemResponse(BaseSchema):
    id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    status: KnowledgeQueueItemStatus
    confidence_score: Optional[float]
    auto_rejected: bool
    auto_reject_reason: Optional[str]
    reviewer_id: Optional[uuid.UUID]
    reviewed_at: Optional[datetime]
    claimed_by: Optional[uuid.UUID]
    claimed_at: Optional[datetime]
    is_manual: bool
    is_pinned: bool
    row_version: int
    created_at: datetime
    updated_at: datetime


class KnowledgeConflictResponse(BaseSchema):
    id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    conflict_type: str
    severity: KnowledgeConflictSeverity
    status: KnowledgeConflictStatus
    calculated_value: float
    threshold_value: float
    resolution_notes: Optional[str]
    resolved_by: Optional[uuid.UUID]
    resolved_at: Optional[datetime]
    row_version: int
    created_at: datetime
    updated_at: datetime
