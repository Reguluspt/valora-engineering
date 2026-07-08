import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Security
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app.core.rbac import require_permission
from app.core.audit import log_audit_event
from app.modules.project_master_data.models import (
    User, WorkbenchSession, WorkbenchSessionStatus, WorkbenchLayout,
    AssetGridView, WorkbenchSelection, InlineEditDraft, InlineEditDraftStatus,
    AutosaveCheckpoint, UndoRedoStackEntry, UndoRedoActionType, PanelState,
    ReviewQueueView, WorkbenchNotification, Project, UserActionLog
)
from app.modules.project_master_data.workbench_schemas import (
    WorkbenchSessionCreate, WorkbenchSessionSchema, WorkbenchSessionHeartbeatRequest,
    WorkbenchLayoutSave, WorkbenchLayoutSchema, AssetGridViewSave, AssetGridViewSchema,
    WorkbenchSelectionSave, WorkbenchSelectionSchema, InlineEditDraftCreate, InlineEditDraftSchema,
    AutosaveCheckpointCreate, AutosaveCheckpointSchema, UndoRedoStackEntrySchema,
    PanelStateSave, PanelStateSchema, WorkbenchNotificationSchema
)

router = APIRouter(prefix="/api/v1/workbench", tags=["Workbench"])


# Helper to log user action
def log_action(db: Session, user_id: uuid.UUID, action_type: str, target_type: str, target_id: uuid.UUID, payload: dict):
    serialized_payload = {}
    for k, v in payload.items():
        if isinstance(v, uuid.UUID):
            serialized_payload[k] = str(v)
        else:
            serialized_payload[k] = v

    log = UserActionLog(
        user_id=user_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        action_payload=serialized_payload
    )
    db.add(log)


@router.post("/sessions", response_model=WorkbenchSessionSchema, status_code=201)
def create_session(
    data: WorkbenchSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:open"))
):
    proj = db.query(Project).filter(Project.id == data.project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    session = WorkbenchSession(
        user_id=current_user.id,
        project_id=data.project_id,
        status=WorkbenchSessionStatus.ACTIVE
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    log_audit_event(
        db=db,
        event_name="WORKBENCH_SESSION_START",
        entity_type="workbench_session",
        entity_id=session.id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "session_start", "workbench_session", session.id, {})
    db.commit()

    return session


@router.get("/sessions/{session_id}", response_model=WorkbenchSessionSchema)
def get_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:read"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions/{session_id}/heartbeat", response_model=WorkbenchSessionSchema)
def session_heartbeat(
    session_id: uuid.UUID,
    req: WorkbenchSessionHeartbeatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.row_version != req.expected_row_version:
        raise HTTPException(status_code=409, detail="Stale row version")

    session.last_active_at = datetime.now(timezone.utc)
    session.row_version += 1
    db.commit()
    db.refresh(session)

    log_action(db, current_user.id, "heartbeat", "workbench_session", session.id, {})
    db.commit()

    return session


@router.post("/sessions/{session_id}/layout", response_model=WorkbenchLayoutSchema)
def save_layout(
    session_id: uuid.UUID,
    layout_data: WorkbenchLayoutSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    layout = db.query(WorkbenchLayout).filter(
        WorkbenchLayout.user_id == current_user.id,
        WorkbenchLayout.layout_name == layout_data.layout_name
    ).first()

    if layout:
        layout.layout_payload = layout_data.layout_payload
        layout.is_default = layout_data.is_default
    else:
        layout = WorkbenchLayout(
            user_id=current_user.id,
            layout_name=layout_data.layout_name,
            layout_payload=layout_data.layout_payload,
            is_default=layout_data.is_default
        )
        db.add(layout)

    db.commit()
    db.refresh(layout)

    log_audit_event(
        db=db,
        event_name="WORKBENCH_LAYOUT_SAVE",
        entity_type="workbench_layout",
        entity_id=layout.id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "layout_save", "workbench_layout", layout.id, {})
    db.commit()

    return layout


@router.get("/sessions/{session_id}/grid-view", response_model=List[AssetGridViewSchema])
def list_grid_views(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:read"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return db.query(AssetGridView).filter(AssetGridView.user_id == current_user.id).all()


@router.post("/sessions/{session_id}/grid-view", response_model=AssetGridViewSchema)
def save_grid_view(
    session_id: uuid.UUID,
    grid_data: AssetGridViewSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    view = db.query(AssetGridView).filter(
        AssetGridView.user_id == current_user.id,
        AssetGridView.view_name == grid_data.view_name
    ).first()

    if view:
        view.columns = grid_data.columns
        view.filters = grid_data.filters
        view.sort = grid_data.sort
        view.is_default = grid_data.is_default
    else:
        view = AssetGridView(
            user_id=current_user.id,
            project_id=session.project_id,
            view_name=grid_data.view_name,
            columns=grid_data.columns,
            filters=grid_data.filters,
            sort=grid_data.sort,
            is_default=grid_data.is_default
        )
        db.add(view)

    db.commit()
    db.refresh(view)
    return view


@router.post("/sessions/{session_id}/selection", response_model=WorkbenchSelectionSchema)
def save_selection(
    session_id: uuid.UUID,
    data: WorkbenchSelectionSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    sel = db.query(WorkbenchSelection).filter(
        WorkbenchSelection.session_id == session_id,
        WorkbenchSelection.selected_target_type == data.selected_target_type
    ).first()

    if sel:
        sel.selected_target_ids = data.selected_target_ids
        sel.updated_at = datetime.now(timezone.utc)
    else:
        sel = WorkbenchSelection(
            session_id=session_id,
            selected_target_type=data.selected_target_type,
            selected_target_ids=data.selected_target_ids
        )
        db.add(sel)

    # Update session selection cache too
    session.current_selection = {"target_type": data.selected_target_type, "target_ids": data.selected_target_ids}
    db.commit()
    db.refresh(sel)

    log_action(db, current_user.id, "selection_update", "workbench_selection", sel.id, {"target_type": data.selected_target_type})
    db.commit()

    return sel


@router.get("/sessions/{session_id}/selection", response_model=List[WorkbenchSelectionSchema])
def get_selection(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:read"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return db.query(WorkbenchSelection).filter(WorkbenchSelection.session_id == session_id).all()


@router.post("/sessions/{session_id}/inline-edit", response_model=InlineEditDraftSchema)
def save_inline_edit(
    session_id: uuid.UUID,
    data: InlineEditDraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session or session.status != WorkbenchSessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Invalid or inactive session")

    # Save to draft only (does not mutate ProjectAssetLine official table)
    draft = InlineEditDraft(
        session_id=session_id,
        target_type=data.target_type,
        target_id=data.target_id,
        field_key=data.field_key,
        draft_value=data.draft_value,
        base_value=data.base_value,
        base_row_version=data.base_row_version,
        status=InlineEditDraftStatus.DRAFT
    )
    db.add(draft)

    # Add stack entry for undo/redo
    max_seq = db.query(func.max(UndoRedoStackEntry.sequence_no)).filter(UndoRedoStackEntry.session_id == session_id).scalar() or 0
    stack = UndoRedoStackEntry(
        session_id=session_id,
        sequence_no=max_seq + 1,
        target_type=data.target_type,
        target_id=data.target_id,
        field_key=data.field_key,
        after_value=data.draft_value,
        before_value=data.base_value,
        action_type=UndoRedoActionType.EDIT
    )
    db.add(stack)

    db.commit()
    db.refresh(draft)

    log_action(db, current_user.id, "inline_draft_creation", "inline_edit_draft", draft.id, {"field_key": data.field_key})
    db.commit()

    return draft


@router.get("/sessions/{session_id}/inline-edits", response_model=List[InlineEditDraftSchema])
def list_inline_edits(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:read"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return db.query(InlineEditDraft).filter(InlineEditDraft.session_id == session_id).all()


@router.post("/sessions/{session_id}/checkpoint", response_model=AutosaveCheckpointSchema)
def save_checkpoint(
    session_id: uuid.UUID,
    data: AutosaveCheckpointCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    checkpoint = AutosaveCheckpoint(
        session_id=session_id,
        checkpoint_payload=data.checkpoint_payload
    )
    db.add(checkpoint)
    db.commit()
    db.refresh(checkpoint)

    log_action(db, current_user.id, "checkpoint_creation", "autosave_checkpoint", checkpoint.id, {})
    db.commit()

    return checkpoint


@router.post("/sessions/{session_id}/undo", response_model=UndoRedoStackEntrySchema)
def execute_undo(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:undo_redo"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    entry = db.query(UndoRedoStackEntry).filter(
        UndoRedoStackEntry.session_id == session_id,
        UndoRedoStackEntry.is_undone == False
    ).order_by(UndoRedoStackEntry.sequence_no.desc()).first()

    if not entry:
        raise HTTPException(status_code=400, detail="Nothing to undo")

    entry.is_undone = True
    db.commit()
    db.refresh(entry)

    log_action(db, current_user.id, "undo", "undo_redo_stack_entry", entry.id, {"sequence_no": entry.sequence_no})
    db.commit()

    return entry


@router.post("/sessions/{session_id}/redo", response_model=UndoRedoStackEntrySchema)
def execute_redo(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:undo_redo"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    entry = db.query(UndoRedoStackEntry).filter(
        UndoRedoStackEntry.session_id == session_id,
        UndoRedoStackEntry.is_undone == True
    ).order_by(UndoRedoStackEntry.sequence_no.asc()).first()

    if not entry:
        raise HTTPException(status_code=400, detail="Nothing to redo")

    entry.is_undone = False
    db.commit()
    db.refresh(entry)

    log_action(db, current_user.id, "redo", "undo_redo_stack_entry", entry.id, {"sequence_no": entry.sequence_no})
    db.commit()

    return entry


@router.post("/sessions/{session_id}/panel-state", response_model=PanelStateSchema)
def save_panel_state(
    session_id: uuid.UUID,
    data: PanelStateSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    panel = db.query(PanelState).filter(
        PanelState.session_id == session_id,
        PanelState.panel_type == data.panel_type
    ).first()

    if panel:
        panel.is_expanded = data.is_expanded
        panel.width = data.width
        panel.updated_at = datetime.now(timezone.utc)
    else:
        panel = PanelState(
            session_id=session_id,
            panel_type=data.panel_type,
            is_expanded=data.is_expanded,
            width=data.width
        )
        db.add(panel)

    db.commit()
    db.refresh(panel)
    return panel


@router.get("/sessions/{session_id}/panel-state", response_model=List[PanelStateSchema])
def list_panel_states(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:read"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return db.query(PanelState).filter(PanelState.session_id == session_id).all()


@router.get("/sessions/{session_id}/notifications", response_model=List[WorkbenchNotificationSchema])
def list_notifications(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:read"))
):
    session = db.query(WorkbenchSession).filter(WorkbenchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return db.query(WorkbenchNotification).filter(
        WorkbenchNotification.user_id == current_user.id
    ).all()
