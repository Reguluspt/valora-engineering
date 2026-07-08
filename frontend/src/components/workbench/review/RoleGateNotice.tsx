import React from "react";
import { MockRole } from "./ReviewQueueTypes";

interface RoleGateNoticeProps {
  currentRole: MockRole;
  requiredRoles: MockRole[];
}

export function RoleGateNotice({ currentRole, requiredRoles }: RoleGateNoticeProps) {
  const isAuthorized = requiredRoles.includes(currentRole);

  if (isAuthorized) {
    return (
      <div style={{ fontSize: "var(--font-size-xs)", color: "var(--status-approved)", marginBottom: "var(--space-md)" }}>
        ✓ Authorized as <strong>{currentRole.toUpperCase()}</strong>.
      </div>
    );
  }

  return (
    <div style={{ padding: "var(--space-md)", border: "1px solid var(--status-blocking)", borderRadius: "var(--radius-md)", backgroundColor: "rgba(155, 44, 44, 0.1)", marginBottom: "var(--space-md)", fontSize: "var(--font-size-xs)" }}>
      <span style={{ color: "var(--status-error)", fontWeight: 600 }}>🔒 Role Restrict Notice</span>
      <p style={{ margin: "var(--space-xs) 0 0 0", color: "var(--text-muted)" }}>
        Your mock role (<strong>{currentRole}</strong>) lacks permissions: <code>{requiredRoles.join(", ")}</code>. UI modification controls remain disabled.
      </p>
    </div>
  );
}
