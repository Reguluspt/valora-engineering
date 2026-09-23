import React, { useEffect, useState } from "react";
import { StatusBadge } from "../common/StatusBadge";
import { checkHealth } from "../../api/client";
import { t } from "../../i18n";

interface WorkbenchHeaderProps {
  projectTitle: string;
  status?: "draft" | "review" | "approved" | "warning" | "error" | "blocking";
  statusLabel?: string;
  onNavigateOverview?: () => void;
}

export function WorkbenchHeader({
  projectTitle,
  status,
  statusLabel,
  onNavigateOverview,
}: WorkbenchHeaderProps) {
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
      <div className="project-status-bar">
        {onNavigateOverview && (
          <button className="valora-button valora-button--secondary" onClick={onNavigateOverview} type="button">
            {t("nav.caseOverview")}
          </button>
        )}
        {apiReachable !== null && (
          <StatusBadge
            label={apiReachable ? t("nav.serverConnected") : t("nav.serverDisconnected")}
            status={apiReachable ? "approved" : "error"}
          />
        )}
        <span>{t("workbench.statusLabel")}</span>
        {status && statusLabel ? (
          <StatusBadge status={status} label={statusLabel} />
        ) : (
          <span>Chưa có dữ liệu trạng thái</span>
        )}
      </div>
    </header>
  );
}
