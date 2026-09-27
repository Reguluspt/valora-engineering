"""First-batch pointer and audit atomicity for the bounded G1.1A route."""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import projects as project_api
from app.db import Base
from app.modules.project_master_data.models import (
    AuditEvent,
    Customer,
    CustomerStatus,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    ProjectAssetImportBatch,
    ProjectWorkflowStatus,
    User,
    UserStatus,
)
from app.modules.project_master_data.workbench_schemas import ProjectAssetImportBatchCreate

@pytest.fixture(name="sqlite_db_session")
def _sqlite_db_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def _seed(db_session):
    suffix = uuid.uuid4().hex[:8]
    org = OrganizationProfile(
        legal_name=f"G1.1A Org {suffix}",
        organization_slug=f"g11a-{suffix}",
        status=OrganizationStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.flush()
    actor = User(
        organization_id=org.id,
        email=f"g11a-{suffix}@example.com",
        full_name="G1.1A Actor",
        status=UserStatus.ACTIVE,
    )
    db_session.add(actor)
    db_session.flush()
    customer = Customer(
        organization_id=org.id,
        legal_name="G1.1A Customer",
        status=CustomerStatus.ACTIVE,
        created_by=actor.id,
    )
    db_session.add(customer)
    db_session.flush()
    project = Project(
        organization_id=org.id,
        customer_id=customer.id,
        code=f"G11A-{suffix}",
        name="G1.1A Project",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=actor.id,
    )
    db_session.add(project)
    db_session.commit()
    return org, actor, project


def _create(db_session, actor, project, filename):
    return project_api.create_project_asset_import(
        project.id,
        ProjectAssetImportBatchCreate(source_filename=filename),
        db=db_session,
        current_user=actor,
    )


def test_first_batch_sets_pointer_and_audits_in_one_commit(sqlite_db_session):
    db_session = sqlite_db_session
    org, actor, project = _seed(db_session)
    before = project.row_version
    batch = _create(db_session, actor, project, "first.xlsx")
    db_session.refresh(project)
    assert project.current_preliminary_import_batch_id == batch.id
    assert project.row_version == before + 1
    assert db_session.query(ProjectAssetImportBatch).filter_by(project_id=project.id).count() == 1
    assert db_session.query(AuditEvent).filter_by(
        organization_id=org.id,
        event_name="ProjectAssetImportBatchCreated",
        entity_id=batch.id,
    ).count() == 1


def test_second_batch_does_not_switch_pointer_or_project_version(sqlite_db_session):
    db_session = sqlite_db_session
    _, actor, project = _seed(db_session)
    first = _create(db_session, actor, project, "first.xlsx")
    db_session.refresh(project)
    version = project.row_version
    second = _create(db_session, actor, project, "second.xlsx")
    db_session.refresh(project)
    assert second.id != first.id
    assert project.current_preliminary_import_batch_id == first.id
    assert project.row_version == version


def test_audit_failure_rolls_back_batch_and_pointer(sqlite_db_session, monkeypatch):
    db_session = sqlite_db_session
    org, actor, project = _seed(db_session)
    before = project.row_version

    def fail_audit(**_kwargs):
        raise RuntimeError("forced audit failure")

    monkeypatch.setattr(project_api, "log_audit_event", fail_audit)
    with pytest.raises(RuntimeError, match="forced audit failure"):
        _create(db_session, actor, project, "failed.xlsx")
    db_session.refresh(project)
    assert project.current_preliminary_import_batch_id is None
    assert project.row_version == before
    assert db_session.query(ProjectAssetImportBatch).filter_by(project_id=project.id).count() == 0
    assert db_session.query(AuditEvent).filter_by(
        organization_id=org.id, event_name="ProjectAssetImportBatchCreated"
    ).count() == 0


def test_commit_failure_rolls_back_batch_pointer_and_success_audit(sqlite_db_session, monkeypatch):
    db_session = sqlite_db_session
    org, actor, project = _seed(db_session)
    before = project.row_version

    def fail_commit():
        raise RuntimeError("forced commit failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="forced commit failure"):
        _create(db_session, actor, project, "failed-commit.xlsx")
    db_session.refresh(project)
    assert project.current_preliminary_import_batch_id is None
    assert project.row_version == before
    assert db_session.query(ProjectAssetImportBatch).filter_by(project_id=project.id).count() == 0
    assert db_session.query(AuditEvent).filter_by(
        organization_id=org.id, event_name="ProjectAssetImportBatchCreated"
    ).count() == 0


def test_ambiguous_legacy_null_pointer_stays_null_on_new_batch(sqlite_db_session):
    db_session = sqlite_db_session
    org, actor, project = _seed(db_session)
    db_session.add_all([
        ProjectAssetImportBatch(
            organization_id=org.id, project_id=project.id, source_filename=name,
            status="created", total_rows=0, valid_rows=0, invalid_rows=0,
            warning_rows=0, created_by_user_id=actor.id,
        )
        for name in ("legacy-a.xlsx", "legacy-b.xlsx")
    ])
    db_session.commit()
    _create(db_session, actor, project, "third.xlsx")
    db_session.refresh(project)
    assert project.current_preliminary_import_batch_id is None
