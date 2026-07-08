import React, { useState } from "react";
import { AssetLineContext } from "../workbench/panels/ContextPanelTypes";
import { KnowledgePanel } from "../workbench/panels/KnowledgePanel";
import { PriceEvidencePanel } from "../workbench/panels/PriceEvidencePanel";
import { LineagePanel } from "../workbench/panels/LineagePanel";
import { ValidationPanel } from "../workbench/panels/ValidationPanel";

interface WorkbenchRightPanelShellProps {
  contextData?: AssetLineContext;
}

type TabType = "knowledge" | "price" | "lineage" | "validation";

export function WorkbenchRightPanelShell({ contextData }: WorkbenchRightPanelShellProps) {
  const [activeTab, setActiveTab] = useState<TabType>("knowledge");

  const tabStyle = (tab: TabType) => ({
    flex: 1,
    padding: "var(--space-sm)",
    backgroundColor: activeTab === tab ? "var(--bg-primary)" : "var(--bg-secondary)",
    border: "none",
    borderBottom: activeTab === tab ? "2px solid var(--accent-cyan)" : "2px solid transparent",
    color: activeTab === tab ? "var(--accent-cyan)" : "var(--text-muted)",
    cursor: "pointer",
    fontSize: "var(--font-size-xs)",
    fontWeight: 600,
    outline: "none",
    textAlign: "center" as const
  });

  const renderActivePanel = () => {
    if (!contextData) {
      return (
        <div style={{ padding: "var(--space-md)", textAlign: "center", color: "var(--text-muted)" }}>
          Select a row in the Asset Grid to load context spec panel data.
        </div>
      );
    }

    switch (activeTab) {
      case "knowledge":
        return <KnowledgePanel data={contextData.knowledge_panel} />;
      case "price":
        return <PriceEvidencePanel data={contextData.price_evidence_panel} />;
      case "lineage":
        return <LineagePanel data={contextData.lineage} />;
      case "validation":
        return <ValidationPanel issues={contextData.validation_issues} />;
      default:
        return null;
    }
  };

  return (
    <aside className="workbench-right-drawer" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Tabs list container */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--border-color)", marginBottom: "var(--space-md)" }}>
        <button style={tabStyle("knowledge")} onClick={() => setActiveTab("knowledge")}>
          Knowledge
        </button>
        <button style={tabStyle("price")} onClick={() => setActiveTab("price")}>
          Price Evidence
        </button>
        <button style={tabStyle("lineage")} onClick={() => setActiveTab("lineage")}>
          Lineage
        </button>
        <button style={tabStyle("validation")} onClick={() => setActiveTab("validation")}>
          Validation
        </button>
      </div>

      {/* Pane viewport area */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {renderActivePanel()}
      </div>
    </aside>
  );
}
