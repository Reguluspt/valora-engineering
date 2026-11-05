import React from "react";
import { act, create } from "react-test-renderer";
import { describe, expect, it, vi } from "vitest";

import type { ProjectAssetImportStagingRowResponse } from "../../../api/assetImports";
import type { PreliminaryAnalysisReadResponse } from "../../../api/preliminaryAnalysis";
import { draftFromStaging, type AnalysisDraft } from "../analysisReviewModel";
import { PreliminaryAnalysisWorkspace } from "../PreliminaryAnalysisWorkspace";

const sourceRows: ProjectAssetImportStagingRowResponse[] = [
  { id: "row-a", import_batch_id: "batch-1", source_row_number: 17, proposed_asset_name: "Máy cắt",
    proposed_description: "Thiết bị cắt công nghiệp với mô tả dài từ tệp nguồn hiện hành", proposed_unit: "Máy",
    proposed_raw_price: "1.200.000", proposed_currency: "VND", proposed_quantity: "2",
    validation_status: "pending", validation_errors: [], validation_warnings: [] },
  { id: "row-b", import_batch_id: "batch-1", source_row_number: 42, proposed_asset_name: "Máy bơm",
    proposed_description: "Bơm cho hệ thống nước", proposed_unit: "Bộ", proposed_quantity: "3",
    validation_status: "pending", validation_errors: [], validation_warnings: [] },
  { id: "row-c", import_batch_id: "batch-1", source_row_number: 92, proposed_asset_name: "Máy ép",
    proposed_quantity: "1", validation_status: "pending", validation_errors: [], validation_warnings: [] },
];
const drafts = () => sourceRows.map(draftFromStaging);

function mount(options: { lines?: AnalysisDraft[]; disabled?: boolean; snapshot?: PreliminaryAnalysisReadResponse } = {}) {
  const onUpdateDraft = vi.fn();
  let renderer: ReturnType<typeof create>;
  act(() => {
    renderer = create(<PreliminaryAnalysisWorkspace drafts={options.lines ?? drafts()} sourceRows={sourceRows}
      disabled={options.disabled ?? false} snapshot={options.snapshot} onUpdateDraft={onUpdateDraft} />);
  });
  return { renderer: renderer!, onUpdateDraft };
}

function input(renderer: ReturnType<typeof create>, name: string) {
  return renderer.root.findAllByType("input").find((node) => node.props.name === name)!;
}
function selectRow(renderer: ReturnType<typeof create>, rowNumber: number) {
  act(() => renderer.root.findAllByType("button").find((node) =>
    node.props["aria-label"]?.startsWith(`Xem chi tiết dòng ${rowNumber}:`))!.props.onClick());
}
function search(renderer: ReturnType<typeof create>, value: string) {
  act(() => renderer.root.findAllByType("input").find((node) => node.props.type === "search")!.props.onChange({ target: { value } }));
}

describe("PreliminaryAnalysisWorkspace presentation", () => {
  it("shows available source fields and edits the original draft after search and selection", () => {
    const { renderer, onUpdateDraft } = mount();
    expect(JSON.stringify(renderer.toJSON())).toContain(sourceRows[0].proposed_description);
    expect(JSON.stringify(renderer.toJSON())).toContain("1.200.000");
    expect(JSON.stringify(renderer.toJSON())).toContain("VND");
    search(renderer, "hệ thống nước");
    expect(renderer.root.findAllByProps({ "data-row-source": 17 })).toHaveLength(0);
    expect(renderer.root.findAllByProps({ "data-row-source": 42 })).toHaveLength(1);
    selectRow(renderer, 42);
    expect(renderer.root.findByType("h2").children).toEqual(["Máy bơm"]);
    act(() => input(renderer, "proposed_unit_price").props.onChange({ target: { value: "1250000" } }));
    expect(onUpdateDraft).toHaveBeenCalledExactlyOnceWith(1, { proposed_unit_price: "1250000" });
  });

  it("binds all four inline editors to the original filtered row without opening the separate detail panel", () => {
    const { renderer, onUpdateDraft } = mount();
    search(renderer, "hệ thống nước");
    for (const [name, value] of Object.entries({
      accepted_price_basis: "Cơ sở giá đã đối chiếu",
      confirmed_reference_price: "1000000",
      transport_percentage: "5",
      proposed_unit_price: "1080000",
    })) {
      const tag = name === "accepted_price_basis" ? "textarea" : "input";
      const editor = renderer.root.findAllByType(tag).find((node) => node.props.name === `${name}_row_42`)!;
      act(() => editor.props.onChange({ target: { value } }));
      expect(onUpdateDraft).toHaveBeenLastCalledWith(1, { [name]: value });
    }
    expect(onUpdateDraft).toHaveBeenCalledTimes(4);
    expect(renderer.root.findByType("h2").children).toEqual(["Máy bơm"]);
    expect(renderer.root.findAllByType("div").some((node) => node.props.className === "precase-analysis-workspace is-detail-open")).toBe(false);
    expect(renderer.root.findAllByType("input").some((node) => node.props.name?.startsWith("quantity"))).toBe(false);
    expect(renderer.root.findAllByType("textarea")[0].props.maxLength).toBe(64);
  });

  it("keeps stable identity through status filters, including sparse source row numbers", () => {
    const lines = drafts();
    lines[0].human_line_confirmed = true;
    lines[2].has_unresolved_blocking_line = true;
    const { renderer, onUpdateDraft } = mount({ lines });
    act(() => renderer.root.findByType("select").props.onChange({ target: { value: "blocked" } }));
    expect(renderer.root.findAllByProps({ "data-row-source": 42 })).toHaveLength(0);
    selectRow(renderer, 92);
    expect(input(renderer, "human_line_confirmed").props.disabled).toBe(true);
    act(() => input(renderer, "has_unresolved_blocking_line").props.onChange({ currentTarget: { checked: false } }));
    expect(onUpdateDraft).toHaveBeenCalledExactlyOnceWith(2, { has_unresolved_blocking_line: false });
  });

  it("returns from the separate detail panel without resetting selection or edited values", () => {
    const lines = drafts();
    lines[1].proposed_unit_price = "1700000";
    const { renderer, onUpdateDraft } = mount({ lines });
    selectRow(renderer, 42);
    expect(renderer.root.findAllByType("div").some((node) => node.props.className === "precase-analysis-workspace is-detail-open")).toBe(true);
    act(() => renderer.root.findAllByType("button").find((node) => node.children.includes("← Về bảng danh mục"))!.props.onClick());
    expect(renderer.root.findAllByType("div").some((node) => node.props.className === "precase-analysis-workspace")).toBe(true);
    expect(input(renderer, "proposed_unit_price").props.value).toBe("1700000");
    expect(renderer.root.findByProps({ "data-row-source": 42 }).props["data-selected"]).toBe("true");
    expect(onUpdateDraft).not.toHaveBeenCalled();
  });

  it("disables editing and ignores stale edit callbacks while the owning screen is locked", () => {
    const { renderer, onUpdateDraft } = mount({ disabled: true });
    for (const node of renderer.root.findAllByType("input").filter((node) => node.props.name)) expect(node.props.disabled).toBe(true);
    for (const node of renderer.root.findAllByType("textarea")) expect(node.props.disabled).toBe(true);
    act(() => input(renderer, "proposed_unit_price_row_42").props.onChange({ target: { value: "999" } }));
    act(() => renderer.root.findAllByType("textarea").find((node) => node.props.name === "accepted_price_basis_row_42")!.props.onChange({ target: { value: "Không được ghi" } }));
    act(() => input(renderer, "proposed_unit_price").props.onChange({ target: { value: "999" } }));
    act(() => input(renderer, "human_line_confirmed").props.onChange({ currentTarget: { checked: true } }));
    expect(onUpdateDraft).not.toHaveBeenCalled();
  });

  it("renders a committed snapshot read-only without substituting mutable staging source fields", () => {
    const snapshot: PreliminaryAnalysisReadResponse = {
      id: "snapshot-1", project_id: "project-1", version: 1, import_batch_id: "batch-1", source_artifact_id: "source-1",
      structure_snapshot_id: "structure-1", mapping_decision_id: "decision-1", mapping_profile_usage_id: "usage-1",
      mapping_decision_digest_sha256: "a".repeat(64), profile_usage_mapping_digest_sha256: "a".repeat(64),
      line_manifest_digest_sha256: "b".repeat(64), finalized_by_user_id: "reviewer-1", finalized_at: "2026-11-05T09:00:00Z",
      line_manifest: [{ source_row_number: 17, identity: "Máy cắt đã xác nhận", quantity: 2, accepted_price_basis: "Báo giá đã kiểm tra",
        confirmed_reference_price: 100, transport_percentage: 5, proposed_unit_price: 108, human_line_confirmed: true, has_unresolved_blocking_line: false }],
    };
    const { renderer, onUpdateDraft } = mount({ snapshot });
    expect(renderer.root.findAllByType("input").filter((node) => node.props.name)).toHaveLength(0);
    expect(renderer.root.findAllByType("textarea")).toHaveLength(0);
    expect(JSON.stringify(renderer.toJSON())).toContain("Bản phân tích đã chốt chỉ cho phép xem");
    expect(JSON.stringify(renderer.toJSON())).not.toContain(sourceRows[0].proposed_description);
    expect(JSON.stringify(renderer.toJSON())).not.toContain("1.200.000");
    expect(onUpdateDraft).not.toHaveBeenCalled();
  });
});
