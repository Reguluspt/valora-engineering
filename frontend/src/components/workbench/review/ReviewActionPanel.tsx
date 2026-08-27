import React from "react";
import { ReviewQueueItem, ReviewRole } from "./ReviewQueueTypes";
import { RoleGateNotice } from "./RoleGateNotice";

interface ReviewActionPanelProps {
  item: ReviewQueueItem | null;
  currentRole: ReviewRole | null;
}

export function ReviewActionPanel({ item, currentRole }: ReviewActionPanelProps) {
  if (!item) {
    return (
      <div className="panel-tab">
        <h4 className="panel-tab-title">Thao tác rà soát</h4>
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>
          Chọn một nhiệm vụ để xem thông tin. Thao tác chính thức chỉ khả dụng sau khi hệ thống xác thực quyền.
        </p>
      </div>
    );
  }

  // Define role rules mapping visually
  // Viewers cannot do anything.
  // Appraisers cannot Approve/Reject (requires Reviewer/Admin).
  const isViewer = currentRole === null || currentRole === "viewer";
  const isAppraiser = currentRole === "appraiser";

  const claimAllowed = !isViewer;
  const decisionAllowed = !isViewer && !isAppraiser;

  return (
    <div className="panel-tab" style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
      <h4 className="panel-tab-title">Thao tác rà soát (ID: {item.id})</h4>
      
      {/* Show authorization status banner */}
      <RoleGateNotice currentRole={currentRole} requiredRoles={["owner", "admin", "reviewer"]} />

      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
        <button
          className="action-btn"
          disabled={!claimAllowed}
          title={!claimAllowed ? "Requires owner/admin/appraiser/reviewer/curator role privileges" : "Locally assign this review task"}
        >
          Nhận nhiệm vụ {!claimAllowed ? "[Khóa]" : ""}
        </button>

        <button
          className="action-btn"
          disabled={!decisionAllowed}
          style={{ borderColor: "var(--status-approved)", color: decisionAllowed ? "var(--status-approved)" : "var(--text-muted)" }}
          title={!decisionAllowed ? "Requires owner/admin/reviewer role privileges" : "Approve this item's values"}
        >
          Chấp nhận {!decisionAllowed ? "[Khóa]" : ""}
        </button>

        <button
          className="action-btn"
          disabled={!decisionAllowed}
          style={{ borderColor: "var(--status-error)", color: decisionAllowed ? "var(--status-error)" : "var(--text-muted)" }}
          title={!decisionAllowed ? "Requires owner/admin/reviewer role privileges" : "Reject this item's values"}
        >
          Từ chối {!decisionAllowed ? "[Khóa]" : ""}
        </button>

        <button
          className="action-btn"
          disabled={!decisionAllowed}
          title={!decisionAllowed ? "Requires owner/admin/reviewer role privileges" : "Defer this item"}
        >
          Để xử lý sau {!decisionAllowed ? "[Khóa]" : ""}
        </button>
      </div>
      
      <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", marginTop: "var(--space-sm)", borderTop: "1px dashed var(--border-color)", paddingTop: "var(--space-sm)" }}>
        Các nút hiện chỉ trình bày luồng rà soát và chưa thực hiện thay đổi trên máy chủ.
      </div>
    </div>
  );
}
