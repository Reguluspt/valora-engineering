import React from "react";
import { KnowledgePanelData } from "./ContextPanelTypes";
import { t } from "../../../i18n";

interface KnowledgePanelProps {
  data?: KnowledgePanelData | null;
}

export function KnowledgePanel({ data }: KnowledgePanelProps) {
  if (!data || !data.current_spec) {
    return <p style={{ color: "var(--text-muted)", padding: "var(--space-md)" }}>{t("empty.selectAssetDesc")}</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
      <div className="panel-tab">
        <h4 className="panel-tab-title">Thông số kỹ thuật</h4>
        <div style={{ fontSize: "var(--font-size-sm)" }}>
          {Object.keys(data.current_spec.attribute_values).length === 0 ? (
            <p style={{ color: "var(--text-muted)" }}>Chưa có dữ liệu</p>
          ) : (
            <ul style={{ paddingLeft: "var(--space-md)", margin: "var(--space-sm) 0" }}>
              {Object.entries(data.current_spec.attribute_values).map(([k, v]) => (
                <li key={k}>{k}: {v}</li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {data.suggestions.length > 0 && (
        <>
          {data.suggestions.map((sugg) => (
            <div key={sugg.suggestion_id} className="panel-tab" style={{ borderLeft: "3px solid var(--accent-cyan)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h4 className="panel-tab-title" style={{ margin: 0 }}>Gợi ý</h4>
                <span style={{ fontSize: "var(--font-size-xs)", color: "var(--accent-cyan)", fontWeight: "bold" }}>
                  {Math.round(sugg.confidence_score * 100)}%
                </span>
              </div>
              <p style={{ fontSize: "var(--font-size-sm)" }}>{sugg.summary}</p>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
