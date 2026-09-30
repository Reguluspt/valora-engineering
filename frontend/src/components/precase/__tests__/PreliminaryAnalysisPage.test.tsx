import React from "react";
import { act, create } from "react-test-renderer";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  fetchCaseState: vi.fn(), getMappingRecovery: vi.fn(), getSourceArtifact: vi.fn(),
  fetchAssetImportRows: vi.fn(), finalizePreliminaryAnalysis: vi.fn(), getPreliminaryAnalysis: vi.fn(),
}));
vi.mock("../../../api/caseState", () => ({ fetchCaseState: api.fetchCaseState }));
vi.mock("../../../api/preliminaryIntake", () => ({
  getMappingRecovery: api.getMappingRecovery, getSourceArtifact: api.getSourceArtifact,
}));
vi.mock("../../../api/assetImports", () => ({ fetchAssetImportRows: api.fetchAssetImportRows }));
vi.mock("../../../api/preliminaryAnalysis", () => ({
  finalizePreliminaryAnalysis: api.finalizePreliminaryAnalysis,
  getPreliminaryAnalysis: api.getPreliminaryAnalysis,
}));
vi.mock("../../workbench/project-context", () => ({
  useResolvedProject: () => ({ state: "ready", projectId: "project-1" }),
}));

import { ApiError } from "../../../api/client";
import { PreliminaryAnalysisPage } from "../PreliminaryAnalysisPage";

const row = {
  id: "row-1", import_batch_id: "batch-1", source_row_number: 17,
  proposed_asset_name: "Máy cắt", proposed_quantity: "2",
  validation_status: "pending", validation_errors: [], validation_warnings: [],
};
const recovery = {
  project_id: "project-1", batch_id: "batch-1", current_batch_id: "batch-1",
  current_source_artifact_id: "source-1", selection_revision: 4, status: "materialized",
  official_intake_closed: false, selected_confirmation_decision_id: "decision-1",
  selected_structure_snapshot_id: "structure-1", selected_source_artifact_id: "source-1",
  selected_usage_id: "usage-1", current_staging_usage_id: "usage-1",
  mapping_digest_sha256: "a".repeat(64), materialized_mapping_digest_sha256: "a".repeat(64),
  materialized_asset_row_count: 1,
};
const state = () => ({
  case_version: "a".repeat(64), current_stage: "PRELIMINARY_ANALYSIS",
  stages: [
    { stage: "PRELIMINARY_REQUEST", result: "COMPLETE" },
    { stage: "PRELIMINARY_ANALYSIS", result: "INCOMPLETE" },
  ],
  preliminary: {
    project_id: "project-1", project_row_version: 6, customer_id: null,
    current_preliminary_import_batch_id: "batch-1", current_source_artifact_id: "source-1",
    current_preliminary_analysis_snapshot_id: null, current_preliminary_analysis_version: null,
    current_preliminary_result_artifact_id: null, current_preliminary_result_version: null,
    official_intake_commit_id: null,
  },
});

describe("PreliminaryAnalysisPage", () => {
  let serverState: ReturnType<typeof state>;
  let stored: Map<string, string>;
  beforeEach(() => {
    vi.resetAllMocks();
    serverState = state();
    stored = new Map();
    vi.stubGlobal("sessionStorage", {
      getItem: (key: string) => stored.get(key) || null,
      setItem: (key: string, value: string) => stored.set(key, value),
      removeItem: (key: string) => stored.delete(key),
    });
    api.fetchCaseState.mockImplementation(async () => serverState);
    api.getMappingRecovery.mockResolvedValue(recovery);
    api.getSourceArtifact.mockResolvedValue({ id: "source-1", import_batch_id: "batch-1", state: "available" });
    api.fetchAssetImportRows.mockResolvedValue({
      project_id: "project-1", import_batch_id: "batch-1", total: 1, limit: 100, offset: 0, items: [row],
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  async function mount() {
    let root: ReturnType<typeof create>;
    await act(async () => {
      root = create(<PreliminaryAnalysisPage projectRef="project-1" onNavigate={vi.fn()} onSessionExpired={vi.fn()} />);
    });
    return root!;
  }

  function button(root: ReturnType<typeof create>, label: string) {
    return root.root.findAllByType("button").find((node) => node.children.includes(label));
  }

  async function reviewLine(root: ReturnType<typeof create>) {
    for (const [name, value] of Object.entries({
      accepted_price_basis: "Giá tham chiếu đã kiểm tra",
      confirmed_reference_price: "100",
      transport_percentage: "0",
      proposed_unit_price: "110",
    })) {
      act(() => root.root.findByProps({ name }).props.onChange({ target: { value } }));
    }
    act(() => root.root.findByProps({ name: "human_line_confirmed" }).props.onChange({ target: { checked: true } }));
  }

  it("loads current materialized staging provenance and requires line review", async () => {
    const root = await mount();
    expect(api.getMappingRecovery).toHaveBeenCalledWith("project-1", "batch-1");
    expect(api.fetchAssetImportRows).toHaveBeenCalledWith("project-1", "batch-1", { limit: 100, offset: 0 });
    expect(JSON.stringify(root.toJSON())).toContain("Máy cắt");
    expect(JSON.stringify(root.toJSON())).toContain("17");
    expect(button(root, "Chốt phân tích sơ bộ")?.props.disabled).toBe(true);
    expect(api.finalizePreliminaryAnalysis).not.toHaveBeenCalled();
  });

  it("loads every ordered staging page and keeps the review table bounded", async () => {
    api.getMappingRecovery.mockResolvedValue({ ...recovery, materialized_asset_row_count: 101 });
    const rows = Array.from({ length: 101 }, (_, index) => ({
      ...row, id: `row-${index + 3}`, source_row_number: index + 3,
    }));
    api.fetchAssetImportRows.mockImplementation(async (_project, _batch, params) => ({
      project_id: "project-1", import_batch_id: "batch-1", total: 101,
      limit: 100, offset: params.offset,
      items: rows.slice(params.offset, params.offset + 100),
    }));
    const root = await mount();
    expect(api.fetchAssetImportRows).toHaveBeenCalledTimes(2);
    expect(root.root.findAllByProps({ "data-row-source": 3 })).toHaveLength(1);
    expect(root.root.findAllByProps({ "data-row-source": 53 })).toHaveLength(0);
    act(() => button(root, "Trang sau")?.props.onClick());
    expect(root.root.findAllByProps({ "data-row-source": 53 })).toHaveLength(1);
    expect(root.root.findAllByProps({ "data-row-source": 103 })).toHaveLength(0);
  });

  it("finalizes exact current lineage only after explicit confirmation and reads selected fact", async () => {
    const root = await mount();
    await reviewLine(root);
    expect(button(root, "Chốt phân tích sơ bộ")?.props.disabled).toBe(false);
    act(() => button(root, "Chốt phân tích sơ bộ")?.props.onClick());
    expect(JSON.stringify(root.toJSON())).toContain("bất biến");
    api.finalizePreliminaryAnalysis.mockImplementation(async () => {
      serverState.preliminary.current_preliminary_analysis_snapshot_id = "analysis-1";
      serverState.preliminary.current_preliminary_analysis_version = 1;
      serverState.stages[1].result = "COMPLETE";
      return { id: "analysis-1", version: 1 };
    });
    api.getPreliminaryAnalysis.mockImplementation(async () => ({
      id: "analysis-1", project_id: "project-1", version: 1,
      import_batch_id: "batch-1", source_artifact_id: "source-1",
      structure_snapshot_id: "structure-1", mapping_decision_id: "decision-1",
      mapping_profile_usage_id: "usage-1", line_manifest: [{
        identity: "Máy cắt", accepted_price_basis: "Giá tham chiếu đã kiểm tra",
        confirmed_reference_price: 100, transport_percentage: 0, proposed_unit_price: 110,
        human_line_confirmed: true, has_unresolved_blocking_line: false,
        source_row_number: 17, quantity: 2,
      }],
    }));
    await act(async () => button(root, "Xác nhận chốt")?.props.onClick());
    expect(api.finalizePreliminaryAnalysis).toHaveBeenCalledWith("project-1", expect.objectContaining({
      expected_project_version: 6, import_batch_id: "batch-1", source_artifact_id: "source-1",
      structure_snapshot_id: "structure-1", mapping_decision_id: "decision-1",
      mapping_profile_usage_id: "usage-1", mapping_decision_digest_sha256: "a".repeat(64),
      profile_usage_mapping_digest_sha256: "a".repeat(64), confirmed: true,
      line_manifest: [expect.objectContaining({ source_row_number: 17, quantity: 2, human_line_confirmed: true })],
    }));
    expect(api.getPreliminaryAnalysis).toHaveBeenCalledWith("project-1", "analysis-1");
    expect(JSON.stringify(root.toJSON())).toContain("Đã chốt phân tích sơ bộ");
    expect(api.finalizePreliminaryAnalysis).toHaveBeenCalledTimes(1);
  });

  it("keeps the same command key after an unknown uncommitted result", async () => {
    const root = await mount();
    await reviewLine(root);
    act(() => button(root, "Chốt phân tích sơ bộ")?.props.onClick());
    api.finalizePreliminaryAnalysis.mockRejectedValueOnce(new ApiError("offline", 0));
    await act(async () => button(root, "Xác nhận chốt")?.props.onClick());
    const firstKey = api.finalizePreliminaryAnalysis.mock.calls[0][1].idempotency_key;
    expect(button(root, "Thử lại cùng mã lệnh")).toBeDefined();
    expect(button(root, "Chốt phân tích sơ bộ")?.props.disabled).toBe(true);
    api.finalizePreliminaryAnalysis.mockResolvedValueOnce({ id: "analysis-1", version: 1 });
    await act(async () => button(root, "Thử lại cùng mã lệnh")?.props.onClick());
    expect(api.finalizePreliminaryAnalysis.mock.calls[1][1].idempotency_key).toBe(firstKey);
  });

  it("restores an uncertain command after navigation and retries its original payload", async () => {
    const first = await mount();
    await reviewLine(first);
    act(() => button(first, "Chốt phân tích sơ bộ")?.props.onClick());
    api.finalizePreliminaryAnalysis.mockRejectedValueOnce(new ApiError("offline", 0));
    await act(async () => button(first, "Xác nhận chốt")?.props.onClick());
    const original = api.finalizePreliminaryAnalysis.mock.calls[0][1];
    act(() => first.unmount());
    const returned = await mount();
    expect(button(returned, "Chốt phân tích sơ bộ")?.props.disabled).toBe(true);
    expect(button(returned, "Thử lại cùng mã lệnh")).toBeDefined();
    api.finalizePreliminaryAnalysis.mockResolvedValueOnce({ id: "analysis-1", version: 1 });
    await act(async () => button(returned, "Thử lại cùng mã lệnh")?.props.onClick());
    expect(api.finalizePreliminaryAnalysis.mock.calls[1][1]).toEqual(original);
  });

  it("treats a stale 409 as a review reset without reusing the command", async () => {
    const root = await mount();
    await reviewLine(root);
    act(() => button(root, "Chốt phân tích sơ bộ")?.props.onClick());
    api.finalizePreliminaryAnalysis.mockRejectedValueOnce(new ApiError("stale", 409));
    await act(async () => button(root, "Xác nhận chốt")?.props.onClick());
    expect(JSON.stringify(root.toJSON())).toContain("Dữ liệu đã thay đổi");
    expect(button(root, "Thử lại cùng mã lệnh")).toBeUndefined();
    expect(button(root, "Chốt phân tích sơ bộ")?.props.disabled).toBe(true);
    expect(api.finalizePreliminaryAnalysis).toHaveBeenCalledTimes(1);
  });

  it("recovers a committed analysis from Case State when session storage is unavailable", async () => {
    vi.stubGlobal("sessionStorage", {
      getItem: () => { throw new Error("blocked"); },
      setItem: () => { throw new Error("blocked"); },
      removeItem: () => { throw new Error("blocked"); },
    });
    serverState.preliminary.current_preliminary_analysis_snapshot_id = "analysis-1";
    serverState.preliminary.current_preliminary_analysis_version = 1;
    serverState.stages[1].result = "COMPLETE";
    api.getPreliminaryAnalysis.mockResolvedValue({
      id: "analysis-1", project_id: "project-1", version: 1, line_manifest: [{ ...row }],
    });
    const root = await mount();
    expect(api.getPreliminaryAnalysis).toHaveBeenCalledWith("project-1", "analysis-1");
    expect(JSON.stringify(root.toJSON())).toContain("Đã chốt phân tích sơ bộ");
    expect(api.fetchAssetImportRows).not.toHaveBeenCalled();
    expect(api.finalizePreliminaryAnalysis).not.toHaveBeenCalled();
  });

  it("blocks creation when the selected mapping is not materialized", async () => {
    api.getMappingRecovery.mockResolvedValue({ ...recovery, status: "selected_unmaterialized", selected_usage_id: null });
    const root = await mount();
    expect(JSON.stringify(root.toJSON())).toContain("Ánh xạ chưa tạo dữ liệu tạm hiện hành");
    expect(api.fetchAssetImportRows).not.toHaveBeenCalled();
    expect(button(root, "Chốt phân tích sơ bộ")).toBeUndefined();
  });
});
