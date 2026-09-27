import { ValidationIssue } from "./ContextPanelTypes";

interface ValidationPanelProps {
  issues?: ValidationIssue[] | null;
}

export function ValidationPanel({ issues }: ValidationPanelProps) {
  if (issues === null || issues === undefined) {
    return <p className="asset-context-empty">Chưa có dữ liệu kiểm tra cho tài sản này.</p>;
  }

  const blockingIssues = issues.filter((i) => i.severity === "blocking" || i.is_blocking);

  return (
    <div>
      {blockingIssues.length > 0 && (
        <div className="valora-message valora-message--error" role="alert">
          Có {blockingIssues.length} vấn đề chặn cần xử lý trước khi tiếp tục.
        </div>
      )}

      <div className="asset-context-card">
        <h3>Chi tiết kiểm tra</h3>
        {issues.length === 0 ? (
          <p className="valora-message valora-message--success">
            Dòng này đáp ứng tất cả quy tắc kiểm tra.
          </p>
        ) : (
          <div>
            {issues.map((issue) => (
              <div key={issue.id} className="asset-context-validation-issue">
                <span className={`valora-status valora-status--${issue.is_blocking ? "error" : issue.severity === "warning" ? "warning" : issue.severity === "error" ? "error" : "info"}`}>
                  {issue.is_blocking || issue.severity === "blocking" ? "Chặn" : issue.severity === "warning" ? "Cảnh báo" : issue.severity === "error" ? "Lỗi" : "Thông tin"}
                </span>
                <strong> {issue.category}</strong>
                <p>{issue.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
