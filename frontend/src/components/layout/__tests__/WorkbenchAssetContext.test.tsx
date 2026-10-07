import { act, create } from "react-test-renderer";
import { describe, expect, it, vi } from "vitest";
import { WorkbenchRightPanelShell } from "../WorkbenchRightPanelShell";
import type { AssetLineGridRow } from "../../workbench/AssetGridTypes";
import type { AssetLineContext } from "../../workbench/panels/ContextPanelTypes";
import { TabList } from "@fluentui/react-components";

vi.mock("@fluentui/react-components", async importOriginal => {
  const original = await importOriginal<typeof import("@fluentui/react-components")>();
  return { ...original, TabList: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    Tab: ({ children, ...props }: any) => <button role="tab" {...props}>{children}</button> };
});

const asset: AssetLineGridRow = {
  project_asset_line_id: "line-1",
  line_no: 1,
  raw_name: "Máy cắt kim loại",
  normalized_name: "Máy cắt kim loại",
  canonical_asset: null,
  asset_variant: null,
  taxonomy_node: null,
  quantity: 2,
  unit: { id: "unit-1", code: "cai", name_vi: "cái" },
  quote_batch_status: null,
  supplier_quote_1: null,
  supplier_quote_2: null,
  supplier_quote_3: null,
  appraised_price: 100000,
  currency: null,
  validation_status: "valid",
  review_status: "raw",
  row_version: 3,
};

const context: AssetLineContext = {
  project_asset_line_id: "line-1",
  knowledge_panel: null,
  price_evidence_panel: null,
  lineage: null,
  validation_issues: null,
};

describe("contextual asset drawer", () => {
  it("labels the current asset, switches read sections and closes without a business callback", () => {
    const onClose = vi.fn();
    let root: ReturnType<typeof create>;
    act(() => { root = create(<WorkbenchRightPanelShell asset={asset} contextData={context} onClose={onClose} />); });

    const initial = JSON.stringify(root!.toJSON());
    expect(initial).toContain("Máy cắt kim loại");
    expect(initial).toContain("Tổng quan");
    expect(initial).not.toContain("Review Queue");
    expect(initial).not.toContain("phê duyệt");

    const tabs = root!.root.findByType(TabList);
    expect(root!.root.findAllByProps({ role: "tab" }).map(t => t.props.children)).toEqual(["Tổng quan", "Thông số kỹ thuật", "Nguồn giá & Chứng cứ", "Lịch sử"]);
    act(() => tabs.props.onTabSelect({}, { value: "price" }));
    expect(tabs.props.selectedValue).toBe("price");
    expect(JSON.stringify(root!.toJSON())).toContain("Nguồn chứng cứ hiện chưa khả dụng");
    expect(JSON.stringify(root!.toJSON())).not.toContain("Giá thẩm định");
    expect(onClose).not.toHaveBeenCalled();

    const close = root!.root.findByProps({ "aria-label": "Đóng ngữ cảnh tài sản" });
    act(() => close.props.onClick());
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(asset.project_asset_line_id).toBe("line-1");
    expect(context.project_asset_line_id).toBe("line-1");
  });

  it("does not display the previous asset's context while the next one loads", () => {
    let root: ReturnType<typeof create>;
    act(() => { root = create(<WorkbenchRightPanelShell asset={asset} contextData={context} onClose={vi.fn()} />); });
    act(() => root!.update(<WorkbenchRightPanelShell asset={{ ...asset, project_asset_line_id: "line-2", raw_name: "Máy tiện" }} contextData={context} onClose={vi.fn()} />));
    const output = JSON.stringify(root!.toJSON());
    expect(output).toContain("Máy tiện");
    expect(output).toContain("Đang tải ngữ cảnh tài sản");
    expect(output).not.toContain("Máy cắt kim loại");
  });
});
