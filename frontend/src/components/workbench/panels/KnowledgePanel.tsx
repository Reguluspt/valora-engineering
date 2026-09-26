import { KnowledgePanelData } from "./ContextPanelTypes";

interface KnowledgePanelProps {
  data?: KnowledgePanelData | null;
}

export function KnowledgePanel({ data }: KnowledgePanelProps) {
  if (!data) {
    return <p className="asset-context-empty">Chưa có dữ liệu Kho tri thức cho tài sản này.</p>;
  }

  return (
    <div>
      <div className="asset-context-card">
        <h3>Thông số kỹ thuật</h3>
        {data.current_spec && Object.keys(data.current_spec.attribute_values).length > 0 ? (
          <ul className="asset-context-list">
            {Object.entries(data.current_spec.attribute_values).map(([key, value]) => (
              <li key={key}>{key}: {value}</li>
            ))}
          </ul>
        ) : (
          <p className="asset-context-empty">Chưa có thông số kỹ thuật được ghi nhận.</p>
        )}
      </div>
      {data.suggestions.length > 0 && (
        <div className="asset-context-card">
          <h3>Gợi ý tham khảo</h3>
          {data.suggestions.map((suggestion) => (
            <div key={suggestion.suggestion_id}>
              <p>{suggestion.summary}</p>
              <p className="asset-context-muted">Mức phù hợp: {Math.round(suggestion.confidence_score * 100)}%</p>
            </div>
          ))}
        </div>
      )}
      {data.conflicts.length > 0 && (
        <div className="valora-message valora-message--warning">
          <div>
            <strong>Cần xem lại thông tin</strong>
            <ul className="asset-context-list">
              {data.conflicts.map((conflict, index) => <li key={index}>{conflict}</li>)}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
