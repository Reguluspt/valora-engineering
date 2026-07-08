import React, { useEffect, useState } from "react";
import { StatusBadge } from "../common/StatusBadge";
import { checkHealth } from "../../api/client";

interface WorkbenchHeaderProps {
  projectTitle: string;
  status: "draft" | "review" | "approved" | "warning" | "error" | "blocking";
  statusLabel: string;
}

export function WorkbenchHeader({ projectTitle, status, statusLabel }: WorkbenchHeaderProps) {
  const [apiReachable, setApiReachable] = useState<boolean | null>(null);

  useEffect(() => {
    checkHealth()
      .then((res) => {
        setApiReachable(res.status === "healthy");
      })
      .catch(() => {
        setApiReachable(false);
      });
  }, []);

  return (
    <header className="workbench-header">
      <h2 className="project-title">{projectTitle}</h2>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-md)" }}>
        {apiReachable !== null && (
          <span style={{
            fontSize: "var(--font-size-xs)",
            color: apiReachable ? "var(--status-approved)" : "var(--status-error)",
            padding: "2px 6px",
            border: `1px solid ${apiReachable ? "var(--status-approved)" : "var(--status-error)"}`,
            borderRadius: "var(--radius-sm)"
          }}>
            API: {apiReachable ? "Connected" : "Disconnected"}
          </span>
        )}
        <div className="project-status-bar">
          <span>Status:</span>
          <StatusBadge status={status} label={statusLabel} />
          <button className="action-btn" disabled title="Requires backend session state">
            Submit QC [Disabled]
          </button>
        </div>
      </div>
    </header>
  );
}
