import React from "react";
import { ReviewRole } from "./ReviewQueueTypes";

interface RoleGateNoticeProps {
  currentRole: ReviewRole | null;
  requiredRoles: ReviewRole[];
}

export function RoleGateNotice({ currentRole, requiredRoles }: RoleGateNoticeProps) {
  const isAuthorized = currentRole !== null && requiredRoles.includes(currentRole);

  if (isAuthorized) {
    return (
      <div style={{ fontSize: "var(--font-size-xs)", color: "var(--status-approved)", marginBottom: "var(--space-md)" }}>
        Đã xác thực vai trò <strong>{currentRole?.toUpperCase()}</strong>.
      </div>
    );
  }

  return (
    <div style={{ padding: "var(--space-md)", border: "1px solid var(--status-blocking)", borderRadius: "var(--radius-md)", backgroundColor: "rgba(155, 44, 44, 0.1)", marginBottom: "var(--space-md)", fontSize: "var(--font-size-xs)" }}>
      <span style={{ color: "var(--status-error)", fontWeight: 600 }}>Chưa đủ quyền thao tác</span>
      <p style={{ margin: "var(--space-xs) 0 0 0", color: "var(--text-muted)" }}>
        {currentRole === null
          ? "Hệ thống chưa xác nhận vai trò của người dùng. Các thao tác thay đổi dữ liệu đang bị khóa."
          : <>Vai trò <strong>{currentRole}</strong> không có quyền thực hiện thao tác này. Các nút thay đổi dữ liệu đang bị khóa.</>}
      </p>
    </div>
  );
}
