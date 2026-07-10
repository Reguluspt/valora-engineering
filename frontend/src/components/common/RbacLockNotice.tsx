import React from "react";
import { getFriendlyError } from "../../errors/errorRegistry";

interface RbacLockNoticeProps {
  permission?: string;
}

export function RbacLockNotice({ permission }: RbacLockNoticeProps) {
  const friendly = getFriendlyError("forbidden");

  return (
    <div style={{
      backgroundColor: "rgba(220,53,69,0.15)",
      color: "var(--status-error)",
      border: "1px solid var(--status-error)",
      borderRadius: "var(--radius-md)",
      padding: "var(--space-md)",
      fontSize: "var(--font-size-sm)",
      marginBottom: "var(--space-md)",
      display: "flex",
      flexDirection: "column",
      gap: "var(--space-xs)"
    }}>
      <div>
        🔒 <strong>{friendly.title}</strong>
      </div>
      <div style={{ color: "var(--text-primary)" }}>
        {friendly.message}
      </div>
      <div style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>
        {friendly.nextAction}
      </div>
    </div>
  );
}
