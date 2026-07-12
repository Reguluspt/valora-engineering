import React from "react";
import { LineageData } from "./ContextPanelTypes";
import { t } from "../../../i18n";

interface LineagePanelProps {
  data?: LineageData | null;
}

export function LineagePanel({ data }: LineagePanelProps) {
  if (!data) {
    return <p style={{ color: "var(--text-muted)", padding: "var(--space-md)" }}>{t("empty.selectAssetDesc")}</p>;
  }

  if (!data.original_source_project && !data.direct_source_project) {
    return (
      <div style={{ padding: "var(--space-md)" }}>
        <h4 className="panel-tab-title">Lịch sử nguồn gốc</h4>
        <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)", marginTop: "var(--space-sm)" }}>
          Chưa có dữ liệu nguồn gốc
        </p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
      <div className="panel-tab">
        <h4 className="panel-tab-title">Chuỗi nguồn gốc</h4>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)", position: "relative", paddingLeft: "var(--space-md)" }}>
          <div style={{ position: "absolute", left: "4px", top: "10px", bottom: "10px", width: "2px", backgroundColor: "var(--border-color)" }} />

          {data.original_source_project && (
            <div style={{ position: "relative" }}>
              <div style={{ position: "absolute", left: "-16px", top: "4px", width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "var(--accent-cyan)" }} />
              <p style={{ margin: 0, fontWeight: "bold" }}>Hồ sơ gốc</p>
              <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
                {data.original_source_project.project_code}
              </p>
            </div>
          )}

          {data.direct_source_project && (
            <div style={{ position: "relative" }}>
              <div style={{ position: "absolute", left: "-16px", top: "4px", width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "var(--accent-blue)" }} />
              <p style={{ margin: 0, fontWeight: "bold" }}>Hồ sơ nguồn trực tiếp</p>
              <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
                {data.direct_source_project.project_code}
              </p>
            </div>
          )}

          <div style={{ position: "relative" }}>
            <div style={{ position: "absolute", left: "-16px", top: "4px", width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "var(--status-review)" }} />
            <p style={{ margin: 0, fontWeight: "bold", color: "#fff" }}>Hồ sơ hiện tại</p>
            <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
              Đang cập nhật...
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
