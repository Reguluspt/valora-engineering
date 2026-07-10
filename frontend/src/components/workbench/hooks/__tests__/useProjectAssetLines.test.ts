import { describe, it, expect, vi, beforeEach } from "vitest";
import { mapAssetLinesToGridRows, useProjectAssetLines } from "../useProjectAssetLines";
import { ProjectAssetLineResponse } from "../../../../api/assetLines";
import * as api from "../../../../api/assetLines";

// Mock the API client
vi.mock("../../../../api/assetLines", () => ({
  fetchProjectAssetLines: vi.fn()
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
    vi.restoreAllMocks();
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

  it("blocks non-UUID slugs and returns friendly limitation state", async () => {
    const fetchSpy = vi.spyOn(api, "fetchProjectAssetLines");

    const setRows = vi.fn();
    const setLoading = vi.fn();
    const setErrorMsg = vi.fn();
    const setFriendlyError = vi.fn();

    // Map the dynamic state setters to tracking spies
    mockStateSetters = [setRows, setLoading, setErrorMsg, setFriendlyError];

    // Invoke hook with non-UUID slug
    useProjectAssetLines("hd-98-gia-lai");

    // Verify fetch API is NOT called
    expect(fetchSpy).not.toHaveBeenCalled();

    // Verify rows are cleared and friendly error set
    expect(setRows).toHaveBeenCalledWith([]);
    expect(setFriendlyError).toHaveBeenCalledWith({
      title: "Chưa xác định được mã hồ sơ",
      message: "Chưa xác định được mã hồ sơ để tải danh sách tài sản.",
      nextAction: "Vui lòng mở hồ sơ từ danh sách hồ sơ hoặc thử tải lại."
    });
    expect(setLoading).toHaveBeenCalledWith(false);
  });

  it("allows valid UUID project IDs to execute the API fetch call", async () => {
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

    mockStateSetters = [setRows, setLoading, setErrorMsg, setFriendlyError];

    // Invoke hook with a valid UUID
    const uuidVal = "033781ee-adca-4af2-a58b-43e7e43823b8";
    useProjectAssetLines(uuidVal);

    expect(fetchSpy).toHaveBeenCalledWith(uuidVal);
  });
});
