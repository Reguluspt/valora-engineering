import { act, create } from "react-test-renderer";
import { describe, expect, it, vi } from "vitest";
import { AssetGrid } from "../AssetGrid";
import type { AssetLineGridRow } from "../AssetGridTypes";

function row(line: number): AssetLineGridRow {
  return {
    project_asset_line_id: `line-${line}`,
    line_no: line,
    raw_name: `Tài sản ${line}`,
    normalized_name: null,
    canonical_asset: null,
    asset_variant: null,
    taxonomy_node: null,
    quantity: 31 - line,
    unit: null,
    quote_batch_status: null,
    supplier_quote_1: null,
    supplier_quote_2: null,
    supplier_quote_3: null,
    appraised_price: line * 1000,
    currency: null,
    validation_status: "valid",
    review_status: "raw",
    row_version: 1,
  };
}

const visibleRows = (root: ReturnType<typeof create>) => root.root.findAllByType("tr")
  .filter((item) => item.props.className?.includes("grid-row"));

describe("AssetGrid interaction and virtualization lock", () => {
  it("keeps sorting, filtering, selection and active asset separate", () => {
    const onActiveRowChange = vi.fn();
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<AssetGrid rows={Array.from({ length: 30 }, (_, index) => row(index + 1))} onActiveRowChange={onActiveRowChange} />);
    });

    expect(visibleRows(root!).length).toBe(10);
    expect(visibleRows(root!)[0].props["data-row-version"]).toBe(1);
    expect(visibleRows(root!)[0].props["aria-label"]).toContain("Tài sản 1");

    const quantitySort = root!.root.findAllByType("button").find((item) =>
      item.props.className?.includes("asset-grid-sort--numeric") && JSON.stringify(item.props.children).includes("SL"));
    act(() => quantitySort!.props.onClick());
    expect(visibleRows(root!)[0].props["aria-label"]).toContain("Tài sản 30");

    const firstCheckbox = visibleRows(root!)[0].findByType("input");
    act(() => firstCheckbox.props.onClick({ stopPropagation: vi.fn() }));
    expect(onActiveRowChange).not.toHaveBeenCalled();
    expect(visibleRows(root!)[0].props["aria-selected"]).toBe(true);
    const selectionStatus = root!.root.findByProps({ role: "status" });
    expect(selectionStatus.props.children.join("")).toBe("Đã chọn 1 dòng");

    act(() => visibleRows(root!)[0].props.onClick());
    expect(onActiveRowChange).toHaveBeenCalledWith("line-30");
    expect(JSON.stringify(root!.toJSON())).toContain("Đang xem");

    const search = root!.root.findByProps({ "aria-label": "Tìm theo tên tài sản" });
    act(() => search.props.onChange({ target: { value: "Tài sản 12" } }));
    expect(visibleRows(root!)).toHaveLength(1);
    expect(visibleRows(root!)[0].props["aria-label"]).toContain("Tài sản 12");
  });

  it("retains the 400px window and 60px row virtualization boundary", () => {
    let root: ReturnType<typeof create>;
    act(() => { root = create(<AssetGrid rows={Array.from({ length: 30 }, (_, index) => row(index + 1))} />); });
    const viewport = root!.root.findByProps({ className: "grid-scroll-viewport valora-table-shell" });
    expect(viewport.props.style.height).toBe("400px");
    act(() => viewport.props.onScroll({ currentTarget: { scrollTop: 600 } }));
    expect(visibleRows(root!)[0].props["aria-label"]).toContain("Tài sản 9");
    expect(visibleRows(root!).some((item) => item.props["aria-label"] === "Tài sản dòng 1: Tài sản 1")).toBe(false);
  });
});
