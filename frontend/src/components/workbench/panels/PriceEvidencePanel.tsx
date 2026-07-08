import React from "react";
import { PriceEvidencePanelData } from "./ContextPanelTypes";

interface PriceEvidencePanelProps {
  data?: PriceEvidencePanelData;
}

export function PriceEvidencePanel({ data }: PriceEvidencePanelProps) {
  if (!data) {
    return <p style={{ color: "var(--text-muted)" }}>Select a row to view price evidence details.</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
      {/* Quote Batch details */}
      <div className="panel-tab">
        <h4 className="panel-tab-title">Quote Batch Info</h4>
        <div style={{ fontSize: "var(--font-size-sm)" }}>
          <p><strong>Name:</strong> {data.quote_batch.display_name}</p>
          <p>
            <strong>Spread:</strong> {data.quote_batch.spread_percent}% 
            {data.quote_batch.spread_percent > 20 && (
              <span style={{ color: "var(--status-warning)", marginLeft: "var(--space-sm)" }}>
                ⚠️ High Spread!
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Quote Lines (Market Quote) */}
      <div className="panel-tab">
        <h4 className="panel-tab-title">Market Quotes (Evidence Source)</h4>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)" }}>
          {data.quote_lines.map((line) => (
            <div key={line.id} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px dashed var(--border-color)", fontSize: "var(--font-size-sm)" }}>
              <span>{line.supplier_name}</span>
              <span style={{ fontWeight: "bold" }}>
                {line.quoted_unit_price.toLocaleString()} {line.currency_code}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Appraised Price (Separated Context visually) */}
      <div className="panel-tab" style={{ border: "1px solid var(--accent-blue)", backgroundColor: "rgba(69, 243, 255, 0.03)" }}>
        <h4 className="panel-tab-title" style={{ color: "var(--accent-blue)" }}>
          Appraised Price Decision
        </h4>
        <div style={{ fontSize: "var(--font-size-sm)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", margin: "var(--space-sm) 0" }}>
            <span>Professional Price:</span>
            <span style={{ fontSize: "var(--font-size-lg)", fontWeight: "bold", color: "var(--accent-blue)" }}>
              {data.appraised_price_decision.selected_unit_price.toLocaleString()} VND
            </span>
          </div>
          <p style={{ margin: "var(--space-xs) 0", fontStyle: "italic", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>
            <strong>Rationale:</strong> {data.appraised_price_decision.rationale}
          </p>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "var(--space-sm)" }}>
            <span>Approval Status:</span>
            <span style={{ color: "var(--status-approved)", fontWeight: "bold" }}>
              {data.appraised_price_decision.status}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
