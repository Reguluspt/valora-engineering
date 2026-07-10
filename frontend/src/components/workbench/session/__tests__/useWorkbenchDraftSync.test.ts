import { describe, it, expect, vi, beforeEach } from "vitest";
import { useWorkbenchDraftSync } from "../useWorkbenchDraftSync";
import * as projectsApi from "../../../../api/projects";
import * as workbenchDraftsApi from "../../../../api/workbenchDrafts";

vi.mock("react", () => ({
  useCallback: (fn: any) => fn
}));

vi.mock("../../../../api/projects", () => ({
  saveAssetLineDraft: vi.fn(),
  commitAssetLineDraft: vi.fn()
}));

vi.mock("../../../../api/workbenchDrafts", () => ({
  saveInlineEdit: vi.fn()
}));

describe("useWorkbenchDraftSync Hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fails and triggers onError callback when unsupported fields are edited", async () => {
    const saveDraftSpy = vi.spyOn(projectsApi, "saveAssetLineDraft").mockResolvedValue({} as any);
    const onErrorMock = vi.fn();

    const { syncInlineEdit } = useWorkbenchDraftSync("sess-123", "proj-uuid", onErrorMock);
    
    await syncInlineEdit("ProjectAssetLine", "l1", "normalized_name", "New Descr", "Old Descr", 42);

    expect(onErrorMock).toHaveBeenCalledWith("Trường dữ liệu này chưa hỗ trợ chỉnh sửa");
    expect(saveDraftSpy).not.toHaveBeenCalled();
  });

  it("handles appraised_price mapping to appraised_unit_price", async () => {
    const saveDraftSpy = vi.spyOn(projectsApi, "saveAssetLineDraft").mockResolvedValue({} as any);

    const { syncInlineEdit } = useWorkbenchDraftSync("sess-123", "proj-uuid");
    await syncInlineEdit("ProjectAssetLine", "l1", "appraised_price", 100000, 90000, 3);

    expect(saveDraftSpy).toHaveBeenCalledWith("proj-uuid", "l1", {
      field_key: "appraised_unit_price",
      draft_value: 100000,
      base_value: 90000,
      version_token: "3"
    });
  });

  it("verifies commitAssetLineDraft API client can be invoked with confirmation parameters", async () => {
    const commitSpy = vi.spyOn(projectsApi, "commitAssetLineDraft").mockResolvedValue({
      project_id: "p1",
      asset_line_id: "l1",
      committed_fields: ["appraised_unit_price"],
      draft_status: "clean",
      has_saved_draft: false,
      has_unsaved_changes: false,
      is_stale: false,
      committed_at: "2026-07-10T16:00:00Z"
    });

    const res = await projectsApi.commitAssetLineDraft("p1", "l1", {
      field_keys: ["appraised_unit_price"],
      confirm: true
    });

    expect(commitSpy).toHaveBeenCalledWith("p1", "l1", {
      field_keys: ["appraised_unit_price"],
      confirm: true
    });
    expect(res.draft_status).toBe("clean");
  });
});
