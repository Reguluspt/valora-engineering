import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.modules.project_master_data.models import (
    IdentityCandidateStatus, IdentityReviewStatus, IdentityDecisionType
)

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# SimilarityScore Schemas
class SimilarityScoreResponse(BaseSchema):
    id: uuid.UUID
    identity_candidate_id: uuid.UUID
    component: str
    score: float
    metadata_info: Optional[Dict[str, Any]] = None


# IdentityCandidate Schemas
class IdentityCandidateUpdate(BaseSchema):
    status: Optional[IdentityCandidateStatus] = None
    row_version: Optional[int] = None


class IdentityCandidateResponse(BaseSchema):
    id: uuid.UUID
    project_asset_line_id: uuid.UUID
    proposed_canonical_asset_id: Optional[uuid.UUID]
    proposed_asset_variant_id: Optional[uuid.UUID]
    proposed_taxonomy_node_id: Optional[uuid.UUID]
    confidence_score: float
    match_method: str
    status: IdentityCandidateStatus
    created_at: datetime
    updated_at: datetime
    similarity_scores: List[SimilarityScoreResponse] = []


# IdentityReviewItem Schemas
class IdentityReviewItemUpdate(BaseSchema):
    assigned_to: Optional[uuid.UUID] = None
    reviewer_note: Optional[str] = Field(None, max_length=500)
    review_status: Optional[IdentityReviewStatus] = None
    row_version: Optional[int] = None


class IdentityReviewItemResolve(BaseSchema):
    review_status: IdentityReviewStatus = IdentityReviewStatus.REVIEWED
    reviewer_note: Optional[str] = Field(None, max_length=500)
    decision_type: IdentityDecisionType = IdentityDecisionType.APPROVE_CANDIDATE
    details: Optional[Dict[str, Any]] = None
    row_version: Optional[int] = None


class IdentityReviewItemResponse(BaseSchema):
    id: uuid.UUID
    project_asset_line_id: uuid.UUID
    identity_candidate_id: Optional[uuid.UUID]
    assigned_to: Optional[uuid.UUID]
    review_status: IdentityReviewStatus
    reviewer_note: Optional[str]
    reviewed_by: Optional[uuid.UUID]
    reviewed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    row_version: int


# IdentityDecisionLog Schemas
class IdentityDecisionLogResponse(BaseSchema):
    id: uuid.UUID
    project_asset_line_id: uuid.UUID
    decision_type: IdentityDecisionType
    actor_user_id: Optional[uuid.UUID]
    executed_at: datetime
    details: Optional[Dict[str, Any]] = None
