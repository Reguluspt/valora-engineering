import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.modules.project_master_data.models import (
    TaxonomyNodeLevel, TaxonomyStatus, AssetFamilyStatus,
    AssetDNAStatus, AssetAttributeDataType, AssetAttributeScope
)

# Config to allow ORM serialization
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# TaxonomyNode Schemas
class TaxonomyNodeCreate(BaseSchema):
    parent_id: Optional[uuid.UUID] = None
    level: TaxonomyNodeLevel
    code: str = Field(..., max_length=64)
    name_vi: str = Field(..., max_length=255)
    name_en: Optional[str] = Field(None, max_length=255)


class TaxonomyNodeUpdate(BaseSchema):
    name_vi: Optional[str] = Field(None, max_length=255)
    name_en: Optional[str] = Field(None, max_length=255)


class TaxonomyNodeResponse(BaseSchema):
    id: uuid.UUID
    parent_id: Optional[uuid.UUID]
    level: TaxonomyNodeLevel
    code: str
    name_vi: str
    name_en: Optional[str]
    status: TaxonomyStatus
    is_system_seed: bool
    merged_into_node_id: Optional[uuid.UUID]
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    row_version: int


# AssetFamily Schemas
class AssetFamilyCreate(BaseSchema):
    taxonomy_node_id: uuid.UUID
    code: str = Field(..., max_length=64)
    name_vi: str = Field(..., max_length=255)
    default_unit_id: Optional[uuid.UUID] = None


class AssetFamilyUpdate(BaseSchema):
    name_vi: Optional[str] = Field(None, max_length=255)
    default_unit_id: Optional[uuid.UUID] = None


class AssetFamilyResponse(BaseSchema):
    id: uuid.UUID
    taxonomy_node_id: uuid.UUID
    code: str
    name_vi: str
    default_unit_id: Optional[uuid.UUID]
    status: AssetFamilyStatus
    is_system_seed: bool
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    row_version: int


# AssetDNA Schemas
class AssetDNACreate(BaseSchema):
    asset_family_id: uuid.UUID
    version: int = Field(1, ge=1)
    name: str = Field(..., max_length=255)


class AssetDNAUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=255)


class AssetDNAResponse(BaseSchema):
    id: uuid.UUID
    asset_family_id: uuid.UUID
    version: int
    name: str
    status: AssetDNAStatus
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    row_version: int


# AssetAttributeDefinition Schemas
class AssetAttributeDefinitionCreate(BaseSchema):
    asset_dna_id: uuid.UUID
    key: str = Field(..., max_length=64)
    label_vi: str = Field(..., max_length=255)
    data_type: AssetAttributeDataType
    unit_id: Optional[uuid.UUID] = None
    scope: AssetAttributeScope = AssetAttributeScope.BOTH
    is_required: bool = False
    is_variant_defining: bool = False
    is_searchable: bool = True
    enum_values: Optional[List[str]] = None
    validation_rule: Optional[dict] = None

    @field_validator("key")
    @classmethod
    def validate_key_snake(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError("Key must be snake_case (lowercase, alphanumeric, and underscores only)")
        return v


class AssetAttributeDefinitionUpdate(BaseSchema):
    label_vi: Optional[str] = Field(None, max_length=255)
    unit_id: Optional[uuid.UUID] = None
    scope: Optional[AssetAttributeScope] = None
    is_required: Optional[bool] = None
    is_variant_defining: Optional[bool] = None
    is_searchable: Optional[bool] = None
    enum_values: Optional[List[str]] = None
    validation_rule: Optional[dict] = None


class AssetAttributeDefinitionResponse(BaseSchema):
    id: uuid.UUID
    asset_dna_id: uuid.UUID
    key: str
    label_vi: str
    data_type: AssetAttributeDataType
    unit_id: Optional[uuid.UUID]
    scope: AssetAttributeScope
    is_required: bool
    is_variant_defining: bool
    is_searchable: bool
    enum_values: Optional[List[str]]
    validation_rule: Optional[dict]
    created_at: datetime
    updated_at: datetime
