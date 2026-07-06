import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, declared_attr


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class UUIDMixin:
    """Mixin to add a UUID primary key to a model."""
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        sort_order=-100
    )


class TimestampMixin:
    """Mixin to add timezone-aware created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        sort_order=90
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
        sort_order=91
    )


class OptimisticLockingMixin:
    """Mixin to add a row_version column for SQLAlchemy optimistic locking."""
    row_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        sort_order=100
    )

    @declared_attr
    def __mapper_args__(cls):
        return {"version_id_col": cls.row_version}
