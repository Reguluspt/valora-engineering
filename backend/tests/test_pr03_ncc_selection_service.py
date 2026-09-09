"""Focused unit tests for PR-03 NCC Selection persistence command."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.project_master_data.application.ncc_selection_service import (
    EVENT_NCC_SELECTION_CHANGED,
    EVENT_NCC_SELECTION_CONFIRMED,
    EVENT_NCC_SELECTION_RECONFIRMED,
    WARNING_NCC_BELOW_CURRENT_PRICE,
    WARNING_NCC_DIFFERENCE_OVER_15_PERCENT,
    confirm_ncc_selection,
    is_ncc_selection_stale,
)
from app.modules.project_master_data.models import (
    AssetFamily,
    AssetFamilyStatus,
    AssetVariant,
    AssetVariantStatus,
    AuditEvent,
    CanonicalAsset,
    CanonicalAssetStatus,
    Customer,
    CustomerStatus,
    EvidenceFile,
    EvidenceFileStatus,
    EvidenceSensitivityLevel,
    NccSelectionCurrentHead,
    NccSelectionRevision,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    ProjectAssetLine,
    ProjectWorkflowStatus,
    QuoteBatch,
    QuoteBatchStatus,
    QuoteLine,
    QuoteLineStatus,
    Role,
    Supplier,
    SupplierStatus,
    TaxonomyNode,
    TaxonomyNodeLevel,
    TaxonomyStatus,
    UniqueConstraint,
    User,
    UserRole,
    UserStatus,
)


NCC_SELECTION_PERMISSION = "project:update"


@pytest.fixture
def selection_db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()


def _seed(
    selection_db: Session,
    *,
    suffix: str = "a",
    grant_permission: bool = True,
    appraised_unit_price: float | None = 1000.0,
    quoted_unit_price: float = 850.0,
    supplier_name: str = "ABB Vietnam",
    quote_batch_status: QuoteBatchStatus = QuoteBatchStatus.ACTIVE,
    quote_line_status: QuoteLineStatus = QuoteLineStatus.ACTIVE,
    approved_by: bool = True,
    evidence_active: bool = True,
    supplier_active: bool = True,
    set_variant: bool = False,
) -> dict:
    org = OrganizationProfile(
        legal_name=f"NCC Selection Org {suffix}",
        organization_slug=f"ncc-selection-{suffix}-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE,
    )
    selection_db.add(org)
    selection_db.flush()

    actor = User(
        organization_id=org.id,
        email=f"ncc-selection-{suffix}-{uuid.uuid4().hex[:8]}@example.com",
        full_name="NCC Selection Human",
        status=UserStatus.ACTIVE,
    )
    selection_db.add(actor)
    selection_db.flush()

    role = Role(
        code=f"ncc-selection-{suffix}-{uuid.uuid4().hex[:8]}",
        display_name="NCC Selection Fixture",
        permissions=[NCC_SELECTION_PERMISSION] if grant_permission else [],
    )
    selection_db.add(role)
    selection_db.flush()

    user_role = UserRole(user_id=actor.id, role_id=role.id, is_active=True)
    selection_db.add(user_role)

    customer = Customer(
        organization_id=org.id,
        legal_name=f"NCC Selection Customer {suffix}",
        status=CustomerStatus.ACTIVE,
        created_by=actor.id,
    )
    selection_db.add(customer)
    selection_db.flush()

    project = Project(
        organization_id=org.id,
        customer_id=customer.id,
        code=f"NCC-{suffix}-{uuid.uuid4().hex[:6]}",
        name=f"NCC Selection Project {suffix}",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=actor.id,
    )
    selection_db.add(project)
    selection_db.flush()

    taxonomy = TaxonomyNode(
        level=TaxonomyNodeLevel.GROUP,
        code=f"TRANS-{suffix}-{uuid.uuid4().hex[:8]}",
        name_vi="Transformers",
        status=TaxonomyStatus.ACTIVE,
        created_by=actor.id,
    )
    selection_db.add(taxonomy)
    selection_db.flush()

    family = AssetFamily(
        taxonomy_node_id=taxonomy.id,
        code=f"TRANSFORMER-{suffix}-{uuid.uuid4().hex[:8]}",
        name_vi="Transformer Family",
        status=AssetFamilyStatus.ACTIVE,
    )
    selection_db.add(family)
    selection_db.flush()

    canonical = CanonicalAsset(
        asset_family_id=family.id,
        primary_taxonomy_node_id=taxonomy.id,
        standard_name="ABB Transformer 110kV",
        status=CanonicalAssetStatus.ACTIVE,
    )
    selection_db.add(canonical)
    selection_db.flush()

    variant = None
    if set_variant:
        variant = AssetVariant(
            asset_family_id=family.id,
            canonical_asset_id=canonical.id,
            code=f"TRANSFORMER-VARIANT-{suffix}-{uuid.uuid4().hex[:8]}",
            display_name="ABB Transformer 110kV Variant",
            status=AssetVariantStatus.ACTIVE,
            approved_by=actor.id,
            approved_at=datetime.now(timezone.utc),
        )
        selection_db.add(variant)
        selection_db.flush()

    asset_line = ProjectAssetLine(
        project_id=project.id,
        asset_name="ABB Transformer",
        quantity=1.0,
        appraised_unit_price=appraised_unit_price,
        approved_canonical_asset_id=canonical.id if variant is None else None,
        approved_asset_variant_id=None if variant is None else variant.id,
    )
    selection_db.add(asset_line)
    selection_db.flush()

    supplier = Supplier(
        organization_id=org.id,
        legal_name=supplier_name,
        display_name=supplier_name,
        status=SupplierStatus.ACTIVE if supplier_active else SupplierStatus.INACTIVE,
        created_by=actor.id,
    )
    selection_db.add(supplier)
    selection_db.flush()

    evidence = EvidenceFile(
        filename="quote.pdf",
        mime_type="application/pdf",
        file_size=1024,
        object_key="uploads/quote.pdf",
        checksum="quotehash",
        sensitivity_level=EvidenceSensitivityLevel.NORMAL,
        status=EvidenceFileStatus.ACTIVE if evidence_active else EvidenceFileStatus.ARCHIVED,
        uploaded_by=actor.id,
    )
    selection_db.add(evidence)
    selection_db.flush()

    batch = QuoteBatch(
        organization_id=org.id,
        canonical_asset_id=canonical.id,
        asset_variant_id=None if variant is None else variant.id,
        created_by=actor.id,
        status=quote_batch_status,
        revision_number=1,
        approved_by=actor.id if approved_by else None,
        approved_at=datetime.now(timezone.utc) if approved_by else None,
    )
    selection_db.add(batch)
    selection_db.flush()

    line = QuoteLine(
        organization_id=org.id,
        quote_batch_id=batch.id,
        evidence_file_id=evidence.id,
        supplier_id=supplier.id,
        supplier_name=supplier_name,
        quoted_unit_price=quoted_unit_price,
        currency="USD",
        quantity=1.0,
        unit_of_measure="set",
        status=quote_line_status,
    )
    selection_db.add(line)
    selection_db.commit()

    return {
        "org": org,
        "actor": actor,
        "role": role,
        "user_role": user_role,
        "customer": customer,
        "project": project,
        "asset_line": asset_line,
        "taxonomy": taxonomy,
        "family": family,
        "canonical": canonical,
        "variant": variant,
        "supplier": supplier,
        "evidence": evidence,
        "batch": batch,
        "line": line,
    }


def _confirm(selection_db: Session, seeded: dict, **overrides) -> Any:
    values = {
        "actor": seeded["actor"],
        "org_id": seeded["org"].id,
        "project_id": seeded["project"].id,
        "project_asset_line_id": seeded["asset_line"].id,
        "quote_line_id": seeded["line"].id,
        "expected_selection_revision": 0,
        "acknowledged_warning_codes": [],
        "idempotency_key": f"ncc-selection-{uuid.uuid4().hex[:8]}",
        "confirmed": True,
        "correlation_id": "corr-ncc-selection",
    }
    values.update(overrides)
    return confirm_ncc_selection(selection_db, **values)


def _assert_error(exc: pytest.ExceptionInfo[HTTPException], status: int, code: str) -> None:
    assert exc.value.status_code == status
    assert exc.value.detail["error_code"] == code


def test_first_confirm_creates_revision_and_current_head(selection_db: Session) -> None:
    seeded = _seed(selection_db)

    revision = _confirm(selection_db, seeded)

    assert revision.selection_revision == 1
    assert revision.project_id == seeded["project"].id
    assert revision.project_asset_line_id == seeded["asset_line"].id
    assert revision.quote_line_id == seeded["line"].id
    assert revision.supplier_id == seeded["supplier"].id
    assert revision.evidence_file_id == seeded["evidence"].id
    assert revision.current_unit_price_snapshot == 1000.0
    assert revision.warning_codes == [WARNING_NCC_BELOW_CURRENT_PRICE]

    head = (
        selection_db.query(NccSelectionCurrentHead)
        .filter(
            NccSelectionCurrentHead.organization_id == seeded["org"].id,
            NccSelectionCurrentHead.project_asset_line_id == seeded["asset_line"].id,
        )
        .one()
    )
    assert head.current_revision_id == revision.id
    assert head.selection_revision == 1

    audits = (
        selection_db.query(AuditEvent)
        .filter(AuditEvent.event_name == EVENT_NCC_SELECTION_CONFIRMED)
        .all()
    )
    assert len(audits) == 1
    assert audits[0].entity_id == revision.id


def test_idempotent_replay_returns_same_revision_without_new_audit(
    selection_db: Session,
) -> None:
    seeded = _seed(selection_db)
    key = "ncc-idempotency-replay"
    first = _confirm(selection_db, seeded, idempotency_key=key)

    replay = _confirm(selection_db, seeded, idempotency_key=key)

    assert replay.id == first.id
    assert selection_db.query(NccSelectionRevision).count() == 1
    assert (
        selection_db.query(AuditEvent)
        .filter(AuditEvent.event_name == EVENT_NCC_SELECTION_CONFIRMED)
        .count()
        == 1
    )


def test_idempotent_replay_ignores_new_correlation_id(selection_db: Session) -> None:
    seeded = _seed(selection_db)
    key = "ncc-idempotency-correlation"
    first = _confirm(
        selection_db,
        seeded,
        idempotency_key=key,
        correlation_id="correlation-first",
    )

    replay = _confirm(
        selection_db,
        seeded,
        idempotency_key=key,
        correlation_id="correlation-retry",
    )

    assert replay.id == first.id
    assert selection_db.query(NccSelectionRevision).count() == 1


def test_second_selection_emits_changed_event(selection_db: Session) -> None:
    seeded = _seed(selection_db)
    _confirm(selection_db, seeded)

    other_supplier = Supplier(
        organization_id=seeded["org"].id,
        legal_name="Siemens Vietnam",
        display_name="Siemens Vietnam",
        status=SupplierStatus.ACTIVE,
        created_by=seeded["actor"].id,
    )
    selection_db.add(other_supplier)
    selection_db.flush()

    other_line = QuoteLine(
        organization_id=seeded["org"].id,
        quote_batch_id=seeded["batch"].id,
        evidence_file_id=seeded["evidence"].id,
        supplier_id=other_supplier.id,
        supplier_name="Siemens Vietnam",
        quoted_unit_price=900.0,
        currency="USD",
        status=QuoteLineStatus.ACTIVE,
    )
    selection_db.add(other_line)
    selection_db.commit()

    second = _confirm(
        selection_db,
        seeded,
        quote_line_id=other_line.id,
        expected_selection_revision=1,
        idempotency_key="ncc-selection-changed",
    )

    assert second.selection_revision == 2
    assert second.quote_line_id == other_line.id
    assert (
        selection_db.query(AuditEvent)
        .filter(AuditEvent.event_name == EVENT_NCC_SELECTION_CHANGED)
        .count()
        == 1
    )


def test_reconfirm_same_quote_line_emits_reconfirmed_event(selection_db: Session) -> None:
    seeded = _seed(selection_db)
    first = _confirm(selection_db, seeded)

    second = _confirm(
        selection_db,
        seeded,
        expected_selection_revision=1,
        idempotency_key="ncc-selection-reconfirmed",
    )

    assert second.selection_revision == 2
    assert second.quote_line_id == first.quote_line_id
    assert (
        selection_db.query(AuditEvent)
        .filter(AuditEvent.event_name == EVENT_NCC_SELECTION_RECONFIRMED)
        .count()
        == 1
    )


def test_expected_revision_conflict_returns_409(selection_db: Session) -> None:
    seeded = _seed(selection_db)
    _confirm(selection_db, seeded)

    with pytest.raises(HTTPException) as exc:
        _confirm(selection_db, seeded, expected_selection_revision=0)

    _assert_error(exc, 409, "selection_revision_conflict")


def test_missing_confirmation_returns_400(selection_db: Session) -> None:
    seeded = _seed(selection_db)

    with pytest.raises(HTTPException) as exc:
        _confirm(selection_db, seeded, confirmed=False)

    _assert_error(exc, 400, "ncc_selection_confirmation_required")


def test_missing_permission_returns_403(selection_db: Session) -> None:
    seeded = _seed(selection_db, grant_permission=False)

    with pytest.raises(HTTPException) as exc:
        _confirm(selection_db, seeded)

    _assert_error(exc, 403, "ncc_selection_forbidden")


def test_inactive_supplier_is_ineligible(selection_db: Session) -> None:
    seeded = _seed(selection_db, supplier_active=False)

    with pytest.raises(HTTPException) as exc:
        _confirm(selection_db, seeded)

    _assert_error(exc, 409, "supplier_not_active")


def test_unconfirmed_quote_batch_is_ineligible(selection_db: Session) -> None:
    seeded = _seed(selection_db, approved_by=False)

    with pytest.raises(HTTPException) as exc:
        _confirm(selection_db, seeded)

    _assert_error(exc, 409, "quote_batch_not_confirmed")


def test_non_active_quote_line_is_ineligible(selection_db: Session) -> None:
    seeded = _seed(selection_db, quote_line_status=QuoteLineStatus.DRAFT)

    with pytest.raises(HTTPException) as exc:
        _confirm(selection_db, seeded)

    _assert_error(exc, 409, "quote_line_not_active")


def test_asset_identity_mismatch_is_ineligible(selection_db: Session) -> None:
    seeded = _seed(selection_db)
    other_canonical = CanonicalAsset(
        asset_family_id=seeded["canonical"].asset_family_id,
        primary_taxonomy_node_id=seeded["canonical"].primary_taxonomy_node_id,
        standard_name="Other Transformer",
        status=CanonicalAssetStatus.ACTIVE,
    )
    selection_db.add(other_canonical)
    selection_db.flush()
    seeded["batch"].canonical_asset_id = other_canonical.id
    selection_db.commit()

    with pytest.raises(HTTPException) as exc:
        _confirm(selection_db, seeded)

    _assert_error(exc, 409, "asset_identity_mismatch")


def test_approved_variant_identity_is_eligible(selection_db: Session) -> None:
    seeded = _seed(selection_db, set_variant=True)

    revision = _confirm(selection_db, seeded)

    assert seeded["variant"] is not None
    assert seeded["batch"].asset_variant_id == seeded["variant"].id
    assert revision.quote_batch_id == seeded["batch"].id


def test_cross_tenant_quote_line_is_rejected(selection_db: Session) -> None:
    seeded = _seed(selection_db, suffix="tenant-owner")
    other = _seed(selection_db, suffix="tenant-other")

    with pytest.raises(HTTPException) as exc:
        _confirm(selection_db, seeded, quote_line_id=other["line"].id)

    _assert_error(exc, 409, "quote_line_not_found")
    assert selection_db.query(NccSelectionRevision).count() == 0


def test_cross_tenant_evidence_is_rejected(selection_db: Session) -> None:
    seeded = _seed(selection_db, suffix="evidence-owner")
    other = _seed(selection_db, suffix="evidence-other")
    seeded["evidence"].uploaded_by = other["actor"].id
    selection_db.commit()

    with pytest.raises(HTTPException) as exc:
        _confirm(selection_db, seeded)

    _assert_error(exc, 409, "evidence_tenant_mismatch")
    assert selection_db.query(NccSelectionRevision).count() == 0


def test_warning_computation_over_15_percent(selection_db: Session) -> None:
    # current = 1000, quote = 1200 -> diff = 20%
    seeded = _seed(selection_db, quoted_unit_price=1200.0)

    revision = _confirm(selection_db, seeded)

    assert WARNING_NCC_DIFFERENCE_OVER_15_PERCENT in revision.warning_codes
    assert revision.difference_amount is not None
    assert revision.difference_percent is not None


def test_warning_computation_current_price_zero(selection_db: Session) -> None:
    seeded = _seed(selection_db, appraised_unit_price=0.0, quoted_unit_price=500.0)

    revision = _confirm(selection_db, seeded)

    assert revision.difference_amount == 500.0
    assert revision.difference_percent is None
    assert WARNING_NCC_BELOW_CURRENT_PRICE not in revision.warning_codes


def test_stale_when_quote_line_no_longer_active(selection_db: Session) -> None:
    seeded = _seed(selection_db)
    revision = _confirm(selection_db, seeded)

    seeded["line"].status = QuoteLineStatus.REJECTED
    selection_db.commit()

    assert is_ncc_selection_stale(selection_db, revision=revision) is True


def test_stale_when_newer_quote_batch_revision_exists(selection_db: Session) -> None:
    seeded = _seed(selection_db)
    revision = _confirm(selection_db, seeded)

    rev_batch = QuoteBatch(
        organization_id=seeded["org"].id,
        canonical_asset_id=seeded["batch"].canonical_asset_id,
        created_by=seeded["actor"].id,
        status=QuoteBatchStatus.DRAFT,
        revision_number=2,
        previous_quote_batch_id=seeded["batch"].id,
    )
    selection_db.add(rev_batch)
    selection_db.commit()

    assert is_ncc_selection_stale(selection_db, revision=revision) is True


def test_not_stale_for_fresh_selection(selection_db: Session) -> None:
    seeded = _seed(selection_db)
    revision = _confirm(selection_db, seeded)

    assert is_ncc_selection_stale(selection_db, revision=revision) is False


def test_acknowledged_warning_codes_are_stored(selection_db: Session) -> None:
    seeded = _seed(selection_db)
    revision = _confirm(
        selection_db,
        seeded,
        acknowledged_warning_codes=[WARNING_NCC_BELOW_CURRENT_PRICE],
    )

    assert revision.acknowledged_warning_codes == [WARNING_NCC_BELOW_CURRENT_PRICE]
    assert revision.warning_codes == [WARNING_NCC_BELOW_CURRENT_PRICE]


def test_current_head_model_has_no_uuid_id_column() -> None:
    """F1: mapped columns must match migration (composite PK, no inherited id)."""
    columns = {col.name for col in NccSelectionCurrentHead.__table__.columns}
    assert "id" not in columns
    assert columns == {
        "organization_id",
        "project_id",
        "project_asset_line_id",
        "current_revision_id",
        "selection_revision",
    }
    pk = {col.name for col in NccSelectionCurrentHead.__table__.primary_key.columns}
    assert pk == {"organization_id", "project_id", "project_asset_line_id"}


def test_null_supplier_id_is_ineligible_even_with_matching_name(
    selection_db: Session,
) -> None:
    """F2: ADR 0039 D1/D3 requires supplier_id; name fallback is not allowed."""
    seeded = _seed(selection_db)
    seeded["line"].supplier_id = None
    seeded["line"].supplier_name = seeded["supplier"].legal_name
    selection_db.commit()

    with pytest.raises(HTTPException) as exc:
        _confirm(selection_db, seeded)

    _assert_error(exc, 409, "supplier_not_resolved")


def test_same_idempotency_key_with_changed_acknowledgements_is_rejected(
    selection_db: Session,
) -> None:
    """F3: idempotency key is bound to the full request digest incl. acknowledgements."""
    seeded = _seed(selection_db)
    key = "ncc-key-ack-change"
    first = _confirm(
        selection_db,
        seeded,
        idempotency_key=key,
        acknowledged_warning_codes=[],
    )
    assert first.acknowledged_warning_codes == []

    with pytest.raises(HTTPException) as exc:
        _confirm(
            selection_db,
            seeded,
            idempotency_key=key,
            acknowledged_warning_codes=[WARNING_NCC_BELOW_CURRENT_PRICE],
        )

    _assert_error(exc, 409, "idempotency_key_reused")


def test_idempotency_key_has_organization_scoped_unique_constraint() -> None:
    """F3: model metadata enforces (organization_id, idempotency_key) uniqueness."""
    table = NccSelectionRevision.__table__
    names = {uc.name for uc in table.constraints if isinstance(uc, UniqueConstraint)}
    assert "uq_ncc_rev_idempotency_org" in names
