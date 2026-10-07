import { act, create } from "react-test-renderer";
import { describe, expect, it, vi } from "vitest";
import { WorkbenchLayout } from "../WorkbenchLayout";

const state = vi.hoisted(() => ({ syncSelection: vi.fn(), loadMore: vi.fn(),
  rows: [{ project_asset_line_id: "line-1", line_no: 1, raw_name: "Máy cắt", quantity: 1 }],
  hasMore: false, evidenceProjection: null as any }));
vi.mock("../../workbench/price-evidence/usePriceEvidence", () => ({
  usePriceEvidence: () => ({ projection: state.evidenceProjection, snapshot: null, workspace: null, enabled: false,
    loading: false, busy: false, error: "", notice: "", pending: null, refresh: vi.fn() }),
}));
vi.mock("@fluentui/react-components", async importOriginal => {
  const original = await importOriginal<typeof import("@fluentui/react-components")>();
  return { ...original, TabList: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    Tab: ({ children, ...props }: any) => <button role="tab" {...props}>{children}</button> };
});

vi.mock("../../workbench/project-context", () => ({
  useResolvedProject: () => ({ projectId: "project-1", displayName: "Hồ sơ 1", state: "ready", error: null, retry: vi.fn() }),
}));
vi.mock("../../workbench/hooks/useProjectAssetLines", () => ({
  useProjectAssetLines: () => ({
    rows: state.rows,
    loading: false, loadingMore: false, friendlyError: null, loadMore: state.loadMore, hasMore: state.hasMore,
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
  it("progressively loads the exact PRICE_EVIDENCE target then opens its price tab without selection mutation", () => {
    state.syncSelection.mockClear(); state.loadMore.mockClear(); state.hasMore = true;
    state.evidenceProjection = { case_version: "case", stages: [], next_action: { kind: "PENDING", stage: "PRICE_EVIDENCE",
      semantic_route_key: "price_evidence_prepare_required", context: { kind: "price_evidence_preparation", project_id: "project-1",
        case_version: "case", line_id: "line-2" } } };
    let root: ReturnType<typeof create>;
    act(() => { root = create(<WorkbenchLayout projectRef="project-1" />); });
    expect(state.loadMore).toHaveBeenCalledOnce(); expect(root!.root.findAllByType("aside")).toHaveLength(0);
    state.rows = [...state.rows, { project_asset_line_id: "line-2", line_no: 2, raw_name: "Máy thứ hai", quantity: 1 }];
    state.hasMore = false;
    act(() => root!.update(<WorkbenchLayout projectRef="project-1" />));
    expect(root!.root.findAllByType("aside")).toHaveLength(1);
    expect(JSON.stringify(root!.toJSON())).toContain("Máy thứ hai");
    expect(root!.root.findByProps({ role: "tabpanel" }).props["aria-labelledby"]).toBe("asset-context-tab-price");
    expect(state.syncSelection).not.toHaveBeenCalled();
    act(() => root!.unmount()); state.rows = state.rows.slice(0, 1); state.evidenceProjection = null;
  });
  it("ignores a PRICE_EVIDENCE target with a mismatched project or case token", () => {
    state.evidenceProjection = { case_version: "case", stages: [], next_action: { kind: "PENDING", stage: "PRICE_EVIDENCE",
      semantic_route_key: "price_evidence_prepare_required", context: { kind: "price_evidence_preparation", project_id: "other",
        case_version: "old-case", line_id: "line-1" } } };
    let root: ReturnType<typeof create>;
    act(() => { root = create(<WorkbenchLayout projectRef="project-1" />); });
    expect(root!.root.findAllByType("aside")).toHaveLength(0);
    act(() => root!.unmount()); state.evidenceProjection = null;
  });
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
    expect(state.syncSelection).toHaveBeenCalledExactlyOnceWith("project_asset_line", ["line-1"]);

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
