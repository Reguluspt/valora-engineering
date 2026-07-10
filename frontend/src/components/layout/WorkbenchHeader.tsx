import React, { useEffect, useState } from "react";
import { StatusBadge } from "../common/StatusBadge";
import { checkHealth } from "../../api/client";
import { t } from "../../i18n";

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
            {apiReachable ? t("nav.serverConnected") : t("nav.serverDisconnected")}
          </span>
        )}
        <div className="project-status-bar">
          <span>{t("workbench.statusLabel")}</span>
          <StatusBadge status={status} label={statusLabel} />
          <button className="action-btn" disabled title="Requires backend session state">
            {t("review.submitQc")} [{t("status.locked")}]
          </button>
        </div>
      </div>
    </header>
  );
}
