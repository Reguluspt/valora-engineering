import { act, create } from "react-test-renderer";
import { describe, expect, it, vi } from "vitest";
import { WorkbenchLayout } from "../WorkbenchLayout";

const state = vi.hoisted(() => ({ syncSelection: vi.fn() }));

vi.mock("../../workbench/project-context", () => ({
  useResolvedProject: () => ({ projectId: "project-1", displayName: "Hồ sơ 1", state: "ready", error: null, retry: vi.fn() }),
}));
vi.mock("../../workbench/hooks/useProjectAssetLines", () => ({
  useProjectAssetLines: () => ({
    rows: [{ project_asset_line_id: "line-1", line_no: 1, raw_name: "Máy cắt", quantity: 1 }],
    loading: false, friendlyError: null, loadMore: vi.fn(), hasMore: false,
    loadedCount: 1, totalCount: 1, retry: vi.fn(),
  }),
}));
vi.mock("../../workbench/hooks/useAssetLineContext", () => ({
  useAssetLineContext: (_projectId: string, asset: { project_asset_line_id: string } | null) => ({
    contextData: asset ? {
      project_asset_line_id: asset.project_asset_line_id,
      knowledge_panel: null, price_evidence_panel: null, lineage: null, validation_issues: null,
    } : undefined,
    loading: false, errorMsg: null,
  }),
}));
vi.mock("../../workbench/hooks/useWorkbenchDraftState", () => ({
  useWorkbenchDraftState: () => ({ draftStates: {}, reload: vi.fn() }),
}));
vi.mock("../../workbench/drafts/useDraftSession", () => ({
  useDraftSession: () => ({
    drafts: {}, undoStack: [], redoStack: [], checkpoint: null,
    updateDraft: vi.fn(), undo: vi.fn(), redo: vi.fn(), triggerAutosaveMock: vi.fn(),
  }),
}));
vi.mock("../../workbench/session/useWorkbenchSession", () => ({
  useWorkbenchSession: () => ({
    session: { id: "session-1", row_version: 1 }, loading: false, error: null,
    rbacError: null, conflictError: false, lastHeartbeat: "12:00", retry: vi.fn(),
  }),
}));
vi.mock("../../workbench/session/useWorkbenchStateSync", () => ({
  useWorkbenchStateSync: () => ({ syncSelection: state.syncSelection }),
}));
vi.mock("../../workbench/session/useWorkbenchDraftSync", () => ({
  useWorkbenchDraftSync: () => ({
    syncInlineEdit: vi.fn(), syncCheckpoint: vi.fn(), syncUndo: vi.fn(), syncRedo: vi.fn(),
  }),
}));
vi.mock("../WorkbenchHeader", () => ({ WorkbenchHeader: () => null }));
vi.mock("../WorkbenchFooter", () => ({ WorkbenchFooter: () => null }));
vi.mock("../../workbench/session/WorkbenchSessionStatus", () => ({ WorkbenchSessionStatus: () => null }));
vi.mock("../../workbench/drafts/UndoRedoControls", () => ({ UndoRedoControls: () => null }));
vi.mock("../../workbench/AssetGrid", () => ({
  AssetGrid: ({ onActiveRowChange }: { onActiveRowChange: (id: string) => void }) => (
    <button onClick={() => onActiveRowChange("line-1")}>Chọn tài sản</button>
  ),
}));

describe("Workbench contextual drawer placement", () => {
  it("mounts the drawer only for an active asset and closes without clearing selection", () => {
    state.syncSelection.mockClear();
    let root: ReturnType<typeof create>;
    act(() => { root = create(<WorkbenchLayout projectRef="project-1" />); });
    expect(root!.root.findAllByType("aside")).toHaveLength(0);
    expect(JSON.stringify(root!.toJSON())).not.toContain("Nguồn giá & chứng cứ");

    const selectAsset = root!.root.findByProps({ children: "Chọn tài sản" });
    act(() => selectAsset.props.onClick());
    expect(root!.root.findAllByType("aside")).toHaveLength(1);
    expect(JSON.stringify(root!.toJSON())).toContain("Máy cắt");
    expect(state.syncSelection).toHaveBeenCalledExactlyOnceWith("ProjectAssetLine", ["line-1"]);

    const close = root!.root.findByProps({ "aria-label": "Đóng ngữ cảnh tài sản" });
    act(() => close.props.onClick());
    expect(root!.root.findAllByType("aside")).toHaveLength(0);
    expect(state.syncSelection).toHaveBeenCalledTimes(1);

    const reopen = root!.root.findByProps({ "aria-controls": "asset-context-drawer" });
    expect(reopen.props.disabled).toBe(false);
    act(() => reopen.props.onClick());
    expect(root!.root.findAllByType("aside")).toHaveLength(1);
    expect(state.syncSelection).toHaveBeenCalledTimes(1);
  });
});
