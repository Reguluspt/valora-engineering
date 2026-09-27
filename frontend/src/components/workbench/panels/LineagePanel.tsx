import { LineageData } from "./ContextPanelTypes";

interface LineagePanelProps {
  data?: LineageData | null;
}

export function LineagePanel({ data }: LineagePanelProps) {
  if (!data) {
    return <p className="asset-context-empty">Chưa được ghi nhận nguồn gốc cho tài sản này.</p>;
  }

  if (!data.original_source_project && !data.direct_source_project) {
    return (
      <div className="asset-context-card">
        <h3>Nguồn gốc</h3>
        <p className="asset-context-empty">Chưa được ghi nhận.</p>
      </div>
    );
  }

  return (
    <div className="asset-context-card">
      <h3>Chuỗi nguồn gốc</h3>
      <dl className="asset-context-facts">
        {data.original_source_project && (
          <div><dt>Hồ sơ gốc</dt><dd>{data.original_source_project.project_code}</dd></div>
        )}
        {data.direct_source_project && (
          <div><dt>Nguồn trực tiếp</dt><dd>{data.direct_source_project.project_code}</dd></div>
        )}
      </dl>
      {data.lineage_path.length > 0 && (
        <ol className="asset-context-list">
          {data.lineage_path.map((step, index) => <li key={`${index}-${step}`}>{step}</li>)}
        </ol>
      )}
    </div>
  );
}
