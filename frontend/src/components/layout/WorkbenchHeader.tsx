import React from "react";
import { StatusBadge } from "../common/StatusBadge";

interface WorkbenchHeaderProps {
  projectTitle: string;
  status: "draft" | "review" | "approved" | "warning" | "error" | "blocking";
  statusLabel: string;
}

export function WorkbenchHeader({ projectTitle, status, statusLabel }: WorkbenchHeaderProps) {
  return (
    <header className="workbench-header">
      <h2 className="project-title">{projectTitle}</h2>
      <div className="project-status-bar">
        <span>Status:</span>
        <StatusBadge status={status} label={statusLabel} />
        <button className="action-btn" disabled title="Requires backend session state">
          Submit QC [Disabled]
        </button>
      </div>
    </header>
  );
}
