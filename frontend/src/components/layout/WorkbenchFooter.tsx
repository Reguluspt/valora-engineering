import React from "react";
import { AutosaveCheckpoint } from "../workbench/drafts/DraftStateTypes";
import { t } from "../../i18n";
import { StatusBadge } from "../common/StatusBadge";

interface WorkbenchFooterProps {
  issuesCount?: number | null;
  draftsCount?: number;
  checkpoint?: AutosaveCheckpoint;
  onAutosaveMock?: () => void;
}

export function WorkbenchFooter({
  issuesCount,
  draftsCount = 0,
  checkpoint = { id: "", timestamp: "—", status: "idle" },
  onAutosaveMock
}: WorkbenchFooterProps) {
  const checkpointStatus = checkpoint.status === "checkpointed"
    ? { status: "approved" as const, label: "Đã lưu" }
    : checkpoint.status === "dirty"
      ? { status: "warning" as const, label: "Chưa lưu" }
      : checkpoint.status === "conflict"
        ? { status: "error" as const, label: "Xung đột" }
        : { status: "review" as const, label: "Chờ" };

  return (
    <footer className="workbench-footer">
      <div className="project-status-bar">
        <span>{t("workbench.issuesLabel")}</span>
        <strong>{issuesCount != null ? issuesCount : "—"}</strong>
        {draftsCount > 0 && (
          <StatusBadge status="draft" label={`${draftsCount} ${t("workbench.unsavedChangesCount")}`} />
        )}
      </div>
      <div className="project-status-bar">
        {onAutosaveMock && (
          <button
            className="valora-button valora-button--secondary"
            disabled={draftsCount === 0}
            onClick={onAutosaveMock}
            type="button"
          >
            Điểm lưu nháp
          </button>
        )}
        <span>Trạng thái lưu nháp:</span>
        <StatusBadge status={checkpointStatus.status} label={checkpointStatus.label} />
        <span>({checkpoint.timestamp})</span>
      </div>
    </footer>
  );
}
