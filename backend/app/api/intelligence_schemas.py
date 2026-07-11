import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.modules.project_master_data.models import (
    ParsedDocumentStatus,
    ExtractedFieldStatus,
    DocumentDiffType,
    DocumentDiffStatus,
    DocumentCorrectionDecision,
    DocumentCorrectionStatus,
)

# ----------------- ParsedDocument -----------------


class ParsedDocumentCreate(BaseModel):
    evidence_file_id: uuid.UUID
    document_type: Optional[str] = Field(None, max_length=50)
    page_count: Optional[int] = None
    text_content_hash: Optional[str] = Field(None, max_length=64)
    parse_status: ParsedDocumentStatus = ParsedDocumentStatus.CANDIDATE
    confidence_score: Optional[float] = None


class ParsedDocumentUpdate(BaseModel):
    document_type: Optional[str] = Field(None, max_length=50)
    page_count: Optional[int] = None
    text_content_hash: Optional[str] = Field(None, max_length=64)
    parse_status: Optional[ParsedDocumentStatus] = None
    confidence_score: Optional[float] = None
    expected_row_version: Optional[int] = None


class ParsedDocumentSchema(BaseModel):
    id: uuid.UUID
    evidence_file_id: uuid.UUID
    document_type: Optional[str]
    page_count: Optional[int]
    text_content_hash: Optional[str]
    parse_status: ParsedDocumentStatus
    confidence_score: Optional[float]
    created_at: datetime
    updated_at: datetime
    row_version: int

    class Config:
        from_attributes = True


# ----------------- ExtractedField -----------------


class ExtractedFieldCreate(BaseModel):
    field_key: str = Field(..., max_length=255)
    field_label: Optional[str] = Field(None, max_length=255)
    extracted_value: Dict[str, Any]
    normalized_value: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    source_page_number: Optional[int] = None
    status: ExtractedFieldStatus = ExtractedFieldStatus.CANDIDATE


class ExtractedFieldUpdate(BaseModel):
    field_label: Optional[str] = Field(None, max_length=255)
    extracted_value: Optional[Dict[str, Any]] = None
    normalized_value: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    status: Optional[ExtractedFieldStatus] = None
    expected_row_version: Optional[int] = None


class ExtractedFieldSchema(BaseModel):
    id: uuid.UUID
    parsed_document_id: uuid.UUID
    field_key: str
    field_label: Optional[str]
    extracted_value: Dict[str, Any]
    normalized_value: Optional[Dict[str, Any]]
    confidence_score: Optional[float]
    source_page_number: Optional[int]
    status: ExtractedFieldStatus
    created_at: datetime
    updated_at: datetime
    row_version: int

    class Config:
        from_attributes = True


# ----------------- DocumentDiff -----------------


class DocumentDiffCreate(BaseModel):
    source_document_id: uuid.UUID
    target_document_id: uuid.UUID
    diff_type: DocumentDiffType
    status: DocumentDiffStatus = DocumentDiffStatus.CANDIDATE
    diff_payload: Optional[Dict[str, Any]] = None


class DocumentDiffSchema(BaseModel):
    id: uuid.UUID
    source_document_id: uuid.UUID
    target_document_id: uuid.UUID
    diff_type: DocumentDiffType
    status: DocumentDiffStatus
    diff_payload: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    row_version: int

    class Config:
        from_attributes = True


# ----------------- DocumentCorrection -----------------


class DocumentCorrectionCreate(BaseModel):
    target_type: str = Field(..., max_length=50)
    target_id: uuid.UUID
    affects_approved_data: bool = False
    correction_payload: Dict[str, Any]
    decision: DocumentCorrectionDecision = DocumentCorrectionDecision.REQUEST_CHANGE
    decided_by: uuid.UUID
    status: DocumentCorrectionStatus = DocumentCorrectionStatus.DRAFT


class DocumentCorrectionReview(BaseModel):
    decision: DocumentCorrectionDecision
    status: DocumentCorrectionStatus
    expected_row_version: int


class DocumentCorrectionSchema(BaseModel):
    id: uuid.UUID
    parsed_document_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    affects_approved_data: bool
    correction_payload: Dict[str, Any]
    decision: DocumentCorrectionDecision
    decided_by: uuid.UUID
    decided_at: datetime
    status: DocumentCorrectionStatus
    created_at: datetime
    updated_at: datetime
    row_version: int

    class Config:
        from_attributes = True
