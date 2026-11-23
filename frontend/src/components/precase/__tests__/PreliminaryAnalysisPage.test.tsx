import React from "react";
import { act, create } from "react-test-renderer";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@fluentui/react-components", async (importOriginal) => {
  const original = await importOriginal<typeof import("@fluentui/react-components")>();
  return { ...original, TabList: ({ children, selectedValue, onTabSelect, ...props }: any) => <div {...props} role="tablist">{React.Children.map(children, child => React.isValidElement(child) ? React.cloneElement(child as React.ReactElement<any>, { selected: child.props.value === selectedValue, onClick: (event: unknown) => onTabSelect(event, { value: child.props.value }) }) : child)}</div>,
    Tab: ({ children, value, selected, onClick, ...props }: any) => <button {...props} role="tab" aria-selected={selected} onClick={onClick}>{children}</button> };
});

const api = vi.hoisted(() => ({
  fetchCaseState: vi.fn(), getMappingRecovery: vi.fn(), getSourceArtifact: vi.fn(),
  fetchAssetImportRows: vi.fn(), finalizePreliminaryAnalysis: vi.fn(), getPreliminaryAnalysis: vi.fn(),
  getCurrentAccount: vi.fn(), getPreliminaryAnalysisAttemptState: vi.fn(), getPreliminaryAnalysisAttempt: vi.fn(),
  claimPreliminaryAnalysisAttempt: vi.fn(), reconcilePreliminaryAnalysisAttempt: vi.fn(),
}));
vi.mock("../../../api/caseState", () => ({ fetchCaseState: api.fetchCaseState }));
vi.mock("../../../api/preliminaryIntake", () => ({
  getMappingRecovery: api.getMappingRecovery, getSourceArtifact: api.getSourceArtifact,
}));
vi.mock("../../../api/assetImports", () => ({ fetchAssetImportRows: api.fetchAssetImportRows }));
vi.mock("../../../api/preliminaryAnalysis", () => ({
  finalizePreliminaryAnalysis: api.finalizePreliminaryAnalysis,
  getPreliminaryAnalysis: api.getPreliminaryAnalysis,
  claimPreliminaryAnalysisAttempt: api.claimPreliminaryAnalysisAttempt,
  getPreliminaryAnalysisAttempt: api.getPreliminaryAnalysisAttempt,
  getPreliminaryAnalysisAttemptState: api.getPreliminaryAnalysisAttemptState,
  reconcilePreliminaryAnalysisAttempt: api.reconcilePreliminaryAnalysisAttempt,
}));
vi.mock("../../../api/auth", () => ({ getCurrentAccount: api.getCurrentAccount }));
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
    api.getCurrentAccount.mockResolvedValue({
      id: "user-1", organization_id: "org-1", session_incarnation: "d".repeat(64), roles: ["appraiser"],
      permissions: ["project:read", "project:preliminary_analysis:finalize"],
    });
    api.getPreliminaryAnalysisAttemptState.mockResolvedValue({ blocked: false, base_analysis_version: 0 });
    api.getPreliminaryAnalysisAttempt.mockResolvedValue({ status: "UNKNOWN" });
    api.claimPreliminaryAnalysisAttempt.mockResolvedValue({ attempt_id: "attempt-1", status: "RECEIVED" });
    api.fetchCaseState.mockImplementation(async () => serverState);
    api.getMappingRecovery.mockResolvedValue(recovery);
    api.getSourceArtifact.mockResolvedValue({ id: "source-1", import_batch_id: "batch-1", state: "available", generation: 1, checksum_sha256: "a".repeat(64) });
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
      act(() => root.root.findAllByType(name === "accepted_price_basis" ? "textarea" : "input").find((node) => node.props.name === name)!.props.onChange({ target: { value } }));
    }
    act(() => root.root.findAllByType("input").find((node) => node.props.name === "human_line_confirmed")!.props.onChange({ currentTarget: { checked: true } }));
  }

  function tableField(root: ReturnType<typeof create>, rowNumber: number, name: string) {
    const tag = name === "accepted_price_basis" ? "textarea" : "input";
    return root.root.findAllByType(tag).find((node) => node.props.name === `${name}_row_${rowNumber}`)!;
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

  it.each([320, 390, 832, 950])("opens with the table on the analysis page at %i CSS px", async (width) => {
    const media = {
      matches: width <= 950,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    const matchMedia = vi.fn(() => media);
    vi.stubGlobal("window", { matchMedia, addEventListener: vi.fn(), removeEventListener: vi.fn() });
    const root = await mount();
    const panel = () => root.root.findByType("aside");
    const scrim = () => root.root.findAllByProps({ className: "analysis-panel-scrim" });

    expect(matchMedia).toHaveBeenCalledWith("(max-width: 950px)");
    expect(root.root.findAllByType("th")).toHaveLength(13);
    expect(panel().props.hidden).toBe(true);
    expect(scrim()).toHaveLength(0);

    const opener = root.root.findAllByType("button").find((node) => node.props["aria-label"]?.startsWith("Xem chi tiết dòng 17:"))!;
    act(() => opener.props.onClick());
    expect(panel().props.hidden).toBe(false);
    expect(panel().props.role).toBe("dialog");
    expect(scrim()).toHaveLength(1);

    act(() => panel().findAllByType("input").find((node) => node.props.name === "confirmed_reference_price")!.props.onChange({ target: { value: "100" } }));
    expect(panel().props.hidden).toBe(false);

    const updateViewport = media.addEventListener.mock.calls[0][1];
    media.matches = false;
    act(() => updateViewport());
    expect(panel().props.hidden).toBe(false);
    expect(panel().props.role).toBeUndefined();

    media.matches = true;
    act(() => updateViewport());
    expect(panel().props.role).toBe("dialog");
    act(() => panel().props.onKeyDown({ key: "Escape", preventDefault: vi.fn() }));
    expect(panel().props.hidden).toBe(true);
    expect(scrim()).toHaveLength(0);
    act(() => root.unmount());
  });

  it("opens the initial detail beside the table above the overlay breakpoint", async () => {
    vi.stubGlobal("window", {
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      matchMedia: () => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }),
    });
    const root = await mount();
    expect(root.root.findByType("aside").props.hidden).toBe(false);
    expect(root.root.findByType("aside").props.role).toBeUndefined();
    act(() => root.unmount());
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
      line_manifest: [expect.objectContaining({ source_row_number: 17, staging_row_id: "row-1", quantity: 2, human_line_confirmed: true })],
    }), "d".repeat(64));
    expect(api.getPreliminaryAnalysis).toHaveBeenCalledWith("project-1", "analysis-1");
    expect(JSON.stringify(root.toJSON())).toContain("Đã chốt phân tích sơ bộ");
    expect(api.finalizePreliminaryAnalysis).toHaveBeenCalledTimes(1);
  });

  it("mirrors inline and detail edits while preserving manual prices and the complete filtered manifest", async () => {
    const second = { ...row, id: "row-2", source_row_number: 42, proposed_asset_name: "Máy nén khí", proposed_quantity: "3" };
    api.getMappingRecovery.mockResolvedValue({ ...recovery, materialized_asset_row_count: 2 });
    api.fetchAssetImportRows.mockResolvedValue({
      project_id: "project-1", import_batch_id: "batch-1", total: 2, limit: 100, offset: 0, items: [row, second],
    });
    const root = await mount();
    await reviewLine(root);
    act(() => root.root.findAllByType("input").find((node) => node.props.type === "search")!.props.onChange({ target: { value: "Máy nén" } }));
    act(() => root.root.findAllByType("button").find(node => node.props["aria-label"] === "Xem nguồn giá dòng 42")!.props.onClick());
    for (const [name, value] of Object.entries({ accepted_price_basis: "Báo giá đã đối chiếu", confirmed_reference_price: "100", transport_percentage: "0", proposed_unit_price: "110" })) {
      act(() => root.root.findAllByType(name === "accepted_price_basis" ? "textarea" : "input").find(node => node.props.name === (name === "proposed_unit_price" ? "proposed_unit_price_row_42" : name))!.props.onChange({ target: { value } }));
      expect(root.root.findAllByType(name === "accepted_price_basis" ? "textarea" : "input").find((node) => node.props.name === name)!.props.value).toBe(value);
    }
    expect(root.root.findByType("aside").findByType("h2").children).toEqual(["Máy nén khí"]);
    act(() => root.root.findAllByType("input").find((node) => node.props.name === "human_line_confirmed")!.props.onChange({ currentTarget: { checked: true } }));
    for (const [name, value] of [["proposed_unit_price", "175"], ["confirmed_reference_price", "200"], ["transport_percentage", "5"]]) {
      act(() => root.root.findAllByType(name === "accepted_price_basis" ? "textarea" : "input").find(node => node.props.name === (name === "proposed_unit_price" ? "proposed_unit_price_row_42" : name))!.props.onChange({ target: { value } }));
    }
    expect(tableField(root, 42, "proposed_unit_price").props.value).toBe("175");
    expect(root.root.findAllByType("input").find((node) => node.props.name === "proposed_unit_price")!.props.value).toBe("175");
    expect(root.root.findAllByType("input").find((node) => node.props.name === "human_line_confirmed")!.props.checked).toBe(false);
    act(() => root.root.findAllByType("textarea").find((node) => node.props.name === "accepted_price_basis")!.props.onChange({ target: { value: "Giá tham chiếu đã kiểm tra" } }));
    expect(root.root.findAllByType("textarea").find(node => node.props.name === "accepted_price_basis")!.props.value).toBe("Giá tham chiếu đã kiểm tra");
    act(() => root.root.findAllByType("input").find((node) => node.props.name === "human_line_confirmed")!.props.onChange({ currentTarget: { checked: true } }));
    expect(root.root.findAllByProps({ "data-row-source": 17 })).toHaveLength(0);
    expect(button(root, "Chốt phân tích sơ bộ")?.props.disabled).toBe(false);
    act(() => button(root, "Chốt phân tích sơ bộ")?.props.onClick());
    api.finalizePreliminaryAnalysis.mockResolvedValueOnce({ id: "analysis-1", version: 1 });
    await act(async () => button(root, "Xác nhận chốt")?.props.onClick());
    const payload = api.finalizePreliminaryAnalysis.mock.calls[0][1];
    expect(payload.expected_project_version).toBe(6);
    expect(payload.mapping_profile_usage_id).toBe("usage-1");
    expect(payload.line_manifest).toEqual([
      expect.objectContaining({ source_row_number: 17, quantity: 2, proposed_unit_price: 110, confirmed_reference_price: 100 }),
      expect.objectContaining({ source_row_number: 42, quantity: 3, proposed_unit_price: 175, confirmed_reference_price: 200, transport_percentage: 5 }),
    ]);
    expect(api.finalizePreliminaryAnalysis).toHaveBeenCalledTimes(1);
  });

  it("retains a row while inline editing changes its filter match, then releases it on leaving the row", async () => {
    const root = await mount();
    act(() => root.root.findAllByType("select").find(node => node.props["aria-label"] === "Lọc trạng thái rà soát")!.props.onChange({ target: { value: "missing-price" } }));
    act(() => tableField(root, 17, "proposed_unit_price").props.onChange({ target: { value: "175" } }));
    expect(root.root.findAllByProps({ "data-row-source": 17 })).toHaveLength(1);
    expect(tableField(root, 17, "proposed_unit_price").props.value).toBe("175");
    expect(JSON.stringify(root.toJSON())).toContain("giữ dòng đang sửa");
    act(() => root.root.findByProps({ "data-row-source": 17 }).props.onBlur({ currentTarget: { contains: () => false }, relatedTarget: null }));
    expect(root.root.findAllByProps({ "data-row-source": 17 })).toHaveLength(0);
    expect(root.root.findAllByType("input").find((node) => node.props.name === "proposed_unit_price")!.props.value).toBe("175");
    expect(api.finalizePreliminaryAnalysis).not.toHaveBeenCalled();
  });

  it.each([false, true])("checks current source before correcting a proved rejection (changed: %s)", async (sourceChanged) => {
    const root = await mount();
    await reviewLine(root);
    api.finalizePreliminaryAnalysis.mockImplementationOnce(async () => {
      api.getPreliminaryAnalysisAttemptState.mockResolvedValue({
        blocked: true, base_analysis_version: 0,
        active_attempt: { attempt_id: "attempt-1", status: "RECEIVED", execution_generation: 0 },
      });
      if (sourceChanged) {
        api.getSourceArtifact.mockResolvedValue({ id: "source-1", import_batch_id: "batch-1", state: "available", generation: 2, checksum_sha256: "a".repeat(64) });
      }
      throw new ApiError("Dòng chưa xác nhận.", 409, "preliminary_analysis_line_confirmation_missing", {
        detail: { execution_started: false },
      });
    });
    act(() => button(root, "Chốt phân tích sơ bộ")?.props.onClick());
    await act(async () => button(root, "Xác nhận chốt")?.props.onClick());
    expect(JSON.stringify(root.toJSON())).toContain("Dữ liệu chốt bị từ chối");
    expect(JSON.stringify(root.toJSON())).not.toContain("Chưa rõ kết quả chốt phân tích");
    expect(button(root, "Đối soát lệnh chốt")).toBeUndefined();
    if (sourceChanged) {
      expect(JSON.stringify(root.toJSON())).toContain("Bản nháp đang được giữ riêng");
      expect(button(root, "Chốt phân tích sơ bộ")?.props.disabled).toBe(true);
      expect(api.finalizePreliminaryAnalysis).toHaveBeenCalledTimes(1);
      expect(api.claimPreliminaryAnalysisAttempt).toHaveBeenCalledTimes(1);
      expect(stored.size).toBe(0);
      return;
    }
    expect(tableField(root, 17, "proposed_unit_price").props.value).toBe("110");
    act(() => tableField(root, 17, "proposed_unit_price").props.onChange({ target: { value: "175" } }));
    expect(button(root, "Chốt phân tích sơ bộ")?.props.disabled).toBe(true);
    act(() => root.root.findAllByType("input").find((node) => node.props.name === "human_line_confirmed")!.props.onChange({ currentTarget: { checked: true } }));
    act(() => button(root, "Chốt phân tích sơ bộ")?.props.onClick());
    expect(api.finalizePreliminaryAnalysis).toHaveBeenCalledTimes(1);
    api.finalizePreliminaryAnalysis.mockResolvedValueOnce({ id: "analysis-1", version: 1 });
    await act(async () => button(root, "Xác nhận chốt")?.props.onClick());
    const first = api.finalizePreliminaryAnalysis.mock.calls[0][1];
    expect(api.finalizePreliminaryAnalysis).toHaveBeenNthCalledWith(2, "project-1", {
      ...first, line_manifest: [{ ...first.line_manifest[0], proposed_unit_price: 175 }],
    }, "d".repeat(64));
    expect(api.claimPreliminaryAnalysisAttempt).toHaveBeenCalledTimes(1);
    expect(api.reconcilePreliminaryAnalysisAttempt).not.toHaveBeenCalled();
    expect(stored.size).toBe(0);
  });

  it.each([0, 409])("never sends another price POST after indeterminate status %i and negative lookup", async (status) => {
    const root = await mount();
    await reviewLine(root);
    act(() => button(root, "Chốt phân tích sơ bộ")?.props.onClick());
    api.finalizePreliminaryAnalysis.mockRejectedValueOnce(new ApiError("indeterminate", status, "preliminary_analysis_line_confirmation_missing"));
    api.getPreliminaryAnalysisAttempt.mockRejectedValue(new ApiError("not found", 404));
    await act(async () => button(root, "Xác nhận chốt")?.props.onClick());
    expect(button(root, "Thử lại cùng mã lệnh")).toBeUndefined();
    expect(button(root, "Chốt phân tích sơ bộ")?.props.disabled).toBe(true);
    await act(async () => button(root, "Kiểm tra trạng thái")?.props.onClick());
    expect(api.finalizePreliminaryAnalysis).toHaveBeenCalledTimes(1);
    expect(stored.size).toBe(0);
    expect(api.claimPreliminaryAnalysisAttempt.mock.calls[0][1]).not.toHaveProperty("line_manifest");
  });

  it("blocks a new browser view when the server reports an unresolved attempt", async () => {
    api.getPreliminaryAnalysisAttemptState.mockResolvedValue({ blocked: true, base_analysis_version: 0 });
    const root = await mount();
    expect(button(root, "Chốt phân tích sơ bộ")?.props.disabled).toBe(true);
    expect(JSON.stringify(root.toJSON())).toContain("Chưa rõ kết quả chốt phân tích");
    expect(api.finalizePreliminaryAnalysis).not.toHaveBeenCalled();
  });

  it("clears the draft on a definitive authorization failure without resending price", async () => {
    const root = await mount();
    await reviewLine(root);
    act(() => button(root, "Chốt phân tích sơ bộ")?.props.onClick());
    api.finalizePreliminaryAnalysis.mockRejectedValueOnce(new ApiError("forbidden", 403));
    await act(async () => button(root, "Xác nhận chốt")?.props.onClick());
    expect(JSON.stringify(root.toJSON())).toContain("Chưa có quyền truy cập");
    expect(button(root, "Chốt phân tích sơ bộ")).toBeUndefined();
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
