import { PriceEvidencePanelData } from "./ContextPanelTypes";

interface PriceEvidencePanelProps {
  data?: PriceEvidencePanelData | null;
}

export function PriceEvidencePanel({ data }: PriceEvidencePanelProps) {
  if (!data) {
    return <p className="asset-context-empty">Chưa có dữ liệu nguồn giá và chứng cứ cho tài sản này.</p>;
  }

  return (
    <div>
      {data.quote_batch ? (
        <div className="asset-context-card">
          <h3>Thông tin báo giá</h3>
          <p><strong>Tên:</strong> {data.quote_batch.display_name}</p>
          <p><strong>Trạng thái:</strong> {data.quote_batch.status}</p>
        </div>
      ) : (
        <div className="asset-context-card">
          <h3>Báo giá</h3>
          <p className="asset-context-empty">Chưa có báo giá.</p>
        </div>
      )}

      {data.quote_lines.length > 0 ? (
        <div className="asset-context-card">
          <h3>Báo giá nhà cung cấp</h3>
          <div>
            {data.quote_lines.map((line) => (
              <div key={line.id} className="asset-context-quote">
                <span>{line.supplier_name}</span>
                <strong>
                  {line.quoted_unit_price.toLocaleString()} {line.currency_code}
                </strong>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="asset-context-card">
          <h3>Báo giá nhà cung cấp</h3>
          <p className="asset-context-empty">Chưa có báo giá.</p>
        </div>
      )}

      {data.appraised_price_decision ? (
        <div className="asset-context-card">
          <h3>Giá thẩm định</h3>
          <div>
            <div className="asset-context-quote">
              <span>Giá thẩm định:</span>
              <strong>
                {data.appraised_price_decision.selected_unit_price != null
                  ? data.appraised_price_decision.selected_unit_price.toLocaleString() + " VND"
                  : "—"}
              </strong>
            </div>
            {data.appraised_price_decision.rationale && (
              <p className="asset-context-muted">
                {data.appraised_price_decision.rationale}
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="asset-context-card">
          <h3>Giá thẩm định</h3>
          <p className="asset-context-empty">Chưa được ghi nhận.</p>
        </div>
      )}
    </div>
  );
}
