import enum
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, ForeignKey, UniqueConstraint, Index, Boolean, DateTime, JSON, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, UUIDMixin, TimestampMixin
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
