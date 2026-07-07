import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, exc, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus,
    User, UserStatus, Customer,
    TaxonomyNode, TaxonomyNodeLevel, TaxonomyStatus,
    AssetFamily, AssetFamilyStatus,
    CanonicalAsset, CanonicalAssetStatus,
    AssetVariant, AssetVariantStatus,
    Project, ProjectWorkflowStatus,
    EvidenceFile, EvidenceFileStatus, EvidenceSensitivityLevel,
    TechnicalSpecification, TechnicalSpecificationVersion, TechnicalSpecificationVersionStatus,
    KnowledgeVersion, KnowledgeVersionStatus, KnowledgeType, KnowledgeLineage
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
        Base.metadata.drop_all(bind=engine)


def test_table_registration() -> None:
    tables = Base.metadata.tables
    assert "technical_specifications" in tables
    assert "technical_specification_versions" in tables
    assert "knowledge_versions" in tables
    assert "knowledge_lineage" in tables

    # Assert forbidden AppraisedPrice and workflow tables are NOT present in metadata
    forbidden_tables = [
        "appraised_price_decisions",
        "knowledge_queue_items",
        "knowledge_conflicts",
        "knowledge_confidence"
    ]
    for table in forbidden_tables:
        assert table not in tables


@pytest.fixture
def setup_seed_data(db_session: Session):
    org = OrganizationProfile(legal_name="Org", organization_slug="org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    db_session.commit()

    user = User(organization_id=org.id, email="curator@test.com", full_name="Curator User", status=UserStatus.ACTIVE)
    db_session.add(user)
    db_session.commit()

    customer = Customer(organization_id=org.id, legal_name="Cust 1", status="active", created_by=user.id)
    db_session.add(customer)
    db_session.commit()

    tax = TaxonomyNode(
        level=TaxonomyNodeLevel.GROUP,
        code="TRANS",
        name_vi="Transformers",
        status=TaxonomyStatus.ACTIVE,
        created_by=user.id
    )
    db_session.add(tax)
    db_session.commit()

    family = AssetFamily(
        taxonomy_node_id=tax.id,
        code="TRANSFORMER",
        name_vi="Transformer Family",
        status=AssetFamilyStatus.ACTIVE
    )
    db_session.add(family)
    db_session.commit()

    canon = CanonicalAsset(
        asset_family_id=family.id,
        primary_taxonomy_node_id=tax.id,
        standard_name="ABB Transformer 110kV Standard",
        status=CanonicalAssetStatus.ACTIVE
    )
    db_session.add(canon)
    db_session.commit()

    proj = Project(
        organization_id=org.id,
        code="PROJ-2026",
        name="Project 2026",
        status=ProjectWorkflowStatus.DRAFT,
        customer_id=customer.id,
        created_by=user.id
    )
    db_session.add(proj)
    db_session.commit()

    ev_file = EvidenceFile(
        filename="datasheet.pdf",
        mime_type="application/pdf",
        file_size=10240,
        object_key="uploads/datasheet.pdf",
        checksum="datasheethash",
        sensitivity_level=EvidenceSensitivityLevel.NORMAL,
        uploaded_by=user.id
    )
    db_session.add(ev_file)
    db_session.commit()

    return {
        "user_id": user.id,
        "canon_id": canon.id,
        "project_id": proj.id,
        "evidence_id": ev_file.id
    }


def test_technical_specification_persistence(db_session: Session, setup_seed_data) -> None:
    spec = TechnicalSpecification(
        canonical_asset_id=setup_seed_data["canon_id"],
        created_by=setup_seed_data["user_id"]
    )
    db_session.add(spec)
    db_session.commit()

    # Create two versions of the technical spec
    v1 = TechnicalSpecificationVersion(
        technical_specification_id=spec.id,
        version_number=1,
        attribute_values={"power_rating_kva": 63000, "cooling_type": "ONAN"},
        source_evidence_ids=[str(setup_seed_data["evidence_id"])],
        source_project_id=setup_seed_data["project_id"],
        confidence_score=0.9500,
        status=TechnicalSpecificationVersionStatus.ACTIVE,
        created_by=setup_seed_data["user_id"]
    )
    db_session.add(v1)
    db_session.commit()

    # Test unique constraint on version_number per spec
    v1_dup = TechnicalSpecificationVersion(
        technical_specification_id=spec.id,
        version_number=1,
        attribute_values={"power_rating_kva": 63000},
        status=TechnicalSpecificationVersionStatus.DRAFT,
        created_by=setup_seed_data["user_id"]
    )
    db_session.add(v1_dup)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Create v2 as draft
    v2 = TechnicalSpecificationVersion(
        technical_specification_id=spec.id,
        version_number=2,
        attribute_values={"power_rating_kva": 80000, "cooling_type": "ONAF"},
        source_evidence_ids=[str(setup_seed_data["evidence_id"])],
        source_project_id=setup_seed_data["project_id"],
        confidence_score=0.9000,
        status=TechnicalSpecificationVersionStatus.DRAFT,
        created_by=setup_seed_data["user_id"]
    )
    db_session.add(v2)
    db_session.commit()

    db_session.expire_all()
    q_spec = db_session.query(TechnicalSpecification).filter(TechnicalSpecification.id == spec.id).one()
    assert len(db_session.query(TechnicalSpecificationVersion).filter(TechnicalSpecificationVersion.technical_specification_id == spec.id).all()) == 2
    assert q_spec.canonical_asset_id == setup_seed_data["canon_id"]


def test_knowledge_version_registry(db_session: Session, setup_seed_data) -> None:
    spec = TechnicalSpecification(
        canonical_asset_id=setup_seed_data["canon_id"],
        created_by=setup_seed_data["user_id"]
    )
    db_session.add(spec)
    db_session.commit()

    v1 = TechnicalSpecificationVersion(
        technical_specification_id=spec.id,
        version_number=1,
        attribute_values={"power": "63kVA"},
        created_by=setup_seed_data["user_id"]
    )
    db_session.add(v1)
    db_session.commit()

    # Register in KnowledgeVersion registry without copying payload attributes
    kv = KnowledgeVersion(
        knowledge_type=KnowledgeType.TECHNICAL_SPEC,
        target_id=spec.id,
        concrete_version_id=v1.id,
        version_number=1,
        canonical_asset_id=setup_seed_data["canon_id"],
        source_project_id=setup_seed_data["project_id"],
        source_evidence_ids=[str(setup_seed_data["evidence_id"])],
        status=KnowledgeVersionStatus.ACTIVE,
        confidence_score=0.9800
    )
    db_session.add(kv)
    db_session.commit()

    db_session.expire_all()
    q_kv = db_session.query(KnowledgeVersion).filter(KnowledgeVersion.concrete_version_id == v1.id).one()
    assert q_kv.knowledge_type == KnowledgeType.TECHNICAL_SPEC
    assert q_kv.version_number == 1
    assert q_kv.canonical_asset_id == setup_seed_data["canon_id"]
    # Ensure attributes payload is not duplicated
    assert not hasattr(q_kv, "attribute_values")


def test_knowledge_lineage_append_only(db_session: Session, setup_seed_data) -> None:
    lineage = KnowledgeLineage(
        knowledge_type=KnowledgeType.TECHNICAL_SPEC,
        target_id=uuid.uuid4(),
        concrete_version_id=uuid.uuid4(),
        event_type="catalog_import",
        source_project_id=setup_seed_data["project_id"],
        source_evidence_ids=[str(setup_seed_data["evidence_id"])],
        actor_user_id=setup_seed_data["user_id"],
        notes="Imported from verified vendor datasheets."
    )
    db_session.add(lineage)
    db_session.commit()

    db_session.expire_all()
    q_lineage = db_session.query(KnowledgeLineage).filter(KnowledgeLineage.id == lineage.id).one()
    assert q_lineage.event_type == "catalog_import"
    assert q_lineage.notes == "Imported from verified vendor datasheets."
    assert q_lineage.created_at is not None


def test_knowledge_parent_deletion_restrict(db_session: Session, setup_seed_data) -> None:
    spec = TechnicalSpecification(
        canonical_asset_id=setup_seed_data["canon_id"],
        created_by=setup_seed_data["user_id"]
    )
    db_session.add(spec)
    db_session.commit()

    v1 = TechnicalSpecificationVersion(
        technical_specification_id=spec.id,
        version_number=1,
        attribute_values={"power": "63kVA"},
        created_by=setup_seed_data["user_id"]
    )
    db_session.add(v1)
    db_session.commit()

    # Attempting to delete TechnicalSpecification must fail due to foreign key RESTRICT on TechnicalSpecificationVersion
    db_session.delete(spec)
    with pytest.raises(exc.IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_migration_chain() -> None:
    import importlib.util
    import os
    
    filepath = os.path.join(os.path.dirname(__file__), "../alembic/versions/a87a9b6da99b_create_technical_specification_knowledge_tables.py")
    spec = importlib.util.spec_from_file_location("migration_a87a9b6da99b", filepath)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    
    assert migration.revision == "a87a9b6da99b"
    assert migration.down_revision == "a87a9b6da99a"
