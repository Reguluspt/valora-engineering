"""PostgreSQL-only S14-R-001 migration and idempotency evidence."""
from __future__ import annotations

import os
import threading
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

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
    AssetFamily,
    AssetVariant,
    AuditEvent,
    CanonicalAsset,
    Customer,
    OrganizationProfile,
    Project,
    ProjectAssetImportBatch,
    Role,
    TaxonomyNode,
    User,
    UserRole,
)
from app.modules.taxonomy_asset_identity.application.identity_decision_service import (
    confirm_identity_decision,
)
from tests.test_s14_pr_003_identity_feedback import TenantSeed, _seed_tenant


def _postgres_engine_or_skip():
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url or not url.startswith("postgres"):
        if os.getenv("CI") == "true":
            pytest.fail("CI=true requires PostgreSQL TEST_DATABASE_URL for S14-R-001")
        pytest.skip("PostgreSQL is required for S14-R-001 migration/concurrency proof")
    engine = create_engine(url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT to_regclass('tenant_boundary_checks')")
        ).scalar_one()
    if exists is None:
        engine.dispose()
        if os.getenv("CI") == "true":
            pytest.fail("CI PostgreSQL is not migrated to the S14-R-001 head")
        pytest.skip("PostgreSQL schema is not migrated to the S14-R-001 head")
    return engine


def _cleanup(SessionLocal, seed: TenantSeed) -> None:
    db: Session = SessionLocal()
    try:
        org_id = seed.organization.id
        user_ids = [row[0] for row in db.query(User.id).filter_by(organization_id=org_id)]
        role_ids = [
            row[0]
            for row in db.query(UserRole.role_id).filter(UserRole.user_id.in_(user_ids)).all()
        ]
        family_id = seed.canonical.asset_family_id
        node_id = seed.canonical.primary_taxonomy_node_id

        db.query(ContextualAssetAlias).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(LearningFeedbackEvent).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(AuditEvent).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(TenantBoundaryCheck).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(SecurityAuditLog).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(SecurityEvent).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(AssetIdentityDecision).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(RawAssetObservation).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(WorkbookStructureSnapshot).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(ProjectAssetImportBatch).filter_by(organization_id=org_id).update(
            {ProjectAssetImportBatch.current_source_artifact_id: None},
            synchronize_session=False,
        )
        db.flush()
        db.query(ImportSourceArtifact).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(ProjectAssetImportBatch).filter_by(organization_id=org_id).delete(
            synchronize_session=False
        )
        db.query(Project).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(Customer).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(AssetAlias).filter_by(id=seed.alias.id).delete(synchronize_session=False)
        db.query(AssetVariant).filter_by(id=seed.variant.id).delete(synchronize_session=False)
        db.query(CanonicalAsset).filter_by(id=seed.canonical.id).delete(synchronize_session=False)
        db.query(AssetFamily).filter_by(id=family_id).delete(synchronize_session=False)
        db.query(TaxonomyNode).filter_by(id=node_id).delete(synchronize_session=False)
        if user_ids:
            db.query(UserRole).filter(UserRole.user_id.in_(user_ids)).delete(
                synchronize_session=False
            )
        db.query(User).filter_by(organization_id=org_id).delete(synchronize_session=False)
        db.query(OrganizationProfile).filter_by(id=org_id).delete(synchronize_session=False)
        if role_ids:
            db.query(Role).filter(Role.id.in_(role_ids)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_postgresql_identity_constraints_are_installed() -> None:
    engine = _postgres_engine_or_skip()
    try:
        inspector = inspect(engine)
        identity_fk_names = {
            item["name"] for item in inspector.get_foreign_keys("asset_identity_decisions")
        }
        identity_check_names = {
            item["name"] for item in inspector.get_check_constraints("asset_identity_decisions")
        }
        assert {
            "fk_identity_decision_actor_tenant",
            "fk_identity_decision_customer_tenant",
            "fk_identity_decision_observation_tenant",
            "fk_identity_decision_project_customer_tenant",
            "fk_identity_decision_canonical",
            "fk_identity_decision_variant",
            "fk_identity_decision_alias",
        } <= identity_fk_names
        assert {
            "chk_identity_decision_type",
            "chk_identity_decision_target_shape",
            "chk_identity_decision_rejection_reason",
        } <= identity_check_names
        assert inspector.has_table("tenant_boundary_checks")
        assert inspector.has_table("security_events")
        assert inspector.has_table("security_audit_logs")
    finally:
        engine.dispose()


def test_postgresql_concurrent_idempotent_replay_has_one_decision_feedback_and_audit() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    setup = SessionLocal()
    seed = None
    try:
        seed = _seed_tenant(setup, f"pg-{uuid.uuid4().hex[:10]}")
        ids = {
            "org": seed.organization.id,
            "actor": seed.actor.id,
            "project": seed.project.id,
            "observation": seed.observation.id,
            "canonical": seed.canonical.id,
            "command": uuid.uuid4(),
        }
    finally:
        setup.close()

    barrier = threading.Barrier(2, timeout=30)
    results: list[tuple[uuid.UUID, uuid.UUID]] = []
    errors: list[BaseException] = []

    def worker() -> None:
        db = SessionLocal()
        try:
            actor = db.get(User, ids["actor"])
            barrier.wait(timeout=30)
            decision, feedback = confirm_identity_decision(
                db,
                actor=actor,
                org_id=ids["org"],
                project_id=ids["project"],
                raw_observation_id=ids["observation"],
                decision_type="accepted",
                chosen_canonical_asset_id=ids["canonical"],
                command_id=ids["command"],
            )
            assert feedback is not None
            results.append((decision.id, feedback.id))
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    try:
        assert all(not thread.is_alive() for thread in threads)
        assert errors == []
        assert len(results) == 2 and len(set(results)) == 1
        verify = SessionLocal()
        try:
            decision = verify.query(AssetIdentityDecision).filter_by(
                organization_id=ids["org"], command_id=ids["command"]
            ).one()
            assert verify.query(LearningFeedbackEvent).filter_by(
                source_decision_id=decision.id
            ).count() == 1
            assert verify.query(AuditEvent).filter_by(
                entity_id=decision.id,
                command_name="ConfirmAssetIdentityDecision",
            ).count() == 1
        finally:
            verify.close()
    finally:
        if seed is not None:
            _cleanup(SessionLocal, seed)
        engine.dispose()
