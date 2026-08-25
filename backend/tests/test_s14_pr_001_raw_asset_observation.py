"""S14-PR-001 unit tests for RawAssetObservation and ContextualAssetAlias."""
import uuid
from app.modules.excel_import.models import RawAssetObservation, ContextualAssetAlias


def test_raw_asset_observation_creation():
    """Verify RawAssetObservation model instantiation and property binding."""
    obs_id = uuid.uuid4()
    org_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    obs = RawAssetObservation(
        id=obs_id,
        organization_id=org_id,
        customer_id=customer_id,
        import_batch_id=batch_id,
        source_artifact_id=artifact_id,
        structure_snapshot_id=snapshot_id,
        row_index=5,
        sheet_name="Chi tiết tài sản",
        raw_asset_name="Máy biến áp 110kV 63MVA ABB",
        raw_unit="Bộ",
        raw_quantity=2.0,
        raw_price=1500000000.0,
        evidence_note="Hóa đơn GTGT số 0012345",
        section_name="I. HẠ TẦNG ĐIỆN",
    )

    assert obs.id == obs_id
    assert obs.raw_asset_name == "Máy biến áp 110kV 63MVA ABB"
    assert obs.raw_unit == "Bộ"
    assert obs.raw_quantity == 2.0
    assert obs.section_name == "I. HẠ TẦNG ĐIỆN"


def test_contextual_asset_alias_scoping():
    """Verify ContextualAssetAlias customer and org template scoping."""
    alias_id = uuid.uuid4()
    org_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    user_id = uuid.uuid4()

    alias = ContextualAssetAlias(
        id=alias_id,
        organization_id=org_id,
        customer_id=customer_id,
        alias_name="MBA 110kV 63MVA",
        normalized_alias_name="mba 110kv 63mva",
        status="active",
        created_by_user_id=user_id,
    )

    assert alias.organization_id == org_id
    assert alias.customer_id == customer_id
    assert alias.normalized_alias_name == "mba 110kv 63mva"
    assert alias.status == "active"
