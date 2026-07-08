import enum
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, ForeignKey, UniqueConstraint, Index, Boolean, DateTime, JSON, text, Numeric, CheckConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin
from app.db.mixins import utc_now


class OrganizationStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    INVITED = "invited"
    LOCKED = "locked"


class OrganizationProfile(Base, UUIDMixin, TimestampMixin):
    """Represents an organization/tenant in the system."""
    __tablename__ = "organization_profiles"

    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    organization_slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    tax_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    default_currency_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    status: Mapped[OrganizationStatus] = mapped_column(
        String(50),
        nullable=False,
        default=OrganizationStatus.ACTIVE
    )

    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan"
    )


class User(Base, UUIDMixin, TimestampMixin):
    """Represents a user account in the system."""
    __tablename__ = "users"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization_profiles.id", ondelete="CASCADE"),
        nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        String(50),
        nullable=False,
        default=UserStatus.ACTIVE
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    organization: Mapped["OrganizationProfile"] = relationship(
        "OrganizationProfile",
        back_populates="users"
    )
    roles: Mapped[List["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        foreign_keys="[UserRole.user_id]",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_user_org_email"),
    )


class Role(Base, UUIDMixin):
    """Represents a system role containing permission scopes."""
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    user_roles: Mapped[List["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan"
    )


class UserRole(Base, UUIDMixin):
    """Relationship table mapping users to roles with active/revoked status."""
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False
    )
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped["User"] = relationship(
        "User",
        back_populates="roles",
        foreign_keys=[user_id]
    )
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")

    __table_args__ = (
        Index(
            "uq_active_user_role",
            "user_id",
            "role_id",
            unique=True,
            postgresql_where=text("is_active = true"),
            sqlite_where=text("is_active = 1")
        ),
    )


class ReferenceStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class UnitType(str, enum.Enum):
    QUANTITY = "quantity"
    LENGTH = "length"
    AREA = "area"
    WEIGHT = "weight"
    OTHER = "other"


class Country(Base, UUIDMixin, TimestampMixin):
    """Represents a country in the lookup database."""
    __tablename__ = "countries"

    iso2: Mapped[Optional[str]] = mapped_column(String(2), unique=True, nullable=True)
    iso3: Mapped[Optional[str]] = mapped_column(String(3), unique=True, nullable=True)
    name_vi: Mapped[str] = mapped_column(String(128), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[ReferenceStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ReferenceStatus.ACTIVE
    )

    provinces: Mapped[List["Province"]] = relationship(
        "Province",
        back_populates="country",
        cascade="all, delete-orphan"
    )


class Province(Base, UUIDMixin):
    """Represents a province/city within a country."""
    __tablename__ = "provinces"

    country_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[ReferenceStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ReferenceStatus.ACTIVE
    )

    country: Mapped["Country"] = relationship("Country", back_populates="provinces")


class Unit(Base, UUIDMixin):
    """Represents a measurement unit lookup."""
    __tablename__ = "units"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    symbol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    unit_type: Mapped[Optional[UnitType]] = mapped_column(
        String(50),
        nullable=True
    )
    status: Mapped[ReferenceStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ReferenceStatus.ACTIVE
    )


class Currency(Base, UUIDMixin):
    """Represents a monetary currency lookup."""
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    symbol: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    decimal_places: Mapped[int] = mapped_column(nullable=False, default=0)
    status: Mapped[ReferenceStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ReferenceStatus.ACTIVE
    )


class CustomerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MERGED = "merged"


class SupplierStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MERGED = "merged"


class BrandStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MERGED = "merged"


class ManufacturerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class SignerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Customer(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Represents a customer organization in the system."""
    __tablename__ = "customers"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization_profiles.id", ondelete="CASCADE"),
        nullable=False
    )
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tax_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    province_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("provinces.id", ondelete="SET NULL"),
        nullable=True
    )
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[CustomerStatus] = mapped_column(
        String(50),
        nullable=False,
        default=CustomerStatus.ACTIVE
    )
    merged_into_customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )

    organization: Mapped["OrganizationProfile"] = relationship("OrganizationProfile")
    province: Mapped[Optional["Province"]] = relationship("Province")
    aliases: Mapped[List["CustomerAlias"]] = relationship(
        "CustomerAlias",
        back_populates="customer",
        cascade="all, delete-orphan"
    )
    merged_into: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        remote_side="[Customer.id]"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "tax_code", name="uq_customer_tax_org"),
    )


class CustomerAlias(Base, UUIDMixin):
    """Stores fuzzy matching name aliases for a customer."""
    __tablename__ = "customer_aliases"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False
    )
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="aliases")


class Supplier(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Represents a supplier organization in the system."""
    __tablename__ = "suppliers"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization_profiles.id", ondelete="CASCADE"),
        nullable=False
    )
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tax_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    province_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("provinces.id", ondelete="SET NULL"),
        nullable=True
    )
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reliability_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    status: Mapped[SupplierStatus] = mapped_column(
        String(50),
        nullable=False,
        default=SupplierStatus.ACTIVE
    )
    merged_into_supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )

    organization: Mapped["OrganizationProfile"] = relationship("OrganizationProfile")
    province: Mapped[Optional["Province"]] = relationship("Province")
    aliases: Mapped[List["SupplierAlias"]] = relationship(
        "SupplierAlias",
        back_populates="supplier",
        cascade="all, delete-orphan"
    )
    merged_into: Mapped[Optional["Supplier"]] = relationship(
        "Supplier",
        remote_side="[Supplier.id]"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "tax_code", name="uq_supplier_tax_org"),
    )


class SupplierAlias(Base, UUIDMixin):
    """Stores fuzzy matching name aliases for a supplier."""
    __tablename__ = "supplier_aliases"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False
    )
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )

    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="aliases")


class Manufacturer(Base, UUIDMixin, TimestampMixin):
    """Represents a product manufacturer."""
    __tablename__ = "manufacturers"

    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("countries.id", ondelete="SET NULL"),
        nullable=True
    )
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[ManufacturerStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ManufacturerStatus.ACTIVE
    )

    country: Mapped[Optional["Country"]] = relationship("Country")
    brands: Mapped[List["Brand"]] = relationship(
        "Brand",
        back_populates="manufacturer"
    )


class Brand(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Represents a product brand name."""
    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("countries.id", ondelete="SET NULL"),
        nullable=True
    )
    manufacturer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("manufacturers.id", ondelete="SET NULL"),
        nullable=True
    )
    status: Mapped[BrandStatus] = mapped_column(
        String(50),
        nullable=False,
        default=BrandStatus.ACTIVE
    )

    country: Mapped[Optional["Country"]] = relationship("Country")
    manufacturer: Mapped[Optional["Manufacturer"]] = relationship(
        "Manufacturer",
        back_populates="brands"
    )

    __table_args__ = (
        Index("uq_brand_name_lower", text("lower(name)"), unique=True),
    )


class SignerProfile(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Represents an authorized signature profile for appraisals."""
    __tablename__ = "signer_profiles"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization_profiles.id", ondelete="CASCADE"),
        nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    certificate_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    signature_image_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[SignerStatus] = mapped_column(
        String(50),
        nullable=False,
        default=SignerStatus.ACTIVE
    )

    organization: Mapped["OrganizationProfile"] = relationship("OrganizationProfile")


class ProjectWorkflowStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


class KnowledgeUpdateStatus(str, enum.Enum):
    PENDING = "pending"
    APPLIED = "applied"
    DEFERRED = "deferred"
    IGNORED = "ignored"


class AssetLineReviewStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    FLAGGED = "flagged"
    REJECTED = "rejected"


class AssetLineValidationStatus(str, enum.Enum):
    UNVALIDATED = "unvalidated"
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"


class ProjectFileCategory(str, enum.Enum):
    INPUT_CONTRACT = "input_contract"
    REFERENCE_DOC = "reference_doc"
    APPRAISAL_REPORT = "appraisal_report"
    SUPPORT_FILE = "support_file"
    OTHER = "other"


class FileProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Represents a valuation project in the system."""
    __tablename__ = "projects"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization_profiles.id", ondelete="CASCADE"),
        nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectWorkflowStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ProjectWorkflowStatus.DRAFT
    )
    knowledge_status: Mapped[KnowledgeUpdateStatus] = mapped_column(
        String(50),
        nullable=False,
        default=KnowledgeUpdateStatus.PENDING
    )
    fee_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0.0)
    fee_currency_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("currencies.id", ondelete="SET NULL"),
        nullable=True
    )
    signer_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("signer_profiles.id", ondelete="SET NULL"),
        nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )

    organization: Mapped["OrganizationProfile"] = relationship("OrganizationProfile")
    customer: Mapped["Customer"] = relationship("Customer")
    currency: Mapped[Optional["Currency"]] = relationship("Currency")
    signer_profile: Mapped[Optional["SignerProfile"]] = relationship("SignerProfile")

    asset_lines: Mapped[List["ProjectAssetLine"]] = relationship(
        "ProjectAssetLine",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    files: Mapped[List["ProjectFile"]] = relationship(
        "ProjectFile",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_project_code_org"),
        CheckConstraint("fee_amount >= 0", name="chk_project_fee_positive"),
    )


class ProjectAssetLine(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Represents a single line item of assets under evaluation in a project."""
    __tablename__ = "project_asset_lines"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False, default=1.0)
    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("units.id", ondelete="SET NULL"),
        nullable=True
    )
    raw_price: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    raw_price_currency_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("currencies.id", ondelete="SET NULL"),
        nullable=True
    )
    appraised_unit_price: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    appraised_currency_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("currencies.id", ondelete="SET NULL"),
        nullable=True
    )
    review_status: Mapped[AssetLineReviewStatus] = mapped_column(
        String(50),
        nullable=False,
        default=AssetLineReviewStatus.PENDING
    )
    validation_status: Mapped[AssetLineValidationStatus] = mapped_column(
        String(50),
        nullable=False,
        default=AssetLineValidationStatus.UNVALIDATED
    )
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL"),
        nullable=True
    )
    manufacturer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("manufacturers.id", ondelete="SET NULL"),
        nullable=True
    )

    # Future Placeholders
    matched_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    matched_knowledge_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    taxonomy_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)

    suggested_taxonomy_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("taxonomy_nodes.id", ondelete="RESTRICT"),
        nullable=True
    )
    approved_taxonomy_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("taxonomy_nodes.id", ondelete="RESTRICT"),
        nullable=True
    )
    suggested_canonical_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("canonical_assets.id", ondelete="RESTRICT"),
        nullable=True
    )
    approved_canonical_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("canonical_assets.id", ondelete="RESTRICT"),
        nullable=True
    )
    suggested_asset_variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("asset_variants.id", ondelete="RESTRICT"),
        nullable=True
    )
    approved_asset_variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("asset_variants.id", ondelete="RESTRICT"),
        nullable=True
    )

    project: Mapped["Project"] = relationship("Project", back_populates="asset_lines")
    unit: Mapped[Optional["Unit"]] = relationship("Unit")
    raw_price_currency: Mapped[Optional["Currency"]] = relationship(
        "Currency",
        foreign_keys=[raw_price_currency_id]
    )
    appraised_currency: Mapped[Optional["Currency"]] = relationship(
        "Currency",
        foreign_keys=[appraised_currency_id]
    )
    brand: Mapped[Optional["Brand"]] = relationship("Brand")
    manufacturer: Mapped[Optional["Manufacturer"]] = relationship("Manufacturer")

    suggested_taxonomy_node: Mapped[Optional["TaxonomyNode"]] = relationship(
        "TaxonomyNode",
        foreign_keys=[suggested_taxonomy_node_id]
    )
    approved_taxonomy_node: Mapped[Optional["TaxonomyNode"]] = relationship(
        "TaxonomyNode",
        foreign_keys=[approved_taxonomy_node_id]
    )
    suggested_canonical_asset: Mapped[Optional["CanonicalAsset"]] = relationship(
        "CanonicalAsset",
        foreign_keys=[suggested_canonical_asset_id]
    )
    approved_canonical_asset: Mapped[Optional["CanonicalAsset"]] = relationship(
        "CanonicalAsset",
        foreign_keys=[approved_canonical_asset_id]
    )
    suggested_asset_variant: Mapped[Optional["AssetVariant"]] = relationship(
        "AssetVariant",
        foreign_keys=[suggested_asset_variant_id]
    )
    approved_asset_variant: Mapped[Optional["AssetVariant"]] = relationship(
        "AssetVariant",
        foreign_keys=[approved_asset_variant_id]
    )

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="chk_asset_quantity_positive"),
        CheckConstraint("raw_price >= 0", name="chk_asset_raw_price_positive"),
        CheckConstraint("appraised_unit_price >= 0", name="chk_asset_appraised_price_positive"),
    )


class ProjectFile(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Represents a file uploaded as part of a project."""
    __tablename__ = "project_files"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_category: Mapped[ProjectFileCategory] = mapped_column(
        String(50),
        nullable=False,
        default=ProjectFileCategory.SUPPORT_FILE
    )
    file_size: Mapped[int] = mapped_column(nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_status: Mapped[FileProcessingStatus] = mapped_column(
        String(50),
        nullable=False,
        default=FileProcessingStatus.PENDING
    )
    extracted_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="files")
    uploader: Mapped["User"] = relationship("User")

    __table_args__ = (
        CheckConstraint("file_size >= 0", name="chk_file_size_positive"),
    )


class AuditEvent(Base, UUIDMixin):
    """Stores append-only audit log events for system and user mutations."""
    __tablename__ = "audit_events"

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("organization_profiles.id", ondelete="SET NULL"),
        nullable=True
    )
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    command_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now()
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    organization: Mapped[Optional["OrganizationProfile"]] = relationship("OrganizationProfile")
    actor: Mapped[Optional["User"]] = relationship("User")


# ==================================================
# TAXONOMY CORE ENUMS & MODELS
# ==================================================

class TaxonomyNodeLevel(str, enum.Enum):
    DOMAIN = "domain"
    CATEGORY = "category"
    SUBCATEGORY = "subcategory"
    GROUP = "group"


class TaxonomyStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"
    MERGED = "merged"


class AssetFamilyStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"
    MERGED = "merged"


class AssetDNAStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class AssetAttributeDataType(str, enum.Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ENUM = "enum"
    DATE = "date"


class AssetAttributeScope(str, enum.Enum):
    CANONICAL = "canonical"
    VARIANT = "variant"
    BOTH = "both"


class TaxonomyChangeRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TaxonomyNode(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Represents a node in the hierarchical equipment/asset taxonomy."""
    __tablename__ = "taxonomy_nodes"

    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("taxonomy_nodes.id", ondelete="CASCADE"),
        nullable=True
    )
    level: Mapped[TaxonomyNodeLevel] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name_vi: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[TaxonomyStatus] = mapped_column(
        String(50),
        nullable=False,
        default=TaxonomyStatus.DRAFT
    )
    is_system_seed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    merged_into_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("taxonomy_nodes.id"),
        nullable=True
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    # Relationships
    parent: Mapped[Optional["TaxonomyNode"]] = relationship(
        "TaxonomyNode",
        remote_side="TaxonomyNode.id",
        back_populates="children",
        foreign_keys=[parent_id]
    )
    children: Mapped[List["TaxonomyNode"]] = relationship(
        "TaxonomyNode",
        back_populates="parent",
        foreign_keys=[parent_id],
        cascade="all, delete-orphan"
    )
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])


class AssetFamily(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Represents a logical grouping of canonical assets within a taxonomy group."""
    __tablename__ = "asset_families"

    taxonomy_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("taxonomy_nodes.id", ondelete="RESTRICT"),
        nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name_vi: Mapped[str] = mapped_column(String(255), nullable=False)
    default_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("units.id", ondelete="SET NULL"),
        nullable=True
    )
    status: Mapped[AssetFamilyStatus] = mapped_column(
        String(50),
        nullable=False,
        default=AssetFamilyStatus.DRAFT
    )
    is_system_seed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    taxonomy_node: Mapped["TaxonomyNode"] = relationship("TaxonomyNode")
    default_unit: Mapped[Optional["Unit"]] = relationship("Unit")
    dna_schemas: Mapped[List["AssetDNA"]] = relationship(
        "AssetDNA",
        back_populates="asset_family",
        cascade="all, delete-orphan"
    )


class AssetDNA(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Represents a versioned schema template mapping technical attributes to a family."""
    __tablename__ = "asset_dna"

    asset_family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("asset_families.id", ondelete="CASCADE"),
        nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[AssetDNAStatus] = mapped_column(
        String(50),
        nullable=False,
        default=AssetDNAStatus.DRAFT
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    asset_family: Mapped["AssetFamily"] = relationship("AssetFamily", back_populates="dna_schemas")
    attributes: Mapped[List["AssetAttributeDefinition"]] = relationship(
        "AssetAttributeDefinition",
        back_populates="asset_dna",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "uq_active_dna_per_family",
            "asset_family_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
            postgresql_where=text("status = 'active'")
        ),
    )


class AssetAttributeDefinition(Base, UUIDMixin, TimestampMixin):
    """Represents a schema validation rule for individual characteristics inside a DNA template."""
    __tablename__ = "asset_attribute_definitions"

    asset_dna_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("asset_dna.id", ondelete="CASCADE"),
        nullable=False
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    label_vi: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[AssetAttributeDataType] = mapped_column(String(50), nullable=False)
    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("units.id", ondelete="SET NULL"),
        nullable=True
    )
    scope: Mapped[AssetAttributeScope] = mapped_column(
        String(50),
        nullable=False,
        default=AssetAttributeScope.BOTH
    )
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_variant_defining: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_searchable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enum_values: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    validation_rule: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    asset_dna: Mapped["AssetDNA"] = relationship("AssetDNA", back_populates="attributes")
    unit: Mapped[Optional["Unit"]] = relationship("Unit")

    __table_args__ = (
        UniqueConstraint("asset_dna_id", "key", name="uq_attribute_definition_dna_key"),
    )


class TaxonomyChangeRequest(Base, UUIDMixin, TimestampMixin):
    """Represents a user-proposed taxonomy node change request requiring review."""
    __tablename__ = "taxonomy_change_requests"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization_profiles.id", ondelete="CASCADE"),
        nullable=False
    )
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)
    node_level: Mapped[str] = mapped_column(String(50), nullable=False)
    parent_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("taxonomy_nodes.id"),
        nullable=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name_vi: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[TaxonomyChangeRequestStatus] = mapped_column(
        String(50),
        nullable=False,
        default=TaxonomyChangeRequestStatus.PENDING
    )
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    # Relationships
    organization: Mapped["OrganizationProfile"] = relationship("OrganizationProfile")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by])


# ==================================================
# CANONICAL ASSET ENUMS & MODELS
# ==================================================

class CanonicalAssetStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    MERGED = "merged"
    REJECTED = "rejected"


class CanonicalAssetMaturity(str, enum.Enum):
    DRAFT = "draft"
    OBSERVED = "observed"
    REVIEWED = "reviewed"
    VALIDATED = "validated"
    CANONICAL = "canonical"
    DEPRECATED = "deprecated"


class AttributeValueSource(str, enum.Enum):
    MANUAL = "manual"
    AI = "ai"
    IMPORT = "import"
    KNOWLEDGE = "knowledge"


class CanonicalAsset(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Represents a master/canonical asset record in the catalog."""
    __tablename__ = "canonical_assets"

    asset_family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("asset_families.id", ondelete="RESTRICT"),
        nullable=False
    )
    primary_taxonomy_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("taxonomy_nodes.id", ondelete="RESTRICT"),
        nullable=False
    )
    standard_name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    brand_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL"),
        nullable=True
    )
    manufacturer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("manufacturers.id", ondelete="SET NULL"),
        nullable=True
    )
    country_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("countries.id", ondelete="SET NULL"),
        nullable=True
    )
    model_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    maturity_level: Mapped[CanonicalAssetMaturity] = mapped_column(
        String(50),
        nullable=False,
        default=CanonicalAssetMaturity.DRAFT
    )
    status: Mapped[CanonicalAssetStatus] = mapped_column(
        String(50),
        nullable=False,
        default=CanonicalAssetStatus.DRAFT
    )
    merged_into_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("canonical_assets.id"),
        nullable=True
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    asset_family: Mapped["AssetFamily"] = relationship("AssetFamily")
    primary_taxonomy_node: Mapped["TaxonomyNode"] = relationship("TaxonomyNode")
    brand: Mapped[Optional["Brand"]] = relationship("Brand")
    manufacturer: Mapped[Optional["Manufacturer"]] = relationship("Manufacturer")
    country: Mapped[Optional["Country"]] = relationship("Country")
    attributes: Mapped[List["CanonicalAssetAttributeValue"]] = relationship(
        "CanonicalAssetAttributeValue",
        back_populates="canonical_asset",
        cascade="all, delete-orphan"
    )


class CanonicalAssetAttributeValue(Base, UUIDMixin):
    """Stores common, identity-level attribute values for CanonicalAsset."""
    __tablename__ = "canonical_asset_attribute_values"

    canonical_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("canonical_assets.id", ondelete="CASCADE"),
        nullable=False
    )
    attribute_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("asset_attribute_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    value_string: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_number: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    value_boolean: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    value_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    normalized_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[AttributeValueSource] = mapped_column(
        String(50),
        nullable=False,
        default=AttributeValueSource.MANUAL
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)

    # Relationships
    canonical_asset: Mapped["CanonicalAsset"] = relationship("CanonicalAsset", back_populates="attributes")
    attribute_definition: Mapped["AssetAttributeDefinition"] = relationship("AssetAttributeDefinition")


# ==================================================
# ASSET VARIANT ENUMS & MODELS
# ==================================================

class AssetVariantStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


class AssetVariant(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Represents a specific configuration/variant of an asset family (e.g. power, capacity details)."""
    __tablename__ = "asset_variants"

    asset_family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("asset_families.id", ondelete="RESTRICT"),
        nullable=False
    )
    canonical_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("canonical_assets.id", ondelete="RESTRICT"),
        nullable=True
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[AssetVariantStatus] = mapped_column(
        String(50),
        nullable=False,
        default=AssetVariantStatus.DRAFT
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    asset_family: Mapped["AssetFamily"] = relationship("AssetFamily")
    canonical_asset: Mapped[Optional["CanonicalAsset"]] = relationship("CanonicalAsset")
    attributes: Mapped[List["AssetVariantAttributeValue"]] = relationship(
        "AssetVariantAttributeValue",
        back_populates="asset_variant",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("canonical_asset_id", "code", name="uq_asset_variant_canonical_code"),
    )


class AssetVariantAttributeValue(Base, UUIDMixin):
    """Stores variant-specific technical attributes for AssetVariant."""
    __tablename__ = "asset_variant_attribute_values"

    asset_variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("asset_variants.id", ondelete="CASCADE"),
        nullable=False
    )
    attribute_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("asset_attribute_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    value_string: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_number: Mapped[Optional[float]] = mapped_column(Numeric(18, 6), nullable=True)
    value_boolean: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    value_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    normalized_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[AttributeValueSource] = mapped_column(
        String(50),
        nullable=False,
        default=AttributeValueSource.MANUAL
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)

    # Relationships
    asset_variant: Mapped["AssetVariant"] = relationship("AssetVariant", back_populates="attributes")
    attribute_definition: Mapped["AssetAttributeDefinition"] = relationship("AssetAttributeDefinition")


# ==================================================
# ALIAS & IDENTITY CANDIDATE ENUMS & MODELS
# ==================================================

class AssetAliasScope(str, enum.Enum):
    CANONICAL = "canonical"
    VARIANT = "variant"


class AssetAliasStatus(str, enum.Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class IdentityCandidateStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IGNORED = "ignored"


def normalize_alias_helper(raw: str) -> str:
    import re
    if not raw:
        return ""
    # Downcase, strip special chars, collapse spaces
    s = raw.lower()
    s = re.sub(r'[^\w\s]', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


class AssetAlias(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Maps variation names or historical catalog labels to canonical assets or variants."""
    __tablename__ = "asset_aliases"

    alias_scope: Mapped[AssetAliasScope] = mapped_column(String(50), nullable=False)
    canonical_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("canonical_assets.id", ondelete="RESTRICT"),
        nullable=True
    )
    asset_variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("asset_variants.id", ondelete="RESTRICT"),
        nullable=True
    )
    raw_alias: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[AssetAliasStatus] = mapped_column(
        String(50),
        nullable=False,
        default=AssetAliasStatus.ACTIVE
    )

    # Relationships
    canonical_asset: Mapped[Optional["CanonicalAsset"]] = relationship("CanonicalAsset")
    asset_variant: Mapped[Optional["AssetVariant"]] = relationship("AssetVariant")

    __table_args__ = (
        UniqueConstraint("normalized_alias", "canonical_asset_id", name="uq_alias_normalized_canonical"),
        UniqueConstraint("normalized_alias", "asset_variant_id", name="uq_alias_normalized_variant"),
    )


class IdentityCandidate(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Holds deterministic or AI suggested target proposals for raw project asset lines."""
    __tablename__ = "identity_candidates"

    project_asset_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_asset_lines.id", ondelete="RESTRICT"),
        nullable=False
    )
    proposed_canonical_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("canonical_assets.id", ondelete="RESTRICT"),
        nullable=True
    )
    proposed_asset_variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("asset_variants.id", ondelete="RESTRICT"),
        nullable=True
    )
    proposed_taxonomy_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("taxonomy_nodes.id", ondelete="RESTRICT"),
        nullable=True
    )
    status: Mapped[IdentityCandidateStatus] = mapped_column(
        String(50),
        nullable=False,
        default=IdentityCandidateStatus.PENDING
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    match_method: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    project_asset_line: Mapped["ProjectAssetLine"] = relationship("ProjectAssetLine")
    proposed_canonical_asset: Mapped[Optional["CanonicalAsset"]] = relationship("CanonicalAsset")
    proposed_asset_variant: Mapped[Optional["AssetVariant"]] = relationship("AssetVariant")
    proposed_taxonomy_node: Mapped[Optional["TaxonomyNode"]] = relationship("TaxonomyNode")
    similarity_scores: Mapped[List["SimilarityScore"]] = relationship(
        "SimilarityScore",
        back_populates="identity_candidate",
        cascade="all, delete-orphan"
    )


class SimilarityScore(Base, UUIDMixin):
    """Stores detailed scoring breakdowns for an IdentityCandidate."""
    __tablename__ = "similarity_scores"

    identity_candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("identity_candidates.id", ondelete="CASCADE"),
        nullable=False
    )
    component: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    metadata_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    identity_candidate: Mapped["IdentityCandidate"] = relationship("IdentityCandidate", back_populates="similarity_scores")


# ==================================================
# DUPLICATE, MERGE & REVIEW ENUMS & MODELS
# ==================================================

class DuplicateCandidateStatus(str, enum.Enum):
    PENDING = "pending"
    IGNORED = "ignored"
    RESOLVED = "resolved"


class MergeDecisionStatus(str, enum.Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class IdentityReviewStatus(str, enum.Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    SKIPPED = "skipped"


class IdentityDecisionType(str, enum.Enum):
    APPROVE_CANDIDATE = "approve_candidate"
    MERGE_ASSETS = "merge_assets"
    IGNORE_CANDIDATE = "ignore_candidate"
    CREATE_NEW = "create_new"


class DuplicateCandidate(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Holds duplicate similarity proposals between two Canonical Assets."""
    __tablename__ = "duplicate_candidates"

    source_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("canonical_assets.id", ondelete="RESTRICT"),
        nullable=False
    )
    target_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("canonical_assets.id", ondelete="RESTRICT"),
        nullable=False
    )
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    status: Mapped[DuplicateCandidateStatus] = mapped_column(
        String(50),
        nullable=False,
        default=DuplicateCandidateStatus.PENDING
    )
    metadata_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    source_asset: Mapped["CanonicalAsset"] = relationship("CanonicalAsset", foreign_keys=[source_asset_id])
    target_asset: Mapped["CanonicalAsset"] = relationship("CanonicalAsset", foreign_keys=[target_asset_id])

    __table_args__ = (
        CheckConstraint("source_asset_id <> target_asset_id", name="chk_duplicate_diff_assets"),
    )


class MergeDecision(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Auditable log of canonical asset merge resolutions."""
    __tablename__ = "merge_decisions"

    source_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("canonical_assets.id", ondelete="RESTRICT"),
        nullable=False
    )
    target_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("canonical_assets.id", ondelete="RESTRICT"),
        nullable=False
    )
    status: Mapped[MergeDecisionStatus] = mapped_column(
        String(50),
        nullable=False,
        default=MergeDecisionStatus.PROPOSED
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    configuration_flags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    executed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    source_asset: Mapped["CanonicalAsset"] = relationship("CanonicalAsset", foreign_keys=[source_asset_id])
    target_asset: Mapped["CanonicalAsset"] = relationship("CanonicalAsset", foreign_keys=[target_asset_id])
    executor: Mapped[Optional["User"]] = relationship("User")

    __table_args__ = (
        CheckConstraint("source_asset_id <> target_asset_id", name="chk_merge_diff_assets"),
    )


class IdentityReviewItem(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Proposals assigned to a human reviewer for asset line verification."""
    __tablename__ = "identity_review_items"

    project_asset_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_asset_lines.id", ondelete="RESTRICT"),
        nullable=False
    )
    identity_candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("identity_candidates.id", ondelete="RESTRICT"),
        nullable=True
    )
    review_status: Mapped[IdentityReviewStatus] = mapped_column(
        String(50),
        nullable=False,
        default=IdentityReviewStatus.PENDING
    )
    reviewer_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    project_asset_line: Mapped["ProjectAssetLine"] = relationship("ProjectAssetLine")
    identity_candidate: Mapped[Optional["IdentityCandidate"]] = relationship("IdentityCandidate")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to])
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by])


class IdentityDecisionLog(Base, UUIDMixin):
    """Append-only audit trail of identity decision approvals or merges."""
    __tablename__ = "identity_decision_logs"

    project_asset_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_asset_lines.id", ondelete="RESTRICT"),
        nullable=False
    )
    decision_type: Mapped[IdentityDecisionType] = mapped_column(String(50), nullable=False)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now()
    )
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    project_asset_line: Mapped["ProjectAssetLine"] = relationship("ProjectAssetLine")
    actor: Mapped[Optional["User"]] = relationship("User")


class EvidenceSourceType(str, enum.Enum):
    CATALOGUE = "catalogue"
    SUPPLIER = "supplier"
    INTERNET = "internet"
    MANUAL = "manual"
    AI = "ai"
    SYSTEM = "system"


class EvidenceFileStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ARCHIVED = "archived"


class EvidenceSensitivityLevel(str, enum.Enum):
    NORMAL = "normal"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


class EvidenceAccessType(str, enum.Enum):
    VIEW = "view"
    DOWNLOAD = "download"
    METADATA = "metadata"


class EvidenceSource(Base, UUIDMixin, TimestampMixin):
    """Tracks source providers or catalogue origins of evidence."""
    __tablename__ = "evidence_sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[EvidenceSourceType] = mapped_column(
        String(50),
        nullable=False,
        default=EvidenceSourceType.MANUAL
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class EvidenceFile(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Container for uploaded document files and metadata."""
    __tablename__ = "evidence_files"

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    sensitivity_level: Mapped[EvidenceSensitivityLevel] = mapped_column(
        String(50),
        nullable=False,
        default=EvidenceSensitivityLevel.NORMAL
    )
    status: Mapped[EvidenceFileStatus] = mapped_column(
        String(50),
        nullable=False,
        default=EvidenceFileStatus.ACTIVE
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )

    uploader: Mapped["User"] = relationship("User")


class EvidenceLink(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Associates an EvidenceFile with a target domain entity (soft-deletable)."""
    __tablename__ = "evidence_links"

    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id", ondelete="RESTRICT"),
        nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(128), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    delete_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )

    evidence_file: Mapped["EvidenceFile"] = relationship("EvidenceFile")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    deleter: Mapped[Optional["User"]] = relationship("User", foreign_keys=[deleted_by])

    __table_args__ = (
        Index("idx_evidence_link_target", "target_type", "target_id"),
    )


class EvidenceAccessLog(Base, UUIDMixin):
    """Append-only audit log tracking accesses to sensitive/restricted evidence files."""
    __tablename__ = "evidence_access_logs"

    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id", ondelete="RESTRICT"),
        nullable=False
    )
    accessed_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    access_type: Mapped[EvidenceAccessType] = mapped_column(String(50), nullable=False)
    access_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now()
    )

    evidence_file: Mapped["EvidenceFile"] = relationship("EvidenceFile")
    accessor: Mapped["User"] = relationship("User")


class EvidenceExtractionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class EvidenceReviewDecisionStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class SupplierQuoteEvidence(Base, UUIDMixin, TimestampMixin):
    """Specialized context details for vendor/supplier quotes."""
    __tablename__ = "supplier_quote_evidences"

    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id", ondelete="RESTRICT"),
        nullable=False
    )
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quote_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    quote_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    total_amount: Mapped[Optional[float]] = mapped_column(nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    evidence_file: Mapped["EvidenceFile"] = relationship("EvidenceFile")


class CatalogueEvidence(Base, UUIDMixin, TimestampMixin):
    """Specialized details for product catalogues/pamphlets."""
    __tablename__ = "catalogue_evidences"

    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id", ondelete="RESTRICT"),
        nullable=False
    )
    manufacturer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    catalogue_name: Mapped[str] = mapped_column(String(255), nullable=False)
    page_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    product_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    evidence_file: Mapped["EvidenceFile"] = relationship("EvidenceFile")


class InternetEvidence(Base, UUIDMixin, TimestampMixin):
    """Captured web links/pages serving as pricing or specification reference."""
    __tablename__ = "internet_evidences"

    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id", ondelete="RESTRICT"),
        nullable=False
    )
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )
    site_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    evidence_file: Mapped["EvidenceFile"] = relationship("EvidenceFile")


class ImageEvidence(Base, UUIDMixin, TimestampMixin):
    """Photo and imaging metadata context."""
    __tablename__ = "image_evidences"

    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id", ondelete="RESTRICT"),
        nullable=False
    )
    resolution: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    captured_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    camera_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    evidence_file: Mapped["EvidenceFile"] = relationship("EvidenceFile")


class EmailEvidence(Base, UUIDMixin, TimestampMixin):
    """Email correspondence records context."""
    __tablename__ = "email_evidences"

    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id", ondelete="RESTRICT"),
        nullable=False
    )
    sender: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    evidence_file: Mapped["EvidenceFile"] = relationship("EvidenceFile")


class EvidenceExtractionResult(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Holds parsed results generated by automated scanning/extraction routines."""
    __tablename__ = "evidence_extraction_results"

    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id", ondelete="RESTRICT"),
        nullable=False
    )
    status: Mapped[EvidenceExtractionStatus] = mapped_column(
        String(50),
        nullable=False,
        default=EvidenceExtractionStatus.PENDING
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    extracted_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    evidence_file: Mapped["EvidenceFile"] = relationship("EvidenceFile")


class EvidenceReviewDecision(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Records audit decisions concerning parses and evidence authenticity reviews."""
    __tablename__ = "evidence_review_decisions"

    evidence_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_files.id", ondelete="RESTRICT"),
        nullable=False
    )
    status: Mapped[EvidenceReviewDecisionStatus] = mapped_column(
        String(50),
        nullable=False,
        default=EvidenceReviewDecisionStatus.PENDING
    )
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    evidence_file: Mapped["EvidenceFile"] = relationship("EvidenceFile")
    reviewer: Mapped[Optional["User"]] = relationship("User")


class TechnicalSpecificationVersionStatus(str, enum.Enum):
    DRAFT = "draft"
    CANDIDATE = "candidate"
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class KnowledgeVersionStatus(str, enum.Enum):
    DRAFT = "draft"
    CANDIDATE = "candidate"
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class KnowledgeType(str, enum.Enum):
    TECHNICAL_SPEC = "technical_spec"
    QUOTE_BATCH = "quote_batch"
    APPRAISED_PRICE = "appraised_price"


class TechnicalSpecification(Base, UUIDMixin, TimestampMixin):
    """Catalog folder mapping technical specifications to canonical assets or variants."""
    __tablename__ = "technical_specifications"

    canonical_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("canonical_assets.id", ondelete="RESTRICT"),
        nullable=True
    )
    asset_variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("asset_variants.id", ondelete="RESTRICT"),
        nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )

    canonical_asset: Mapped[Optional["CanonicalAsset"]] = relationship("CanonicalAsset")
    asset_variant: Mapped[Optional["AssetVariant"]] = relationship("AssetVariant")
    creator: Mapped["User"] = relationship("User")


class TechnicalSpecificationVersion(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Stores the concrete technical specifications payload attributes and lineage source links."""
    __tablename__ = "technical_specification_versions"

    technical_specification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("technical_specifications.id", ondelete="RESTRICT"),
        nullable=False
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    attribute_values: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source_evidence_ids: Mapped[list[uuid.UUID]] = mapped_column(JSON, nullable=False, default=list)
    source_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=True
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    status: Mapped[TechnicalSpecificationVersionStatus] = mapped_column(
        String(50),
        nullable=False,
        default=TechnicalSpecificationVersionStatus.DRAFT
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    technical_specification: Mapped["TechnicalSpecification"] = relationship("TechnicalSpecification")
    source_project: Mapped[Optional["Project"]] = relationship("Project")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])

    __table_args__ = (
        UniqueConstraint("technical_specification_id", "version_number", name="uq_tech_spec_version_num"),
    )


class KnowledgeVersion(Base, UUIDMixin, TimestampMixin):
    """Generic indexing registry mapping active version indicators across catalog entities."""
    __tablename__ = "knowledge_versions"

    knowledge_type: Mapped[KnowledgeType] = mapped_column(String(50), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    concrete_version_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    version_number: Mapped[int] = mapped_column(nullable=False)
    canonical_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("canonical_assets.id", ondelete="RESTRICT"),
        nullable=True
    )
    asset_variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("asset_variants.id", ondelete="RESTRICT"),
        nullable=True
    )
    source_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=True
    )
    source_evidence_ids: Mapped[list[uuid.UUID]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[KnowledgeVersionStatus] = mapped_column(
        String(50),
        nullable=False,
        default=KnowledgeVersionStatus.DRAFT
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)

    canonical_asset: Mapped[Optional["CanonicalAsset"]] = relationship("CanonicalAsset")
    asset_variant: Mapped[Optional["AssetVariant"]] = relationship("AssetVariant")
    source_project: Mapped[Optional["Project"]] = relationship("Project")

    __table_args__ = (
        Index("idx_knowledge_version_active", "canonical_asset_id", "asset_variant_id", "knowledge_type", "status"),
    )


class KnowledgeLineage(Base, UUIDMixin):
    """Append-only audit trail logging transitions, imports, and approval context events."""
    __tablename__ = "knowledge_lineage"

    knowledge_type: Mapped[KnowledgeType] = mapped_column(String(50), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    concrete_version_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=True
    )
    source_evidence_ids: Mapped[list[uuid.UUID]] = mapped_column(JSON, nullable=False, default=list)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now()
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    source_project: Mapped[Optional["Project"]] = relationship("Project")
    actor: Mapped[Optional["User"]] = relationship("User")


class QuoteBatchStatus(str, enum.Enum):
    DRAFT = "draft"
    CANDIDATE = "candidate"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class QuoteLineStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    REJECTED = "rejected"


class QuoteBatch(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Aggregation folder for vendor/market pricing quotes relating to canonical assets or variants."""
    __tablename__ = "quote_batches"

    canonical_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("canonical_assets.id", ondelete="RESTRICT"),
        nullable=True
    )
    asset_variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("asset_variants.id", ondelete="RESTRICT"),
        nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    status: Mapped[QuoteBatchStatus] = mapped_column(
        String(50),
        nullable=False,
        default=QuoteBatchStatus.DRAFT
    )
    revision_number: Mapped[int] = mapped_column(nullable=False, default=1)
    previous_quote_batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("quote_batches.id", ondelete="RESTRICT"),
        nullable=True
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    override_blocking_conflict_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    canonical_asset: Mapped[Optional["CanonicalAsset"]] = relationship("CanonicalAsset")
    asset_variant: Mapped[Optional["AssetVariant"]] = relationship("AssetVariant")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])
    previous_quote_batch: Mapped[Optional["QuoteBatch"]] = relationship("QuoteBatch", remote_side="QuoteBatch.id")
    quote_lines: Mapped[list["QuoteLine"]] = relationship("QuoteLine", back_populates="quote_batch")


class QuoteLine(Base, UUIDMixin, TimestampMixin):
    """Raw pricing detail entries extracted from evidence files or catalog sources."""
    __tablename__ = "quote_lines"

    quote_batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quote_batches.id", ondelete="RESTRICT"),
        nullable=False
    )
    evidence_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("evidence_files.id", ondelete="RESTRICT"),
        nullable=True
    )
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quoted_unit_price: Mapped[float] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[Optional[float]] = mapped_column(nullable=True)
    unit_of_measure: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quote_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    quote_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    status: Mapped[QuoteLineStatus] = mapped_column(
        String(50),
        nullable=False,
        default=QuoteLineStatus.DRAFT
    )

    quote_batch: Mapped["QuoteBatch"] = relationship("QuoteBatch", back_populates="quote_lines")
    evidence_file: Mapped[Optional["EvidenceFile"]] = relationship("EvidenceFile")


class AppraisedPriceDecisionStatus(str, enum.Enum):
    DRAFT = "draft"
    CANDIDATE = "candidate"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class AppraisedPriceDecision(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Professional catalog price decision standard and appraiser rationale."""
    __tablename__ = "appraised_price_decisions"

    canonical_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("canonical_assets.id", ondelete="RESTRICT"),
        nullable=True
    )
    asset_variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("asset_variants.id", ondelete="RESTRICT"),
        nullable=True
    )
    quote_batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("quote_batches.id", ondelete="RESTRICT"),
        nullable=True
    )
    final_unit_price: Mapped[float] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AppraisedPriceDecisionStatus] = mapped_column(
        String(50),
        nullable=False,
        default=AppraisedPriceDecisionStatus.DRAFT
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    canonical_asset: Mapped[Optional["CanonicalAsset"]] = relationship("CanonicalAsset")
    asset_variant: Mapped[Optional["AssetVariant"]] = relationship("AssetVariant")
    quote_batch: Mapped[Optional["QuoteBatch"]] = relationship("QuoteBatch")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])


class KnowledgeQueueItemStatus(str, enum.Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    COMPLETED = "completed"
    REJECTED = "rejected"


class KnowledgeConflictStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class KnowledgeConflictSeverity(str, enum.Enum):
    WARNING = "warning"
    BLOCKING = "blocking"


class KnowledgeQueueItem(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Holds candidate suggestions and extraction queue records before approval workflows."""
    __tablename__ = "knowledge_queue_items"

    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    status: Mapped[KnowledgeQueueItemStatus] = mapped_column(
        String(50),
        nullable=False,
        default=KnowledgeQueueItemStatus.PENDING
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    auto_rejected: Mapped[bool] = mapped_column(nullable=False, default=False)
    auto_reject_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    claimed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )
    claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    is_manual: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_pinned: Mapped[bool] = mapped_column(nullable=False, default=False)

    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewer_id])
    claimant: Mapped[Optional["User"]] = relationship("User", foreign_keys=[claimed_by])


class KnowledgeConfidence(Base, UUIDMixin):
    """Logs calculated metrics and metadata sources backing standard confidence scores."""
    __tablename__ = "knowledge_confidence"

    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    confidence_score: Mapped[float] = mapped_column(nullable=False)
    confidence_source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now()
    )


class KnowledgeConflict(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Tracks catalog price deviations, attribute misfits, and audit resolution logs."""
    __tablename__ = "knowledge_conflicts"

    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    conflict_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[KnowledgeConflictSeverity] = mapped_column(
        String(50),
        nullable=False,
        default=KnowledgeConflictSeverity.WARNING
    )
    status: Mapped[KnowledgeConflictStatus] = mapped_column(
        String(50),
        nullable=False,
        default=KnowledgeConflictStatus.OPEN
    )
    calculated_value: Mapped[float] = mapped_column(nullable=False)
    threshold_value: Mapped[float] = mapped_column(nullable=False)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    resolver: Mapped[Optional["User"]] = relationship("User")


class WorkflowDefinitionStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class WorkflowDefinition(Base, UUIDMixin, TimestampMixin):
    """Configuration definition specifying states and lifecycle rules."""
    __tablename__ = "workflow_definitions"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    status: Mapped[WorkflowDefinitionStatus] = mapped_column(
        String(50),
        nullable=False,
        default=WorkflowDefinitionStatus.DRAFT
    )

    transitions: Mapped[List["WorkflowTransition"]] = relationship(
        "WorkflowTransition",
        back_populates="workflow_definition"
    )


class WorkflowInstanceStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WorkflowInstance(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Running execution tracker of a workflow lifecycle target."""
    __tablename__ = "workflow_instances"

    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_definitions.id", ondelete="RESTRICT"),
        nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    current_state: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[WorkflowInstanceStatus] = mapped_column(
        String(50),
        nullable=False,
        default=WorkflowInstanceStatus.ACTIVE
    )

    workflow_definition: Mapped["WorkflowDefinition"] = relationship("WorkflowDefinition")
    tasks: Mapped[List["WorkflowTask"]] = relationship("WorkflowTask", back_populates="workflow_instance")


class WorkflowTransition(Base, UUIDMixin):
    """Authorized paths linking lifecycle states together."""
    __tablename__ = "workflow_transitions"

    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_definitions.id", ondelete="RESTRICT"),
        nullable=False
    )
    from_state: Mapped[str] = mapped_column(String(100), nullable=False)
    to_state: Mapped[str] = mapped_column(String(100), nullable=False)
    command_name: Mapped[str] = mapped_column(String(100), nullable=False)
    required_permission: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    guard_expression: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    workflow_definition: Mapped["WorkflowDefinition"] = relationship(
        "WorkflowDefinition",
        back_populates="transitions"
    )


class WorkflowTaskStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WorkflowTaskPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class WorkflowTask(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    """Curation task checklist record associated with workflow instances."""
    __tablename__ = "workflow_tasks"

    workflow_instance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_instances.id", ondelete="RESTRICT"),
        nullable=False
    )
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[WorkflowTaskStatus] = mapped_column(
        String(50),
        nullable=False,
        default=WorkflowTaskStatus.OPEN
    )
    priority: Mapped[WorkflowTaskPriority] = mapped_column(
        String(50),
        nullable=False,
        default=WorkflowTaskPriority.NORMAL
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )
    due_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    workflow_instance: Mapped["WorkflowInstance"] = relationship(
        "WorkflowInstance",
        back_populates="tasks"
    )
    assignee: Mapped[Optional["User"]] = relationship("User")


class ReviewDecisionChoice(str, enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"
    REQUEST_CHANGES = "request_changes"
    OVERRIDE = "override"


class ReviewDecision(Base, UUIDMixin):
    """Append-only audit record detailing human curator review gates."""
    __tablename__ = "review_decisions"

    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    decision: Mapped[ReviewDecisionChoice] = mapped_column(
        String(50),
        nullable=False
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now()
    )
    evidence_ids: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    previous_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    new_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    decider: Mapped["User"] = relationship("User")


class ApprovalGateStatus(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"


class ApprovalGate(Base, UUIDMixin):
    """Consolidated gates evaluating checklist status constraints."""
    __tablename__ = "approval_gates"

    gate_code: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    gate_status: Mapped[ApprovalGateStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ApprovalGateStatus.NOT_APPLICABLE
    )
    blocking_issue_count: Mapped[int] = mapped_column(nullable=False, default=0)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now()
    )


class ValidationRuleCategory(str, enum.Enum):
    IDENTITY = "identity"
    TAXONOMY = "taxonomy"
    TECHNICAL_SPEC = "technical_spec"
    EVIDENCE = "evidence"
    QUOTE = "quote"


class ValidationRule(Base, UUIDMixin):
    """Declarative check validation constraints definition library."""
    __tablename__ = "validation_rules"

    rule_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    category: Mapped[ValidationRuleCategory] = mapped_column(
        String(50),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_blocking: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)


class ValidationIssueSeverity(str, enum.Enum):
    WARNING = "warning"
    BLOCKING = "blocking"


class ValidationIssueStatus(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class ValidationIssue(Base, UUIDMixin, OptimisticLockingMixin):
    """Anomalies flagged by rule checker running against assets or data batches."""
    __tablename__ = "validation_issues"

    validation_rule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("validation_rules.id", ondelete="RESTRICT"),
        nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    severity: Mapped[ValidationIssueSeverity] = mapped_column(
        String(50),
        nullable=False,
        default=ValidationIssueSeverity.WARNING
    )
    status: Mapped[ValidationIssueStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ValidationIssueStatus.OPEN
    )
    issue_message: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now()
    )
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    validation_rule: Mapped["ValidationRule"] = relationship("ValidationRule")
    resolver: Mapped[Optional["User"]] = relationship("User")


class UserActionLog(Base, UUIDMixin):
    """Append-only timeline events detailing human curation workspace history."""
    __tablename__ = "user_action_logs"

    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    action_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now()
    )

    user: Mapped["User"] = relationship("User")
















