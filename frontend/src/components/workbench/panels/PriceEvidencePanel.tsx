import React from "react";
import { PriceEvidencePanelData } from "./ContextPanelTypes";
import { t } from "../../../i18n";

interface PriceEvidencePanelProps {
  data?: PriceEvidencePanelData | null;
}

export function PriceEvidencePanel({ data }: PriceEvidencePanelProps) {
  if (!data) {
    return <p style={{ color: "var(--text-muted)", padding: "var(--space-md)" }}>{t("empty.selectAssetDesc")}</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
      {data.quote_batch ? (
        <div className="panel-tab">
          <h4 className="panel-tab-title">Thông tin báo giá</h4>
          <div style={{ fontSize: "var(--font-size-sm)" }}>
            <p><strong>Tên:</strong> {data.quote_batch.display_name}</p>
            <p><strong>Trạng thái:</strong> {data.quote_batch.status}</p>
          </div>
        </div>
      ) : (
        <div className="panel-tab">
          <h4 className="panel-tab-title">Báo giá</h4>
          <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>Chưa có báo giá</p>
        </div>
      )}

      {data.quote_lines.length > 0 ? (
        <div className="panel-tab">
          <h4 className="panel-tab-title">Báo giá thị trường</h4>
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
      ) : (
        <div className="panel-tab">
          <h4 className="panel-tab-title">Báo giá thị trường</h4>
          <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>Chưa có báo giá</p>
        </div>
      )}

      {data.appraised_price_decision ? (
        <div className="panel-tab" style={{ border: "1px solid var(--accent-blue)", backgroundColor: "rgba(69, 243, 255, 0.03)" }}>
          <h4 className="panel-tab-title" style={{ color: "var(--accent-blue)" }}>
            Giá thẩm định
          </h4>
          <div style={{ fontSize: "var(--font-size-sm)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", margin: "var(--space-sm) 0" }}>
              <span>Giá thẩm định:</span>
              <span style={{ fontSize: "var(--font-size-lg)", fontWeight: "bold", color: "var(--accent-blue)" }}>
                {data.appraised_price_decision.selected_unit_price != null
                  ? data.appraised_price_decision.selected_unit_price.toLocaleString() + " VND"
                  : "—"}
              </span>
            </div>
            {data.appraised_price_decision.rationale && (
              <p style={{ margin: "var(--space-xs) 0", fontStyle: "italic", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>
                {data.appraised_price_decision.rationale}
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="panel-tab">
          <h4 className="panel-tab-title" style={{ color: "var(--accent-blue)" }}>Giá thẩm định</h4>
          <p style={{ color: "var(--text-muted)", fontSize: "var(--font-size-sm)" }}>—</p>
        </div>
      )}
    </div>
  );
}
