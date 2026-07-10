import React from "react";
import { getFriendlyError, getFriendlyErrorFromUnknown } from "../../../errors/errorRegistry";
import { t } from "../../../i18n";

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
        🔄 {t("workbench.status.initializing")}
      </div>
    );
  }

  if (rbacError) {
    const friendly = getFriendlyError("forbidden");
    return (
      <div style={{ backgroundColor: "rgba(220,53,69,0.15)", color: "var(--status-error)", padding: "var(--space-md)", borderBottom: "2px solid var(--status-error)", fontSize: "var(--font-size-sm)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>🔒 <strong>{friendly.title}:</strong> {friendly.message}</span>
        <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>{t("workbench.sessionLocked")}</span>
      </div>
    );
  }

  if (conflictError) {
    const friendly = getFriendlyError("optimistic_conflict");
    return (
      <div style={{ backgroundColor: "rgba(255,193,7,0.15)", color: "var(--status-warning)", padding: "var(--space-md)", borderBottom: "2px solid var(--status-warning)", fontSize: "var(--font-size-sm)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>⚠️ <strong>{friendly.title}:</strong> {friendly.message}</span>
        <button className="action-btn" style={{ borderColor: "var(--status-warning)", color: "var(--status-warning)" }} onClick={onRetry}>
          {t("workbench.status.staleAction")}
        </button>
      </div>
    );
  }

  if (error) {
    const friendly = getFriendlyErrorFromUnknown(error);
    return (
      <div style={{ backgroundColor: "rgba(220,53,69,0.15)", color: "var(--status-error)", padding: "var(--space-md)", borderBottom: "2px solid var(--status-error)", fontSize: "var(--font-size-sm)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span>❌ <strong>{friendly.title}:</strong> {friendly.message} {friendly.nextAction}</span>
        <button className="action-btn" onClick={onRetry}>{t("workbench.status.retry")}</button>
      </div>
    );
  }

  // Hide Session ID and Row Version from end users. Only display heartbeat status in friendly Vietnamese.
  return (
    <div style={{ backgroundColor: "var(--bg-secondary)", borderBottom: "1px solid var(--border-color)", padding: "var(--space-xs) var(--space-lg)", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "11px", color: "var(--text-muted)" }}>
      <div>
        <span>{t("nav.serverConnected")}</span>
      </div>
      <div>
        <span>{t("nav.serverConnected")}: <strong style={{ color: "var(--status-approved)" }}>{t("workbench.sessionActive")}</strong> ({lastHeartbeat})</span>
      </div>
    </div>
  );
}
