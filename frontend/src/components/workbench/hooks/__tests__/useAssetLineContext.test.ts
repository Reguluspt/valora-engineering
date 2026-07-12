import { describe, it, expect, vi, beforeEach } from "vitest";
import { useAssetLineContext } from "../useAssetLineContext";
import { AssetLineGridRow } from "../../AssetGridTypes";

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
  };
});

describe("useAssetLineContext hook tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStateValues = [];
    mockStateSetters = [];
    mockStateIndex = 0;
  });

  const mockGridRow: AssetLineGridRow = {
    project_asset_line_id: "row-123",
    line_no: 1,
    raw_name: "Cáp điện Cadivi 2x1.5",
    normalized_name: null,
    canonical_asset: null,
    asset_variant: null,
    taxonomy_node: null,
    quantity: 100,
    unit: null,
    quote_batch_status: null,
    supplier_quote_1: null,
    supplier_quote_2: null,
    supplier_quote_3: null,
    appraised_price: 14500,
    currency: null,
    validation_status: "valid",
    review_status: "raw",
    row_version: 3
  };

  it("returns undefined contextData if no row is selected", () => {
    const setContextData = vi.fn();
    const setLoading = vi.fn();
    const setErrorMsg = vi.fn();

    mockStateSetters = [setContextData, setLoading, setErrorMsg];

    const { contextData } = useAssetLineContext("proj-uuid", null);

    expect(contextData).toBeUndefined();
    expect(setContextData).toHaveBeenCalledWith(undefined);
  });

  it("returns null panels for unavailable data — no fabricated entities", () => {
    const setContextData = vi.fn();
    const setLoading = vi.fn();
    const setErrorMsg = vi.fn();

    mockStateSetters = [setContextData, setLoading, setErrorMsg];

    mockStateValues[0] = undefined;

    const { contextData } = useAssetLineContext("proj-uuid", mockGridRow);

    expect(setLoading).toHaveBeenCalledWith(true);

    expect(setContextData).toHaveBeenCalled();
    const resolvedData = setContextData.mock.calls[0][0];

    expect(resolvedData.project_asset_line_id).toBe("row-123");

    // All panels are null — no fabricated technical specs, decisions, or IDs
    expect(resolvedData.knowledge_panel).toBeNull();
    expect(resolvedData.price_evidence_panel).toBeNull();
    expect(resolvedData.lineage).toBeNull();
    expect(resolvedData.validation_issues).toBeNull();

    // Guardrail check: row_version / version_token must not be exposed
    const allText = JSON.stringify(resolvedData);
    expect(allText).not.toContain("row_version");
    expect(allText).not.toContain("version_token");
  });
});
