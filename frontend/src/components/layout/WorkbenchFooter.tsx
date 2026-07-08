import React from "react";
import { AutosaveCheckpoint } from "../workbench/drafts/DraftStateTypes";

interface WorkbenchFooterProps {
  issuesCount: number;
  draftsCount?: number;
  checkpoint?: AutosaveCheckpoint;
  onAutosaveMock?: () => void;
}

export function WorkbenchFooter({
  issuesCount,
  draftsCount = 0,
  checkpoint = { id: "", timestamp: "N/A", status: "idle" },
  onAutosaveMock
}: WorkbenchFooterProps) {
  return (
    <footer className="workbench-footer">
      <div>
        <span>Issues: </span>
        <span style={{ fontWeight: 600, color: issuesCount > 0 ? "var(--status-warning)" : "var(--status-approved)", marginRight: "var(--space-md)" }}>
          {issuesCount}
        </span>

        {draftsCount > 0 && (
          <span style={{ color: "var(--status-draft)", fontWeight: 600 }}>
            ⚡ {draftsCount} draft change(s)
          </span>
        )}
      </div>
      <div>
        <button
          className="action-btn"
          disabled={draftsCount === 0}
          style={{ marginRight: "var(--space-sm)" }}
          title={draftsCount > 0 ? "Commit local edits to official records [Requires backend API]" : "No active drafts to commit"}
        >
          Commit Edits {draftsCount > 0 ? "[Disabled]" : ""}
        </button>
        <button className="action-btn" disabled style={{ marginRight: "var(--space-sm)" }} title="Requires backend session state">
          Preview Approve [Disabled]
        </button>
        <button className="action-btn" disabled title="Requires backend session state">
          Assign [Disabled]
        </button>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-md)" }}>
        {onAutosaveMock && (
          <button
            className="action-btn"
            style={{ fontSize: "var(--font-size-xs)", padding: "2px 6px" }}
            onClick={onAutosaveMock}
            disabled={draftsCount === 0}
          >
            Autosave Checkpoint
          </button>
        )}
        <span>
          Autosave Status:{" "}
          <strong style={{
            color: checkpoint.status === "checkpointed"
              ? "var(--status-approved)"
              : checkpoint.status === "dirty"
              ? "var(--status-draft)"
              : "var(--text-muted)"
          }}>
            {checkpoint.status.toUpperCase()}
          </strong>{" "}
          ({checkpoint.timestamp})
        </span>
      </div>
    </footer>
  );
}
