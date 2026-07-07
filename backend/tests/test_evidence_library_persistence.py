import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, exc, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus,
    User, UserStatus,
    EvidenceSource, EvidenceSourceType,
    EvidenceFile, EvidenceFileStatus, EvidenceSensitivityLevel,
    EvidenceLink, EvidenceAccessLog, EvidenceAccessType
)

@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
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
    # 1. Verify expected tables are registered in Metadata
    tables = Base.metadata.tables
    assert "evidence_sources" in tables
    assert "evidence_files" in tables
    assert "evidence_links" in tables
    assert "evidence_access_logs" in tables

    # 2. Confirm future workflow tables are NOT present in this scope
    forbidden_tables = [
        "knowledge_queue_items",
        "knowledge_conflicts",
        "knowledge_confidence"
    ]
    for table in forbidden_tables:
        assert table not in tables


def test_evidence_source_persistence(db_session: Session) -> None:
    source = EvidenceSource(
        name="Vendor Portal v1",
        source_type=EvidenceSourceType.SUPPLIER,
        description="Core supplier quote intake portal"
    )
    db_session.add(source)
    db_session.commit()

    db_session.expire_all()
    queried = db_session.query(EvidenceSource).filter(EvidenceSource.name == "Vendor Portal v1").one()
    assert queried.source_type == EvidenceSourceType.SUPPLIER
    assert queried.id is not None
    assert queried.created_at is not None


def test_evidence_file_immutability_and_enums(db_session: Session) -> None:
    # Seed uploader user
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()
    user = User(organization_id=org.id, email="uploader@test.com", full_name="Uploader User", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    # 1. Create file with restricted sensitivity
    ev_file = EvidenceFile(
        filename="quote_110kv.pdf",
        mime_type="application/pdf",
        file_size=102450,
        object_key="uploads/quote_110kv_abc123.pdf",
        checksum="sha256:d57b1f3c306",
        sensitivity_level=EvidenceSensitivityLevel.RESTRICTED,
        status=EvidenceFileStatus.ACTIVE,
        uploaded_by=user.id
    )
    db_session.add(ev_file)
    db_session.commit()

    db_session.expire_all()
    q_file = db_session.query(EvidenceFile).filter(EvidenceFile.filename == "quote_110kv.pdf").one()
    assert q_file.mime_type == "application/pdf"
    assert q_file.file_size == 102450
    assert q_file.object_key == "uploads/quote_110kv_abc123.pdf"
    assert q_file.checksum == "sha256:d57b1f3c306"
    assert q_file.sensitivity_level == EvidenceSensitivityLevel.RESTRICTED
    assert q_file.status == EvidenceFileStatus.ACTIVE
    assert q_file.row_version == 1


def test_evidence_link_soft_delete(db_session: Session) -> None:
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()
    user = User(organization_id=org.id, email="creator@test.com", full_name="Creator User", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    ev_file = EvidenceFile(
        filename="specs.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size=20480,
        object_key="uploads/specs.xlsx",
        checksum="md5:a1b2c3d4",
        sensitivity_level=EvidenceSensitivityLevel.NORMAL,
        uploaded_by=user.id
    )
    db_session.add(ev_file)
    db_session.commit()

    # Link to a mock target
    target_uuid = uuid.uuid4()
    link = EvidenceLink(
        evidence_file_id=ev_file.id,
        target_type="technical_specification_version",
        target_id=target_uuid,
        created_by=user.id
    )
    db_session.add(link)
    db_session.commit()

    # Verify link target columns
    assert link.target_type == "technical_specification_version"
    assert link.target_id == target_uuid
    assert link.is_deleted is False

    # Soft delete (unlink)
    link.is_deleted = True
    link.deleted_by = user.id
    link.deleted_at = datetime.now(timezone.utc)
    link.delete_reason = "Duplicate connection"
    db_session.commit()

    db_session.expire_all()
    q_link = db_session.query(EvidenceLink).filter(EvidenceLink.id == link.id).one()
    assert q_link.is_deleted is True
    assert q_link.deleted_by == user.id
    assert q_link.delete_reason == "Duplicate connection"
    assert q_link.deleted_at is not None

    # Verify the underlying file is still present and not deleted
    assert db_session.query(EvidenceFile).filter(EvidenceFile.id == ev_file.id).count() == 1


def test_evidence_access_log_fields(db_session: Session) -> None:
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()
    user = User(organization_id=org.id, email="accessor@test.com", full_name="Accessor User", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    ev_file = EvidenceFile(
        filename="sensitive.pdf",
        mime_type="application/pdf",
        file_size=5000,
        object_key="uploads/sensitive.pdf",
        checksum="hash123",
        sensitivity_level=EvidenceSensitivityLevel.SENSITIVE,
        uploaded_by=user.id
    )
    db_session.add(ev_file)
    db_session.commit()

    log = EvidenceAccessLog(
        evidence_file_id=ev_file.id,
        accessed_by=user.id,
        access_type=EvidenceAccessType.DOWNLOAD,
        access_reason="Audit request verification",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0"
    )
    db_session.add(log)
    db_session.commit()

    db_session.expire_all()
    q_log = db_session.query(EvidenceAccessLog).filter(EvidenceAccessLog.evidence_file_id == ev_file.id).one()
    assert q_log.access_type == EvidenceAccessType.DOWNLOAD
    assert q_log.access_reason == "Audit request verification"
    assert q_log.ip_address == "192.168.1.100"
    assert q_log.user_agent == "Mozilla/5.0"
    assert q_log.accessed_at is not None


def test_parent_deletion_restrict_constraints(db_session: Session) -> None:
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()
    user = User(organization_id=org.id, email="audit@test.com", full_name="Audit User", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    ev_file = EvidenceFile(
        filename="restrict.pdf",
        mime_type="application/pdf",
        file_size=123,
        object_key="uploads/restrict.pdf",
        checksum="hashrestrict",
        uploaded_by=user.id
    )
    db_session.add(ev_file)
    db_session.commit()

    link = EvidenceLink(
        evidence_file_id=ev_file.id,
        target_type="test",
        target_id=uuid.uuid4(),
        created_by=user.id
    )
    db_session.add(link)
    db_session.commit()

    # Attempting to delete EvidenceFile must fail because ondelete is RESTRICT
    db_session.delete(ev_file)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_migration_chain() -> None:
    import importlib.util
    import os
    
    # Load migration file dynamically to prevent ModuleNotFoundError in test environment path
    filepath = os.path.join(os.path.dirname(__file__), "../alembic/versions/a87a9b6da999_create_evidence_core_tables.py")
    spec = importlib.util.spec_from_file_location("migration_a87a9b6da999", filepath)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    
    assert migration.revision == "a87a9b6da999"
    assert migration.down_revision == "a87a9b6da998"
