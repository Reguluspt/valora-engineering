import uuid
from datetime import timezone
from sqlalchemy import String, create_engine
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.core.config import get_settings
from app.db import Base, get_db
from app.db.mixins import UUIDMixin, TimestampMixin, OptimisticLockingMixin


def test_settings_database_url() -> None:
    """Verifies that Settings constructs a correct PostgreSQL psycopg URL."""
    settings = get_settings()
    assert "postgresql+psycopg://" in settings.database_url
    assert settings.postgres_user in settings.database_url
    assert settings.postgres_db in settings.database_url
    assert settings.postgres_password in settings.database_url
    assert str(settings.postgres_port) in settings.database_url


# Create a test model inheriting from Base and all mixins to verify column mappings
class DummyModel(Base, UUIDMixin, TimestampMixin, OptimisticLockingMixin):
    __tablename__ = "dummy_model"
    name: Mapped[str] = mapped_column(String(50), nullable=False)


def test_mixins_structure() -> None:
    """Uses SQLite in-memory to verify declarative mapping, default generation, and locking."""
    # 1. Assert timezone-aware UTC default generator works directly
    from app.db.mixins import utc_now

    now = utc_now()
    assert now.tzinfo == timezone.utc

    # 2. Assert column types have timezone=True configured
    from sqlalchemy import DateTime

    created_at_col = DummyModel.__table__.c.created_at
    updated_at_col = DummyModel.__table__.c.updated_at
    assert isinstance(created_at_col.type, DateTime)
    assert created_at_col.type.timezone is True
    assert isinstance(updated_at_col.type, DateTime)
    assert updated_at_col.type.timezone is True

    # 3. Assert optimistic locking configuration is wired on the mapper
    assert DummyModel.__mapper__.version_id_col == DummyModel.__table__.c.row_version

    # 4. Use SQLite to check ID default and optimistic locking update behavior
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    try:
        with Session(bind=engine) as session:
            dummy = DummyModel(name="test_record")
            session.add(dummy)
            session.commit()

            assert isinstance(dummy.id, uuid.UUID)
            assert dummy.row_version == 1

            dummy.name = "updated_record"
            session.commit()

            assert dummy.name == "updated_record"
            assert dummy.row_version == 2
    finally:
        Base.metadata.drop_all(bind=engine)


def test_get_db_yields_session() -> None:
    """Verifies that the get_db generator yields a Session object and closes properly."""
    generator = get_db()
    db = next(generator)
    try:
        assert isinstance(db, Session)
    finally:
        # Complete generator to trigger close
        try:
            next(generator)
        except StopIteration:
            pass
