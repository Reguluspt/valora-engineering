import uuid
from typing import Optional
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.rbac import get_current_user
from app.modules.project_master_data.models import (
    User, WorkbenchSession, WorkbenchSessionStatus, Project, ProjectAssetLine
)

def raise_safe_404():
    raise HTTPException(
        status_code=404,
        detail={
            "title": "Không tìm thấy",
            "message": "Không tìm thấy phiên làm việc hoặc bạn không có quyền truy cập.",
            "nextAction": "Vui lòng kiểm tra lại đường dẫn hoặc liên hệ với Quản trị viên để được hỗ trợ.",
            "severity": "error",
            "retryable": False
        }
    )

def require_owned_workbench_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    require_active: bool = True,
    expected_project_id: Optional[uuid.UUID] = None
) -> WorkbenchSession:
    # 1. Query session, join Project, and enforce scoping directly in SQL
    query = (
        db.query(WorkbenchSession)
        .join(Project, Project.id == WorkbenchSession.project_id)
        .filter(
            WorkbenchSession.id == session_id,
            WorkbenchSession.user_id == current_user.id,
            Project.organization_id == current_user.organization_id,
        )
    )

    if expected_project_id is not None:
        query = query.filter(
            WorkbenchSession.project_id == expected_project_id
        )

    if require_active:
        query = query.filter(
            WorkbenchSession.status == WorkbenchSessionStatus.ACTIVE
        )

    session = query.first()
    if session is None:
        raise_safe_404()

    return session


def resolve_workbench_target(
    target_type: str,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    db: Session
):
    if target_type != "project_asset_line":
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Loại đối tượng không hợp lệ",
                "message": "Loại đối tượng chỉnh sửa không hợp lệ.",
                "nextAction": "Vui lòng liên hệ với Quản trị viên để được hỗ trợ.",
                "severity": "error",
                "retryable": False
            }
        )

    line = db.query(ProjectAssetLine).filter(
        ProjectAssetLine.id == target_id,
        ProjectAssetLine.project_id == project_id
    ).first()
    if not line:
        raise HTTPException(
            status_code=404,
            detail={
                "title": "Không tìm thấy đối tượng",
                "message": "Không tìm thấy đối tượng chỉnh sửa trong hồ sơ hiện tại.",
                "nextAction": "Vui lòng liên hệ với Quản trị viên để được hỗ trợ.",
                "severity": "error",
                "retryable": False
            }
        )
    return line
