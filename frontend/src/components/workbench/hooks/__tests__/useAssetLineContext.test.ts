import { describe, it, expect, vi, beforeEach } from "vitest";
import { useAssetLineContext } from "../useAssetLineContext";
import { AssetLineGridRow } from "../../AssetGridTypes";

// Mock React useState and useEffect
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
    normalized_name: "Cáp điện Cadivi 2x1.5mm2",
    canonical_asset: {
      id: "can-cadivi",
      standard_name: "Cáp điện Cadivi tiêu chuẩn"
    },
    asset_variant: {
      id: "var-cadivi",
      display_name: "Cadivi Việt Nam"
    },
    taxonomy_node: {
      id: "tax-cable",
      path: "Vật tư điện > Dây cáp điện"
    },
    quantity: 100,
    unit: {
      id: "u-meter",
      code: "m",
      name_vi: "mét"
    },
    quote_batch_status: "active",
    supplier_quote_1: 15000,
    supplier_quote_2: 0,
    supplier_quote_3: 0,
    appraised_price: 14500,
    currency: {
      id: "cur-vnd",
      code: "VND"
    },
    validation_status: "valid",
    review_status: "raw",
    row_version: 3
  };

  it("returns undefined contextData if no row is selected", () => {
    const setContextData = vi.fn();
    const setLoading = vi.fn();
    const setErrorMsg = vi.fn();

    mockStateSetters = [setContextData, setLoading, setErrorMsg];

    const { contextData } = useAssetLineContext("hd-98-gia-lai", null);

    expect(contextData).toBeUndefined();
    expect(setContextData).toHaveBeenCalledWith(undefined);
  });

  it("correctly constructs context panel structures from selected row details", () => {
    const setContextData = vi.fn();
    const setLoading = vi.fn();
    const setErrorMsg = vi.fn();

    mockStateSetters = [setContextData, setLoading, setErrorMsg];

    // Mock initial hook trigger by assigning state values
    mockStateValues[0] = undefined; 

    const { contextData } = useAssetLineContext("hd-98-gia-lai", mockGridRow);

    // Verify loading indicator is triggered
    expect(setLoading).toHaveBeenCalledWith(true);

    // Verify contextData setter was called with the mapped structure
    expect(setContextData).toHaveBeenCalled();
    const resolvedData = setContextData.mock.calls[0][0];

    expect(resolvedData.project_asset_line_id).toBe("row-123");
    
    // Knowledge specifications
    expect(resolvedData.knowledge_panel.current_spec.attribute_values["Tên chuẩn hóa"]).toBe("Cáp điện Cadivi 2x1.5mm2");
    expect(resolvedData.knowledge_panel.current_spec.attribute_values["Hãng sản xuất/Model"]).toBe("Cadivi Việt Nam");
    
    // Quote lines pricing details
    expect(resolvedData.price_evidence_panel.quote_lines[0].quoted_unit_price).toBe(15000);
    expect(resolvedData.price_evidence_panel.quote_lines[0].currency_code).toBe("VND");
    expect(resolvedData.price_evidence_panel.appraised_price_decision.selected_unit_price).toBe(14500);

    // Guardrail check: row_version / version_token must not be exposed to user display keys in the drawer
    const allText = JSON.stringify(resolvedData);
    expect(allText).not.toContain("row_version");
    expect(allText).not.toContain("version_token");
  });
});
