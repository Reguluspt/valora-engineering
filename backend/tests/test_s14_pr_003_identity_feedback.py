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
    assert feedback.target_type == "CanonicalAsset"
    assert feedback.target_id == canonical_id


def test_corrected_human_decision_generates_positive_feedback(db_session: Session):
    """Verify that a corrected human decision generates positive learning feedback and contextual alias."""
    org_id = uuid.uuid4()
    project_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    variant_id = uuid.uuid4()

    obs = RawAssetObservation(
        id=uuid.uuid4(),
        organization_id=org_id,
        import_batch_id=uuid.uuid4(),
        source_artifact_id=uuid.uuid4(),
        structure_snapshot_id=uuid.uuid4(),
        row_index=3,
        sheet_name="Sheet1",
        raw_asset_name="Máy biến áp 1000kVA",
    )
    db_session.add(obs)
    db_session.commit()

    decision, feedback = confirm_identity_decision(
        db_session,
        actor_id=actor_id,
        org_id=org_id,
        project_id=project_id,
        raw_observation_id=obs.id,
        decision_type="corrected",
        chosen_asset_variant_id=variant_id,
        create_contextual_alias=True,
        command_id=uuid.uuid4(),
    )

    assert decision.decision_type == "corrected"
    assert decision.chosen_asset_variant_id == variant_id
    assert feedback is not None
    assert feedback.event_type == "positive_match"
    assert feedback.target_type == "AssetVariant"
    assert feedback.target_id == variant_id


def test_rejected_human_decision_generates_negative_feedback(db_session: Session):
    """Verify that a rejected human decision generates negative learning feedback with rejection reason."""
    org_id = uuid.uuid4()
    project_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    canonical_id = uuid.uuid4()

    obs = RawAssetObservation(
        id=uuid.uuid4(),
        organization_id=org_id,
        import_batch_id=uuid.uuid4(),
        source_artifact_id=uuid.uuid4(),
        structure_snapshot_id=uuid.uuid4(),
        row_index=4,
        sheet_name="Sheet1",
        raw_asset_name="Tủ điều khiển PLC S7-1200",
    )
    db_session.add(obs)
    db_session.commit()

    decision, feedback = confirm_identity_decision(
        db_session,
        actor_id=actor_id,
        org_id=org_id,
        project_id=project_id,
        raw_observation_id=obs.id,
        decision_type="rejected",
        chosen_canonical_asset_id=canonical_id,
        rejection_reason="Không đúng chủng loại thiết bị trong hệ thống",
        command_id=uuid.uuid4(),
    )

    assert decision.decision_type == "rejected"
    assert decision.rejection_reason == "Không đúng chủng loại thiết bị trong hệ thống"
    assert feedback is not None
    assert feedback.event_type == "negative_match"
    assert feedback.feedback_metadata == {"rejection_reason": "Không đúng chủng loại thiết bị trong hệ thống"}


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


def test_command_idempotency(db_session: Session):
    """Verify idempotency: re-executing command_id returns existing decision and avoids duplicate creation."""
    org_id = uuid.uuid4()
    project_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    cmd_id = uuid.uuid4()
    canonical_id = uuid.uuid4()

    obs = RawAssetObservation(
        id=uuid.uuid4(),
        organization_id=org_id,
        import_batch_id=uuid.uuid4(),
        source_artifact_id=uuid.uuid4(),
        structure_snapshot_id=uuid.uuid4(),
        row_index=5,
        sheet_name="Sheet1",
        raw_asset_name="Đầu báo khói Hochiki",
    )
    db_session.add(obs)
    db_session.commit()

    dec1, fb1 = confirm_identity_decision(
        db_session,
        actor_id=actor_id,
        org_id=org_id,
        project_id=project_id,
        raw_observation_id=obs.id,
        decision_type="accepted",
        chosen_canonical_asset_id=canonical_id,
        command_id=cmd_id,
    )

    dec2, fb2 = confirm_identity_decision(
        db_session,
        actor_id=actor_id,
        org_id=org_id,
        project_id=project_id,
        raw_observation_id=obs.id,
        decision_type="accepted",
        chosen_canonical_asset_id=canonical_id,
        command_id=cmd_id,
    )

    assert dec1.id == dec2.id
    assert fb2 is None


def test_invalid_decision_type_raises_http_400(db_session: Session):
    """Verify that unsupported decision types raise 400 Bad Request."""
    from fastapi import HTTPException
    org_id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc_info:
        confirm_identity_decision(
            db_session,
            actor_id=uuid.uuid4(),
            org_id=org_id,
            project_id=uuid.uuid4(),
            raw_observation_id=uuid.uuid4(),
            decision_type="invalid_type",
            command_id=uuid.uuid4(),
        )
    assert exc_info.value.status_code == 400


def test_missing_observation_raises_http_404(db_session: Session):
    """Verify that non-existent raw observation ID raises 404 Not Found."""
    from fastapi import HTTPException
    org_id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc_info:
        confirm_identity_decision(
            db_session,
            actor_id=uuid.uuid4(),
            org_id=org_id,
            project_id=uuid.uuid4(),
            raw_observation_id=uuid.uuid4(),
            decision_type="accepted",
            command_id=uuid.uuid4(),
        )
    assert exc_info.value.status_code == 404

