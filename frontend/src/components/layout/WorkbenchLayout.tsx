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

import { useWorkbenchStateSync } from "../workbench/session/useWorkbenchStateSync";

import { useWorkbenchDraftSync } from "../workbench/session/useWorkbenchDraftSync";

import { ApiErrorBanner } from "../common/ApiErrorBanner";
import { ConflictWarning } from "../common/ConflictWarning";
import { RbacLockNotice } from "../common/RbacLockNotice";

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

  const [syncError, setSyncError] = useState<string | null>(null);
  const [syncConflict, setSyncConflict] = useState(false);

  const { syncSelection } = useWorkbenchStateSync(session?.id, (msg) => setSyncError(msg));

  const {
    syncInlineEdit,
    syncCheckpoint,
    syncUndo,
    syncRedo
  } = useWorkbenchDraftSync(
    session?.id,
    (msg) => setSyncError(msg),
    () => setSyncConflict(true)
  );

  const handleActiveRowChange = (id: string | null) => {
    setActiveRowId(id);
    if (id) {
      syncSelection("ProjectAssetLine", [id]);
    }
  };

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

  const handleDraftChange = (id: string, field: string, value: any, baseValue: any, rowVersion: number) => {
    if (conflictError || syncConflict || rbacError) return; // Prevent edits when locked
    updateDraft(id, field, value, baseValue, rowVersion);
    syncInlineEdit("ProjectAssetLine", id, field, value, baseValue, rowVersion);
  };

  const handleUndo = () => {
    if (conflictError || syncConflict || rbacError) return;
    undo();
    syncUndo();
  };

  const handleRedo = () => {
    if (conflictError || syncConflict || rbacError) return;
    redo();
    syncRedo();
  };

  const handleCheckpoint = () => {
    if (conflictError || syncConflict || rbacError) return;
    triggerAutosaveMock();
    syncCheckpoint(drafts);
  };

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

      {(conflictError || syncConflict) && (
        <ConflictWarning
          onResolve={() => {
            setSyncConflict(false);
            setSyncError(null);
            retry();
          }}
        />
      )}

      {rbacError && <RbacLockNotice permission="workbench:edit" />}

      {syncError && (
        <ApiErrorBanner
          message={syncError}
          onDismiss={() => setSyncError(null)}
        />
      )}
      
      {/* Session lock banner status */}
      <WorkbenchSessionStatus
        loading={loading}
        error={error || syncError}
        rbacError={rbacError}
        conflictError={conflictError || syncConflict}
        sessionId={session?.id}
        rowVersion={session?.row_version}
        lastHeartbeat={lastHeartbeat}
        onRetry={() => {
          setSyncConflict(false);
          setSyncError(null);
          retry();
        }}
      />
      
      {/* Inline Toolbar for Undo/Redo */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "var(--space-sm) var(--space-lg)", borderBottom: "1px solid var(--border-color)", backgroundColor: "rgba(255,255,255,0.01)" }}>
        <UndoRedoControls
          undoDisabled={undoStack.length === 0}
          redoDisabled={redoStack.length === 0}
          onUndo={handleUndo}
          onRedo={handleRedo}
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
              onActiveRowChange={handleActiveRowChange}
              drafts={drafts}
              onDraftChange={handleDraftChange}
            />
          )}
        </main>
        <WorkbenchRightPanelShell contextData={selectedContextData} />
      </div>
      <WorkbenchFooter
        issuesCount={issuesCount}
        draftsCount={draftsCount}
        checkpoint={checkpoint}
        onAutosaveMock={handleCheckpoint}
      />
    </div>
  );
}
