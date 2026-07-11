import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.modules.project_master_data.models import (
    EvidenceSourceType,
    EvidenceFileStatus,
    EvidenceSensitivityLevel,
    EvidenceAccessType,
)


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EvidenceSourceCreate(BaseSchema):
    name: str = Field(..., max_length=255)
    source_type: EvidenceSourceType
    description: Optional[str] = None


class EvidenceSourceUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=255)
    source_type: Optional[EvidenceSourceType] = None
    description: Optional[str] = None


class EvidenceSourceResponse(BaseSchema):
    id: uuid.UUID
    name: str
    source_type: EvidenceSourceType
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class EvidenceFileUpdate(BaseSchema):
    status: Optional[EvidenceFileStatus] = None
    sensitivity_level: Optional[EvidenceSensitivityLevel] = None
    description: Optional[str] = None
    expected_row_version: int = Field(..., description="For optimistic locking validation")


class EvidenceFileResponse(BaseSchema):
    id: uuid.UUID
    filename: str
    mime_type: str
    file_size: int
    object_key: str
    checksum: str
    sensitivity_level: EvidenceSensitivityLevel
    status: EvidenceFileStatus
    row_version: int
    uploaded_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class EvidenceLinkCreate(BaseSchema):
    evidence_file_id: uuid.UUID
    target_type: str = Field(..., max_length=100)
    target_id: uuid.UUID


class EvidenceLinkResponse(BaseSchema):
    id: uuid.UUID
    evidence_file_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    is_deleted: bool
    deleted_by: Optional[uuid.UUID]
    deleted_at: Optional[datetime]
    delete_reason: Optional[str]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class EvidenceAccessLogResponse(BaseSchema):
    id: uuid.UUID
    evidence_file_id: uuid.UUID
    accessed_by: uuid.UUID
    access_type: EvidenceAccessType
    access_reason: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    accessed_at: datetime
