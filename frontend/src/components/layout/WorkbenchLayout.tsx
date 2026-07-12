import React, { useState } from "react";
import { WorkbenchHeader } from "./WorkbenchHeader";
import { WorkbenchFooter } from "./WorkbenchFooter";
import { WorkbenchRightPanelShell } from "./WorkbenchRightPanelShell";
import { AssetGrid } from "../workbench/AssetGrid";
import { useProjectAssetLines } from "../workbench/hooks/useProjectAssetLines";
import { useAssetLineContext } from "../workbench/hooks/useAssetLineContext";
import { useWorkbenchDraftState } from "../workbench/hooks/useWorkbenchDraftState";
import { commitAssetLineDraft } from "../../api/projects";

import { useDraftSession } from "../workbench/drafts/useDraftSession";
import { UndoRedoControls } from "../workbench/drafts/UndoRedoControls";

import { useWorkbenchSession } from "../workbench/session/useWorkbenchSession";
import { WorkbenchSessionStatus } from "../workbench/session/WorkbenchSessionStatus";

import { useWorkbenchStateSync } from "../workbench/session/useWorkbenchStateSync";
import { useWorkbenchDraftSync } from "../workbench/session/useWorkbenchDraftSync";

import { useResolvedProject } from "../workbench/project-context";

import { ApiErrorBanner } from "../common/ApiErrorBanner";
import { ConflictWarning } from "../common/ConflictWarning";
import { RbacLockNotice } from "../common/RbacLockNotice";

interface WorkbenchLayoutProps {
  projectRef: string | null;
  children?: React.ReactNode;
}

export function WorkbenchLayout({ projectRef, children }: WorkbenchLayoutProps) {
  const { projectId, displayName, state, error: resolveError, retry: retryResolve } = useResolvedProject(projectRef);

  if (state === "idle" && !projectRef) {
    return (
      <div style={{ padding: "var(--space-xl)", textAlign: "center" }}>
        <h2 style={{ color: "#fff" }}>Chọn hồ sơ</h2>
        <p style={{ color: "var(--text-muted)", marginBottom: "var(--space-lg)" }}>
          Vui lòng chọn một hồ sơ từ thanh điều hướng để bắt đầu làm việc.
        </p>
      </div>
    );
  }

  if (state === "loading") {
    return (
      <div style={{ padding: "var(--space-xl)", textAlign: "center", color: "var(--text-muted)" }}>
        Đang tải thông tin hồ sơ...
      </div>
    );
  }

  if (state === "error" && resolveError) {
    return (
      <div className="state-container" style={{ padding: "var(--space-xl)", textAlign: "center" }}>
        <h2 className="state-title" style={{ color: "var(--color-danger)" }}>{resolveError.title}</h2>
        <p className="state-message" style={{ margin: "var(--space-md) 0" }}>{resolveError.message}</p>
        <p className="state-message" style={{ fontSize: "var(--font-size-sm)", color: "var(--text-muted)", marginBottom: "var(--space-lg)" }}>{resolveError.nextAction}</p>
        <button className="action-btn" onClick={retryResolve}>
          Thử lại
        </button>
      </div>
    );
  }

  if (!projectId) {
    return null;
  }

  return (
    <WorkbenchLayoutInner
      projectId={projectId}
      displayName={displayName || "Hồ sơ"}
      children={children}
    />
  );
}

function WorkbenchLayoutInner({
  projectId,
  displayName,
  children
}: {
  projectId: string;
  displayName: string;
  children?: React.ReactNode;
}) {
  const {
    rows,
    loading: gridLoading,
    friendlyError: gridFriendlyError,
    loadMore,
    hasMore,
    loadedCount,
    totalCount,
    retry: retryGrid
  } = useProjectAssetLines(projectId);
  const [activeRowId, setActiveRowId] = useState<string | null>(null);

  const {
    session,
    loading,
    error,
    rbacError,
    conflictError,
    lastHeartbeat,
    retry
  } = useWorkbenchSession(projectId);

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
    projectId,
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

  const handleDraftChange = async (id: string, field: string, value: any, baseValue: any, rowVersion: number) => {
    if (conflictError || syncConflict || rbacError) return;
    updateDraft(id, field, value, baseValue, rowVersion);
    await syncInlineEdit("ProjectAssetLine", id, field, value, baseValue, rowVersion);
    reloadDrafts();
  };

  const handleCommitDraft = async (id: string, fields: string[], versionToken: string) => {
    try {
      await commitAssetLineDraft(projectId, id, {
        field_keys: fields,
        confirm: true,
        version_token: versionToken
      });
      retryGrid();
      reloadDrafts();
    } catch (err: any) {
      alert("Không thể áp dụng nháp\n" + (err.message || ""));
    }
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

  const { contextData: resolvedContextData } = useAssetLineContext(projectId, activeRow);

  const { draftStates, reload: reloadDrafts } = useWorkbenchDraftState(projectId);

  const draftsCount = Object.keys(drafts).length;

  return (
    <div className="workbench-container">
      <WorkbenchHeader
        projectTitle={displayName}
        status="draft"
        statusLabel="Bản nháp"
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

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "var(--space-sm) var(--space-lg)", borderBottom: "1px solid var(--border-color)", backgroundColor: "rgba(255,255,255,0.01)" }}>
        <UndoRedoControls
          undoDisabled={undoStack.length === 0}
          redoDisabled={redoStack.length === 0}
          onUndo={handleUndo}
          onRedo={handleRedo}
        />
        <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>
          Nhấn đúp vào ô để chỉnh sửa nháp.
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
              <>
                <AssetGrid
                  rows={rows}
                  onActiveRowChange={handleActiveRowChange}
                  drafts={drafts}
                  onDraftChange={handleDraftChange}
                  draftStates={draftStates}
                  onCommitDraft={handleCommitDraft}
                />
                {hasMore && (
                  <div style={{ textAlign: "center", padding: "var(--space-md)" }}>
                    <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)", marginRight: "var(--space-md)" }}>
                      Đã tải {loadedCount}/{totalCount} dòng
                    </span>
                    <button className="action-btn" onClick={loadMore} style={{ fontSize: "var(--font-size-xs)" }}>
                      Tải thêm
                    </button>
                  </div>
                )}
                {!hasMore && totalCount > 0 && (
                  <div style={{ textAlign: "center", padding: "var(--space-md)", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>
                    Đã tải toàn bộ {totalCount} dòng
                  </div>
                )}
              </>
            )
          )}
        </main>
        <WorkbenchRightPanelShell contextData={resolvedContextData} />
      </div>
      <WorkbenchFooter
        issuesCount={0}
        draftsCount={draftsCount}
        checkpoint={checkpoint}
        onAutosaveMock={handleCheckpoint}
      />
    </div>
  );
}
