"""S14-R-001 tests for tenant-safe identity decisions and feedback."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.ai_governance_security.models import (
    SecurityAuditLog,
    SecurityEvent,
    TenantBoundaryCheck,
)
from app.modules.excel_import.models import (
    AssetIdentityDecision,
    ContextualAssetAlias,
    ImportSourceArtifact,
    LearningFeedbackEvent,
    RawAssetObservation,
    WorkbookStructureSnapshot,
)
from app.modules.project_master_data.models import (
    AssetAlias,
    AssetAliasScope,
    AssetAliasStatus,
    AssetFamily,
    AssetFamilyStatus,
    AssetVariant,
    AssetVariantStatus,
    AuditEvent,
    CanonicalAsset,
    CanonicalAssetStatus,
    Customer,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    ProjectAssetImportBatch,
    Role,
    TaxonomyNode,
    TaxonomyNodeLevel,
    TaxonomyStatus,
    User,
    UserRole,
    UserStatus,
)
from app.modules.taxonomy_asset_identity.application.identity_decision_service import (
    confirm_identity_decision,
)


@dataclass(frozen=True)
class TenantSeed:
    organization: OrganizationProfile
    actor: User
    customer: Customer
    project: Project
    observation: RawAssetObservation
    canonical: CanonicalAsset
    variant: AssetVariant
    alias: AssetAlias


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed_tenant(db: Session, slug: str) -> TenantSeed:
    org = OrganizationProfile(
        legal_name=f"Organization {slug}",
        organization_slug=slug,
        status=OrganizationStatus.ACTIVE,
    )
    role = Role(
        code=f"identity-approver-{slug}",
        display_name=f"Identity Approver {slug}",
        permissions=["asset_identity:approve"],
    )
    db.add_all([org, role])
    db.commit()

    actor = User(
        organization_id=org.id,
        email=f"approver-{slug}@example.test",
        full_name=f"Approver {slug}",
        status=UserStatus.ACTIVE,
    )
    db.add(actor)
    db.commit()
    db.add(UserRole(user_id=actor.id, role_id=role.id, is_active=True))
    db.commit()

    customer = Customer(
        organization_id=org.id,
        legal_name=f"Customer {slug}",
        status="active",
        created_by=actor.id,
    )
    db.add(customer)
    db.commit()
    project = Project(
        organization_id=org.id,
        customer_id=customer.id,
        code=f"PRJ-{slug}",
        name=f"Project {slug}",
        created_by=actor.id,
    )
    db.add(project)
    db.commit()

    node = TaxonomyNode(
        level=TaxonomyNodeLevel.GROUP,
        code=f"NODE-{slug}",
        name_vi=f"Nhóm {slug}",
        status=TaxonomyStatus.ACTIVE,
        created_by=actor.id,
    )
    db.add(node)
    db.commit()
    family = AssetFamily(
        taxonomy_node_id=node.id,
        code=f"FAMILY-{slug}",
        name_vi=f"Họ tài sản {slug}",
        status=AssetFamilyStatus.ACTIVE,
    )
    db.add(family)
    db.commit()
    canonical = CanonicalAsset(
        asset_family_id=family.id,
        primary_taxonomy_node_id=node.id,
        standard_name=f"Tài sản chuẩn {slug}",
        status=CanonicalAssetStatus.ACTIVE,
    )
    db.add(canonical)
    db.commit()
    variant = AssetVariant(
        asset_family_id=family.id,
        canonical_asset_id=canonical.id,
        code=f"VAR-{slug}",
        display_name=f"Biến thể {slug}",
        status=AssetVariantStatus.ACTIVE,
    )
    db.add(variant)
    db.commit()
    alias = AssetAlias(
        alias_scope=AssetAliasScope.CANONICAL,
        canonical_asset_id=canonical.id,
        raw_alias=f"Alias {slug}",
        normalized_alias=f"alias {slug}",
        status=AssetAliasStatus.ACTIVE,
    )
    db.add(alias)
    db.commit()

    batch = ProjectAssetImportBatch(
        organization_id=org.id,
        project_id=project.id,
        source_filename=f"assets-{slug}.xlsx",
        source_sheet_name="Sheet1",
        total_rows=1,
        created_by_user_id=actor.id,
    )
    db.add(batch)
    db.commit()
    artifact = ImportSourceArtifact(
        organization_id=org.id,
        project_id=project.id,
        import_batch_id=batch.id,
        generation=1,
        original_filename=f"assets-{slug}.xlsx",
        detected_format="xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=128,
        checksum_sha256="a" * 64,
        storage_object_key=f"{slug}/assets.xlsx",
        state="available",
        adapter_name="openpyxl",
        adapter_version="1",
        adapter_metadata={},
        created_by_user_id=actor.id,
    )
    db.add(artifact)
    db.commit()
    batch.current_source_artifact_id = artifact.id
    db.commit()
    snapshot = WorkbookStructureSnapshot(
        organization_id=org.id,
        project_id=project.id,
        import_batch_id=batch.id,
        source_artifact_id=artifact.id,
        snapshot_version=1,
        source_checksum_sha256="a" * 64,
        rule_version="test-rule-v1",
        adapter_name="openpyxl",
        adapter_version="1",
        disposition="proposed",
        candidate_count=0,
        structure_payload={"candidates": []},
        analysis_digest_sha256="b" * 64,
        created_by_user_id=actor.id,
    )
    db.add(snapshot)
    db.commit()
    observation = RawAssetObservation(
        organization_id=org.id,
        customer_id=customer.id,
        project_id=project.id,
        import_batch_id=batch.id,
        source_artifact_id=artifact.id,
        structure_snapshot_id=snapshot.id,
        row_index=1,
        sheet_name="Sheet1",
        raw_asset_name=f"Tủ điện hạ thế 400A {slug}",
    )
    db.add(observation)
    db.commit()
    return TenantSeed(org, actor, customer, project, observation, canonical, variant, alias)


def _seed_viewer(db: Session, seed: TenantSeed) -> User:
    role = Role(
        code=f"identity-viewer-{seed.organization.organization_slug}",
        display_name="Identity Viewer",
        permissions=[],
    )
    viewer = User(
        organization_id=seed.organization.id,
        email=f"viewer-{seed.organization.organization_slug}@example.test",
        full_name="Viewer",
        status=UserStatus.ACTIVE,
    )
    db.add_all([role, viewer])
    db.commit()
    db.add(UserRole(user_id=viewer.id, role_id=role.id, is_active=True))
    db.commit()
    return viewer


def test_accepted_decision_is_atomic_audited_and_preserves_raw_text(db_session: Session) -> None:
    seed = _seed_tenant(db_session, "org-a")
    raw_before = seed.observation.raw_asset_name

    decision, feedback = confirm_identity_decision(
        db_session,
        actor=seed.actor,
        org_id=seed.organization.id,
        project_id=seed.project.id,
        raw_observation_id=seed.observation.id,
        decision_type="accepted",
        chosen_canonical_asset_id=seed.canonical.id,
        create_contextual_alias=True,
        command_id=uuid.uuid4(),
        correlation_id="s14-r-001-test",
    )

    assert decision.customer_id == seed.customer.id
    assert decision.actor_user_id == seed.actor.id
    assert feedback is not None
    assert feedback.event_type == "positive_match"
    assert feedback.target_type == "CanonicalAsset"
    assert db_session.get(RawAssetObservation, seed.observation.id).raw_asset_name == raw_before
    contextual = db_session.query(ContextualAssetAlias).one()
    assert contextual.canonical_asset_id == seed.canonical.id
    assert contextual.source_decision_id == decision.id
    audit = db_session.query(AuditEvent).filter_by(entity_id=decision.id).one()
    assert audit.command_name == "ConfirmAssetIdentityDecision"
    assert audit.correlation_id == "s14-r-001-test"
    assert db_session.query(TenantBoundaryCheck).filter_by(result="pass").count() == 3
    assert db_session.query(SecurityAuditLog).filter_by(
        action_type="tenant_boundary_check_passed"
    ).count() == 3
    assert db_session.query(SecurityEvent).count() == 0


def test_corrected_variant_and_rejected_target_generate_expected_feedback(
    db_session: Session,
) -> None:
    seed = _seed_tenant(db_session, "org-b")
    corrected, positive = confirm_identity_decision(
        db_session,
        actor=seed.actor,
        org_id=seed.organization.id,
        project_id=seed.project.id,
        raw_observation_id=seed.observation.id,
        decision_type="corrected",
        chosen_asset_variant_id=seed.variant.id,
        command_id=uuid.uuid4(),
    )
    rejected, negative = confirm_identity_decision(
        db_session,
        actor=seed.actor,
        org_id=seed.organization.id,
        project_id=seed.project.id,
        raw_observation_id=seed.observation.id,
        decision_type="rejected",
        chosen_alias_id=seed.alias.id,
        rejection_reason="  Không đúng chủng loại  ",
        command_id=uuid.uuid4(),
    )

    assert corrected.chosen_asset_variant_id == seed.variant.id
    assert positive is not None and positive.target_type == "AssetVariant"
    assert rejected.rejection_reason == "Không đúng chủng loại"
    assert negative is not None and negative.target_type == "AssetAlias"
    assert negative.feedback_metadata["rejection_reason"] == "Không đúng chủng loại"


def test_deferred_decision_has_no_target_or_feedback(db_session: Session) -> None:
    seed = _seed_tenant(db_session, "org-c")
    decision, feedback = confirm_identity_decision(
        db_session,
        actor=seed.actor,
        org_id=seed.organization.id,
        project_id=seed.project.id,
        raw_observation_id=seed.observation.id,
        decision_type="deferred",
        command_id=uuid.uuid4(),
    )
    assert decision.decision_type == "deferred"
    assert feedback is None


def test_exact_idempotent_replay_returns_same_decision_and_feedback(db_session: Session) -> None:
    seed = _seed_tenant(db_session, "org-d")
    command_id = uuid.uuid4()
    first, first_feedback = confirm_identity_decision(
        db_session,
        actor=seed.actor,
        org_id=seed.organization.id,
        project_id=seed.project.id,
        raw_observation_id=seed.observation.id,
        decision_type="accepted",
        chosen_canonical_asset_id=seed.canonical.id,
        command_id=command_id,
    )
    replay, replay_feedback = confirm_identity_decision(
        db_session,
        actor=seed.actor,
        org_id=seed.organization.id,
        project_id=seed.project.id,
        raw_observation_id=seed.observation.id,
        decision_type="accepted",
        chosen_canonical_asset_id=seed.canonical.id,
        command_id=command_id,
    )

    assert replay.id == first.id
    assert replay_feedback is not None and first_feedback is not None
    assert replay_feedback.id == first_feedback.id
    assert db_session.query(AssetIdentityDecision).count() == 1
    assert db_session.query(LearningFeedbackEvent).count() == 1
    assert db_session.query(AuditEvent).filter_by(entity_id=first.id).count() == 1


def test_idempotency_key_reuse_with_different_intent_is_rejected(db_session: Session) -> None:
    seed = _seed_tenant(db_session, "org-e")
    command_id = uuid.uuid4()
    confirm_identity_decision(
        db_session,
        actor=seed.actor,
        org_id=seed.organization.id,
        project_id=seed.project.id,
        raw_observation_id=seed.observation.id,
        decision_type="accepted",
        chosen_canonical_asset_id=seed.canonical.id,
        command_id=command_id,
    )
    with pytest.raises(HTTPException) as exc_info:
        confirm_identity_decision(
            db_session,
            actor=seed.actor,
            org_id=seed.organization.id,
            project_id=seed.project.id,
            raw_observation_id=seed.observation.id,
            decision_type="accepted",
            chosen_asset_variant_id=seed.variant.id,
            command_id=command_id,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error_code"] == "idempotency_key_reused"
    assert db_session.query(AssetIdentityDecision).count() == 1


def test_permission_denial_is_durable_and_creates_no_decision(db_session: Session) -> None:
    seed = _seed_tenant(db_session, "org-f")
    viewer = _seed_viewer(db_session, seed)

    with pytest.raises(HTTPException) as exc_info:
        confirm_identity_decision(
            db_session,
            actor=viewer,
            org_id=seed.organization.id,
            project_id=seed.project.id,
            raw_observation_id=seed.observation.id,
            decision_type="accepted",
            chosen_canonical_asset_id=seed.canonical.id,
            command_id=uuid.uuid4(),
        )

    assert exc_info.value.status_code == 403
    assert db_session.query(AssetIdentityDecision).count() == 0
    assert db_session.query(SecurityEvent).filter_by(event_type="authorization_denied").count() == 1
    assert db_session.query(SecurityAuditLog).filter_by(action_type="authorization_denied").count() == 1


def test_cross_tenant_project_is_non_disclosing_and_security_audited(db_session: Session) -> None:
    tenant_a = _seed_tenant(db_session, "org-g")
    tenant_b = _seed_tenant(db_session, "org-h")

    with pytest.raises(HTTPException) as exc_info:
        confirm_identity_decision(
            db_session,
            actor=tenant_a.actor,
            org_id=tenant_a.organization.id,
            project_id=tenant_b.project.id,
            raw_observation_id=tenant_b.observation.id,
            decision_type="accepted",
            chosen_canonical_asset_id=tenant_b.canonical.id,
            command_id=uuid.uuid4(),
        )

    assert exc_info.value.status_code == 404
    failed = db_session.query(TenantBoundaryCheck).filter_by(result="fail").one()
    assert failed.resource_type == "Project"
    assert failed.resource_id == tenant_b.project.id
    event_row = db_session.query(SecurityEvent).filter_by(
        event_type="cross_tenant_access_attempt"
    ).one()
    assert event_row.severity == "high"
    assert db_session.query(SecurityAuditLog).filter_by(
        action_type="tenant_boundary_check_failed"
    ).count() == 1
    assert db_session.query(AssetIdentityDecision).count() == 0


@pytest.mark.parametrize(
    ("decision_type", "target_kwargs", "reason", "expected_code"),
    [
        ("accepted", {}, None, "identity_decision_target_invalid"),
        ("deferred", {"chosen_canonical_asset_id": uuid.uuid4()}, None, "identity_decision_target_invalid"),
        ("rejected", {"chosen_canonical_asset_id": uuid.uuid4()}, "   ", "identity_rejection_reason_required"),
        ("rejected", {"chosen_canonical_asset_id": uuid.uuid4()}, "reason", "contextual_alias_decision_invalid"),
    ],
)
def test_invalid_command_shapes_fail_before_mutation(
    db_session: Session,
    decision_type: str,
    target_kwargs: dict,
    reason: str | None,
    expected_code: str,
) -> None:
    seed = _seed_tenant(db_session, f"shape-{expected_code[-8:]}-{uuid.uuid4().hex[:4]}")
    with pytest.raises(HTTPException) as exc_info:
        confirm_identity_decision(
            db_session,
            actor=seed.actor,
            org_id=seed.organization.id,
            project_id=seed.project.id,
            raw_observation_id=seed.observation.id,
            decision_type=decision_type,
            create_contextual_alias=(expected_code == "contextual_alias_decision_invalid"),
            rejection_reason=reason,
            command_id=uuid.uuid4(),
            **target_kwargs,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == expected_code
    assert db_session.query(AssetIdentityDecision).count() == 0


def test_database_composite_fk_rejects_cross_tenant_project_ownership(db_session: Session) -> None:
    tenant_a = _seed_tenant(db_session, "org-i")
    tenant_b = _seed_tenant(db_session, "org-j")
    invalid = AssetIdentityDecision(
        organization_id=tenant_a.organization.id,
        customer_id=tenant_a.customer.id,
        project_id=tenant_b.project.id,
        raw_observation_id=tenant_a.observation.id,
        decision_type="accepted",
        chosen_canonical_asset_id=tenant_a.canonical.id,
        actor_user_id=tenant_a.actor.id,
        command_id=uuid.uuid4(),
    )
    db_session.add(invalid)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert db_session.query(AssetIdentityDecision).count() == 0
