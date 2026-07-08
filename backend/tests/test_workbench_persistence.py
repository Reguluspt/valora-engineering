import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, exc, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, User, UserStatus, Project, ProjectWorkflowStatus, Customer,
    WorkbenchSession, WorkbenchSessionStatus,
    WorkbenchLayout,
    AssetGridView,
    WorkbenchSelection,
    InlineEditDraft, InlineEditDraftStatus,
    AutosaveCheckpoint,
    UndoRedoStackEntry, UndoRedoActionType,
    PanelState, WorkbenchPanelType,
    ReviewQueueView,
    WorkbenchNotification, WorkbenchNotificationType
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
    tables = Base.metadata.tables
    assert "workbench_sessions" in tables
    assert "workbench_layouts" in tables
    assert "asset_grid_views" in tables
    assert "workbench_selections" in tables
    assert "inline_edit_drafts" in tables
    assert "autosave_checkpoints" in tables
    assert "undo_redo_stack_entries" in tables
    assert "panel_states" in tables
    assert "review_queue_views" in tables
    assert "workbench_notifications" in tables

    # Assert no ChangeRequest tables
    assert "change_requests" not in tables


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

    return {
        "user_id": user.id,
        "project_id": proj.id
    }


def test_workbench_session_persistence(db_session: Session, setup_seed_data) -> None:
    # 1. Create a session with row_version
    session = WorkbenchSession(
        user_id=setup_seed_data["user_id"],
        project_id=setup_seed_data["project_id"],
        status=WorkbenchSessionStatus.ACTIVE,
        current_selection={"selected_rows": [str(uuid.uuid4())]}
    )
    db_session.add(session)
    db_session.commit()

    assert session.row_version == 1
    assert session.status == WorkbenchSessionStatus.ACTIVE
    assert "selected_rows" in session.current_selection


def test_workbench_layout_and_views(db_session: Session, setup_seed_data) -> None:
    # 1. Save custom layout
    layout = WorkbenchLayout(
        user_id=setup_seed_data["user_id"],
        layout_name="My Custom Workspace",
        layout_payload={"panels": ["knowledge", "lineage"], "sizes": [400, 300]}
    )
    db_session.add(layout)

    # 2. Save grid view
    grid_view = AssetGridView(
        user_id=setup_seed_data["user_id"],
        project_id=setup_seed_data["project_id"],
        view_name="Transformer Review View",
        columns={"standard_name": True, "brand": False},
        filters={"status": "draft"}
    )
    db_session.add(grid_view)
    db_session.commit()

    db_session.expire_all()
    q_layout = db_session.query(WorkbenchLayout).filter(WorkbenchLayout.id == layout.id).one()
    assert q_layout.layout_payload == {"panels": ["knowledge", "lineage"], "sizes": [400, 300]}


def test_ephemeral_workbench_actions(db_session: Session, setup_seed_data) -> None:
    session = WorkbenchSession(
        user_id=setup_seed_data["user_id"],
        project_id=setup_seed_data["project_id"]
    )
    db_session.add(session)
    db_session.commit()

    # 1. WorkbenchSelection
    sel = WorkbenchSelection(
        session_id=session.id,
        selected_target_type="project_asset_line",
        selected_target_ids=[str(uuid.uuid4())]
    )
    db_session.add(sel)

    # 2. InlineEditDraft
    draft = InlineEditDraft(
        session_id=session.id,
        target_type="project_asset_line",
        target_id=uuid.uuid4(),
        field_key="standard_name",
        draft_value={"val": "ABB Transformer Revised"},
        status=InlineEditDraftStatus.DRAFT
    )
    db_session.add(draft)

    # 3. AutosaveCheckpoint
    checkpoint = AutosaveCheckpoint(
        session_id=session.id,
        checkpoint_payload={"drafts": [{"field": "standard_name"}]}
    )
    db_session.add(checkpoint)

    # 4. UndoRedoStackEntry
    entry = UndoRedoStackEntry(
        session_id=session.id,
        sequence_no=1,
        target_type="project_asset_line",
        target_id=uuid.uuid4(),
        action_type=UndoRedoActionType.EDIT
    )
    db_session.add(entry)

    # 5. PanelState
    panel = PanelState(
        session_id=session.id,
        panel_type=WorkbenchPanelType.LINEAGE_VIEWER,
        is_expanded=True
    )
    db_session.add(panel)
    db_session.commit()

    db_session.expire_all()
    assert db_session.query(InlineEditDraft).filter(InlineEditDraft.session_id == session.id).count() == 1


def test_workbench_cascading_deletes(db_session: Session, setup_seed_data) -> None:
    # Ephemeral session-owned child rows should cascade delete when session is dropped
    session = WorkbenchSession(
        user_id=setup_seed_data["user_id"],
        project_id=setup_seed_data["project_id"]
    )
    db_session.add(session)
    db_session.commit()

    sel = WorkbenchSelection(
        session_id=session.id,
        selected_target_type="project_asset_line",
        selected_target_ids=[str(uuid.uuid4())]
    )
    db_session.add(sel)
    db_session.commit()
    sel_id = sel.id

    # Drop session
    db_session.delete(session)
    db_session.commit()

    # Assert selection is cascade deleted
    assert db_session.query(WorkbenchSelection).filter(WorkbenchSelection.id == sel_id).count() == 0


def test_migration_chain() -> None:
    import importlib.util
    import os
    
    filepath = os.path.join(os.path.dirname(__file__), "../alembic/versions/a87a9b6da9a0_create_workbench_tables.py")
    spec = importlib.util.spec_from_file_location("migration_a87a9b6da9a0", filepath)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    
    assert migration.revision == "a87a9b6da9a0"
    assert migration.down_revision == "a87a9b6da99f"
