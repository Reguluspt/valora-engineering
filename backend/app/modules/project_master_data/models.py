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




