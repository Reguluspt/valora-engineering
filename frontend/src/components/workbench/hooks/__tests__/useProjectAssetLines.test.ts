import { describe, it, expect, vi, beforeEach } from "vitest";
import { mapAssetLinesToGridRows, useProjectAssetLines } from "../useProjectAssetLines";
import { ProjectAssetLineResponse } from "../../../../api/assetLines";
import * as api from "../../../../api/assetLines";
import * as projectsApi from "../../../../api/projects";

// Mock the API clients
vi.mock("../../../../api/assetLines", () => ({
  fetchProjectAssetLines: vi.fn()
}));

vi.mock("../../../../api/projects", () => ({
  resolveProjectReference: vi.fn()
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

describe("useProjectAssetLines read adapter helper tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStateValues = [];
    mockStateSetters = [];
    mockStateIndex = 0;
  });

  it("correctly maps API responses to AssetLineGridRow items", () => {
    const mockApiResponseItems: ProjectAssetLineResponse[] = [
      {
        id: "id-123",
        project_id: "proj-abc",
        asset_name: "Máy phát điện ABB 500kVA",
        description: "ABB Generator Spec",
        quantity: 2,
        unit_id: "unit-pcs",
        raw_price: 150000000,
        raw_price_currency_id: "cur-vnd",
        appraised_unit_price: 145000000,
        appraised_currency_id: "cur-vnd",
        review_status: "raw",
        validation_status: "needs_review",
        brand_id: "brand-abb",
        manufacturer_id: "mfg-abb",
        version_token: "7"
      }
    ];

    const gridRows = mapAssetLinesToGridRows(mockApiResponseItems);

    expect(gridRows).toHaveLength(1);
    const row = gridRows[0];

    // Assert key mapping values
    expect(row.project_asset_line_id).toBe("id-123");
    expect(row.line_no).toBe(1);
    expect(row.raw_name).toBe("Máy phát điện ABB 500kVA");
    expect(row.quantity).toBe(2);
    expect(row.unit.id).toBe("unit-pcs");
    expect(row.supplier_quote_1).toBe(150000000);
    expect(row.appraised_price).toBe(145000000);
    
    // Check validation and review statuses mapping
    expect(row.validation_status).toBe("warning"); // mapped from needs_review
    expect(row.review_status).toBe("raw");

    // Concurrency token checks
    expect(row.row_version).toBe(7); // parsed from version_token

    // Guardrail check: version_token / row_version must not be exposed to user display keys
    const displayedKeys = Object.keys(row);
    expect(displayedKeys).not.toContain("version_token");
  });

  it("handles empty items lists correctly returning empty arrays", () => {
    const gridRows = mapAssetLinesToGridRows([]);
    expect(gridRows).toHaveLength(0);
  });

  it("triggers resolver on slug route params and calls asset lines only after resolution", async () => {
    const resolveSpy = vi.spyOn(projectsApi, "resolveProjectReference").mockResolvedValue({
      project_id: "033781ee-adca-4af2-a58b-43e7e43823b8",
      display_name: "Gia Lai 98",
      matched_by: "code_slug"
    });
    const fetchSpy = vi.spyOn(api, "fetchProjectAssetLines").mockResolvedValue({
      project_id: "033781ee-adca-4af2-a58b-43e7e43823b8",
      items: [],
      total: 0,
      limit: 50,
      offset: 0
    });

    const setRows = vi.fn();
    const setLoading = vi.fn();
    const setErrorMsg = vi.fn();
    const setFriendlyError = vi.fn();
    const setResolvedUuid = vi.fn();

    mockStateSetters = [setRows, setLoading, setErrorMsg, setFriendlyError, setResolvedUuid];

    // Mock initial value for resolvedUuid inside the state flow to simulate useEffect dependency updates
    mockStateValues[4] = "033781ee-adca-4af2-a58b-43e7e43823b8";

    // Invoke hook with non-UUID slug
    useProjectAssetLines("hd-98-gia-lai");

    // Wait for resolve promise to settle
    await new Promise(resolve => setTimeout(resolve, 10));

    // Verify resolve endpoint was called first
    expect(resolveSpy).toHaveBeenCalledWith("hd-98-gia-lai");
    // Verify fetch endpoint was called with the resolved UUID
    expect(fetchSpy).toHaveBeenCalledWith("033781ee-adca-4af2-a58b-43e7e43823b8");
  });

  it("handles resolver failure showing friendly Vietnamese state", async () => {
    const resolveSpy = vi.spyOn(projectsApi, "resolveProjectReference").mockRejectedValue({
      status: 404,
      message: "Project not found"
    });
    const fetchSpy = vi.spyOn(api, "fetchProjectAssetLines");

    const setRows = vi.fn();
    const setLoading = vi.fn();
    const setErrorMsg = vi.fn();
    const setFriendlyError = vi.fn();
    const setResolvedUuid = vi.fn();

    mockStateSetters = [setRows, setLoading, setErrorMsg, setFriendlyError, setResolvedUuid];

    // Invoke hook with non-UUID slug
    useProjectAssetLines("hd-98-invalid-slug");

    // Wait for the promise rejection and state updates to settle
    await new Promise(resolve => setTimeout(resolve, 10));

    // Verify resolve was triggered
    expect(resolveSpy).toHaveBeenCalledWith("hd-98-invalid-slug");
    // Verify fetch was NOT triggered since resolution failed
    expect(fetchSpy).not.toHaveBeenCalled();

    // Verify friendly error matches Vietnamese dictionary limits
    expect(setFriendlyError).toHaveBeenCalledWith({
      title: "Không tìm thấy hồ sơ",
      message: "Không tìm thấy hồ sơ tương ứng với mã cung cấp.",
      nextAction: "Vui lòng mở hồ sơ từ danh sách hồ sơ hoặc thử tải lại."
    });
  });

  it("allows valid UUID project IDs to bypass resolver and fetch asset lines directly", async () => {
    const resolveSpy = vi.spyOn(projectsApi, "resolveProjectReference");
    const fetchSpy = vi.spyOn(api, "fetchProjectAssetLines").mockResolvedValue({
      project_id: "033781ee-adca-4af2-a58b-43e7e43823b8",
      items: [],
      total: 0,
      limit: 50,
      offset: 0
    });

    const setRows = vi.fn();
    const setLoading = vi.fn();
    const setErrorMsg = vi.fn();
    const setFriendlyError = vi.fn();
    const setResolvedUuid = vi.fn();

    mockStateSetters = [setRows, setLoading, setErrorMsg, setFriendlyError, setResolvedUuid];

    // Simulating UUID resolution mapping
    mockStateValues[4] = "033781ee-adca-4af2-a58b-43e7e43823b8";

    // Invoke hook with a valid UUID
    const uuidVal = "033781ee-adca-4af2-a58b-43e7e43823b8";
    useProjectAssetLines(uuidVal);

    // Wait for any async effects to drain
    await new Promise(resolve => setTimeout(resolve, 10));

    // Verify resolver was bypassed
    expect(resolveSpy).not.toHaveBeenCalled();
    // Verify fetch was executed directly
    expect(fetchSpy).toHaveBeenCalledWith(uuidVal);
  });
});
