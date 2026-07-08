import React from "react";
import { KnowledgePanelData } from "./ContextPanelTypes";

interface KnowledgePanelProps {
  data?: KnowledgePanelData;
}

export function KnowledgePanel({ data }: KnowledgePanelProps) {
  if (!data) {
    return <p style={{ color: "var(--text-muted)" }}>Select a row to view technical specifications.</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
      {/* Current Specs */}
      <div className="panel-tab">
        <h4 className="panel-tab-title">Current Specification</h4>
        <div style={{ fontSize: "var(--font-size-sm)" }}>
          <p><strong>Specification ID:</strong> {data.current_spec.technical_specification_id}</p>
          <p><strong>Version:</strong> {data.current_spec.version_id} ({data.current_spec.status})</p>
          <ul style={{ paddingLeft: "var(--space-md)", margin: "var(--space-sm) 0" }}>
            {Object.entries(data.current_spec.attribute_values).map(([k, v]) => (
              <li key={k}>{k}: {v}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Suggested Specs */}
      {data.suggestions.map((sugg) => (
        <div key={sugg.suggestion_id} className="panel-tab" style={{ borderLeft: "3px solid var(--accent-cyan)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h4 className="panel-tab-title" style={{ margin: 0 }}>Suggestion</h4>
            <span style={{ fontSize: "var(--font-size-xs)", color: "var(--accent-cyan)", fontWeight: "bold" }}>
              Confidence: {Math.round(sugg.confidence_score * 100)}%
            </span>
          </div>
          <p style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", margin: "var(--space-xs) 0" }}>
            Source: {sugg.source_type}
          </p>
          <p style={{ fontSize: "var(--font-size-sm)" }}>{sugg.summary}</p>
          <ul style={{ paddingLeft: "var(--space-md)", fontSize: "var(--font-size-sm)" }}>
            {Object.entries(sugg.attribute_values).map(([k, v]) => (
              <li key={k}>{k}: {v}</li>
            ))}
          </ul>
          {sugg.warnings.map((w, idx) => (
            <p key={idx} style={{ color: "var(--status-warning)", fontSize: "var(--font-size-xs)", margin: "4px 0" }}>
              ⚠️ {w}
            </p>
          ))}
          <button
            className="action-btn"
            style={{ width: "100%", marginTop: "var(--space-sm)" }}
            disabled
            title="Requires backend draft session"
          >
            Apply to Draft [Requires session]
          </button>
        </div>
      ))}

      {/* Conflicts */}
      {data.conflicts.length > 0 && (
        <div style={{ padding: "var(--space-md)", border: "1px solid var(--status-warning)", borderRadius: "var(--radius-md)", backgroundColor: "rgba(230, 126, 34, 0.1)" }}>
          <h4 style={{ color: "var(--status-warning)", margin: "0 0 var(--space-xs) 0" }}>Conflicts Detected</h4>
          {data.conflicts.map((c, idx) => (
            <p key={idx} style={{ margin: 0, fontSize: "var(--font-size-xs)" }}>• {c}</p>
          ))}
        </div>
      )}
    </div>
  );
}
