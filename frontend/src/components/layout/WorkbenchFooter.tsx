import React from "react";

interface WorkbenchFooterProps {
  issuesCount: number;
}

export function WorkbenchFooter({ issuesCount }: WorkbenchFooterProps) {
  return (
    <footer className="workbench-footer">
      <div>
        <span>Issues: </span>
        <span style={{ fontWeight: 600, color: issuesCount > 0 ? "var(--status-warning)" : "var(--status-approved)" }}>
          {issuesCount}
        </span>
      </div>
      <div>
        <button className="action-btn" disabled style={{ marginRight: "var(--space-sm)" }} title="Requires backend session state">
          Preview Approve [Disabled]
        </button>
        <button className="action-btn" disabled title="Requires backend session state">
          Assign [Disabled]
        </button>
      </div>
      <div>
        <span>Autosave Checkpoint: Idle</span>
      </div>
    </footer>
  );
}
