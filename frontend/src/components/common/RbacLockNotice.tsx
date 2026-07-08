import React from "react";

interface RbacLockNoticeProps {
  permission: string;
}

export function RbacLockNotice({ permission }: RbacLockNoticeProps) {
  return (
    <div style={{
      backgroundColor: "rgba(220,53,69,0.15)",
      color: "var(--status-error)",
      border: "1px solid var(--status-error)",
      borderRadius: "var(--radius-md)",
      padding: "var(--space-md)",
      fontSize: "var(--font-size-sm)",
      marginBottom: "var(--space-md)"
    }}>
      🔒 <strong>Access Restrained:</strong> Your role lack the required scope (<code>{permission}</code>). 
      Workbench saving and commit functions are locked. Action buttons remain disabled.
    </div>
  );
}
