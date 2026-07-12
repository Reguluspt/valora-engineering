import React from "react";
import { AutosaveCheckpoint } from "../workbench/drafts/DraftStateTypes";
import { t } from "../../i18n";

interface WorkbenchFooterProps {
  issuesCount?: number | null;
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
        <span>{t("workbench.issuesLabel")}</span>
        <span style={{ fontWeight: 600, color: issuesCount != null && issuesCount > 0 ? "var(--status-warning)" : "var(--text-muted)", marginRight: "var(--space-md)" }}>
          {issuesCount != null ? issuesCount : "—"}
        </span>

        {draftsCount > 0 && (
          <span style={{ color: "var(--status-draft)", fontWeight: 600 }}>
            ⚡ {draftsCount} {t("workbench.unsavedChangesCount")}
          </span>
        )}
      </div>
      <div>
        <button
          className="action-btn"
          disabled={draftsCount === 0}
          style={{ marginRight: "var(--space-sm)" }}
          title={draftsCount > 0 ? "Lưu các chỉnh sửa cục bộ vào hồ sơ chính thức" : "Không có bản nháp nào cần lưu"}
        >
          {t("workbench.saveOfficial")} {draftsCount > 0 ? `[${t("status.locked")}]` : ""}
        </button>
        <button className="action-btn" disabled style={{ marginRight: "var(--space-sm)" }} title="Requires backend session state">
          Xem trước phê duyệt [{t("status.locked")}]
        </button>
        <button className="action-btn" disabled title="Requires backend session state">
          Phân công [{t("status.locked")}]
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
            Điểm lưu nháp
          </button>
        )}
        <span>
          Trạng thái lưu nháp:{" "}
          <strong style={{
            color: checkpoint.status === "checkpointed"
              ? "var(--status-approved)"
              : checkpoint.status === "dirty"
              ? "var(--status-draft)"
              : "var(--text-muted)"
          }}>
            {checkpoint.status === "checkpointed" ? "ĐÃ LƯU" : checkpoint.status === "dirty" ? "CHƯA LƯU" : "CHỜ"}
          </strong>{" "}
          ({checkpoint.timestamp})
        </span>
      </div>
    </footer>
  );
}
