import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, EmailStr

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
