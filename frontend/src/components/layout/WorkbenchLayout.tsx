import React, { useState } from "react";
import { WorkbenchHeader } from "./WorkbenchHeader";
import { WorkbenchFooter } from "./WorkbenchFooter";
import { WorkbenchRightPanelShell } from "./WorkbenchRightPanelShell";
import { AssetGrid } from "../workbench/AssetGrid";
import { useProjectAssetLines } from "../workbench/hooks/useProjectAssetLines";
import { useAssetLineContext } from "../workbench/hooks/useAssetLineContext";
import { useWorkbenchDraftState } from "../workbench/hooks/useWorkbenchDraftState";

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
  const {
    rows,
    loading: gridLoading,
    friendlyError: gridFriendlyError,
    retry: retryGrid
  } = useProjectAssetLines("hd-98-gia-lai");
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

  const activeRow = React.useMemo(() => {
    return rows.find((r) => r.project_asset_line_id === activeRowId) || null;
  }, [rows, activeRowId]);

  const { contextData: resolvedContextData } = useAssetLineContext("hd-98-gia-lai", activeRow);

  const { draftStates } = useWorkbenchDraftState("hd-98-gia-lai");

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
            gridLoading ? (
              <div style={{ padding: "var(--space-lg)", color: "var(--text-muted)", textAlign: "center" }}>
                Đang tải danh sách tài sản...
              </div>
            ) : gridFriendlyError ? (
              <div className="state-container" style={{ padding: "var(--space-xl)", textAlign: "center" }}>
                <h2 className="state-title" style={{ color: "var(--color-danger)" }}>{gridFriendlyError.title}</h2>
                <p className="state-message" style={{ margin: "var(--space-md) 0" }}>{gridFriendlyError.message}</p>
                <p className="state-message" style={{ fontSize: "var(--font-size-sm)", color: "var(--text-muted)", marginBottom: "var(--space-lg)" }}>{gridFriendlyError.nextAction}</p>
                <button className="action-btn" onClick={retryGrid}>
                  Tải lại dữ liệu
                </button>
              </div>
            ) : (
              <AssetGrid
                rows={rows}
                onActiveRowChange={handleActiveRowChange}
                drafts={drafts}
                onDraftChange={handleDraftChange}
                draftStates={draftStates}
              />
            )
          )}
        </main>
        <WorkbenchRightPanelShell contextData={resolvedContextData} />
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
