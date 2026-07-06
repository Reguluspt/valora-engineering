import enum
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, ForeignKey, UniqueConstraint, Index, Boolean, DateTime, JSON, text, Numeric
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


