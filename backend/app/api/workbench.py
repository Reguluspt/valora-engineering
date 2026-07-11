import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.db import get_db
from app.core.rbac import require_permission
from app.core.audit import log_audit_event
from app.modules.project_master_data.models import (
    User, WorkbenchSession, WorkbenchSessionStatus, WorkbenchLayout,
    AssetGridView, WorkbenchSelection, InlineEditDraft, InlineEditDraftStatus,
    AutosaveCheckpoint, UndoRedoStackEntry, UndoRedoActionType, PanelState,
    WorkbenchNotification, Project, UserActionLog
)
from app.modules.project_master_data.workbench_schemas import (
    WorkbenchSessionCreate, WorkbenchSessionSchema, WorkbenchSessionHeartbeatRequest,
    WorkbenchLayoutSave, WorkbenchLayoutSchema, AssetGridViewSave, AssetGridViewSchema,
    WorkbenchSelectionSave, WorkbenchSelectionSchema, InlineEditDraftCreate, InlineEditDraftSchema,
    AutosaveCheckpointCreate, AutosaveCheckpointSchema, UndoRedoStackEntrySchema,
    PanelStateSave, PanelStateSchema, WorkbenchNotificationSchema
)
from app.modules.workflow_workbench import (
    require_owned_workbench_session,
    resolve_workbench_target,
    raise_safe_404
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
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:open"))
):
    proj = db.query(Project).filter(
        Project.id == data.project_id,
        Project.organization_id == current_user.organization_id
    ).first()
    if not proj:
        raise_safe_404()

    # Enforce active session policy: resume if exists
    existing = db.query(WorkbenchSession).filter(
        WorkbenchSession.user_id == current_user.id,
        WorkbenchSession.project_id == data.project_id,
        WorkbenchSession.status == WorkbenchSessionStatus.ACTIVE
    ).first()
    if existing:
        response.status_code = 200
        return existing

    session = None
    try:
        with db.begin_nested():
            session = WorkbenchSession(
                user_id=current_user.id,
                project_id=data.project_id,
                status=WorkbenchSessionStatus.ACTIVE
            )
            db.add(session)
            db.flush()
    except IntegrityError as e:
        is_expected_constraint = False
        orig = getattr(e, "orig", None)
        diag = getattr(orig, "diag", None)
        constraint_name = getattr(diag, "constraint_name", None)
        if constraint_name == "uq_active_session_per_user_project":
            is_expected_constraint = True
        else:
            err_msg = str(e)
            if "uq_active_session_per_user_project" in err_msg:
                is_expected_constraint = True
            elif "workbench_sessions.user_id" in err_msg and "workbench_sessions.project_id" in err_msg:
                is_expected_constraint = True

        if not is_expected_constraint:
            db.rollback()
            raise e

        db.rollback()
        # Retrieve the session that won the concurrency race
        existing_concurrent = db.query(WorkbenchSession).filter(
            WorkbenchSession.user_id == current_user.id,
            WorkbenchSession.project_id == data.project_id,
            WorkbenchSession.status == WorkbenchSessionStatus.ACTIVE
        ).first()
        if existing_concurrent is None:
            raise e

        response.status_code = 200
        return existing_concurrent

    try:
        log_audit_event(
            db=db,
            event_name="workbench.session.started",
            entity_type="WorkbenchSession",
            entity_id=session.id,
            organization_id=proj.organization_id,
            actor_user_id=current_user.id,
            payload={
                "session_id": str(session.id),
                "project_id": str(proj.id),
                "before_status": None,
                "after_status": "active"
            }
        )
        log_action(db, current_user.id, "session_start", "workbench_session", session.id, {})
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(session)
    response.status_code = 201
    return session


@router.get("/sessions/{session_id}", response_model=WorkbenchSessionSchema)
def get_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:read"))
):
    return require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )


@router.post("/sessions/{session_id}/heartbeat", response_model=WorkbenchSessionSchema)
def session_heartbeat(
    session_id: uuid.UUID,
    req: WorkbenchSessionHeartbeatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    session = require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )

    if session.row_version != req.expected_row_version:
        raise HTTPException(
            status_code=409,
            detail={
                "title": "Xung đột phiên bản",
                "message": "Dữ liệu phiên làm việc đã bị thay đổi ở nơi khác.",
                "nextAction": "Vui lòng tải lại trang để đồng bộ dữ liệu mới nhất.",
                "severity": "warning",
                "retryable": True
            }
        )

    try:
        session.last_active_at = datetime.now(timezone.utc)
        session.row_version += 1
        db.flush()
        log_action(db, current_user.id, "heartbeat", "workbench_session", session.id, {})
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(session)

    return session


@router.post("/sessions/{session_id}/close", response_model=WorkbenchSessionSchema)
def close_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    session = require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=False
    )

    allowed_statuses = [WorkbenchSessionStatus.ACTIVE, WorkbenchSessionStatus.CLOSED]
    if session.status not in allowed_statuses:
        raise_safe_404()

    if session.status == WorkbenchSessionStatus.ACTIVE:
        try:
            before_status = session.status.value if hasattr(session.status, "value") else session.status
            session.status = WorkbenchSessionStatus.CLOSED
            log_audit_event(
                db=db,
                event_name="workbench.session.ended",
                entity_type="WorkbenchSession",
                entity_id=session.id,
                organization_id=session.project.organization_id,
                actor_user_id=current_user.id,
                payload={
                    "session_id": str(session.id),
                    "project_id": str(session.project_id),
                    "before_status": before_status,
                    "after_status": "closed",
                    "reason": "user_closed"
                }
            )
            log_action(db, current_user.id, "session_close", "workbench_session", session.id, {})
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(session)

    return session


@router.post("/sessions/{session_id}/layout", response_model=WorkbenchLayoutSchema)
def save_layout(
    session_id: uuid.UUID,
    layout_data: WorkbenchLayoutSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )

    layout = db.query(WorkbenchLayout).filter(
        WorkbenchLayout.user_id == current_user.id,
        WorkbenchLayout.layout_name == layout_data.layout_name
    ).first()

    try:
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
        db.flush()

        log_audit_event(
            db=db,
            event_name="WORKBENCH_LAYOUT_SAVE",
            entity_type="workbench_layout",
            entity_id=layout.id,
            actor_user_id=current_user.id
        )
        log_action(db, current_user.id, "layout_save", "workbench_layout", layout.id, {})
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(layout)

    return layout


@router.get("/sessions/{session_id}/grid-view", response_model=List[AssetGridViewSchema])
def list_grid_views(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:read"))
):
    session = require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )

    return db.query(AssetGridView).filter(
        AssetGridView.user_id == current_user.id,
        AssetGridView.project_id == session.project_id
    ).all()


@router.post("/sessions/{session_id}/grid-view", response_model=AssetGridViewSchema)
def save_grid_view(
    session_id: uuid.UUID,
    grid_data: AssetGridViewSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    session = require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )

    view = db.query(AssetGridView).filter(
        AssetGridView.user_id == current_user.id,
        AssetGridView.project_id == session.project_id,
        AssetGridView.view_name == grid_data.view_name
    ).first()

    try:
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
    except Exception:
        db.rollback()
        raise
    db.refresh(view)
    return view


@router.post("/sessions/{session_id}/selection", response_model=WorkbenchSelectionSchema)
def save_selection(
    session_id: uuid.UUID,
    data: WorkbenchSelectionSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    session = require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )

    # Validate target type
    allowed_types = ["project_asset_line"]
    if data.selected_target_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Loại đối tượng không được hỗ trợ",
                "message": "Loại đối tượng được chọn không được hỗ trợ.",
                "nextAction": "Vui lòng kiểm tra lại yêu cầu.",
                "severity": "error",
                "retryable": False
            }
        )

    # Validate target IDs
    if data.selected_target_ids:
        for tid_str in data.selected_target_ids:
            try:
                tid = uuid.UUID(tid_str)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "title": "Định dạng mã đối tượng không hợp lệ",
                        "message": "Mã đối tượng không đúng định dạng UUID.",
                        "nextAction": "Vui lòng kiểm tra lại yêu cầu.",
                        "severity": "error",
                        "retryable": False
                    }
                )
            resolve_workbench_target(data.selected_target_type, tid, session.project_id, db)

    sel = db.query(WorkbenchSelection).filter(
        WorkbenchSelection.session_id == session_id,
        WorkbenchSelection.selected_target_type == data.selected_target_type
    ).first()

    try:
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

        session.current_selection = {"target_type": data.selected_target_type, "target_ids": data.selected_target_ids}
        db.flush()

        log_action(db, current_user.id, "selection_update", "workbench_selection", sel.id, {"target_type": data.selected_target_type})
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(sel)

    return sel


@router.get("/sessions/{session_id}/selection", response_model=List[WorkbenchSelectionSchema])
def get_selection(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:read"))
):
    require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )

    return db.query(WorkbenchSelection).filter(WorkbenchSelection.session_id == session_id).all()


@router.post("/sessions/{session_id}/inline-edit", response_model=InlineEditDraftSchema)
def save_inline_edit(
    session_id: uuid.UUID,
    data: InlineEditDraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    session = require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )

    resolve_workbench_target(data.target_type, data.target_id, session.project_id, db)

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

    try:
        db.add(draft)
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
        db.flush()

        log_action(db, current_user.id, "inline_draft_creation", "inline_edit_draft", draft.id, {"field_key": data.field_key})
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(draft)

    return draft


@router.get("/sessions/{session_id}/inline-edits", response_model=List[InlineEditDraftSchema])
def list_inline_edits(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:read"))
):
    require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )

    return db.query(InlineEditDraft).filter(InlineEditDraft.session_id == session_id).all()


@router.post("/sessions/{session_id}/checkpoint", response_model=AutosaveCheckpointSchema)
def save_checkpoint(
    session_id: uuid.UUID,
    data: AutosaveCheckpointCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )

    checkpoint = AutosaveCheckpoint(
        session_id=session_id,
        checkpoint_payload=data.checkpoint_payload
    )

    try:
        db.add(checkpoint)
        db.flush()
        log_action(db, current_user.id, "checkpoint_creation", "autosave_checkpoint", checkpoint.id, {})
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(checkpoint)

    return checkpoint


@router.post("/sessions/{session_id}/undo", response_model=UndoRedoStackEntrySchema)
def execute_undo(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:undo_redo"))
):
    require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )

    entry = db.query(UndoRedoStackEntry).filter(
        UndoRedoStackEntry.session_id == session_id,
        UndoRedoStackEntry.is_undone == False
    ).order_by(UndoRedoStackEntry.sequence_no.desc()).first()

    if not entry:
        raise HTTPException(status_code=400, detail="Nothing to undo")

    try:
        entry.is_undone = True
        db.flush()
        log_action(db, current_user.id, "undo", "undo_redo_stack_entry", entry.id, {"sequence_no": entry.sequence_no})
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(entry)

    return entry


@router.post("/sessions/{session_id}/redo", response_model=UndoRedoStackEntrySchema)
def execute_redo(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:undo_redo"))
):
    require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )

    entry = db.query(UndoRedoStackEntry).filter(
        UndoRedoStackEntry.session_id == session_id,
        UndoRedoStackEntry.is_undone == True
    ).order_by(UndoRedoStackEntry.sequence_no.asc()).first()

    if not entry:
        raise HTTPException(status_code=400, detail="Nothing to redo")

    try:
        entry.is_undone = False
        db.flush()
        log_action(db, current_user.id, "redo", "undo_redo_stack_entry", entry.id, {"sequence_no": entry.sequence_no})
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(entry)

    return entry


@router.post("/sessions/{session_id}/panel-state", response_model=PanelStateSchema)
def save_panel_state(
    session_id: uuid.UUID,
    data: PanelStateSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )

    panel = db.query(PanelState).filter(
        PanelState.session_id == session_id,
        PanelState.panel_type == data.panel_type
    ).first()

    try:
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
    except Exception:
        db.rollback()
        raise
    db.refresh(panel)
    return panel


@router.get("/sessions/{session_id}/panel-state", response_model=List[PanelStateSchema])
def list_panel_states(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:read"))
):
    require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )

    return db.query(PanelState).filter(PanelState.session_id == session_id).all()


@router.get("/sessions/{session_id}/notifications", response_model=List[WorkbenchNotificationSchema])
def list_notifications(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:read"))
):
    require_owned_workbench_session(
        session_id=session_id,
        db=db,
        current_user=current_user,
        require_active=True
    )

    return db.query(WorkbenchNotification).filter(
        WorkbenchNotification.user_id == current_user.id,
        WorkbenchNotification.session_id == session_id
    ).all()
