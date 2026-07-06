import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import Base
from app.modules.project_master_data.models import (
    Country,
    Province,
    Unit,
    Currency,
    ReferenceStatus,
    UnitType,
)


@pytest.fixture
def db_session() -> Session:
    """Fixture that initializes a SQLite in-memory database and provides a session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_country_uniqueness(db_session: Session) -> None:
    """Verifies Country ISO code uniqueness constraints."""
    country1 = Country(
        iso2="VN",
        iso3="VNM",
        name_vi="Việt Nam",
        status=ReferenceStatus.ACTIVE,
    )
    db_session.add(country1)
    db_session.commit()

    # 1. Duplicate ISO2 (should fail)
    country2 = Country(
        iso2="VN",
        iso3="OTH",
        name_vi="Duplicate ISO2",
        status=ReferenceStatus.ACTIVE,
    )
    db_session.add(country2)
    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()

    # 2. Duplicate ISO3 (should fail)
    country3 = Country(
        iso2="OT",
        iso3="VNM",
        name_vi="Duplicate ISO3",
        status=ReferenceStatus.ACTIVE,
    )
    db_session.add(country3)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_country_province_relationship(db_session: Session) -> None:
    """Verifies relationships between Country and Province."""
    country = Country(
        iso2="VN",
        iso3="VNM",
        name_vi="Việt Nam",
        status=ReferenceStatus.ACTIVE,
    )
    db_session.add(country)
    db_session.commit()

    province1 = Province(
        country_id=country.id,
        name="Gia Lai",
        code="GL",
        status=ReferenceStatus.ACTIVE,
    )
    province2 = Province(
        country_id=country.id,
        name="Kon Tum",
        code="KT",
        status=ReferenceStatus.ACTIVE,
    )
    db_session.add_all([province1, province2])
    db_session.commit()

    db_session.refresh(country)
    assert len(country.provinces) == 2
    assert {p.name for p in country.provinces} == {"Gia Lai", "Kon Tum"}
    assert province1.country.name_vi == "Việt Nam"


def test_unit_uniqueness_and_type(db_session: Session) -> None:
    """Verifies Unit code uniqueness and unit_type configuration."""
    unit1 = Unit(
        code="cai",
        display_name="Cái",
        symbol="cái",
        unit_type=UnitType.QUANTITY,
        status=ReferenceStatus.ACTIVE,
    )
    db_session.add(unit1)
    db_session.commit()

    # 1. Duplicate Unit Code (should fail)
    unit2 = Unit(
        code="cai",
        display_name="Duplicate Cái",
        status=ReferenceStatus.ACTIVE,
    )
    db_session.add(unit2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_currency_uniqueness_and_decimals(db_session: Session) -> None:
    """Verifies Currency code uniqueness and decimal configuration."""
    currency1 = Currency(
        code="VND",
        display_name="Việt Nam Đồng",
        symbol="₫",
        decimal_places=0,
        status=ReferenceStatus.ACTIVE,
    )
    db_session.add(currency1)
    db_session.commit()

    # 1. Duplicate Currency Code (should fail)
    currency2 = Currency(
        code="VND",
        display_name="Duplicate VND",
        decimal_places=2,
        status=ReferenceStatus.ACTIVE,
    )
    db_session.add(currency2)
    with pytest.raises(IntegrityError):
        db_session.commit()
