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
    useEffect: (fn: any) => fn(),
    useCallback: (fn: any) => fn,
  };
});

describe("mapAssetLinesToGridRows truthful mapping", () => {
  it("maps API responses with null for unavailable fields", () => {
    const mockApiResponseItems: ProjectAssetLineResponse[] = [
      {
        id: "id-123",
        project_id: "proj-abc",
        asset_name: "Máy phát điện ABB 500kVA",
        description: "ABB Generator Spec",
        quantity: 2,
        unit_id: null,
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

    expect(row.project_asset_line_id).toBe("id-123");
    expect(row.line_no).toBe(1);
    expect(row.raw_name).toBe("Máy phát điện ABB 500kVA");
    expect(row.normalized_name).toBeNull();
    expect(row.canonical_asset).toBeNull();
    expect(row.asset_variant).toBeNull();
    expect(row.taxonomy_node).toBeNull();
    expect(row.quantity).toBe(2);
    expect(row.unit).toBeNull();
    expect(row.supplier_quote_1).toBeNull();
    expect(row.supplier_quote_2).toBeNull();
    expect(row.supplier_quote_3).toBeNull();
    expect(row.appraised_price).toBe(145000000);
    expect(row.currency).toBeNull();
    expect(row.validation_status).toBe("warning");
    expect(row.review_status).toBe("raw");
    expect(row.row_version).toBe(7);

    const displayedKeys = Object.keys(row);
    expect(displayedKeys).not.toContain("version_token");
  });

  it("handles null appraised_unit_price correctly", () => {
    const items: ProjectAssetLineResponse[] = [{
      id: "id-2",
      project_id: "p",
      asset_name: "Item",
      description: null,
      quantity: 1,
      unit_id: null,
      raw_price: null,
      raw_price_currency_id: null,
      appraised_unit_price: null,
      appraised_currency_id: null,
      review_status: "raw",
      validation_status: "valid",
      brand_id: null,
      manufacturer_id: null,
      version_token: "1"
    }];

    const rows = mapAssetLinesToGridRows(items);
    expect(rows[0].appraised_price).toBeNull();
    expect(rows[0].row_version).toBe(1);
  });

  it("handles invalid version_token safely", () => {
    const items: ProjectAssetLineResponse[] = [{
      id: "id-3", project_id: "p", asset_name: "X",
      description: null, quantity: 1, unit_id: null, raw_price: null,
      raw_price_currency_id: null, appraised_unit_price: null, appraised_currency_id: null,
      review_status: "raw", validation_status: "valid",
      brand_id: null, manufacturer_id: null,
      version_token: "invalid"
    }];

    const rows = mapAssetLinesToGridRows(items);
    expect(rows[0].row_version).toBeNull();
  });

  it("handles empty items list", () => {
    const gridRows = mapAssetLinesToGridRows([]);
    expect(gridRows).toHaveLength(0);
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
      project_id: "uuid-123",
      items: [],
      total: 120,
      limit: 50,
      offset: 0
    });

    const setRows = vi.fn();
    mockStateSetters = [setRows, vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn()];

    useProjectAssetLines("uuid-123");

    await new Promise(resolve => setTimeout(resolve, 10));

    expect(fetchSpy).toHaveBeenCalledWith("uuid-123", { limit: 50, offset: 0 });
  });

  it("exposes totalCount and hasMore from paginated response", async () => {
    vi.spyOn(api, "fetchProjectAssetLines").mockResolvedValue({
      project_id: "uuid-456",
      items: [],
      total: 75,
      limit: 50,
      offset: 0
    });

    const setTotalCount = vi.fn();
    const setHasMore = vi.fn();
    mockStateSetters = [vi.fn(), vi.fn(), vi.fn(), vi.fn(), vi.fn(), setTotalCount, setHasMore];

    useProjectAssetLines("uuid-456");

    await new Promise(resolve => setTimeout(resolve, 10));

    expect(setTotalCount).toHaveBeenCalledWith(75);
    expect(setHasMore).toHaveBeenCalledWith(true);
  });

  it("does not fetch when projectId is empty", () => {
    const fetchSpy = vi.spyOn(api, "fetchProjectAssetLines");
    useProjectAssetLines("");
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
