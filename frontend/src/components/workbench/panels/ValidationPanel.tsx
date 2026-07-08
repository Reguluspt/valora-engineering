import React from "react";
import { ValidationIssue } from "./ContextPanelTypes";

interface ValidationPanelProps {
  issues?: ValidationIssue[];
}

export function ValidationPanel({ issues = [] }: ValidationPanelProps) {
  const blockingIssues = issues.filter((i) => i.severity === "blocking" || i.is_blocking);
  const otherIssues = issues.filter((i) => i.severity !== "blocking" && !i.is_blocking);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
      {/* Blocking Issues Banner */}
      {blockingIssues.length > 0 && (
        <div style={{ padding: "var(--space-md)", border: "1px solid var(--status-blocking)", borderRadius: "var(--radius-md)", backgroundColor: "rgba(155, 44, 44, 0.15)" }}>
          <h4 style={{ color: "var(--status-error)", margin: "0 0 var(--space-xs) 0" }}>
            ❌ Appraisals Gate Blocked
          </h4>
          <p style={{ margin: 0, fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
            The following blocking constraints must be resolved before this row can be approved.
          </p>
        </div>
      )}

      {/* Issues list group */}
      <div className="panel-tab">
        <h4 className="panel-tab-title">Validation Details</h4>
        {issues.length === 0 ? (
          <p style={{ color: "var(--status-approved)", fontSize: "var(--font-size-sm)" }}>
            ✓ Row matches all semantic validation rules.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
            {issues.map((issue) => (
              <div key={issue.id} style={{ display: "flex", flexDirection: "column", gap: "2px", padding: "var(--space-sm) 0", borderBottom: "1px solid var(--border-color)", fontSize: "var(--font-size-sm)" }}>
                <div style={{ display: "flex", gap: "var(--space-sm)", alignItems: "center" }}>
                  <span className={`badge badge-${issue.severity}`}>
                    {issue.severity}
                  </span>
                  <span style={{ fontWeight: 600 }}>{issue.category}</span>
                </div>
                <p style={{ margin: "4px 0 0 0" }}>{issue.message}</p>
                <button
                  className="action-btn"
                  style={{ width: "fit-content", marginTop: "var(--space-sm)", fontSize: "var(--font-size-xs)", padding: "2px 6px" }}
                  disabled
                  title="Requires session authentication write privilege"
                >
                  Resolve Issue [Disabled]
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
