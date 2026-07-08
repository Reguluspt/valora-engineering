import React from "react";

interface WorkbenchSessionStatusProps {
  loading: boolean;
  error: string | null;
  rbacError: string | null;
  conflictError: boolean;
  sessionId: string | undefined;
  rowVersion: number | undefined;
  lastHeartbeat: string;
  onRetry: () => void;
}

export function WorkbenchSessionStatus({
  loading,
  error,
  rbacError,
  conflictError,
  sessionId,
  rowVersion,
  lastHeartbeat,
  onRetry
}: WorkbenchSessionStatusProps) {
  if (loading) {
    return (
      <div style={{ backgroundColor: "rgba(0,0,0,0.5)", color: "var(--accent-cyan)", padding: "var(--space-md)", textAlign: "center", borderBottom: "1px solid var(--border-color)", fontSize: "var(--font-size-sm)" }}>
        🔄 Initializing Live Workbench Session Lock...
      </div>
    );
  }

  if (rbacError) {
    return (
      <div style={{ backgroundColor: "rgba(220,53,69,0.15)", color: "var(--status-error)", padding: "var(--space-md)", borderBottom: "2px solid var(--status-error)", fontSize: "var(--font-size-sm)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>🔒 <strong>RBAC Warning:</strong> {rbacError}</span>
        <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Session Lock: Disabled</span>
      </div>
    );
  }

  if (conflictError) {
    return (
      <div style={{ backgroundColor: "rgba(255,193,7,0.15)", color: "var(--status-warning)", padding: "var(--space-md)", borderBottom: "2px solid var(--status-warning)", fontSize: "var(--font-size-sm)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>⚠️ <strong>Stale Collision Warning (409):</strong> Another client has updated this session's configuration state. Modifications are locked.</span>
        <button className="action-btn" style={{ borderColor: "var(--status-warning)", color: "var(--status-warning)" }} onClick={onRetry}>
          Re-sync Session
        </button>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ backgroundColor: "rgba(220,53,69,0.15)", color: "var(--status-error)", padding: "var(--space-md)", borderBottom: "2px solid var(--status-error)", fontSize: "var(--font-size-sm)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>❌ <strong>Connection Error:</strong> {error}</span>
        <button className="action-btn" onClick={onRetry}>Retry Session Connection</button>
      </div>
    );
  }

  return (
    <div style={{ backgroundColor: "var(--bg-secondary)", borderBottom: "1px solid var(--border-color)", padding: "var(--space-xs) var(--space-lg)", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "11px", color: "var(--text-muted)" }}>
      <div>
        <span>Session ID: <strong style={{ color: "#fff" }}>{sessionId || "N/A"}</strong></span>
        <span style={{ marginLeft: "var(--space-md)" }}>Row Version: <strong style={{ color: "#fff" }}>{rowVersion ?? "N/A"}</strong></span>
      </div>
      <div>
        <span>Heartbeat: <strong style={{ color: "var(--status-approved)" }}>ACTIVE</strong> ({lastHeartbeat})</span>
      </div>
    </div>
  );
}
