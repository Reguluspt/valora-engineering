"""S15-R-001 tests for tenant-safe paired dossier creation."""
from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.ai_governance_security.models import SecurityEvent, TenantBoundaryCheck
from app.modules.document_engine_intelligence.application.dossier_bundle_service import (
    DossierSourceSpec,
    create_paired_dossier_bundle,
)
from app.modules.excel_import.models import DossierBundle, DossierSourceFile
from app.modules.project_master_data.models import (
    AuditEvent,
    Customer,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    Role,
    User,
    UserRole,
    UserStatus,
)


@dataclass(frozen=True)
class TenantSeed:
    organization: OrganizationProfile
    actor: User
    viewer: User
    customer: Customer
    project: Project


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
    organization = OrganizationProfile(
        legal_name=f"Organization {slug}",
        organization_slug=slug,
        status=OrganizationStatus.ACTIVE,
    )
    creator_role = Role(
        code=f"dossier-creator-{slug}",
        display_name=f"Dossier creator {slug}",
        permissions=["document_intelligence:job:create"],
    )
    viewer_role = Role(
        code=f"dossier-viewer-{slug}",
        display_name=f"Dossier viewer {slug}",
        permissions=[],
    )
    db.add_all([organization, creator_role, viewer_role])
    db.commit()

    actor = User(
        organization_id=organization.id,
        email=f"creator-{slug}@example.test",
        full_name=f"Creator {slug}",
        status=UserStatus.ACTIVE,
    )
    viewer = User(
        organization_id=organization.id,
        email=f"viewer-{slug}@example.test",
        full_name=f"Viewer {slug}",
        status=UserStatus.ACTIVE,
    )
    db.add_all([actor, viewer])
    db.commit()
    db.add_all(
        [
            UserRole(user_id=actor.id, role_id=creator_role.id, is_active=True),
            UserRole(user_id=viewer.id, role_id=viewer_role.id, is_active=True),
        ]
    )
    db.commit()

    customer = Customer(
        organization_id=organization.id,
        legal_name=f"Customer {slug}",
        status="active",
        created_by=actor.id,
    )
    db.add(customer)
    db.commit()
    project = Project(
        organization_id=organization.id,
        customer_id=customer.id,
        code=f"PRJ-{slug}",
        name=f"Project {slug}",
        created_by=actor.id,
    )
    db.add(project)
    db.commit()
    return TenantSeed(organization, actor, viewer, customer, project)


def _sources(suffix: str = "1") -> list[DossierSourceSpec]:
    return [
        DossierSourceSpec(
            file_role="customer_asset_list",
            file_name=f"Danh_sach_tai_san_{suffix}.xlsx",
            file_size_bytes=102_400,
            checksum_sha256="a" * 64,
            storage_object_key=f"verified/{suffix}/assets.xlsx",
        ),
        DossierSourceSpec(
            file_role="final_appraisal_report",
            file_name=f"Bao_cao_tham_dinh_{suffix}.docx",
            file_size_bytes=204_800,
            checksum_sha256="b" * 64,
            storage_object_key=f"verified/{suffix}/report.docx",
        ),
        DossierSourceSpec(
            file_role="supplier_quote",
            file_name=f"Bao_gia_A_{suffix}.pdf",
            file_size_bytes=30_000,
            checksum_sha256="c" * 64,
            storage_object_key=f"verified/{suffix}/quote-a.pdf",
        ),
        DossierSourceSpec(
            file_role="supplier_quote",
            file_name=f"Bao_gia_B_{suffix}.pdf",
            file_size_bytes=31_000,
            checksum_sha256="d" * 64,
            storage_object_key=f"verified/{suffix}/quote-b.pdf",
        ),
    ]


def test_create_source_backed_dossier_with_atomic_audit(db_session: Session) -> None:
    seed = _seed_tenant(db_session, "alpha")

    bundle, source_files = create_paired_dossier_bundle(
        db_session,
        actor=seed.actor,
        org_id=seed.organization.id,
        customer_id=seed.customer.id,
        project_id=seed.project.id,
        bundle_code="HS-2026-VAL-001",
        files=_sources(),
        correlation_id="corr-dossier-001",
    )

    assert bundle.status == "pending"
    assert bundle.organization_id == seed.organization.id
    assert bundle.customer_id == seed.customer.id
    assert bundle.project_id == seed.project.id
    assert len(source_files) == 4
    assert [item.file_role for item in source_files].count("supplier_quote") == 2
    audit = db_session.query(AuditEvent).filter_by(entity_id=bundle.id).one()
    assert audit.event_name == "DossierBundleCreated"
    assert audit.actor_user_id == seed.actor.id
    assert "storage_object_key" not in (audit.payload or {})
    assert (
        db_session.query(TenantBoundaryCheck)
        .filter_by(organization_id=seed.organization.id, result="pass")
        .count()
        == 2
    )


def test_primary_pair_and_verified_metadata_are_required(db_session: Session) -> None:
    seed = _seed_tenant(db_session, "validation")
    incomplete = _sources()[:1]

    with pytest.raises(HTTPException) as exc_info:
        create_paired_dossier_bundle(
            db_session,
            actor=seed.actor,
            org_id=seed.organization.id,
            customer_id=seed.customer.id,
            project_id=None,
            bundle_code="HS-MISSING-REPORT",
            files=incomplete,
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error_code"] == "paired_primary_sources_required"

    with pytest.raises(HTTPException) as raw_dict_error:
        create_paired_dossier_bundle(
            db_session,
            actor=seed.actor,
            org_id=seed.organization.id,
            customer_id=seed.customer.id,
            project_id=None,
            bundle_code="HS-RAW-METADATA",
            files=[{"file_role": "customer_asset_list"}],  # type: ignore[list-item]
        )
    assert raw_dict_error.value.detail["error_code"] == "verified_source_metadata_required"


def test_bundle_code_is_idempotent_only_for_exact_intent(db_session: Session) -> None:
    seed = _seed_tenant(db_session, "idempotent")
    kwargs = {
        "actor": seed.actor,
        "org_id": seed.organization.id,
        "customer_id": seed.customer.id,
        "project_id": seed.project.id,
        "bundle_code": "HS-IDEMPOTENT-001",
        "files": _sources("idem"),
    }
    first, _ = create_paired_dossier_bundle(db_session, **kwargs)
    second, _ = create_paired_dossier_bundle(db_session, **kwargs)
    assert second.id == first.id
    assert db_session.query(DossierBundle).count() == 1
    assert db_session.query(AuditEvent).filter_by(event_name="DossierBundleCreated").count() == 1

    changed = list(_sources("idem"))
    changed[-1] = DossierSourceSpec(
        file_role="supplier_quote",
        file_name="Bao_gia_B_idem.pdf",
        file_size_bytes=99_999,
        checksum_sha256="d" * 64,
        storage_object_key="verified/idem/quote-b.pdf",
    )
    with pytest.raises(HTTPException) as exc_info:
        create_paired_dossier_bundle(db_session, **{**kwargs, "files": changed})
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error_code"] == "dossier_idempotency_conflict"


def test_permission_and_cross_tenant_ownership_are_enforced(db_session: Session) -> None:
    first = _seed_tenant(db_session, "tenant-a")
    second = _seed_tenant(db_session, "tenant-b")

    with pytest.raises(HTTPException) as permission_error:
        create_paired_dossier_bundle(
            db_session,
            actor=first.viewer,
            org_id=first.organization.id,
            customer_id=first.customer.id,
            project_id=first.project.id,
            bundle_code="HS-NO-PERMISSION",
            files=_sources("viewer"),
        )
    assert permission_error.value.status_code == 403
    assert db_session.query(SecurityEvent).filter_by(event_type="authorization_denied").count() == 1

    with pytest.raises(HTTPException) as tenant_error:
        create_paired_dossier_bundle(
            db_session,
            actor=first.actor,
            org_id=first.organization.id,
            customer_id=second.customer.id,
            project_id=second.project.id,
            bundle_code="HS-CROSS-TENANT",
            files=_sources("cross"),
        )
    assert tenant_error.value.status_code == 404
    assert tenant_error.value.detail["error_code"] == "resource_not_found"
    assert (
        db_session.query(SecurityEvent)
        .filter_by(event_type="cross_tenant_access_attempt")
        .count()
        == 1
    )


def test_database_rejects_cross_tenant_source_file_fk(db_session: Session) -> None:
    first = _seed_tenant(db_session, "fk-a")
    second = _seed_tenant(db_session, "fk-b")
    bundle, _ = create_paired_dossier_bundle(
        db_session,
        actor=first.actor,
        org_id=first.organization.id,
        customer_id=first.customer.id,
        project_id=None,
        bundle_code="HS-FK-001",
        files=_sources("fk"),
    )
    db_session.add(
        DossierSourceFile(
            organization_id=second.organization.id,
            dossier_bundle_id=bundle.id,
            file_role="other_evidence",
            file_name="evidence.pdf",
            file_size_bytes=10,
            checksum_sha256="e" * 64,
            storage_object_key="verified/fk/evidence.pdf",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
