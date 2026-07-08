import React from "react";
import { LineageData } from "./ContextPanelTypes";

interface LineagePanelProps {
  data?: LineageData;
}

export function LineagePanel({ data }: LineagePanelProps) {
  if (!data) {
    return <p style={{ color: "var(--text-muted)" }}>Select a row to view lineage trace details.</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
      <div className="panel-tab">
        <h4 className="panel-tab-title">Historical Lineage Chain</h4>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)", position: "relative", paddingLeft: "var(--space-md)" }}>
          <div style={{ position: "absolute", left: "4px", top: "10px", bottom: "10px", width: "2px", backgroundColor: "var(--border-color)" }} />
          
          <div style={{ position: "relative" }}>
            <div style={{ position: "absolute", left: "-16px", top: "4px", width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "var(--accent-cyan)" }} />
            <p style={{ margin: 0, fontWeight: "bold" }}>Original Source Project</p>
            <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
              ID: {data.original_source_project.id} | Code: {data.original_source_project.project_code}
            </p>
          </div>

          <div style={{ position: "relative" }}>
            <div style={{ position: "absolute", left: "-16px", top: "4px", width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "var(--accent-blue)" }} />
            <p style={{ margin: 0, fontWeight: "bold" }}>Direct Source Project</p>
            <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
              ID: {data.direct_source_project.id} | Code: {data.direct_source_project.project_code}
            </p>
          </div>

          <div style={{ position: "relative" }}>
            <div style={{ position: "absolute", left: "-16px", top: "4px", width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "var(--status-review)" }} />
            <p style={{ margin: 0, fontWeight: "bold", color: "#fff" }}>Current Target Project</p>
            <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
              Draft context updating...
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
