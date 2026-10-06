import { useEffect, useRef, useState } from "react";
import type { AssetLineGridRow } from "../workbench/AssetGridTypes";
import type { AssetLineContext } from "../workbench/panels/ContextPanelTypes";
import { KnowledgePanel } from "../workbench/panels/KnowledgePanel";
import { PriceEvidencePanel } from "../workbench/panels/PriceEvidencePanel";
import { LineagePanel } from "../workbench/panels/LineagePanel";
import { ValidationPanel } from "../workbench/panels/ValidationPanel";
import { FluentProvider, webLightTheme, Tab, TabList } from "@fluentui/react-components";
import type { PriceEvidenceController } from "../workbench/price-evidence/usePriceEvidence";
type ContextSection = "information" | "specifications" | "price" | "lineage";

const sections: { id: ContextSection; label: string }[] = [
  { id: "information", label: "Tổng quan" },
  { id: "specifications", label: "Thông số kỹ thuật" },
  { id: "price", label: "Nguồn giá & Chứng cứ" },
  { id: "lineage", label: "Lịch sử" },
];

interface WorkbenchRightPanelShellProps {
  asset: AssetLineGridRow;
  contextData?: AssetLineContext;
  loading?: boolean;
  error?: string | null;
  onClose: () => void;
  evidence?: PriceEvidenceController;
  projectId?: string;
  focusPrice?: boolean;
}

export function WorkbenchRightPanelShell({ asset, contextData, loading, error, onClose, evidence, projectId, focusPrice }: WorkbenchRightPanelShellProps) {
  const [section, setSection] = useState<ContextSection>("information");
  const closeRef = useRef<HTMLButtonElement>(null);
  const priceRef = useRef<HTMLButtonElement>(null);
  const currentContext = contextData?.project_asset_line_id === asset.project_asset_line_id ? contextData : undefined;

  useEffect(() => {
    setSection(focusPrice ? "price" : "information");
    if (focusPrice) priceRef.current?.focus(); else closeRef.current?.focus();
  }, [asset.project_asset_line_id, focusPrice]);

  const content = () => {
    if (section === "price") return evidence && projectId
      ? <PriceEvidencePanel key={asset.project_asset_line_id} evidence={evidence} projectId={projectId}
          lineId={asset.project_asset_line_id} lineLabel={asset.raw_name} />
      : <p role="status">Nguồn chứng cứ hiện chưa khả dụng. Tải lại trạng thái hồ sơ.</p>;
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
            <ValidationPanel issues={currentContext.validation_issues} />
          </>
        );
      case "specifications":
        return <KnowledgePanel data={currentContext.knowledge_panel} />;
      case "lineage":
        return <LineagePanel data={currentContext.lineage} />;
    }
  };

  return (
    <FluentProvider theme={webLightTheme} className="asset-context-provider"><aside className="valora-drawer asset-context-drawer" aria-labelledby="asset-context-title"
      onKeyDown={event => { if (event.key === "Escape" && !(event.target as HTMLElement).closest('[role="dialog"]')) onClose(); }}>
      <div className="valora-drawer__header asset-context-drawer__header">
        <div>
          <span className="asset-context-drawer__eyebrow">Ngữ cảnh tài sản · Dòng {asset.line_no}</span>
          <h2 id="asset-context-title">{asset.raw_name}</h2>
        </div>
        <button ref={closeRef} type="button" className="valora-button valora-button--subtle" onClick={onClose} aria-label="Đóng ngữ cảnh tài sản">Đóng</button>
      </div>
      <TabList className="asset-context-drawer__sections" selectedValue={section}
        onTabSelect={(_, data) => setSection(data.value as ContextSection)} aria-label="Nội dung của tài sản đang chọn">
        {sections.map((item) => (
          <Tab
            key={item.id}
            value={item.id}
            id={`asset-context-tab-${item.id}`}
            aria-controls="asset-context-tabpanel"
            ref={item.id === "price" ? priceRef : undefined}
            className="asset-context-drawer__section"
          >
            {item.label}
          </Tab>
        ))}
      </TabList>
      <div id="asset-context-tabpanel" className="valora-drawer__body asset-context-drawer__body" role="tabpanel" aria-labelledby={`asset-context-tab-${section}`}>
        {content()}
      </div>
    </aside></FluentProvider>
  );
}
