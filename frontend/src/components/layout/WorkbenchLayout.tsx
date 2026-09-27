import React, { useRef, useState } from "react";
import "../workbench/workbench.css";
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
  onNavigateOverview?: () => void;
  children?: React.ReactNode;
}

export function WorkbenchLayout({ projectRef, onNavigateOverview, children }: WorkbenchLayoutProps) {
  const { projectId, displayName, state, error: resolveError, retry: retryResolve } = useResolvedProject(projectRef);

  if (state === "idle" && !projectRef) {
    return (
      <div className="workbench-page-state">
        <h2>Chọn hồ sơ</h2>
        <p>
          Vui lòng chọn một hồ sơ từ thanh điều hướng để bắt đầu làm việc.
        </p>
      </div>
    );
  }

  if (state === "loading") {
    return (
      <div className="workbench-page-state" role="status">
        Đang tải thông tin hồ sơ...
      </div>
    );
  }

  if (state === "error" && resolveError) {
    return (
      <div className="state-container workbench-page-state" role="alert">
        <h2 className="state-title">{resolveError.title}</h2>
        <p className="state-message">{resolveError.message}</p>
        <p className="state-message">{resolveError.nextAction}</p>
        <button className="valora-button valora-button--secondary" onClick={retryResolve}>
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
      key={projectId}
      projectId={projectId}
      displayName={displayName || "Hồ sơ"}
      onNavigateOverview={onNavigateOverview}
      children={children}
    />
  );
}

function WorkbenchLayoutInner({
  projectId,
  displayName,
  onNavigateOverview,
  children
}: {
  projectId: string;
  displayName: string;
  onNavigateOverview?: () => void;
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
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerTriggerRef = useRef<HTMLButtonElement>(null);

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
      setDrawerOpen(true);
      syncSelection("ProjectAssetLine", [id]);
    } else {
      setDrawerOpen(false);
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

  const { contextData: resolvedContextData, loading: contextLoading, errorMsg: contextError } = useAssetLineContext(projectId, activeRow);

  const { draftStates, reload: reloadDrafts } = useWorkbenchDraftState(projectId);

  const draftsCount = Object.keys(drafts).length;

  return (
    <div className="workbench-container">
      <WorkbenchHeader
        projectTitle={displayName}
        onNavigateOverview={onNavigateOverview}
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

      <div className="valora-command-bar workbench-command-bar">
        <UndoRedoControls
          undoDisabled={undoStack.length === 0}
          redoDisabled={redoStack.length === 0}
          onUndo={handleUndo}
          onRedo={handleRedo}
        />
        <button
          ref={drawerTriggerRef}
          type="button"
          className="valora-button valora-button--secondary"
          disabled={!activeRow}
          onClick={() => setDrawerOpen(true)}
          aria-expanded={Boolean(activeRow && drawerOpen)}
          aria-controls="asset-context-drawer"
        >
          Xem ngữ cảnh tài sản
        </button>
        {activeRow && <span className="workbench-active-asset">Đang chọn: {activeRow.raw_name}</span>}
        <span className="workbench-command-hint">
          Chọn ô giá để chỉnh sửa nháp.
        </span>
      </div>

      <div className="workbench-body">
        <main className="workbench-grid-pane">
          {children || (
            gridLoading ? (
              <div className="workbench-page-state" role="status">
                Đang tải danh sách tài sản...
              </div>
            ) : gridFriendlyError ? (
              <div className="state-container workbench-page-state" role="alert">
                <h2 className="state-title">{gridFriendlyError.title}</h2>
                <p className="state-message">{gridFriendlyError.message}</p>
                <p className="state-message">{gridFriendlyError.nextAction}</p>
                <button className="valora-button valora-button--secondary" onClick={retryGrid}>
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
                  <div className="workbench-load-more">
                    <span>
                      Đã tải {loadedCount}/{totalCount} dòng
                    </span>
                    <button className="valora-button valora-button--secondary" onClick={loadMore}>
                      Tải thêm
                    </button>
                  </div>
                )}
                {!hasMore && totalCount > 0 && (
                  <div className="workbench-load-more">
                    Đã tải toàn bộ {totalCount} dòng
                  </div>
                )}
              </>
            )
          )}
        </main>
        {activeRow && drawerOpen && (
          <div id="asset-context-drawer" className="workbench-drawer-layer">
            <WorkbenchRightPanelShell
              asset={activeRow}
              contextData={resolvedContextData}
              loading={contextLoading}
              error={contextError}
              onClose={() => {
                setDrawerOpen(false);
                drawerTriggerRef.current?.focus();
              }}
            />
          </div>
        )}
      </div>
      <WorkbenchFooter
        draftsCount={draftsCount}
        checkpoint={checkpoint}
        onAutosaveMock={handleCheckpoint}
      />
    </div>
  );
}
