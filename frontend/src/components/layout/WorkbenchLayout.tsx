import React, { useState } from "react";
import { WorkbenchHeader } from "./WorkbenchHeader";
import { WorkbenchFooter } from "./WorkbenchFooter";
import { WorkbenchRightPanelShell } from "./WorkbenchRightPanelShell";
import { AssetGrid } from "../workbench/AssetGrid";
import { generateLargeMockSet } from "../workbench/mockAssetRows";
import { MOCK_CONTEXT_DATA } from "../workbench/panels/mockContextData";

import { useDraftSession } from "../workbench/drafts/useDraftSession";
import { UndoRedoControls } from "../workbench/drafts/UndoRedoControls";

import { useWorkbenchSession } from "../workbench/session/useWorkbenchSession";
import { WorkbenchSessionStatus } from "../workbench/session/WorkbenchSessionStatus";

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

  const {
    session,
    loading,
    error,
    rbacError,
    conflictError,
    lastHeartbeat,
    retry
  } = useWorkbenchSession("hd-98-gia-lai");

  const {
    drafts,
    undoStack,
    redoStack,
    checkpoint,
    updateDraft,
    undo,
    redo,
    triggerAutosaveMock
  } = useDraftSession();

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

  const draftsCount = Object.keys(drafts).length;

  return (
    <div className="workbench-container">
      <WorkbenchHeader
        projectTitle={projectTitle}
        status={status}
        statusLabel={statusLabel}
      />
      
      {/* Session lock banner status */}
      <WorkbenchSessionStatus
        loading={loading}
        error={error}
        rbacError={rbacError}
        conflictError={conflictError}
        sessionId={session?.id}
        rowVersion={session?.row_version}
        lastHeartbeat={lastHeartbeat}
        onRetry={retry}
      />
      
      {/* Inline Toolbar for Undo/Redo */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "var(--space-sm) var(--space-lg)", borderBottom: "1px solid var(--border-color)", backgroundColor: "rgba(255,255,255,0.01)" }}>
        <UndoRedoControls
          undoDisabled={undoStack.length === 0}
          redoDisabled={redoStack.length === 0}
          onUndo={undo}
          onRedo={redo}
        />
        <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
          * Double click cell values to enter draft edit mode.
        </span>
      </div>

      <div className="workbench-body">
        <main className="workbench-grid-pane" style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {children || (
            <AssetGrid
              rows={largeMockData}
              onActiveRowChange={setActiveRowId}
              drafts={drafts}
              onDraftChange={updateDraft}
            />
          )}
        </main>
        <WorkbenchRightPanelShell contextData={selectedContextData} />
      </div>
      <WorkbenchFooter
        issuesCount={issuesCount}
        draftsCount={draftsCount}
        checkpoint={checkpoint}
        onAutosaveMock={triggerAutosaveMock}
      />
    </div>
  );
}
