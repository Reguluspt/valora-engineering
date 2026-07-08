import React from "react";

interface ConflictWarningProps {
  onResolve: () => void;
}

export function ConflictWarning({ onResolve }: ConflictWarningProps) {
  return (
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: "rgba(0,0,0,0.85)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 1000,
      backdropFilter: "blur(4px)"
    }}>
      <div style={{
        backgroundColor: "var(--bg-secondary)",
        border: "2px solid var(--status-warning)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-xl)",
        maxWidth: "500px",
        textAlign: "center",
        boxShadow: "0 10px 25px rgba(0,0,0,0.5)"
      }}>
        <h3 style={{ color: "var(--status-warning)", marginTop: 0 }}>⚠️ Stale Row Collision (409)</h3>
        <p style={{ color: "var(--text-primary)", fontSize: "var(--font-size-sm)", lineHeight: "1.6" }}>
          Another client has updated this session's configuration state or row versions since it was loaded. 
          To prevent data corruption, modification operations are locked.
        </p>
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>
          Note: Local draft changes will be preserved in memory, but backend syncing is paused.
        </p>
        <div style={{ marginTop: "var(--space-lg)" }}>
          <button
            className="action-btn"
            style={{
              borderColor: "var(--status-warning)",
              color: "var(--status-warning)",
              padding: "var(--space-sm) var(--space-lg)"
            }}
            onClick={onResolve}
          >
            Re-sync Workspace Session
          </button>
        </div>
      </div>
    </div>
  );
}
