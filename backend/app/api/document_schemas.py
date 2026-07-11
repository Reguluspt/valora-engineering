import uuid
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from app.modules.project_master_data.models import (
    DocumentTemplateStatus, TemplateVersionStatus, PlaceholderDataType,
    PlaceholderSourceContext, PlaceholderBindingType, RenderJobStatus,
    GeneratedDocumentStatus, DocumentPackageType, DocumentPackageStatus
)

# ----------------- DocumentTemplate -----------------

class DocumentTemplateCreate(BaseModel):
    organization_id: uuid.UUID
    document_type: str = Field(..., max_length=50)
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    status: DocumentTemplateStatus = DocumentTemplateStatus.DRAFT

class DocumentTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[DocumentTemplateStatus] = None
    current_version_id: Optional[uuid.UUID] = None
    replacement_template_id: Optional[uuid.UUID] = None
    expected_row_version: Optional[int] = None

class DocumentTemplateSchema(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    document_type: str
    code: str
    name: str
    description: Optional[str]
    current_version_id: Optional[uuid.UUID]
    replacement_template_id: Optional[uuid.UUID]
    status: DocumentTemplateStatus
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    row_version: int

    class Config:
        from_attributes = True


# ----------------- TemplateVersion -----------------

class TemplateVersionCreate(BaseModel):
    version_number: int
    source_file_id: Optional[uuid.UUID] = None
    template_format: str = Field(..., max_length=50)
    placeholder_manifest: Optional[Dict[str, Any]] = None
    status: TemplateVersionStatus = TemplateVersionStatus.DRAFT

class TemplateVersionDeprecate(BaseModel):
    deprecation_reason: str
    replacement_version_id: Optional[uuid.UUID] = None
    expected_row_version: int

class TemplateVersionSchema(BaseModel):
    id: uuid.UUID
    document_template_id: uuid.UUID
    version_number: int
    source_file_id: Optional[uuid.UUID]
    template_format: str
    placeholder_manifest: Optional[Dict[str, Any]]
    status: TemplateVersionStatus
    deprecation_reason: Optional[str]
    replacement_version_id: Optional[uuid.UUID]
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    row_version: int

    class Config:
        from_attributes = True


# ----------------- ComputedPlaceholderExpression -----------------

class ComputedPlaceholderExpressionCreate(BaseModel):
    placeholder_key: str = Field(..., max_length=255)
    expression_type: str = Field("valora_expr", max_length=50)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    expression: str
    output_data_type: PlaceholderDataType

class ComputedPlaceholderExpressionSchema(BaseModel):
    id: uuid.UUID
    placeholder_key: str
    expression_type: str
    inputs: Dict[str, Any]
    expression: str
    output_data_type: PlaceholderDataType
    status: str
    created_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ----------------- TemplatePlaceholder -----------------

class TemplatePlaceholderCreate(BaseModel):
    placeholder_key: str = Field(..., max_length=255)
    label_vi: str = Field(..., max_length=255)
    data_type: PlaceholderDataType
    source_context: PlaceholderSourceContext
    source_path: str = Field(..., max_length=255)
    is_required: bool = True
    default_value: Optional[Dict[str, Any]] = None
    format_rule: Optional[Dict[str, Any]] = None
    validation_rule: Optional[Dict[str, Any]] = None
    computed_expression_id: Optional[uuid.UUID] = None
    status: str = "active"

class TemplatePlaceholderSchema(BaseModel):
    id: uuid.UUID
    template_version_id: uuid.UUID
    placeholder_key: str
    label_vi: str
    data_type: PlaceholderDataType
    source_context: PlaceholderSourceContext
    source_path: str
    is_required: bool
    default_value: Optional[Dict[str, Any]]
    format_rule: Optional[Dict[str, Any]]
    validation_rule: Optional[Dict[str, Any]]
    computed_expression_id: Optional[uuid.UUID]
    status: str

    class Config:
        from_attributes = True


# ----------------- PlaceholderBinding -----------------

class PlaceholderBindingCreate(BaseModel):
    template_placeholder_id: uuid.UUID
    binding_path: str = Field(..., max_length=255)
    binding_type: PlaceholderBindingType
    fallback_value: Optional[Dict[str, Any]] = None
    is_required: bool = True

class PlaceholderBindingSchema(BaseModel):
    id: uuid.UUID
    template_version_id: uuid.UUID
    template_placeholder_id: uuid.UUID
    binding_path: str
    binding_type: PlaceholderBindingType
    fallback_value: Optional[Dict[str, Any]]
    is_required: bool

    class Config:
        from_attributes = True


# ----------------- RenderJob -----------------

class RenderJobCreate(BaseModel):
    project_id: uuid.UUID
    template_version_id: uuid.UUID
    render_mode: str = Field("draft", max_length=50)
    output_formats: List[str] = Field(default_factory=lambda: ["docx", "pdf"])
    data_snapshot: Dict[str, Any]

class RenderJobSchema(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    template_version_id: uuid.UUID
    render_mode: str
    output_formats: List[str]
    data_snapshot: Dict[str, Any]
    data_snapshot_hash: str
    status: RenderJobStatus
    error_code: Optional[str]
    error_message: Optional[str]
    failed_step: Optional[str]
    retry_count: int
    timeout_at: Optional[datetime]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    row_version: int

    class Config:
        from_attributes = True


# ----------------- GeneratedDocument -----------------

class GeneratedDocumentSchema(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    render_job_id: uuid.UUID
    document_type: str
    output_format: str
    filename: str
    storage_key: str
    checksum_sha256: str
    file_size_bytes: int
    template_version_id: uuid.UUID
    data_snapshot_hash: str
    status: GeneratedDocumentStatus
    created_at: datetime
    archived_by: Optional[uuid.UUID]
    archived_at: Optional[datetime]

    class Config:
        from_attributes = True


# ----------------- DocumentPackage -----------------

class DocumentPackageCreate(BaseModel):
    project_id: uuid.UUID
    package_type: DocumentPackageType
    name: str = Field(..., max_length=255)
    status: DocumentPackageStatus = DocumentPackageStatus.DRAFT

class DocumentPackageSchema(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    package_type: DocumentPackageType
    name: str
    status: DocumentPackageStatus
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    row_version: int

    class Config:
        from_attributes = True


# ----------------- DocumentPackageItem -----------------

class DocumentPackageItemCreate(BaseModel):
    generated_document_id: uuid.UUID
    sort_order: int

class DocumentPackageItemSchema(BaseModel):
    id: uuid.UUID
    document_package_id: uuid.UUID
    generated_document_id: uuid.UUID
    sort_order: int

    class Config:
        from_attributes = True
