import React from "react";
import { WorkbenchHeader } from "./WorkbenchHeader";
import { WorkbenchFooter } from "./WorkbenchFooter";
import { WorkbenchRightPanelShell } from "./WorkbenchRightPanelShell";

interface WorkbenchLayoutProps {
  projectTitle: string;
  status: "draft" | "review" | "approved" | "warning" | "error" | "blocking";
  statusLabel: string;
  issuesCount: number;
  children?: React.ReactNode;
}

export function WorkbenchLayout({
  projectTitle,
  status,
  statusLabel,
  issuesCount,
  children
}: WorkbenchLayoutProps) {
  return (
    <div className="workbench-container">
      <WorkbenchHeader
        projectTitle={projectTitle}
        status={status}
        statusLabel={statusLabel}
      />
      <div className="workbench-body">
        <main className="workbench-grid-pane">
          {children || (
            <div style={{ padding: "var(--space-md)", border: "1px dashed var(--border-color)", borderRadius: "var(--radius-lg)" }}>
              <h3>Main Workspace Grid Region Placeholder</h3>
              <p style={{ color: "var(--text-muted)" }}>
                This section will house the virtualized Asset Grid implementation.
              </p>
            </div>
          )}
        </main>
        <WorkbenchRightPanelShell />
      </div>
      <WorkbenchFooter issuesCount={issuesCount} />
    </div>
  );
}
