"""Focused API tests for PR-04 NCC Selection read aggregate and confirm command."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db
from app.modules.project_master_data.models import (
    AssetFamily,
    AssetFamilyStatus,
    AssetVariant,
    AssetVariantStatus,
    CanonicalAsset,
    CanonicalAssetStatus,
    Customer,
    CustomerStatus,
    EvidenceFile,
    EvidenceFileStatus,
    EvidenceSensitivityLevel,
    AuditEvent,
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
    User,
    UserRole,
    UserStatus,
)


@pytest.fixture
def db_session() -> Session:
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

    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session: Session) -> TestClient:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_full(
    db: Session,
    *,
    suffix: str = "a",
    appraised_unit_price: float | None = 1000.0,
    quoted_unit_price: float = 850.0,
    set_variant: bool = False,
) -> dict:
    org = OrganizationProfile(
        legal_name=f"NCC PR04 Org {suffix}",
        organization_slug=f"ncc-pr04-{suffix}-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.flush()

    actor = User(
        organization_id=org.id,
        email=f"ncc-pr04-{suffix}-{uuid.uuid4().hex[:8]}@example.com",
        full_name="NCC PR04 Actor",
        status=UserStatus.ACTIVE,
    )
    db.add(actor)
    db.flush()

    role_admin = Role(
        code=f"ncc-pr04-admin-{suffix}-{uuid.uuid4().hex[:8]}",
        display_name="Admin",
        permissions=["project:read", "project:update", "knowledge:update"],
    )
    db.add(role_admin)
    db.flush()
    db.add(UserRole(user_id=actor.id, role_id=role_admin.id, is_active=True))

    customer = Customer(
        organization_id=org.id,
        legal_name=f"NCC PR04 Customer {suffix}",
        status=CustomerStatus.ACTIVE,
        created_by=actor.id,
    )
    db.add(customer)
    db.flush()

    project = Project(
        organization_id=org.id,
        customer_id=customer.id,
        code=f"NCC-PR04-{suffix}-{uuid.uuid4().hex[:6]}",
        name=f"NCC PR04 Project {suffix}",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=actor.id,
    )
    db.add(project)
    db.flush()

    taxonomy = TaxonomyNode(
        level=TaxonomyNodeLevel.GROUP,
        code=f"TRANS-{suffix}-{uuid.uuid4().hex[:8]}",
        name_vi="Transformers",
        status=TaxonomyStatus.ACTIVE,
        created_by=actor.id,
    )
    db.add(taxonomy)
    db.flush()

    family = AssetFamily(
        taxonomy_node_id=taxonomy.id,
        code=f"TRANSFORMER-{suffix}-{uuid.uuid4().hex[:8]}",
        name_vi="Transformer Family",
        status=AssetFamilyStatus.ACTIVE,
    )
    db.add(family)
    db.flush()

    canonical = CanonicalAsset(
        asset_family_id=family.id,
        primary_taxonomy_node_id=taxonomy.id,
        standard_name="ABB Transformer 110kV",
        status=CanonicalAssetStatus.ACTIVE,
    )
    db.add(canonical)
    db.flush()

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
        db.add(variant)
        db.flush()

    asset_line = ProjectAssetLine(
        project_id=project.id,
        asset_name="ABB Transformer",
        quantity=1.0,
        appraised_unit_price=appraised_unit_price,
        approved_canonical_asset_id=canonical.id if variant is None else None,
        approved_asset_variant_id=None if variant is None else variant.id,
    )
    db.add(asset_line)
    db.flush()

    supplier = Supplier(
        organization_id=org.id,
        legal_name="ABB Vietnam",
        display_name="ABB Vietnam",
        status=SupplierStatus.ACTIVE,
        created_by=actor.id,
    )
    db.add(supplier)
    db.flush()

    evidence = EvidenceFile(
        filename="quote.pdf",
        mime_type="application/pdf",
        file_size=1024,
        object_key="uploads/quote.pdf",
        checksum="quotehash",
        sensitivity_level=EvidenceSensitivityLevel.NORMAL,
        status=EvidenceFileStatus.ACTIVE,
        uploaded_by=actor.id,
    )
    db.add(evidence)
    db.flush()

    batch = QuoteBatch(
        organization_id=org.id,
        canonical_asset_id=canonical.id,
        asset_variant_id=None if variant is None else variant.id,
        created_by=actor.id,
        status=QuoteBatchStatus.ACTIVE,
        revision_number=1,
        approved_by=actor.id,
        approved_at=datetime.now(timezone.utc),
    )
    db.add(batch)
    db.flush()

    line = QuoteLine(
        organization_id=org.id,
        quote_batch_id=batch.id,
        evidence_file_id=evidence.id,
        supplier_id=supplier.id,
        supplier_name="ABB Vietnam",
        quoted_unit_price=quoted_unit_price,
        currency="USD",
        quantity=1.0,
        unit_of_measure="set",
        status=QuoteLineStatus.ACTIVE,
    )
    db.add(line)
    db.flush()

    db.commit()

    return {
        "org": org,
        "actor": actor,
        "customer": customer,
        "project": project,
        "asset_line": asset_line,
        "canonical": canonical,
        "supplier": supplier,
        "evidence": evidence,
        "batch": batch,
        "line": line,
    }


def _confirm_payload(line_id: uuid.UUID, *, expected: int = 0, **overrides) -> dict:
    payload = {
        "quote_line_id": str(line_id),
        "expected_selection_revision": expected,
        "acknowledged_warning_codes": [],
        "idempotency_key": f"ncc-pr04-{uuid.uuid4().hex[:8]}",
        "confirmed": True,
    }
    payload.update(overrides)
    return payload


def test_read_requires_permission_and_hides_foreign(client: TestClient, db_session: Session) -> None:
    seeded = _seed_full(db_session)
    org = seeded["org"]
    project = seeded["project"]

    role_none = Role(code=f"none-{uuid.uuid4().hex[:6]}", display_name="None", permissions=[])
    role_foreign = Role(code=f"foreign-{uuid.uuid4().hex[:6]}", display_name="Foreign", permissions=["project:read"])
    db_session.add_all([role_none, role_foreign])
    db_session.flush()

    noperm = User(organization_id=org.id, email=f"noperm-{uuid.uuid4().hex[:6]}@example.com", full_name="No Perm", status=UserStatus.ACTIVE)
    foreign_org = OrganizationProfile(legal_name="Foreign Org", organization_slug=f"foreign-{uuid.uuid4().hex[:8]}", status=OrganizationStatus.ACTIVE)
    db_session.add_all([noperm, foreign_org])
    db_session.flush()
    foreign = User(organization_id=foreign_org.id, email=f"foreign-{uuid.uuid4().hex[:6]}@example.com", full_name="Foreign", status=UserStatus.ACTIVE)
    db_session.add(foreign)
    db_session.flush()
    db_session.add_all([
        UserRole(user_id=noperm.id, role_id=role_none.id, is_active=True),
        UserRole(user_id=foreign.id, role_id=role_foreign.id, is_active=True),
    ])
    db_session.commit()

    url = f"/api/v1/projects/{project.id}/ncc-selections"

    resp = client.get(url)
    assert resp.status_code == 401

    resp = client.get(url, headers={"X-User-Id": str(noperm.id)})
    assert resp.status_code == 403

    resp = client.get(url, headers={"X-User-Id": str(foreign.id)})
    assert resp.status_code == 404

    resp = client.get(url, headers={"X-User-Id": str(seeded["actor"].id)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == str(project.id)
    assert data["kpis"]["total_asset_lines"] == 1
    assert data["kpis"]["eligible_quotes"] == 1
    assert data["asset_lines"][0]["asset_line_id"] == str(seeded["asset_line"].id)


def test_read_aggregate_shape_and_nullables(client: TestClient, db_session: Session) -> None:
    seeded = _seed_full(db_session, appraised_unit_price=None, quoted_unit_price=850.0)
    headers = {"X-User-Id": str(seeded["actor"].id)}
    url = f"/api/v1/projects/{seeded['project'].id}/ncc-selections"

    resp = client.get(url, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    line = data["asset_lines"][0]
    assert line["state"] == "unselected"
    assert line["current_selection"] is None
    assert line["history"] == []
    assert line["appraised_unit_price"] is None
    assert line["unit_name"] is None

    candidate = line["candidates"][0]
    assert candidate["eligible"] is True
    assert candidate["quote_line_id"] == str(seeded["line"].id)
    assert candidate["supplier_name"] == "ABB Vietnam"
    assert candidate["quoted_unit_price"] == 850.0
    assert candidate["currency"] == "USD"
    assert candidate["difference_amount"] is None
    assert candidate["difference_percent"] is None
    assert candidate["warnings"] == []
    assert candidate["evidence"]["evidence_file_id"] == str(seeded["evidence"].id)
    assert candidate["evidence"]["filename"] == "quote.pdf"
    assert candidate["evidence"]["status"] == "active"

    assert data["kpis"] == {
        "total_asset_lines": 1,
        "selected": 0,
        "unselected": 1,
        "stale": 0,
        "eligible_quotes": 1,
    }


def test_read_aggregate_excludes_cross_tenant_quote_line(
    client: TestClient, db_session: Session
) -> None:
    seeded = _seed_full(db_session, suffix="tenant-owner")
    foreign_org = OrganizationProfile(
        legal_name="NCC PR04 Foreign Org",
        organization_slug=f"ncc-pr04-foreign-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add(foreign_org)
    db_session.flush()

    seeded["line"].organization_id = foreign_org.id
    db_session.commit()

    response = client.get(
        f"/api/v1/projects/{seeded['project'].id}/ncc-selections",
        headers={"X-User-Id": str(seeded["actor"].id)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["kpis"]["eligible_quotes"] == 0
    assert data["asset_lines"][0]["candidates"] == []


def test_confirm_flow_and_idempotent_replay(client: TestClient, db_session: Session) -> None:
    seeded = _seed_full(db_session)
    headers = {"X-User-Id": str(seeded["actor"].id)}
    url = f"/api/v1/projects/{seeded['project'].id}/asset-lines/{seeded['asset_line'].id}/ncc-selection"

    key = f"ncc-pr04-{uuid.uuid4().hex[:8]}"
    payload = _confirm_payload(seeded["line"].id, idempotency_key=key)

    resp = client.post(url, json=payload, headers=headers)
    assert resp.status_code == 200
    current = resp.json()
    assert current["selection_revision"] == 1
    assert current["selection_id"]
    assert current["quote_line_id"] == str(seeded["line"].id)
    assert current["supplier_name"] == "ABB Vietnam"
    assert current["current_unit_price"] == 1000.0
    assert current["stale"] is False
    assert current["difference_percent"] == -15.0
    assert current["warnings"] == ["NCC_BELOW_CURRENT_PRICE"]

    replay = client.post(url, json=payload, headers=headers)
    assert replay.status_code == 200
    assert replay.json()["selection_id"] == current["selection_id"]

    assert db_session.query(NccSelectionRevision).count() == 1

    agg = client.get(f"/api/v1/projects/{seeded['project'].id}/ncc-selections", headers=headers)
    assert agg.status_code == 200
    line = agg.json()["asset_lines"][0]
    assert line["state"] == "selected"
    assert line["current_selection"]["selection_revision"] == 1
    assert len(line["history"]) == 1
    assert agg.json()["kpis"]["selected"] == 1
    assert agg.json()["kpis"]["unselected"] == 0


def test_revised_quote_batch_preserves_tenant_supplier_and_marks_selection_stale(
    client: TestClient, db_session: Session
) -> None:
    seeded = _seed_full(db_session, suffix="revision-stale")
    headers = {"X-User-Id": str(seeded["actor"].id)}
    confirm_url = (
        f"/api/v1/projects/{seeded['project'].id}/asset-lines/"
        f"{seeded['asset_line'].id}/ncc-selection"
    )

    confirmed = client.post(
        confirm_url,
        json=_confirm_payload(seeded["line"].id),
        headers=headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["stale"] is False

    revised_response = client.post(
        f"/api/v1/knowledge/quote-batches/{seeded['batch'].id}/revise",
        headers=headers,
    )
    assert revised_response.status_code == 201
    revised = db_session.get(QuoteBatch, uuid.UUID(revised_response.json()["id"]))
    assert revised is not None
    try:
        aggregate = client.get(
            f"/api/v1/projects/{seeded['project'].id}/ncc-selections",
            headers=headers,
        )
        assert aggregate.status_code == 200
        aggregate_line = aggregate.json()["asset_lines"][0]
        assert aggregate_line["state"] == "stale"
        assert aggregate_line["current_selection"]["stale"] is True
        assert aggregate.json()["kpis"]["stale"] == 1

        assert revised.organization_id == seeded["org"].id
        assert revised.previous_quote_batch_id == seeded["batch"].id
        assert len(revised.quote_lines) == 1
        revised_line = revised.quote_lines[0]
        assert revised_line.organization_id == seeded["org"].id
        assert revised_line.supplier_id == seeded["supplier"].id
    finally:
        for revised_line in revised.quote_lines:
            db_session.delete(revised_line)
        db_session.delete(revised)
        db_session.commit()


def test_cross_tenant_quote_revision_cannot_inject_stale_selection(
    client: TestClient, db_session: Session
) -> None:
    victim = _seed_full(db_session, suffix="revision-victim")
    victim_headers = {"X-User-Id": str(victim["actor"].id)}
    confirmed = client.post(
        (
            f"/api/v1/projects/{victim['project'].id}/asset-lines/"
            f"{victim['asset_line'].id}/ncc-selection"
        ),
        json=_confirm_payload(victim["line"].id),
        headers=victim_headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["stale"] is False

    attacker_org = OrganizationProfile(
        legal_name="NCC PR04 Revision Attacker",
        organization_slug=f"ncc-pr04-attacker-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE,
    )
    attacker_role = Role(
        code=f"ncc-pr04-attacker-{uuid.uuid4().hex[:8]}",
        display_name="Knowledge updater",
        permissions=["knowledge:update"],
    )
    db_session.add_all([attacker_org, attacker_role])
    db_session.flush()
    attacker = User(
        organization_id=attacker_org.id,
        email=f"ncc-pr04-attacker-{uuid.uuid4().hex[:8]}@example.com",
        full_name="NCC PR04 Attacker",
        status=UserStatus.ACTIVE,
    )
    db_session.add(attacker)
    db_session.flush()
    db_session.add(UserRole(user_id=attacker.id, role_id=attacker_role.id, is_active=True))
    db_session.commit()

    attacked = client.post(
        f"/api/v1/knowledge/quote-batches/{victim['batch'].id}/revise",
        headers={"X-User-Id": str(attacker.id)},
    )
    successors = (
        db_session.query(QuoteBatch)
        .filter(QuoteBatch.previous_quote_batch_id == victim["batch"].id)
        .all()
    )
    try:
        aggregate = client.get(
            f"/api/v1/projects/{victim['project'].id}/ncc-selections",
            headers=victim_headers,
        )
        assert aggregate.status_code == 200
        aggregate_line = aggregate.json()["asset_lines"][0]
        assert {
            "attack_status": attacked.status_code,
            "successor_count": len(successors),
            "victim_state": aggregate_line["state"],
            "victim_stale": aggregate_line["current_selection"]["stale"],
        } == {
            "attack_status": 404,
            "successor_count": 0,
            "victim_state": "selected",
            "victim_stale": False,
        }
    finally:
        for successor in successors:
            for revised_line in successor.quote_lines:
                db_session.delete(revised_line)
            db_session.delete(successor)
        db_session.commit()


def test_confirm_strict_input_and_validation(client: TestClient, db_session: Session) -> None:
    seeded = _seed_full(db_session)
    headers = {"X-User-Id": str(seeded["actor"].id)}
    url = f"/api/v1/projects/{seeded['project'].id}/asset-lines/{seeded['asset_line'].id}/ncc-selection"

    unknown = _confirm_payload(seeded["line"].id)
    unknown["unexpected_field"] = "x"
    resp = client.post(url, json=unknown, headers=headers)
    assert resp.status_code == 422

    not_confirmed = _confirm_payload(seeded["line"].id, confirmed=False)
    resp = client.post(url, json=not_confirmed, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["detail"]["error_code"] == "ncc_selection_confirmation_required"

    bad_key = _confirm_payload(seeded["line"].id, idempotency_key="   ")
    resp = client.post(url, json=bad_key, headers=headers)
    assert resp.status_code == 422

    bad_revision = _confirm_payload(seeded["line"].id, expected_selection_revision=-1)
    resp = client.post(url, json=bad_revision, headers=headers)
    assert resp.status_code == 422


def test_confirm_409_selection_revision_conflict(client: TestClient, db_session: Session) -> None:
    seeded = _seed_full(db_session)
    headers = {"X-User-Id": str(seeded["actor"].id)}
    url = f"/api/v1/projects/{seeded['project'].id}/asset-lines/{seeded['asset_line'].id}/ncc-selection"

    first = client.post(url, json=_confirm_payload(seeded["line"].id), headers=headers)
    assert first.status_code == 200

    second = client.post(
        url,
        json=_confirm_payload(seeded["line"].id, expected_selection_revision=0),
        headers=headers,
    )
    assert second.status_code == 409
    assert second.json()["detail"]["error_code"] == "selection_revision_conflict"


def test_confirm_foreign_and_missing_quote_line_are_publicly_indistinguishable_without_mutation(
    client: TestClient, db_session: Session
) -> None:
    seeded = _seed_full(db_session, suffix="tenant-owner")
    foreign = _seed_full(db_session, suffix="tenant-foreign")
    headers = {"X-User-Id": str(seeded["actor"].id)}
    url = (
        f"/api/v1/projects/{seeded['project'].id}/asset-lines/"
        f"{seeded['asset_line'].id}/ncc-selection"
    )
    baseline = {
        "revisions": db_session.query(NccSelectionRevision).count(),
        "heads": db_session.query(NccSelectionCurrentHead).count(),
        "audits": db_session.query(AuditEvent).count(),
    }

    foreign_response = client.post(
        url, json=_confirm_payload(foreign["line"].id), headers=headers
    )
    missing_response = client.post(
        url, json=_confirm_payload(uuid.uuid4()), headers=headers
    )

    def public_error(response) -> tuple[int, str, str]:
        detail = response.json()["detail"]
        return response.status_code, detail["error_code"], detail["detail"]

    assert public_error(foreign_response) == public_error(missing_response)
    assert {
        "revisions": db_session.query(NccSelectionRevision).count(),
        "heads": db_session.query(NccSelectionCurrentHead).count(),
        "audits": db_session.query(AuditEvent).count(),
    } == baseline


def test_confirm_requires_update_permission(client: TestClient, db_session: Session) -> None:
    seeded = _seed_full(db_session)
    role_read = Role(code=f"read-{uuid.uuid4().hex[:6]}", display_name="Read", permissions=["project:read"])
    db_session.add(role_read)
    db_session.flush()
    reader = User(organization_id=seeded["org"].id, email=f"reader-{uuid.uuid4().hex[:6]}@example.com", full_name="Reader", status=UserStatus.ACTIVE)
    db_session.add(reader)
    db_session.flush()
    db_session.add(UserRole(user_id=reader.id, role_id=role_read.id, is_active=True))
    db_session.commit()

    url = f"/api/v1/projects/{seeded['project'].id}/asset-lines/{seeded['asset_line'].id}/ncc-selection"
    resp = client.post(url, json=_confirm_payload(seeded["line"].id), headers={"X-User-Id": str(reader.id)})
    assert resp.status_code == 403
