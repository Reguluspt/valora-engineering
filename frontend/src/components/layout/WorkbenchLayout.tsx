import React, { useState } from "react";
import { WorkbenchHeader } from "./WorkbenchHeader";
import { WorkbenchFooter } from "./WorkbenchFooter";
import { WorkbenchRightPanelShell } from "./WorkbenchRightPanelShell";
import { AssetGrid } from "../workbench/AssetGrid";
import { generateLargeMockSet } from "../workbench/mockAssetRows";
import { MOCK_CONTEXT_DATA } from "../workbench/panels/mockContextData";

interface WorkbenchLayoutProps {
  projectTitle: string;
  status: "draft" | "review" | "approved" | "warning" | "error" | "blocking";
  statusLabel: string;
  issuesCount: number;
  children?: React.ReactNode;
}

export function WorkbenchLayout({
  projectTitle,
  status,
  statusLabel,
  issuesCount,
  children
}: WorkbenchLayoutProps) {
  const largeMockData = React.useMemo(() => generateLargeMockSet(), []);
  const [activeRowId, setActiveRowId] = useState<string | null>(null);

  const selectedContextData = React.useMemo(() => {
    if (!activeRowId) return undefined;
    return MOCK_CONTEXT_DATA[activeRowId] || {
      project_asset_line_id: activeRowId,
      knowledge_panel: {
        current_spec: {
          technical_specification_id: `spec-${activeRowId}`,
          version_id: "v-1",
          status: "active",
          attribute_values: { info: "Auto-generated dummy spec info" }
        },
        suggestions: [],
        conflicts: []
      },
      price_evidence_panel: {
        quote_batch: {
          id: "qb-auto",
          display_name: "Mock Auto Batch",
          status: "active",
          conflict_status: "valid",
          spread_percent: 0
        },
        quote_lines: [],
        appraised_price_decision: {
          id: "apd-auto",
          selected_unit_price: 0,
          rationale: "Default rationales.",
          status: "draft"
        }
      },
      lineage: {
        original_source_project: { id: "p-auto-org", project_code: "PRJ-AUTO" },
        direct_source_project: { id: "p-auto-dir", project_code: "PRJ-AUTO" },
        lineage_path: ["p-auto-org", "current-proj"]
      },
      validation_issues: []
    };
  }, [activeRowId]);

  return (
    <div className="workbench-container">
      <WorkbenchHeader
        projectTitle={projectTitle}
        status={status}
        statusLabel={statusLabel}
      />
      <div className="workbench-body">
        <main className="workbench-grid-pane" style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {children || <AssetGrid rows={largeMockData} onActiveRowChange={setActiveRowId} />}
        </main>
        <WorkbenchRightPanelShell contextData={selectedContextData} />
      </div>
      <WorkbenchFooter issuesCount={issuesCount} />
    </div>
  );
}
