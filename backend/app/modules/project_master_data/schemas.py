import math
import uuid
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Config to allow ORM serialization
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Country Schemas
class CountryCreate(BaseSchema):
    iso2: Optional[str] = Field(None, max_length=2)
    iso3: Optional[str] = Field(None, max_length=3)
    name_vi: str = Field(..., max_length=128)
    name_en: Optional[str] = Field(None, max_length=128)


class CountryResponse(BaseSchema):
    id: uuid.UUID
    iso2: Optional[str]
    iso3: Optional[str]
    name_vi: str
    name_en: Optional[str]
    status: str


# Province Schemas
class ProvinceCreate(BaseSchema):
    country_id: uuid.UUID
    name: str = Field(..., max_length=128)
    code: Optional[str] = Field(None, max_length=64)


class ProvinceResponse(BaseSchema):
    id: uuid.UUID
    country_id: uuid.UUID
    name: str
    code: Optional[str]
    status: str


# Unit Schemas
class UnitCreate(BaseSchema):
    code: str = Field(..., max_length=32)
    display_name: str = Field(..., max_length=128)
    symbol: Optional[str] = Field(None, max_length=32)
    unit_type: Optional[str] = Field(None, max_length=50)


class UnitResponse(BaseSchema):
    id: uuid.UUID
    code: str
    display_name: str
    symbol: Optional[str]
    unit_type: Optional[str]
    status: str


# Currency Schemas
class CurrencyCreate(BaseSchema):
    code: str = Field(..., max_length=3)
    display_name: str = Field(..., max_length=128)
    symbol: Optional[str] = Field(None, max_length=16)
    decimal_places: int = Field(0, ge=0)


class CurrencyResponse(BaseSchema):
    id: uuid.UUID
    code: str
    display_name: str
    symbol: Optional[str]
    decimal_places: int
    status: str


# Brand Schemas
class BrandCreate(BaseSchema):
    name: str = Field(..., max_length=255)
    country_id: Optional[uuid.UUID] = None
    manufacturer_id: Optional[uuid.UUID] = None


class BrandResponse(BaseSchema):
    id: uuid.UUID
    name: str
    country_id: Optional[uuid.UUID]
    manufacturer_id: Optional[uuid.UUID]
    status: str


# Manufacturer Schemas
class ManufacturerCreate(BaseSchema):
    legal_name: str = Field(..., max_length=255)
    country_id: Optional[uuid.UUID] = None
    website: Optional[str] = Field(None, max_length=255)


class ManufacturerResponse(BaseSchema):
    id: uuid.UUID
    legal_name: str
    country_id: Optional[uuid.UUID]
    website: Optional[str]
    status: str


# Signer Profile Schemas
class SignerProfileCreate(BaseSchema):
    full_name: str = Field(..., max_length=255)
    title: Optional[str] = Field(None, max_length=255)
    certificate_number: Optional[str] = Field(None, max_length=100)
    is_default: bool = False


class SignerProfileUpdate(BaseSchema):
    title: Optional[str] = Field(None, max_length=255)
    is_default: Optional[bool] = None


class SignerProfileResponse(BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    full_name: str
    title: Optional[str]
    certificate_number: Optional[str]
    is_default: bool
    status: str


# Customer Schemas
class CustomerCreate(BaseSchema):
    legal_name: str = Field(..., max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    tax_code: Optional[str] = Field(None, max_length=64)
    address: Optional[str] = None
    province_id: Optional[uuid.UUID] = None
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    contact_email: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None


class CustomerUpdate(BaseSchema):
    display_name: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    province_id: Optional[uuid.UUID] = None
    contact_phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class CustomerDeactivate(BaseSchema):
    reason: str = Field(..., max_length=255)


class CustomerMerge(BaseSchema):
    source_customer_id: uuid.UUID
    target_customer_id: uuid.UUID
    reason: str = Field(..., max_length=255)


class CustomerResponse(BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    legal_name: str
    display_name: Optional[str]
    tax_code: Optional[str]
    address: Optional[str]
    province_id: Optional[uuid.UUID]
    contact_name: Optional[str]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    notes: Optional[str]
    status: str
    warnings: Optional[List[str]] = None


# Supplier Schemas
class SupplierCreate(BaseSchema):
    legal_name: str = Field(..., max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    tax_code: Optional[str] = Field(None, max_length=64)
    province_id: Optional[uuid.UUID] = None
    reliability_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class SupplierUpdate(BaseSchema):
    display_name: Optional[str] = Field(None, max_length=255)
    reliability_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class SupplierDeactivate(BaseSchema):
    reason: str = Field(..., max_length=255)


class SupplierMerge(BaseSchema):
    source_supplier_id: uuid.UUID
    target_supplier_id: uuid.UUID
    reason: str = Field(..., max_length=255)


class SupplierResponse(BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    legal_name: str
    display_name: Optional[str]
    tax_code: Optional[str]
    province_id: Optional[uuid.UUID]
    reliability_score: Optional[float]
    status: str
    warnings: Optional[List[str]] = None


# Project Schemas
class ProjectCreate(BaseSchema):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    customer_id: uuid.UUID
    description: Optional[str] = None
    fee_amount: float = Field(0.0, ge=0.0)
    fee_currency_id: Optional[uuid.UUID] = None
    signer_profile_id: Optional[uuid.UUID] = None


class ProjectUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    fee_amount: Optional[float] = Field(None, ge=0.0)
    fee_currency_id: Optional[uuid.UUID] = None
    signer_profile_id: Optional[uuid.UUID] = None
    row_version: int = Field(..., ge=1)


class ProjectResponse(BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    customer_id: uuid.UUID
    code: str
    name: str
    description: Optional[str]
    status: str
    knowledge_status: str
    fee_amount: float
    fee_currency_id: Optional[uuid.UUID]
    signer_profile_id: Optional[uuid.UUID]
    row_version: int
    created_at: datetime
    updated_at: datetime


CaseStage = Literal[
    "PRELIMINARY_REQUEST",
    "PRELIMINARY_ANALYSIS",
    "PRELIMINARY_READY",
    "OFFICIAL_INTAKE",
    "ASSET_REVIEW",
    "ASSET_WORKBENCH",
    "PRICE_EVIDENCE",
    "SUPPLIER_QUOTES",
    "SUPPLIER_SELECTION",
    "APPRAISAL_RESULT",
    "DOCUMENT_WORKSPACE",
    "DOCUMENT_SYNC_REVIEW",
    "PUBLISHING_PREPARATION",
    "PUBLISHING_EXCEPTION_REVIEW",
    "PUBLISHING_CONFIRMATION",
    "PUBLISHED",
]


class CaseStateStageResponse(BaseSchema):
    stage: CaseStage
    result: Literal["COMPLETE", "INCOMPLETE", "BLOCKED", "STALE", "NOT_AVAILABLE"]
    provider_key: Optional[str]


class CaseStateNextActionResponse(BaseSchema):
    kind: Literal[
        "BLOCKER",
        "PENDING",
        "UNAVAILABLE",
        "NO_AUTHORIZED_DOWNSTREAM_ACTION",
    ]
    stage: Optional[CaseStage]
    semantic_route_key: Optional[str]
    validation_issue_id: Optional[uuid.UUID]


class CaseStateIssueResponse(BaseSchema):
    id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    severity: Literal["blocking", "warning"]
    status: Literal["open"]
    row_version: int


class CaseStateCapabilityResponse(BaseSchema):
    stage: CaseStage
    available: bool
    provider_key: Optional[str]
    version: str


class CaseStateResponse(BaseSchema):
    case_version: str = Field(..., min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    current_stage: CaseStage
    next_action: Optional[CaseStateNextActionResponse] = None
    stages: list[CaseStateStageResponse]
    blockers: list[CaseStateIssueResponse]
    warnings: list[CaseStateIssueResponse]
    stale: list[dict[str, object]]
    capabilities: list[CaseStateCapabilityResponse]


# ProjectAssetLine Schemas
class ProjectAssetLineCreate(BaseSchema):
    asset_name: str = Field(..., max_length=255)
    description: Optional[str] = None
    quantity: float = Field(1.0, ge=0.0)
    unit_id: Optional[uuid.UUID] = None
    raw_price: Optional[float] = Field(None, ge=0.0)
    raw_price_currency_id: Optional[uuid.UUID] = None
    appraised_unit_price: Optional[float] = Field(None, ge=0.0)
    appraised_currency_id: Optional[uuid.UUID] = None
    brand_id: Optional[uuid.UUID] = None
    manufacturer_id: Optional[uuid.UUID] = None


class ProjectAssetLineUpdate(BaseSchema):
    asset_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    quantity: Optional[float] = Field(None, ge=0.0)
    unit_id: Optional[uuid.UUID] = None
    raw_price: Optional[float] = Field(None, ge=0.0)
    raw_price_currency_id: Optional[uuid.UUID] = None
    appraised_unit_price: Optional[float] = Field(None, ge=0.0)
    appraised_currency_id: Optional[uuid.UUID] = None
    brand_id: Optional[uuid.UUID] = None
    manufacturer_id: Optional[uuid.UUID] = None
    review_status: Optional[str] = Field(None, max_length=50)
    validation_status: Optional[str] = Field(None, max_length=50)
    row_version: int = Field(..., ge=1)


class ProjectAssetLineResponse(BaseSchema):
    id: uuid.UUID
    project_id: uuid.UUID
    asset_name: str
    description: Optional[str]
    quantity: float
    unit_id: Optional[uuid.UUID]
    raw_price: Optional[float]
    raw_price_currency_id: Optional[uuid.UUID]
    appraised_unit_price: Optional[float]
    appraised_currency_id: Optional[uuid.UUID]
    review_status: str
    validation_status: str
    brand_id: Optional[uuid.UUID]
    manufacturer_id: Optional[uuid.UUID]
    version_token: str = Field(..., serialization_alias="version_token", validation_alias="row_version")

    @field_validator("version_token", mode="before")
    @classmethod
    def convert_version_to_str(cls, v):
        if v is not None:
            return str(v)
        return v


class ProjectAssetLinePaginationResponse(BaseSchema):
    project_id: uuid.UUID
    items: List[ProjectAssetLineResponse]
    total: int
    limit: int
    offset: int


# ProjectFile Schemas (Metadata only)
class ProjectFileCreate(BaseSchema):
    file_name: str = Field(..., max_length=255)
    file_category: str = Field(..., max_length=50)
    file_size: int = Field(..., ge=0)
    mime_type: str = Field(..., max_length=100)
    storage_object_key: str = Field(..., max_length=1024)
    checksum_sha256: str = Field(..., max_length=64)
    extracted_metadata: Optional[dict] = None


class ProjectFileResponse(BaseSchema):
    id: uuid.UUID
    project_id: uuid.UUID
    file_name: str
    file_category: str
    file_size: int
    mime_type: str
    storage_object_key: str
    checksum_sha256: str
    processing_status: str
    extracted_metadata: Optional[dict]
    uploaded_by: uuid.UUID
    created_at: datetime


class ProjectResolutionResponse(BaseSchema):
    project_id: uuid.UUID
    display_name: str
    matched_by: str


class PreliminaryAnalysisLineItem(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    identity: str = Field(..., max_length=255)
    accepted_price_basis: str = Field(..., max_length=64)
    confirmed_reference_price: float = Field(..., ge=0.0)
    transport_percentage: float = Field(..., ge=0.0, le=100.0)
    proposed_unit_price: float = Field(..., ge=0.0)
    human_line_confirmed: bool
    has_unresolved_blocking_line: bool
    source_row_number: int = Field(..., ge=1, le=1048576)
    quantity: float = Field(..., ge=0.0)

    @field_validator(
        "human_line_confirmed", "has_unresolved_blocking_line", mode="before"
    )
    @classmethod
    def _strict_bool(cls, value):
        if not isinstance(value, bool):
            raise ValueError("must be a boolean")
        return value

    @field_validator(
        "confirmed_reference_price",
        "transport_percentage",
        "proposed_unit_price",
        "quantity",
        mode="before",
    )
    @classmethod
    def _finite_number(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("must be a finite number")
        if not math.isfinite(value):
            raise ValueError("must be a finite number")
        return value

    @field_validator("source_row_number", mode="before")
    @classmethod
    def _strict_positive_int(cls, value):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be a positive integer")
        return value


class PreliminaryAnalysisFinalizeRequest(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    project_id: uuid.UUID
    expected_project_version: int = Field(..., ge=1)
    import_batch_id: uuid.UUID
    source_artifact_id: uuid.UUID
    structure_snapshot_id: uuid.UUID
    mapping_decision_id: uuid.UUID
    mapping_profile_usage_id: uuid.UUID
    line_manifest: List[PreliminaryAnalysisLineItem]
    idempotency_key: str = Field(..., max_length=128)
    confirmed: bool

    @field_validator("confirmed", mode="before")
    @classmethod
    def _strict_bool(cls, value):
        if not isinstance(value, bool):
            raise ValueError("must be a boolean")
        return value


class PreliminaryAnalysisSnapshotResponse(BaseSchema):
    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    version: int
    source_artifact_id: uuid.UUID
    mapping_decision_id: uuid.UUID
    mapping_profile_usage_id: uuid.UUID
    line_manifest_digest_sha256: str
    finalized_by_user_id: uuid.UUID
    finalized_at: datetime


# ==========================================
# NCC Selection (PR-04) Schemas
# ==========================================

NccSelectionState = Literal["unselected", "selected", "stale"]


class NccSelectionConfirmRequest(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    quote_line_id: uuid.UUID
    expected_selection_revision: int = Field(..., ge=0)
    acknowledged_warning_codes: list[str] = Field(default_factory=list)
    idempotency_key: str = Field(..., max_length=128)
    confirmed: bool

    @field_validator("confirmed", mode="before")
    @classmethod
    def _strict_bool(cls, value):
        if not isinstance(value, bool):
            raise ValueError("must be a boolean")
        return value

    @field_validator("acknowledged_warning_codes", mode="before")
    @classmethod
    def _strict_str_list(cls, value):
        if value is None:
            return []
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError("must be a list of strings")
        return value


class NccSelectionEvidenceResponse(BaseSchema):
    evidence_file_id: uuid.UUID
    filename: Optional[str]
    status: Optional[str]


class NccSelectionCandidateResponse(BaseSchema):
    quote_line_id: uuid.UUID
    quote_batch_id: uuid.UUID
    quote_batch_revision_number: int
    supplier_id: uuid.UUID
    supplier_name: str
    quoted_unit_price: float
    currency: str
    quantity: Optional[float]
    unit_of_measure: Optional[str]
    quote_date: Optional[datetime]
    evidence: NccSelectionEvidenceResponse
    difference_amount: Optional[float]
    difference_percent: Optional[float]
    warnings: List[str]
    eligible: bool


class NccSelectionCurrentResponse(BaseSchema):
    selection_id: uuid.UUID
    selection_revision: int
    quote_line_id: uuid.UUID
    quote_batch_id: uuid.UUID
    quote_batch_revision_number: int
    supplier_id: uuid.UUID
    supplier_name: str
    quoted_unit_price: float
    currency: str
    quantity: Optional[float]
    unit_of_measure: Optional[str]
    quote_date: Optional[datetime]
    evidence: NccSelectionEvidenceResponse
    current_unit_price: Optional[float]
    current_unit_price_currency_id: Optional[uuid.UUID]
    difference_amount: Optional[float]
    difference_percent: Optional[float]
    warnings: List[str]
    acknowledged_warning_codes: List[str]
    confirmed_by_user_id: uuid.UUID
    confirmed_at: datetime
    stale: bool


class NccSelectionHistoryItemResponse(BaseSchema):
    selection_revision: int
    quote_line_id: uuid.UUID
    supplier_name: str
    quoted_unit_price: float
    currency: str
    difference_amount: Optional[float]
    difference_percent: Optional[float]
    warnings: List[str]
    confirmed_by_user_id: uuid.UUID
    confirmed_at: datetime


class NccSelectionAssetLineResponse(BaseSchema):
    asset_line_id: uuid.UUID
    asset_name: str
    unit_id: Optional[uuid.UUID]
    unit_name: Optional[str]
    quantity: float
    appraised_unit_price: Optional[float]
    appraised_currency_id: Optional[uuid.UUID]
    current_selection: Optional[NccSelectionCurrentResponse]
    candidates: List[NccSelectionCandidateResponse]
    history: List[NccSelectionHistoryItemResponse]
    state: NccSelectionState


class NccSelectionKpisResponse(BaseSchema):
    total_asset_lines: int
    selected: int
    unselected: int
    stale: int
    eligible_quotes: int


class NccSelectionAggregateResponse(BaseSchema):
    project_id: uuid.UUID
    kpis: NccSelectionKpisResponse
    asset_lines: List[NccSelectionAssetLineResponse]

