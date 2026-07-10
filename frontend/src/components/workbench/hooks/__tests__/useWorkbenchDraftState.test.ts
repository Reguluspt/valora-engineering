import { describe, it, expect, vi, beforeEach } from "vitest";
import { getDraftStatusLabelVi, getDraftStatusBadge, useWorkbenchDraftState } from "../useWorkbenchDraftState";
import * as projectsApi from "../../../../api/projects";

// Mock the API client
vi.mock("../../../../api/projects", () => ({
  fetchProjectDraftState: vi.fn()
}));

// Dynamic mocks for React hooks
let mockStateValues: any[] = [];
let mockStateSetters: any[] = [];
let mockStateIndex = 0;

vi.mock("react", async () => {
  const actual = await vi.importActual<any>("react");
  return {
    ...actual,
    useState: (init: any) => {
      const idx = mockStateIndex;
      mockStateIndex++;
      if (mockStateValues[idx] === undefined) {
        mockStateValues[idx] = init;
      }
      const setter = (val: any) => {
        mockStateValues[idx] = val;
        if (mockStateSetters[idx]) {
          mockStateSetters[idx](val);
        }
      };
      return [mockStateValues[idx], setter];
    },
    useEffect: (fn: any) => fn(),
    useCallback: (fn: any) => fn,
  };
});

describe("useWorkbenchDraftState hook tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStateValues = [];
    mockStateSetters = [];
    mockStateIndex = 0;
  });

  it("correctly maps raw status values to friendly Vietnamese labels and status badges", () => {
    // 1. stale
    expect(getDraftStatusLabelVi("stale", false)).toBe("Cần cập nhật mới");
    expect(getDraftStatusBadge("stale", false)).toBe("warning");

    // 2. locked
    expect(getDraftStatusLabelVi("locked", false)).toBe("Đang khóa");
    expect(getDraftStatusBadge("locked", false)).toBe("blocking");

    // 3. unsaved changes (local dirty states check takes precedence over clean/saved drafts)
    expect(getDraftStatusLabelVi("clean", true)).toBe("Chưa lưu");
    expect(getDraftStatusBadge("clean", true)).toBe("draft");

    // 4. saved_draft
    expect(getDraftStatusLabelVi("saved_draft", false)).toBe("Đã lưu nháp");
    expect(getDraftStatusBadge("saved_draft", false)).toBe("review");

    // 5. clean
    expect(getDraftStatusLabelVi("clean", false)).toBe("Không có thay đổi");
    expect(getDraftStatusBadge("clean", false)).toBe("approved");
  });

  it("fetches and maps draft states safely without leaking internal tokens", async () => {
    const mockApiResponse: projectsApi.ProjectDraftStateResponse = {
      project_id: "033781ee-adca-4af2-a58b-43e7e43823b8",
      items: [
        {
          asset_line_id: "line-abc",
          has_saved_draft: true,
          has_unsaved_changes: false,
          is_locked: false,
          is_stale: true,
          draft_status: "stale",
          changed_fields: ["appraised_price"],
          last_saved_at: "2026-07-10T15:00:00Z",
          last_saved_by: "user-1"
        }
      ],
      total: 1
    };

    const fetchSpy = vi.spyOn(projectsApi, "fetchProjectDraftState").mockResolvedValue(mockApiResponse);

    const setDraftStates = vi.fn();
    const setLoading = vi.fn();
    const setErrorMsg = vi.fn();
    const setFriendlyError = vi.fn();

    mockStateSetters = [setDraftStates, setLoading, setErrorMsg, setFriendlyError];

    // Invoke hook with a valid UUID
    const uuidVal = "033781ee-adca-4af2-a58b-43e7e43823b8";
    useWorkbenchDraftState(uuidVal);

    // Wait for the async effect to resolve
    await new Promise(resolve => setTimeout(resolve, 10));

    expect(fetchSpy).toHaveBeenCalledWith(uuidVal);
    expect(setDraftStates).toHaveBeenCalled();

    const resolvedMap = setDraftStates.mock.calls[0][0];
    expect(resolvedMap["line-abc"]).toBeDefined();
    expect(resolvedMap["line-abc"].draft_status).toBe("stale");

    // Guardrail: version_token or row_version are not returned in the draft response model
    const textStr = JSON.stringify(resolvedMap);
    expect(textStr).not.toContain("row_version");
    expect(textStr).not.toContain("version_token");
  });
});
