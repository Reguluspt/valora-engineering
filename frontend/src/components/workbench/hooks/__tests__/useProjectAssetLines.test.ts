import { describe, it, expect, vi, beforeEach } from "vitest";
import { mapAssetLinesToGridRows, useProjectAssetLines } from "../useProjectAssetLines";
import { ProjectAssetLineResponse } from "../../../../api/assetLines";
import * as api from "../../../../api/assetLines";

vi.mock("../../../../api/assetLines", () => ({
  fetchProjectAssetLines: vi.fn()
}));

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
    useEffect: (fn: any, deps?: any[]) => fn(),
    useCallback: (fn: any) => fn,
    useRef: (init: any) => ({ current: init }),
  };
});

describe("mapAssetLinesToGridRows truthful mapping", () => {
  const mk = (overrides: Partial<ProjectAssetLineResponse> = {}): ProjectAssetLineResponse => ({
    id: "id-x", project_id: "p", asset_name: "X",
    description: null, quantity: 1, unit_id: null, raw_price: null,
    raw_price_currency_id: null, appraised_unit_price: null, appraised_currency_id: null,
    review_status: "raw", validation_status: "valid",
    brand_id: null, manufacturer_id: null, version_token: "1",
    ...overrides
  });

  it("maps API responses with null for unavailable fields and offset-based line_no", () => {
    const items = [mk({ id: "id-123", asset_name: "A" }), mk({ id: "id-124", asset_name: "B" })]
    const rows = mapAssetLinesToGridRows(items, 10);
    expect(rows[0].line_no).toBe(11);
    expect(rows[1].line_no).toBe(12);
    expect(rows[0].normalized_name).toBeNull();
    expect(rows[0].canonical_asset).toBeNull();
    expect(rows[0].unit).toBeNull();
    expect(rows[0].currency).toBeNull();
  });

  it("handles null appraised_unit_price correctly — preserves null", () => {
    const rows = mapAssetLinesToGridRows([mk({ appraised_unit_price: null })], 0);
    expect(rows[0].appraised_price).toBeNull();
  });

  it("preserves legitimate zero as zero", () => {
    const rows = mapAssetLinesToGridRows([mk({ appraised_unit_price: 0 })], 0);
    expect(rows[0].appraised_price).toBe(0);
  });

  it("handles invalid version_token strictly — returns null", () => {
    const invalidTokens = ["", "0", "1abc", "abc", "1.5", "-1", " 1", "99999999999999999999"];
    for (const tok of invalidTokens) {
      const rows = mapAssetLinesToGridRows([mk({ version_token: tok })], 0);
      expect(rows[0].row_version).toBeNull();
    }
  });

  it("parses valid positive integer version_token", () => {
    const rows = mapAssetLinesToGridRows([mk({ version_token: "7" })], 0);
    expect(rows[0].row_version).toBe(7);
  });

  it("handles empty items list", () => {
    expect(mapAssetLinesToGridRows([], 0)).toHaveLength(0);
  });
});

describe("useProjectAssetLines pagination", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStateValues = [];
    mockStateSetters = [];
    mockStateIndex = 0;
  });

  it("fetches first page with limit and offset 0", async () => {
    const fetchSpy = vi.spyOn(api, "fetchProjectAssetLines").mockResolvedValue({
      project_id: "uuid-123", items: [], total: 120, limit: 50, offset: 0
    });
    mockStateSetters = [vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn()];
    useProjectAssetLines("uuid-123");
    await new Promise(resolve => setTimeout(resolve, 10));
    expect(fetchSpy).toHaveBeenCalledWith("uuid-123", { limit: 50, offset: 0 });
  });

  it("exposes totalCount and hasMore from paginated response", async () => {
    vi.spyOn(api, "fetchProjectAssetLines").mockResolvedValue({
      project_id: "uuid-456", items: [], total: 75, limit: 50, offset: 0
    });
    const setTotalCount = vi.fn();
    const setHasMore = vi.fn();
    mockStateSetters = [vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), setTotalCount, setHasMore];
    useProjectAssetLines("uuid-456");
    await new Promise(resolve => setTimeout(resolve, 10));
    expect(setTotalCount).toHaveBeenCalledWith(75);
    expect(setHasMore).toHaveBeenCalledWith(true);
  });

  it("hasMore is false when total <= page size", async () => {
    vi.spyOn(api, "fetchProjectAssetLines").mockResolvedValue({
      project_id: "uuid-3", items: [], total: 30, limit: 50, offset: 0
    });
    const setHasMore = vi.fn();
    mockStateSetters = [vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), setHasMore];
    useProjectAssetLines("uuid-3");
    await new Promise(resolve => setTimeout(resolve, 10));
    expect(setHasMore).toHaveBeenCalledWith(false);
  });

  it("does not fetch when projectId is empty", () => {
    const fetchSpy = vi.spyOn(api, "fetchProjectAssetLines");
    useProjectAssetLines("");
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
