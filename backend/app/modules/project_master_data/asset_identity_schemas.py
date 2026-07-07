import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.modules.project_master_data.models import (
    CanonicalAssetMaturity, CanonicalAssetStatus,
    AssetVariantStatus, AssetAliasScope, AssetAliasStatus
)

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# CanonicalAsset Schemas
class CanonicalAssetCreate(BaseSchema):
    asset_family_id: uuid.UUID
    primary_taxonomy_node_id: uuid.UUID
    standard_name: str = Field(..., max_length=255)
    short_name: Optional[str] = Field(None, max_length=128)
    brand_id: Optional[uuid.UUID] = None
    manufacturer_id: Optional[uuid.UUID] = None
    country_id: Optional[uuid.UUID] = None
    model_code: Optional[str] = Field(None, max_length=128)
    maturity_level: CanonicalAssetMaturity = CanonicalAssetMaturity.DRAFT


class CanonicalAssetUpdate(BaseSchema):
    standard_name: Optional[str] = Field(None, max_length=255)
    short_name: Optional[str] = Field(None, max_length=128)
    brand_id: Optional[uuid.UUID] = None
    manufacturer_id: Optional[uuid.UUID] = None
    country_id: Optional[uuid.UUID] = None
    model_code: Optional[str] = Field(None, max_length=128)
    maturity_level: Optional[CanonicalAssetMaturity] = None
    status: Optional[CanonicalAssetStatus] = None


class CanonicalAssetResponse(BaseSchema):
    id: uuid.UUID
    asset_family_id: uuid.UUID
    primary_taxonomy_node_id: uuid.UUID
    standard_name: str
    short_name: Optional[str]
    brand_id: Optional[uuid.UUID]
    manufacturer_id: Optional[uuid.UUID]
    country_id: Optional[uuid.UUID]
    model_code: Optional[str]
    maturity_level: CanonicalAssetMaturity
    status: CanonicalAssetStatus
    merged_into_asset_id: Optional[uuid.UUID]
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    row_version: int


# AssetVariant Schemas
class AssetVariantCreate(BaseSchema):
    asset_family_id: uuid.UUID
    code: str = Field(..., max_length=128)
    display_name: str = Field(..., max_length=255)


class AssetVariantUpdate(BaseSchema):
    display_name: Optional[str] = Field(None, max_length=255)
    status: Optional[AssetVariantStatus] = None


class AssetVariantResponse(BaseSchema):
    id: uuid.UUID
    asset_family_id: uuid.UUID
    canonical_asset_id: uuid.UUID
    code: str
    display_name: str
    status: AssetVariantStatus
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    row_version: int


# AssetAlias Schemas
class AssetAliasCreate(BaseSchema):
    asset_variant_id: Optional[uuid.UUID] = None
    alias_scope: AssetAliasScope = AssetAliasScope.CANONICAL
    raw_alias: str = Field(..., max_length=255)


class AssetAliasUpdate(BaseSchema):
    status: Optional[AssetAliasStatus] = None


class AssetAliasResponse(BaseSchema):
    id: uuid.UUID
    canonical_asset_id: uuid.UUID
    asset_variant_id: Optional[uuid.UUID]
    alias_scope: AssetAliasScope
    raw_alias: str
    normalized_alias: str
    status: AssetAliasStatus
    created_at: datetime
    updated_at: datetime
