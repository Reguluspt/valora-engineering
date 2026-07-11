import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from decimal import Decimal, InvalidOperation
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.modules.project_master_data.models import (
    User, Project, ProjectWorkflowStatus, ProjectAssetLine,
    InlineEditDraft, WorkbenchSession, WorkbenchSessionStatus
)
from app.modules.workflow_workbench.resolve_owned_session import require_owned_workbench_session
from app.core.audit import log_audit_event

def validate_description(val: Any) -> Optional[str]:
    if val is None:
        return None
    # Reject boolean, objects, arrays, numbers
    if isinstance(val, bool) or isinstance(val, (dict, list, int, float, Decimal)):
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Kiểu dữ liệu không hợp lệ",
                "message": "Trường description phải là chuỗi ký tự.",
                "nextAction": "Vui lòng kiểm tra lại dữ liệu gửi lên.",
                "severity": "error",
                "retryable": False
            }
        )
    val_str = str(val)
    # Check optional length constraints (e.g. max 5000 characters)
    if len(val_str) > 5000:
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Độ dài không hợp lệ",
                "message": "Trường description không được vượt quá 5000 ký tự.",
                "nextAction": "Vui lòng rút ngắn mô tả.",
                "severity": "error",
                "retryable": False
            }
        )
    return val_str

def validate_appraised_unit_price(val: Any) -> Optional[float]:
    if val is None:
        return None
    
    # Reject boolean, list, dict
    if isinstance(val, bool) or isinstance(val, (list, dict)):
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Kiểu dữ liệu không hợp lệ",
                "message": "Trường appraised_unit_price phải là số thực hợp lệ.",
                "nextAction": "Vui lòng kiểm tra lại dữ liệu.",
                "severity": "error",
                "retryable": False
            }
        )
    
    try:
        # Check if float/int is NaN or Infinity
        val_str = str(val).strip()
        if val_str.lower() in ("nan", "inf", "-inf", "infinity", "-infinity"):
            raise ValueError()
        
        dec_val = Decimal(val_str)
        if dec_val < 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "title": "Giá trị âm không hợp lệ",
                    "message": "Giá trị appraised_unit_price không được âm.",
                    "nextAction": "Vui lòng nhập giá trị dương.",
                    "severity": "error",
                    "retryable": False
                }
            )
        
        # Scale check: maximum 15 digits total, 2 decimal places
        # (Numeric(15,2) can hold up to 9999999999999.99)
        # Check integer part
        normalized = dec_val.normalize()
        sign, digits, exponent = normalized.as_tuple()
        if exponent < -2:
            # We allow it, but we round or reject based on database scale.
            # Let's reject if scale > 2 to prevent silent database truncations
            raise HTTPException(
                status_code=400,
                detail={
                    "title": "Độ chính xác không hợp lệ",
                    "message": "Giá trị appraised_unit_price chỉ cho phép tối đa 2 chữ số thập phân.",
                    "nextAction": "Vui lòng nhập giá trị hợp lệ.",
                    "severity": "error",
                    "retryable": False
                }
            )
        # Check precision
        integer_digits = len(digits) + exponent if exponent < 0 else len(digits) + exponent
        if integer_digits > 13:
            raise HTTPException(
                status_code=400,
                detail={
                    "title": "Tràn số lượng chữ số",
                    "message": "Giá trị appraised_unit_price vượt quá giới hạn hệ thống cho phép.",
                    "nextAction": "Vui lòng giảm giá trị đơn giá.",
                    "severity": "error",
                    "retryable": False
                }
            )
            
        return float(dec_val)
    except (ValueError, InvalidOperation):
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Kiểu dữ liệu không hợp lệ",
                "message": "Trường appraised_unit_price phải là số thực hợp lệ.",
                "nextAction": "Vui lòng nhập lại số hợp lệ.",
                "severity": "error",
                "retryable": False
            }
        )

FIELD_HANDLERS = {
    "description": validate_description,
    "appraised_unit_price": validate_appraised_unit_price
}

def execute_commit_asset_line_draft(
    db: Session,
    actor: User,
    project_id: uuid.UUID,
    line_id: uuid.UUID,
    field_keys: List[str],
    confirm: bool,
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    # 1. Human confirmation check (must be human confirmation API path)
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Thiếu xác nhận từ người dùng",
                "message": "Thao tác yêu cầu xác nhận xác thực từ người dùng (confirm=true).",
                "nextAction": "Vui lòng đánh dấu xác nhận để lưu.",
                "severity": "warning",
                "retryable": False
            }
        )

    # 2. Resolve project within organization context
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.organization_id == actor.organization_id
    ).first()
    if not project:
        # Return safe 404
        raise HTTPException(
            status_code=404,
            detail={
                "title": "Không tìm thấy hồ sơ",
                "message": "Hồ sơ dự án không tồn tại hoặc không thuộc tổ chức của bạn.",
                "nextAction": "Vui lòng kiểm tra lại mã hồ sơ.",
                "severity": "error",
                "retryable": False
            }
        )

    # 3. Resolve active session
    active_sess = db.query(WorkbenchSession).filter(
        WorkbenchSession.project_id == project_id,
        WorkbenchSession.user_id == actor.id,
        WorkbenchSession.status == WorkbenchSessionStatus.ACTIVE
    ).first()
    if not active_sess:
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Không tìm thấy phiên làm việc",
                "message": "Không tìm thấy phiên làm việc hoạt động cho hồ sơ này.",
                "nextAction": "Vui lòng mở lại phiên làm việc Workbench.",
                "severity": "error",
                "retryable": False
            }
        )

    session = require_owned_workbench_session(
        session_id=active_sess.id,
        db=db,
        current_user=actor,
        require_active=True,
        expected_project_id=project_id
    )

    # 4. Resolve official asset line
    line = db.query(ProjectAssetLine).filter(
        ProjectAssetLine.id == line_id,
        ProjectAssetLine.project_id == project_id
    ).first()
    if not line:
        raise HTTPException(
            status_code=404,
            detail={
                "title": "Không tìm thấy dòng tài sản",
                "message": "Dòng tài sản không tồn tại trong dự án hiện tại.",
                "nextAction": "Vui lòng kiểm tra lại.",
                "severity": "error",
                "retryable": False
            }
        )

    # 5. Validate workflow status (project status must be DRAFT)
    if project.status != ProjectWorkflowStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Trạng thái hồ sơ không hợp lệ",
                "message": "Chỉ cho phép cập nhật dòng tài sản khi hồ sơ ở trạng thái Bản nháp.",
                "nextAction": "Vui lòng đưa hồ sơ về bản nháp trước.",
                "severity": "error",
                "retryable": False
            }
        )

    # 6. Load saved drafts matching targeted fields
    drafts = db.query(InlineEditDraft).filter(
        InlineEditDraft.session_id == session.id,
        InlineEditDraft.target_id == line_id
    ).all()
    
    drafts_by_key = {d.field_key: d for d in drafts}
    drafts_to_commit = []
    
    for key in field_keys:
        if key not in FIELD_HANDLERS:
            raise HTTPException(
                status_code=400,
                detail={
                    "title": "Trường không hỗ trợ",
                    "message": f"Trường {key} không được hỗ trợ lưu trữ chính thức.",
                    "nextAction": "Vui lòng liên hệ với Quản trị viên để được hỗ trợ.",
                    "severity": "error",
                    "retryable": False
                }
            )
        
        draft = drafts_by_key.get(key)
        if not draft:
            raise HTTPException(
                status_code=400,
                detail={
                    "title": "Không tìm thấy bản nháp",
                    "message": f"Không có bản nháp nào được lưu cho trường {key}.",
                    "nextAction": "Vui lòng nhập giá trị nháp trước khi áp dụng.",
                    "severity": "error",
                    "retryable": False
                }
            )
        
        # 7. Exact optimistic lock version check
        if draft.base_row_version != line.row_version:
            raise HTTPException(
                status_code=409,
                detail={
                    "title": "Xung đột phiên bản",
                    "message": "Không thể áp dụng bản nháp do dữ liệu chính thức đã thay đổi.",
                    "nextAction": "Vui lòng tải lại trang và thực hiện lại.",
                    "severity": "warning",
                    "retryable": True
                }
            )
        drafts_to_commit.append(draft)

    # 8. Before values extraction & typed validation
    before_values = {}
    validated_values = {}
    for d in drafts_to_commit:
        key = d.field_key
        raw_before = getattr(line, key)
        if isinstance(raw_before, Decimal):
            before_values[key] = float(raw_before)
        else:
            before_values[key] = raw_before
            
        raw_val = d.draft_value.get("value") if isinstance(d.draft_value, dict) else d.draft_value
        # Strict handler invocation
        handler = FIELD_HANDLERS[key]
        validated_val = handler(raw_val)
        if isinstance(validated_val, Decimal):
            validated_values[key] = float(validated_val)
        else:
            validated_values[key] = validated_val

    # 9. Mutate values
    for key, val in validated_values.items():
        setattr(line, key, val)

    # 10. Increment version
    old_version = line.row_version
    new_version = old_version + 1
    line.row_version = new_version

    # 11. Delete applied drafts
    for d in drafts_to_commit:
        db.delete(d)

    # 12. Log audit event atomically within the transaction
    log_payload = {
        "session_id": str(session.id),
        "project_id": str(project_id),
        "asset_line_id": str(line_id),
        "field_keys": field_keys,
        "before_values": before_values,
        "after_values": validated_values,
        "draft_base_version": old_version,
        "official_current_version": old_version,
        "official_new_version": new_version,
        "confirm": confirm
    }
    
    log_audit_event(
        db=db,
        event_name="project.asset_line.draft_committed",
        entity_type="ProjectAssetLine",
        entity_id=line_id,
        organization_id=actor.organization_id,
        actor_user_id=actor.id,
        command_name="CommitProjectAssetLineDraft",
        correlation_id=correlation_id,
        payload=log_payload
    )

    # 13. Flush (but do not commit) so caller controls commit
    db.flush()
    
    return {
        "project_id": project_id,
        "asset_line_id": line_id,
        "committed_fields": field_keys,
        "draft_status": "clean",
        "has_saved_draft": False,
        "has_unsaved_changes": False,
        "is_stale": False,
        "committed_at": line.updated_at or datetime.now(timezone.utc)
    }
