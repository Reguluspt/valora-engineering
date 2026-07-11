import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from decimal import Decimal, InvalidOperation
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.modules.project_master_data.models import (
    User,
    Project,
    ProjectWorkflowStatus,
    ProjectAssetLine,
    InlineEditDraft,
    WorkbenchSession,
    WorkbenchSessionStatus,
)
from app.modules.workflow_workbench.resolve_owned_session import require_owned_workbench_session
from app.core.audit import log_audit_event
from app.core.rbac import derive_effective_permissions


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
                "retryable": False,
            },
        )
    val_str = str(val)
    if len(val_str) > 5000:
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Độ dài không hợp lệ",
                "message": "Trường description không được vượt quá 5000 ký tự.",
                "nextAction": "Vui lòng rút ngắn mô tả.",
                "severity": "error",
                "retryable": False,
            },
        )
    return val_str


def validate_appraised_unit_price(val: Any) -> Optional[Decimal]:
    if val is None:
        return None

    # Reject boolean, list, dict, set, tuple
    if isinstance(val, bool) or isinstance(val, (list, dict, set, tuple)):
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Kiểu dữ liệu không hợp lệ",
                "message": "Trường appraised_unit_price phải là số thực hợp lệ.",
                "nextAction": "Vui lòng kiểm tra lại dữ liệu.",
                "severity": "error",
                "retryable": False,
            },
        )

    try:
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
                    "retryable": False,
                },
            )

        # Scale & Precision check for Numeric(15,2)
        # Max 13 integer digits, max 2 decimal places. No silent rounding.
        sign, digits, exponent = dec_val.as_tuple()
        if exponent < -2:
            raise HTTPException(
                status_code=400,
                detail={
                    "title": "Độ chính xác không hợp lệ",
                    "message": "Giá trị appraised_unit_price chỉ cho phép tối đa 2 chữ số thập phân và không được tự động làm tròn.",
                    "nextAction": "Vui lòng nhập giá trị hợp lệ.",
                    "severity": "error",
                    "retryable": False,
                },
            )

        int_part_digits = len(digits) + exponent if exponent >= 0 else len(digits) + exponent
        int_part_digits = max(0, int_part_digits)
        if int_part_digits > 13:
            raise HTTPException(
                status_code=400,
                detail={
                    "title": "Tràn số lượng chữ số",
                    "message": "Giá trị appraised_unit_price vượt quá giới hạn hệ thống cho phép.",
                    "nextAction": "Vui lòng giảm giá trị đơn giá.",
                    "severity": "error",
                    "retryable": False,
                },
            )

        return dec_val
    except (ValueError, InvalidOperation):
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Kiểu dữ liệu không hợp lệ",
                "message": "Trường appraised_unit_price phải là số thực hợp lệ.",
                "nextAction": "Vui lòng nhập lại số hợp lệ.",
                "severity": "error",
                "retryable": False,
            },
        )


FIELD_HANDLERS = {
    "description": validate_description,
    "appraised_unit_price": validate_appraised_unit_price,
}


def apply_description(line: ProjectAssetLine, val: Any) -> None:
    line.description = val


def apply_appraised_unit_price(line: ProjectAssetLine, val: Any) -> None:
    line.appraised_unit_price = val


MUTATION_REGISTRY = {
    "description": apply_description,
    "appraised_unit_price": apply_appraised_unit_price,
}


def raise_safe_404():
    raise HTTPException(
        status_code=404,
        detail={
            "title": "Không tìm thấy phiên làm việc",
            "message": "Phiên làm việc không tồn tại hoặc đã bị đóng.",
            "nextAction": "Vui lòng mở phiên làm việc mới.",
            "severity": "error",
            "retryable": False,
        },
    )


def execute_commit_asset_line_draft(
    db: Session,
    actor: User,
    project_id: uuid.UUID,
    line_id: uuid.UUID,
    field_keys: List[str],
    confirm: bool,
    version_token: str,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    # 1. Human confirmation check
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Thiếu xác nhận từ người dùng",
                "message": "Thao tác yêu cầu xác nhận xác thực từ người dùng (confirm=true).",
                "nextAction": "Vui lòng đánh dấu xác nhận để lưu.",
                "severity": "warning",
                "retryable": False,
            },
        )

    # Internal authorization enforcement
    perms = derive_effective_permissions(actor, db)
    if "workbench:edit" not in perms:
        raise HTTPException(
            status_code=403,
            detail={
                "title": "Không có quyền thực hiện",
                "message": "Tài khoản của bạn không được cấp quyền thực hiện thao tác này.",
                "nextAction": "Vui lòng liên hệ với Quản trị viên để được hỗ trợ.",
                "severity": "error",
                "retryable": False,
            },
        )

    # Parse version token strictly
    try:
        request_version = int(version_token)
        if request_version < 0:
            raise ValueError()
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Mã phiên bản không hợp lệ",
                "message": "Mã phiên bản phải là số nguyên dương hợp lệ.",
                "nextAction": "Vui lòng tải lại trang và thử lại.",
                "severity": "error",
                "retryable": False,
            },
        )

    # Validate field_keys
    if not field_keys:
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Danh sách trường trống",
                "message": "Danh sách các trường cần áp dụng không được để trống.",
                "nextAction": "Vui lòng chọn ít nhất một trường.",
                "severity": "error",
                "retryable": False,
            },
        )

    seen = set()
    for key in field_keys:
        if key in seen:
            raise HTTPException(
                status_code=400,
                detail={
                    "title": "Trường bị trùng lặp",
                    "message": f"Trường '{key}' bị trùng lặp trong yêu cầu.",
                    "nextAction": "Vui lòng loại bỏ các trường trùng lặp.",
                    "severity": "error",
                    "retryable": False,
                },
            )
        seen.add(key)
        if key not in MUTATION_REGISTRY:
            raise HTTPException(
                status_code=400,
                detail={
                    "title": "Trường không hỗ trợ",
                    "message": f"Trường {key} không được hỗ trợ lưu trữ chính thức.",
                    "nextAction": "Vui lòng liên hệ với Quản trị viên để được hỗ trợ.",
                    "severity": "error",
                    "retryable": False,
                },
            )

    # 2. Resolve project within organization context
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == actor.organization_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=404,
            detail={
                "title": "Không tìm thấy hồ sơ",
                "message": "Hồ sơ dự án không tồn tại hoặc không thuộc tổ chức của bạn.",
                "nextAction": "Vui lòng kiểm tra lại mã hồ sơ.",
                "severity": "error",
                "retryable": False,
            },
        )

    # 3. Resolve active session
    active_sess = (
        db.query(WorkbenchSession)
        .filter(
            WorkbenchSession.project_id == project_id,
            WorkbenchSession.user_id == actor.id,
            WorkbenchSession.status == WorkbenchSessionStatus.ACTIVE,
        )
        .first()
    )
    if not active_sess:
        raise_safe_404()

    session = require_owned_workbench_session(
        session_id=active_sess.id,
        db=db,
        current_user=actor,
        require_active=True,
        expected_project_id=project_id,
    )

    # 4. Resolve official asset line with PostgreSQL row lock
    line = (
        db.query(ProjectAssetLine)
        .filter(ProjectAssetLine.id == line_id, ProjectAssetLine.project_id == project_id)
        .with_for_update()
        .first()
    )
    if not line:
        raise HTTPException(
            status_code=404,
            detail={
                "title": "Không tìm thấy dòng tài sản",
                "message": "Dòng tài sản không tồn tại trong dự án hiện tại.",
                "nextAction": "Vui lòng kiểm tra lại.",
                "severity": "error",
                "retryable": False,
            },
        )

    # Enforce optimistic version lock
    if line.row_version != request_version:
        raise HTTPException(
            status_code=409,
            detail={
                "title": "Xung đột phiên bản",
                "message": "Dòng tài sản đã được cập nhật bởi một phiên làm việc khác.",
                "nextAction": "Vui lòng tải lại trang và thực hiện lại.",
                "severity": "warning",
                "retryable": True,
            },
        )

    # 5. Validate workflow status
    if project.status != ProjectWorkflowStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Trạng thái hồ sơ không hợp lệ",
                "message": "Chỉ cho phép cập nhật dòng tài sản khi hồ sơ ở trạng thái Bản nháp.",
                "nextAction": "Vui lòng đưa hồ sơ về bản nháp trước.",
                "severity": "error",
                "retryable": False,
            },
        )

    # 6. Load saved drafts matching targeted fields
    drafts = (
        db.query(InlineEditDraft)
        .filter(InlineEditDraft.session_id == session.id, InlineEditDraft.target_id == line_id)
        .all()
    )

    drafts_by_key = {d.field_key: d for d in drafts}
    drafts_to_commit = []

    for key in field_keys:
        draft = drafts_by_key.get(key)
        if not draft:
            raise HTTPException(
                status_code=400,
                detail={
                    "title": "Không tìm thấy bản nháp",
                    "message": f"Không có bản nháp nào được lưu cho trường {key}.",
                    "nextAction": "Vui lòng nhập giá trị nháp trước khi áp dụng.",
                    "severity": "error",
                    "retryable": False,
                },
            )

        # Verify base row version matches request version and line row version
        if draft.base_row_version != request_version:
            raise HTTPException(
                status_code=409,
                detail={
                    "title": "Xung đột phiên bản",
                    "message": "Không thể áp dụng bản nháp do dữ liệu chính thức đã thay đổi.",
                    "nextAction": "Vui lòng tải lại trang và thực hiện lại.",
                    "severity": "warning",
                    "retryable": True,
                },
            )
        drafts_to_commit.append(draft)

    # 8. Before values extraction & typed validation
    before_values = {}
    validated_values = {}
    for d in drafts_to_commit:
        key = d.field_key
        raw_before = getattr(line, key)
        if isinstance(raw_before, Decimal):
            before_values[key] = str(raw_before)
        else:
            before_values[key] = raw_before

        raw_val = d.draft_value.get("value") if isinstance(d.draft_value, dict) else d.draft_value
        handler = FIELD_HANDLERS[key]
        validated_val = handler(raw_val)
        validated_values[key] = validated_val

    # 9. Mutate values using explicit mutation registry
    for key, val in validated_values.items():
        MUTATION_REGISTRY[key](line, val)

    # 10. Increment version
    old_version = line.row_version
    new_version = old_version + 1
    line.row_version = new_version

    # 11. Delete applied drafts
    for d in drafts_to_commit:
        db.delete(d)

    # 12. Log audit event atomically within the transaction
    # Prepare serializable values converting Decimal to string
    serializable_before = {}
    for k, v in before_values.items():
        if isinstance(v, Decimal):
            serializable_before[k] = str(v)
        else:
            serializable_before[k] = v

    serializable_after = {}
    for k, v in validated_values.items():
        if isinstance(v, Decimal):
            serializable_after[k] = str(v)
        else:
            serializable_after[k] = v

    log_payload = {
        "session_id": str(session.id),
        "project_id": str(project_id),
        "asset_line_id": str(line_id),
        "field_keys": field_keys,
        "before_values": serializable_before,
        "after_values": serializable_after,
        "draft_base_version": old_version,
        "official_current_version": old_version,
        "official_new_version": new_version,
        "confirm": confirm,
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
        payload=log_payload,
    )

    db.flush()

    return {
        "project_id": project_id,
        "asset_line_id": line_id,
        "committed_fields": field_keys,
        "draft_status": "clean",
        "has_saved_draft": False,
        "has_unsaved_changes": False,
        "is_stale": False,
        "committed_at": line.updated_at or datetime.now(timezone.utc),
    }
