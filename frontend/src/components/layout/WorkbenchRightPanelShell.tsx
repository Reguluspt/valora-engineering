import { useEffect, useRef, useState } from "react";
import type { AssetLineGridRow } from "../workbench/AssetGridTypes";
import type { AssetLineContext } from "../workbench/panels/ContextPanelTypes";
import { KnowledgePanel } from "../workbench/panels/KnowledgePanel";
import { PriceEvidencePanel } from "../workbench/panels/PriceEvidencePanel";
import { LineagePanel } from "../workbench/panels/LineagePanel";
import { ValidationPanel } from "../workbench/panels/ValidationPanel";
type ContextSection = "information" | "price" | "lineage" | "validation";

const sections: { id: ContextSection; label: string }[] = [
  { id: "information", label: "Thông tin tài sản" },
  { id: "price", label: "Nguồn giá & chứng cứ" },
  { id: "lineage", label: "Nguồn gốc" },
  { id: "validation", label: "Kiểm tra dữ liệu" },
];

interface WorkbenchRightPanelShellProps {
  asset: AssetLineGridRow;
  contextData?: AssetLineContext;
  loading?: boolean;
  error?: string | null;
  onClose: () => void;
}

export function WorkbenchRightPanelShell({ asset, contextData, loading, error, onClose }: WorkbenchRightPanelShellProps) {
  const [section, setSection] = useState<ContextSection>("information");
  const closeRef = useRef<HTMLButtonElement>(null);
  const currentContext = contextData?.project_asset_line_id === asset.project_asset_line_id ? contextData : undefined;

  useEffect(() => {
    setSection("information");
    closeRef.current?.focus();
  }, [asset.project_asset_line_id]);

  const content = () => {
    if (error) return <p className="valora-message valora-message--error" role="alert">Không thể tải ngữ cảnh tài sản. {error}</p>;
    if (loading || !currentContext) return <p className="valora-loading" role="status">Đang tải ngữ cảnh tài sản...</p>;

    switch (section) {
      case "information":
        return (
          <>
            <dl className="asset-context-facts">
              <div><dt>Tên gốc</dt><dd>{asset.raw_name}</dd></div>
              <div><dt>Tên chuẩn hóa</dt><dd>{asset.normalized_name || "Chưa được ghi nhận"}</dd></div>
              <div><dt>Tài sản chuẩn</dt><dd>{asset.canonical_asset?.standard_name || "Chưa được ghi nhận"}</dd></div>
              <div><dt>Số lượng</dt><dd>{asset.quantity} {asset.unit?.name_vi || ""}</dd></div>
            </dl>
            <KnowledgePanel data={currentContext.knowledge_panel} />
          </>
        );
      case "price":
        return <PriceEvidencePanel data={currentContext.price_evidence_panel} />;
      case "lineage":
        return <LineagePanel data={currentContext.lineage} />;
      case "validation":
        return <ValidationPanel issues={currentContext.validation_issues} />;
    }
  };

  return (
    <aside className="valora-drawer asset-context-drawer" aria-labelledby="asset-context-title">
      <div className="valora-drawer__header asset-context-drawer__header">
        <div>
          <span className="asset-context-drawer__eyebrow">Ngữ cảnh tài sản · Dòng {asset.line_no}</span>
          <h2 id="asset-context-title">{asset.raw_name}</h2>
        </div>
        <button ref={closeRef} type="button" className="valora-button valora-button--subtle" onClick={onClose} aria-label="Đóng ngữ cảnh tài sản">Đóng</button>
      </div>
      <div className="asset-context-drawer__sections" role="group" aria-label="Nội dung của tài sản đang chọn">
        {sections.map((item) => (
          <button
            key={item.id}
            type="button"
            className="asset-context-drawer__section"
            aria-pressed={section === item.id}
            onClick={() => setSection(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="valora-drawer__body asset-context-drawer__body" role="region" aria-label={sections.find((item) => item.id === section)?.label}>
        {content()}
      </div>
    </aside>
  );
}
