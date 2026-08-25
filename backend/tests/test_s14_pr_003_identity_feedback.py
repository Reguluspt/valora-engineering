"""S14-PR-003 unit tests for Identity Decision and Feedback Contract."""
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
import app.modules.excel_import.models  # noqa: F401
from app.modules.excel_import.models import RawAssetObservation
from app.modules.taxonomy_asset_identity.application.identity_decision_service import confirm_identity_decision


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_committed_human_decision_generates_positive_feedback(db_session: Session):
    """Verify that a confirmed human decision generates positive learning feedback (ADR 0031 §6)."""
    org_id = uuid.uuid4()
    project_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()
    canonical_id = uuid.uuid4()

    obs = RawAssetObservation(
        id=uuid.uuid4(),
        organization_id=org_id,
        import_batch_id=batch_id,
        source_artifact_id=artifact_id,
        structure_snapshot_id=snapshot_id,
        row_index=1,
        sheet_name="Sheet1",
        raw_asset_name="Tủ điện hạ thế 400A",
    )
    db_session.add(obs)
    db_session.commit()

    decision, feedback = confirm_identity_decision(
        db_session,
        actor_id=actor_id,
        org_id=org_id,
        project_id=project_id,
        raw_observation_id=obs.id,
        decision_type="accepted",
        chosen_canonical_asset_id=canonical_id,
        create_contextual_alias=True,
        command_id=uuid.uuid4(),
    )

    assert decision.decision_type == "accepted"
    assert decision.chosen_canonical_asset_id == canonical_id
    assert feedback is not None
    assert feedback.event_type == "positive_match"
    assert feedback.raw_wording == "Tủ điện hạ thế 400A"


def test_deferred_decision_does_not_generate_feedback(db_session: Session):
    """Verify that deferred decisions do NOT create learning feedback events."""
    org_id = uuid.uuid4()
    project_id = uuid.uuid4()
    actor_id = uuid.uuid4()

    obs = RawAssetObservation(
        id=uuid.uuid4(),
        organization_id=org_id,
        import_batch_id=uuid.uuid4(),
        source_artifact_id=uuid.uuid4(),
        structure_snapshot_id=uuid.uuid4(),
        row_index=2,
        sheet_name="Sheet1",
        raw_asset_name="Cáp điện Cadivi 3x25",
    )
    db_session.add(obs)
    db_session.commit()

    decision, feedback = confirm_identity_decision(
        db_session,
        actor_id=actor_id,
        org_id=org_id,
        project_id=project_id,
        raw_observation_id=obs.id,
        decision_type="deferred",
        command_id=uuid.uuid4(),
    )

    assert decision.decision_type == "deferred"
    assert feedback is None
