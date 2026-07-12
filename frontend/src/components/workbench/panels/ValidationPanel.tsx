import React from "react";
import { ValidationIssue } from "./ContextPanelTypes";

interface ValidationPanelProps {
  issues?: ValidationIssue[] | null;
}

export function ValidationPanel({ issues }: ValidationPanelProps) {
  if (issues === null || issues === undefined) {
    return (
      <div style={{ padding: "var(--space-md)" }}>
        <h4 className="panel-tab-title">Kiểm tra dữ liệu</h4>
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)", marginTop: "var(--space-sm)" }}>
          Chưa có dữ liệu kiểm tra. Chọn một dòng tài sản để kiểm tra.
        </p>
      </div>
    );
  }

  const blockingIssues = issues.filter((i) => i.severity === "blocking" || i.is_blocking);
  const otherIssues = issues.filter((i) => i.severity !== "blocking" && !i.is_blocking);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
      {blockingIssues.length > 0 && (
        <div style={{ padding: "var(--space-md)", border: "1px solid var(--status-blocking)", borderRadius: "var(--radius-md)", backgroundColor: "rgba(155, 44, 44, 0.15)" }}>
          <h4 style={{ color: "var(--status-error)", margin: "0 0 var(--space-xs) 0" }}>
            Có lỗi chặn thẩm định
          </h4>
          <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
            Các ràng buộc sau phải được giải quyết trước khi phê duyệt.
          </p>
        </div>
      )}

      <div className="panel-tab">
        <h4 className="panel-tab-title">Chi tiết kiểm tra</h4>
        {issues.length === 0 ? (
          <p style={{ color: "var(--status-approved)", fontSize: "var(--font-size-sm)" }}>
            Dòng này đáp ứng tất cả quy tắc kiểm tra.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
            {issues.map((issue) => (
              <div key={issue.id} style={{ display: "flex", flexDirection: "column", gap: "2px", padding: "var(--space-sm) 0", borderBottom: "1px solid var(--border-color)", fontSize: "var(--font-size-sm)" }}>
                <div style={{ display: "flex", gap: "var(--space-sm)", alignItems: "center" }}>
                  <span className={`badge badge-${issue.severity}`}>
                    {issue.severity}
                  </span>
                  <span style={{ fontWeight: 600 }}>{issue.category}</span>
                </div>
                <p style={{ margin: "4px 0 0 0" }}>{issue.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
