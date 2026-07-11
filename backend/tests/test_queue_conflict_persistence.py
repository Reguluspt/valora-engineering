import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserStatus,
    KnowledgeQueueItem,
    KnowledgeQueueItemStatus,
    KnowledgeConfidence,
    KnowledgeConflict,
    KnowledgeConflictStatus,
    KnowledgeConflictSeverity,
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()


def test_table_registration() -> None:
    tables = Base.metadata.tables
    assert "knowledge_queue_items" in tables
    assert "knowledge_confidence" in tables
    assert "knowledge_conflicts" in tables


@pytest.fixture
def setup_seed_data(db_session: Session):
    org = OrganizationProfile(
        legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE
    )
    db_session.add(org)
    db_session.commit()

    user = User(
        organization_id=org.id,
        email="auditor@test.com",
        full_name="Auditor User",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()

    return {"user_id": user.id}


def test_knowledge_queue_item_persistence(db_session: Session, setup_seed_data) -> None:
    # 1. Standard candidate queue item
    target_uuid = uuid.uuid4()
    item = KnowledgeQueueItem(
        target_type="technical_specification_version",
        target_id=target_uuid,
        status=KnowledgeQueueItemStatus.PENDING,
        confidence_score=0.8800,
        is_manual=False,
        is_pinned=False,
    )
    db_session.add(item)
    db_session.commit()

    db_session.expire_all()
    q_item = db_session.query(KnowledgeQueueItem).filter(KnowledgeQueueItem.id == item.id).one()
    assert q_item.target_type == "technical_specification_version"
    assert q_item.target_id == target_uuid
    assert q_item.confidence_score == 0.8800
    assert q_item.auto_rejected is False


def should_auto_reject(item: KnowledgeQueueItem, threshold: float = 0.50) -> bool:
    """Helper representing the auto-reject rules of ADR 0023."""
    if item.is_manual or item.is_pinned:
        return False
    if item.confidence_score is not None and item.confidence_score < threshold:
        return True
    return False


def test_knowledge_queue_auto_reject_logic(db_session: Session, setup_seed_data) -> None:
    # 1. Low confidence candidate (should auto-reject)
    item_low = KnowledgeQueueItem(
        target_type="quote_batch",
        target_id=uuid.uuid4(),
        status=KnowledgeQueueItemStatus.PENDING,
        confidence_score=0.4500,
        is_manual=False,
        is_pinned=False,
    )
    assert should_auto_reject(item_low) is True

    # Perform metadata rejection transition
    item_low.status = KnowledgeQueueItemStatus.REJECTED
    item_low.auto_rejected = True
    item_low.auto_reject_reason = "auto_rejected_low_confidence"
    item_low.reviewed_at = datetime.now(timezone.utc)
    db_session.add(item_low)
    db_session.commit()

    # 2. Pinned low confidence candidate (should NOT auto-reject)
    item_pinned = KnowledgeQueueItem(
        target_type="quote_batch",
        target_id=uuid.uuid4(),
        status=KnowledgeQueueItemStatus.PENDING,
        confidence_score=0.4500,
        is_manual=False,
        is_pinned=True,
    )
    assert should_auto_reject(item_pinned) is False


def test_knowledge_confidence_persistence(db_session: Session) -> None:
    target_uuid = uuid.uuid4()
    conf = KnowledgeConfidence(
        target_type="evidence_extraction_result",
        target_id=target_uuid,
        confidence_score=0.9250,
        confidence_source="ai_extraction",
        source_metadata={"model_name": "ValoraExtractor-v2", "tokens_processed": 540},
    )
    db_session.add(conf)
    db_session.commit()

    db_session.expire_all()
    q_conf = db_session.query(KnowledgeConfidence).filter(KnowledgeConfidence.id == conf.id).one()
    assert q_conf.target_id == target_uuid
    assert q_conf.confidence_score == 0.9250
    assert q_conf.confidence_source == "ai_extraction"
    assert q_conf.source_metadata == {"model_name": "ValoraExtractor-v2", "tokens_processed": 540}


def calculate_quote_conflict(prices: list[float]) -> tuple[float, float, str]:
    """Helper representing the deterministic quote conflict formulas from ADR 0019."""
    if len(prices) < 2:
        return 0.0, 0.0, "warning"
    min_price = min(prices)
    max_price = max(prices)

    if min_price == 0.0:
        # Undefined percent spread, triggers blocking manual review
        return 999.0, 999.0, "blocking"

    spread_percent = ((max_price - min_price) / min_price) * 100

    # Calculate median deviation
    sorted_prices = sorted(prices)
    n = len(prices)
    if n % 2 == 1:
        median_price = sorted_prices[n // 2]
    else:
        median_price = (sorted_prices[n // 2 - 1] + sorted_prices[n // 2]) / 2.0

    max_median_deviation_percent = max(abs(p - median_price) / median_price for p in prices) * 100

    severity = "warning"
    if spread_percent >= 35.0 or max_median_deviation_percent >= 35.0:
        severity = "blocking"

    return spread_percent, max_median_deviation_percent, severity


def test_knowledge_conflict_formula_and_persistence(db_session: Session, setup_seed_data) -> None:
    # 1. Evaluate normal spread (e.g. 980k, 1M, 1.05M) -> less than 20%
    spread, deviation, severity = calculate_quote_conflict([980000, 1000000, 1050000])
    assert spread < 20.0
    assert severity == "warning"

    # 2. Evaluate high spread (e.g. 980k, 1M, 1.35M) -> triggers blocking conflict (spread > 35%)
    spread, deviation, severity = calculate_quote_conflict([980000, 1000000, 1350000])
    assert spread >= 35.0
    assert severity == "blocking"

    # Persist the calculated conflict log
    target_uuid = uuid.uuid4()
    conflict = KnowledgeConflict(
        target_type="quote_batch",
        target_id=target_uuid,
        conflict_type="quote_price_variance",
        severity=KnowledgeConflictSeverity.BLOCKING
        if severity == "blocking"
        else KnowledgeConflictSeverity.WARNING,
        status=KnowledgeConflictStatus.OPEN,
        calculated_value=spread,
        threshold_value=35.0,
    )
    db_session.add(conflict)
    db_session.commit()

    db_session.expire_all()
    q_conflict = (
        db_session.query(KnowledgeConflict).filter(KnowledgeConflict.id == conflict.id).one()
    )
    assert q_conflict.target_id == target_uuid
    assert q_conflict.severity == KnowledgeConflictSeverity.BLOCKING
    assert q_conflict.calculated_value == spread
    assert q_conflict.status == KnowledgeConflictStatus.OPEN


def test_migration_chain() -> None:
    import importlib.util
    import os

    filepath = os.path.join(
        os.path.dirname(__file__),
        "../alembic/versions/a87a9b6da99e_create_queue_conflict_tables.py",
    )
    spec = importlib.util.spec_from_file_location("migration_a87a9b6da99e", filepath)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "a87a9b6da99e"
    assert migration.down_revision == "a87a9b6da99d"
