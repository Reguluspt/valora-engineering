import React from "react";
import { act, create } from "react-test-renderer";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
const native = vi.hoisted(() => ({ availability: { state: "browser-only" }, statusText: "Trình duyệt",
  pickExcelFile: vi.fn(), saveArtifact: vi.fn() }));
vi.mock("../../../native/useNativeIntegration", () => ({ useNativeIntegration: () => native }));

const api = vi.hoisted(() => ({
  getProject: vi.fn(), listPreliminaryBatches: vi.fn(), createPreliminaryBatch: vi.fn(),
  getMappingRecovery: vi.fn(), getSourceArtifact: vi.fn(), uploadSourceArtifact: vi.fn(),
  listSourceArtifacts: vi.fn(),
  listStructureSnapshots: vi.fn(), analyzeStructure: vi.fn(), proposeMapping: vi.fn(),
  confirmMapping: vi.fn(), materializeMapping: vi.fn(),
}));
vi.mock("../../../api/projects", () => ({ getProject: api.getProject }));
vi.mock("../../../api/preliminaryIntake", () => api);
vi.mock("../../workbench/project-context", () => ({
  useResolvedProject: () => ({ state: "ready", projectId: "p-1" }),
}));

import { ApiError } from "../../../api/client";
import { PreliminaryIntakePage } from "../PreliminaryIntakePage";

const project = {
  id: "p-1", code: "SB-1", name: "Yêu cầu An Phú", customer_id: null,
  current_preliminary_import_batch_id: "b-1",
};
const batch = { id: "b-1", project_id: "p-1", status: "created" };
const source = { id: "s-1", import_batch_id: "b-1", state: "available", original_filename: "assets.xlsx" };
const candidate = {
  sheet_name: "Danh mục", header_start_row: 2, header_end_row: 2, data_start_row: 3,
  candidate_table_bounds: { min_row: 2, max_row: 12, min_column: 1, max_column: 2 },
  header_labels: ["Tên", "Số lượng"], confidence: 0.9, reasons: [], boundary_reason: "", boundary_flags: [],
};
const snapshot = {
  id: "st-1", import_batch_id: "b-1", source_artifact_id: "s-1", snapshot_version: 1,
  candidate_count: 1, structure_payload: { candidates: [candidate] },
};
const mappingSnapshot = {
  contract_version: "v1", source: { source_artifact_id: "s-1", generation: 1, checksum_sha256: "sha" },
  structure: { structure_snapshot_id: "st-1", snapshot_version: 1, rule_version: "r1", analysis_digest_sha256: "digest" },
  template_fingerprint_sha256: "template", candidate: {
    candidate_index: 0, sheet_name: "Danh mục", header_start_row: 2, header_end_row: 2,
    data_start_row: 3, min_row: 2, max_row: 12, min_column: 1, max_column: 2,
  },
  fields: [
    { source_column_index: 1, source_column_letter: "A", original_header: "Tên", semantic_role: "raw_asset_name" },
    { source_column_index: 2, source_column_letter: "B", original_header: "Số lượng", semantic_role: "quantity" },
  ],
};
const proposal = {
  decision_id: "pr-1", source_artifact_id: "s-1", structure_snapshot_id: "st-1",
  mapping_snapshot: mappingSnapshot, mapping_digest_sha256: "digest", review_required: true,
  review_reasons: [], exact_profile_id: null, similar_profile_ids: [], organization_template_id: null,
};

function recovery(status: string, overrides: Record<string, unknown> = {}) {
  return {
    project_id: "p-1", batch_id: "b-1", current_batch_id: "b-1", current_source_artifact_id: "s-1",
    selection_revision: 7, status, official_intake_closed: false,
    selected_confirmation_decision_id: null, selected_structure_snapshot_id: null,
    selected_source_artifact_id: null, selected_candidate: null, mapping_snapshot: null,
    mapping_digest_sha256: null, memory_scope: null, profile_id: null, selected_command_id: null,
    selected_outcome: null, selected_usage_id: null, current_staging_usage_id: null,
    materialized_asset_row_count: null, materialized_mapping_digest_sha256: null, recent_proposals: [],
    ...overrides,
  };
}

describe("PreliminaryIntakePage", () => {
  let serverRecovery: ReturnType<typeof recovery>;
  beforeEach(() => {
    vi.resetAllMocks();
    native.availability = { state: "browser-only" };
    native.statusText = "Trình duyệt";
    const pending = new Map<string, string>();
    vi.stubGlobal("sessionStorage", {
      getItem: (key: string) => pending.get(key) || null,
      setItem: (key: string, value: string) => pending.set(key, value),
      removeItem: (key: string) => pending.delete(key),
    });
    serverRecovery = recovery("no_selection");
    api.getProject.mockImplementation(async () => project);
    api.listPreliminaryBatches.mockImplementation(async () => [batch]);
    api.getMappingRecovery.mockImplementation(async () => serverRecovery);
    api.getSourceArtifact.mockImplementation(async () => source);
    api.listSourceArtifacts.mockImplementation(async () => [source]);
    api.listStructureSnapshots.mockImplementation(async () => [snapshot]);
    api.analyzeStructure.mockImplementation(async () => snapshot);
    api.proposeMapping.mockImplementation(async () => proposal);
  });
  afterEach(() => vi.unstubAllGlobals());

  async function mount() {
    let root: any;
    await act(async () => {
      root = create(React.createElement(PreliminaryIntakePage, {
        projectRef: "p-1", onNavigate: vi.fn(), onSessionExpired: vi.fn(),
      }));
    });
    return root;
  }

  function button(root: any, label: string) {
    return root.root.findAllByType("button").find((item: any) => item.children.includes(label));
  }

  it("fills the existing File state through Windows and waits for explicit upload", async () => {
    native.availability = { state: "native-compatible" };
    api.getSourceArtifact.mockResolvedValue(null);
    api.listSourceArtifacts.mockResolvedValue([]);
    api.getMappingRecovery.mockResolvedValue(recovery("no_selection", { current_source_artifact_id: null }));
    api.listStructureSnapshots.mockResolvedValue([]);
    const file = new File([new Uint8Array([1, 2])], "native.xlsx");
    native.pickExcelFile.mockResolvedValue(file);
    api.uploadSourceArtifact.mockResolvedValue(source);
    const root = await mount();
    expect(root.root.findByType("input").props.type).toBe("file");
    await act(async () => button(root, "Chọn tệp bằng Windows").props.onClick());
    expect(api.uploadSourceArtifact).not.toHaveBeenCalled();
    expect(api.createPreliminaryBatch).not.toHaveBeenCalled();
    expect(api.analyzeStructure).not.toHaveBeenCalled();
    expect(api.materializeMapping).not.toHaveBeenCalled();
    expect(JSON.stringify(root.toJSON())).toContain("native.xlsx");
    await act(async () => button(root, "Tải tệp Excel").props.onClick());
    expect(api.uploadSourceArtifact).toHaveBeenCalledWith("p-1", "b-1", file);
  });

  it.each(["native-incompatible/update-required", "revoked/error"])("preserves the browser input when %s", async state => {
    native.availability = { state };
    native.statusText = "Windows cần cập nhật";
    api.getSourceArtifact.mockResolvedValue(null);
    api.listSourceArtifacts.mockResolvedValue([]);
    api.getMappingRecovery.mockResolvedValue(recovery("no_selection", { current_source_artifact_id: null }));
    api.listStructureSnapshots.mockResolvedValue([]);
    const root = await mount();
    expect(button(root, "Chọn tệp bằng Windows")).toBeUndefined();
    expect(root.root.findByType("input").props.disabled).toBe(false);
    expect(JSON.stringify(root.toJSON())).toContain("Windows cần cập nhật");
    expect(api.uploadSourceArtifact).not.toHaveBeenCalled();
  });

  async function selectCandidate(root: any) {
    const selector = root.root.findAllByType("select").find((item: any) =>
      item.props.className === "valora-field" && item.props.value === "");
    if (selector) act(() => selector.props.onChange({ target: { value: "st-1" } }));
    const structure = root.root.findByProps({ "aria-label": "Vùng bảng được phát hiện" });
    act(() => structure.findByType("input").props.onChange());
  }

  it("uses the explicit current batch and authoritative source, with no automatic confirmation", async () => {
    api.listPreliminaryBatches.mockResolvedValue([{ id: "old-batch" }, batch]);
    const root = await mount();
    expect(api.getMappingRecovery).toHaveBeenCalledWith("p-1", "b-1");
    expect(api.getSourceArtifact).toHaveBeenCalledWith("p-1", "b-1", "s-1");
    expect(JSON.stringify(root.toJSON())).toContain("assets.xlsx");
    await selectCandidate(root);
    await act(async () => button(root, "Tạo đề xuất ánh xạ").props.onClick());
    expect(api.proposeMapping).toHaveBeenCalledWith("p-1", "b-1", expect.objectContaining({
      source_artifact_id: "s-1", structure_snapshot_id: "st-1", candidate_index: 0,
      command_id: expect.any(String),
    }));
    expect(api.confirmMapping).not.toHaveBeenCalled();
    expect(JSON.stringify(root.toJSON())).toContain("Đề xuất chưa có hiệu lực");
  });

  it("fails closed when retained batches exist but the current pointer is NULL", async () => {
    api.getProject.mockResolvedValue({ ...project, current_preliminary_import_batch_id: null });
    api.listPreliminaryBatches.mockResolvedValue([batch]);
    const root = await mount();
    expect(JSON.stringify(root.toJSON())).toContain("Chưa xác định batch hiện hành");
    expect(api.getMappingRecovery).not.toHaveBeenCalled();
    expect(button(root, "Tải tệp Excel")).toBeUndefined();
  });

  it("blocks a second upload while the current batch still has a pending artifact", async () => {
    api.getMappingRecovery.mockResolvedValue(recovery("no_selection", { current_source_artifact_id: null }));
    api.listSourceArtifacts.mockResolvedValue([{ ...source, state: "pending" }]);
    const root = await mount();
    expect(JSON.stringify(root.toJSON())).toContain("Tệp đang được xử lý");
    expect(button(root, "Tải tệp Excel")).toBeUndefined();
    expect(api.uploadSourceArtifact).not.toHaveBeenCalled();
  });

  it("opens the session recovery state when upload loses authorization", async () => {
    api.getMappingRecovery.mockResolvedValue(recovery("no_selection", { current_source_artifact_id: null }));
    api.listSourceArtifacts.mockResolvedValue([]);
    api.uploadSourceArtifact.mockRejectedValue(new ApiError("expired", 401));
    const root = await mount();
    act(() => root.root.findByType("input").props.onChange({ target: { files: [{ name: "assets.xlsx" }] } }));
    await act(async () => button(root, "Tải tệp Excel").props.onClick());
    expect(JSON.stringify(root.toJSON())).toContain("Phiên làm việc đã hết hạn");
  });

  it("offers an explicit replacement path for the current available source", async () => {
    const root = await mount();
    act(() => button(root, "Tải tệp Excel khác").props.onClick());
    expect(JSON.stringify(root.toJSON())).toContain("Tệp mới sẽ trở thành nguồn hiện hành");
    expect(button(root, "Tải tệp Excel")).toBeDefined();
    expect(button(root, "Phân tích cấu trúc")).toBeUndefined();
    await act(async () => button(root, "Hủy thay tệp").props.onClick());
    expect(button(root, "Tải tệp Excel")).toBeUndefined();
  });

  it("disables mutations when an authoritative refresh fails and the visible data is stale", async () => {
    const root = await mount();
    api.analyzeStructure.mockRejectedValueOnce(new ApiError("invalid", 422));
    api.getMappingRecovery.mockRejectedValueOnce(new ApiError("unavailable", 503));
    await act(async () => button(root, "Phân tích lại cấu trúc").props.onClick());
    expect(JSON.stringify(root.toJSON())).toContain("Thông tin đang hiển thị có thể đã cũ");
    expect(button(root, "Phân tích lại cấu trúc").props.disabled).toBe(true);
    expect(api.analyzeStructure).toHaveBeenCalledTimes(1);
  });

  it("creates the first batch, uploads the selected file, and never calls Apply", async () => {
    let currentProject = { ...project, current_preliminary_import_batch_id: null as string | null };
    let currentBatches: any[] = [];
    let currentSource: any = null;
    api.getProject.mockImplementation(async () => currentProject);
    api.listPreliminaryBatches.mockImplementation(async () => currentBatches);
    api.getMappingRecovery.mockImplementation(async () => recovery("no_selection", {
      current_source_artifact_id: currentSource?.id || null,
    }));
    api.getSourceArtifact.mockImplementation(async () => currentSource);
    api.listSourceArtifacts.mockImplementation(async () => currentSource ? [currentSource] : []);
    api.createPreliminaryBatch.mockImplementation(async () => {
      currentProject = { ...currentProject, current_preliminary_import_batch_id: "b-1" };
      currentBatches = [batch];
      return batch;
    });
    api.uploadSourceArtifact.mockImplementation(async () => {
      currentSource = source;
      return source;
    });
    const root = await mount();
    expect(JSON.stringify(root.toJSON())).toContain("Chưa có batch nhập liệu");
    const file = { name: "assets.xlsx" } as File;
    act(() => root.root.findByType("input").props.onChange({ target: { files: [file] } }));
    await act(async () => button(root, "Tải tệp Excel").props.onClick());
    expect(api.createPreliminaryBatch).toHaveBeenCalledWith("p-1", "assets.xlsx");
    expect(api.uploadSourceArtifact).toHaveBeenCalledWith("p-1", "b-1", file);
    expect(JSON.stringify(root.toJSON())).toContain("Tiếp tục phân tích cấu trúc");
  });

  it("keeps an unknown upload blocked across reload until the current-source GET proves completion", async () => {
    let currentSource: typeof source | null = null;
    api.getMappingRecovery.mockImplementation(async () => recovery("no_selection", {
      current_source_artifact_id: currentSource?.id || null,
    }));
    api.getSourceArtifact.mockImplementation(async () => currentSource);
    api.listSourceArtifacts.mockImplementation(async () => currentSource ? [currentSource] : []);
    api.uploadSourceArtifact.mockRejectedValue(new ApiError("network", 0));
    const first = await mount();
    act(() => first.root.findByType("input").props.onChange({ target: { files: [{ name: "assets.xlsx" }] } }));
    await act(async () => button(first, "Tải tệp Excel").props.onClick());
    expect(api.uploadSourceArtifact).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(first.toJSON())).toContain("Kết quả thao tác chưa rõ");
    const reloaded = await mount();
    expect(button(reloaded, "Tải tệp Excel").props.disabled).toBe(true);
    currentSource = source;
    await act(async () => button(reloaded, "Kiểm tra trạng thái").props.onClick());
    expect(JSON.stringify(reloaded.toJSON())).not.toContain("Kết quả thao tác chưa rõ");
    expect(JSON.stringify(reloaded.toJSON())).toContain("Sẵn sàng");
    expect(api.uploadSourceArtifact).toHaveBeenCalledTimes(1);
  });

  it("recovers an unknown upload in the same view when session storage is unavailable", async () => {
    let currentSource: typeof source | null = null;
    api.getMappingRecovery.mockImplementation(async () => recovery("no_selection", {
      current_source_artifact_id: currentSource?.id || null,
    }));
    api.getSourceArtifact.mockImplementation(async () => currentSource);
    api.listSourceArtifacts.mockImplementation(async () => currentSource ? [currentSource] : []);
    api.uploadSourceArtifact.mockRejectedValue(new ApiError("network", 0));
    sessionStorage.setItem = () => { throw new Error("storage denied"); };
    const root = await mount();
    act(() => root.root.findByType("input").props.onChange({ target: { files: [{ name: "assets.xlsx" }] } }));
    await act(async () => button(root, "Tải tệp Excel").props.onClick());
    expect(JSON.stringify(root.toJSON())).toContain("Kết quả thao tác chưa rõ");
    currentSource = source;
    await act(async () => button(root, "Kiểm tra trạng thái").props.onClick());
    expect(JSON.stringify(root.toJSON())).not.toContain("Kết quả thao tác chưa rõ");
    expect(api.uploadSourceArtifact).toHaveBeenCalledTimes(1);
  });

  it("requires human review and sends the server revision with NULL-customer memory disabled", async () => {
    const root = await mount();
    await selectCandidate(root);
    await act(async () => button(root, "Tạo đề xuất ánh xạ").props.onClick());
    expect(JSON.stringify(root.toJSON())).not.toContain("Ghi nhớ ánh xạ cho khách hàng");
    const role = root.root.findByProps({ "aria-label": "Vai trò cho cột B" });
    act(() => role.props.onChange({ target: { value: "unit" } }));
    expect(button(root, "Xác nhận ánh xạ").props.disabled).toBe(true);
    const check = root.root.findByProps({ className: "precase-review-check" }).findByType("input");
    act(() => check.props.onChange({ target: { checked: true } }));
    api.confirmMapping.mockImplementation(async (_projectId, _batchId, payload) => {
      serverRecovery = recovery("selected_unmaterialized", {
        selection_revision: 8, selected_confirmation_decision_id: "cf-1",
        selected_command_id: payload.command_id, mapping_snapshot: payload.mapping_snapshot,
        selected_structure_snapshot_id: "st-1",
      });
      return { decision_id: "cf-1" };
    });
    await act(async () => button(root, "Xác nhận ánh xạ").props.onClick());
    expect(api.confirmMapping).toHaveBeenCalledWith("p-1", "b-1", expect.objectContaining({
      proposal_decision_id: "pr-1", expected_selection_revision: 7, memory_scope: "none",
      mapping_snapshot: expect.objectContaining({ fields: expect.arrayContaining([
        expect.objectContaining({ source_column_letter: "B", semantic_role: "unit" }),
      ]) }),
    }));
    expect(button(root, "Tạo dữ liệu tạm")).toBeDefined();
    api.materializeMapping.mockImplementation(async (_projectId, _batchId, payload) => {
      serverRecovery = recovery("materialized", {
        selection_revision: 9, selected_confirmation_decision_id: "cf-1",
        mapping_snapshot: mappingSnapshot, materialized_asset_row_count: 10,
        current_staging_usage_id: "usage-1",
      });
      return { usage_id: "usage-1", ...payload };
    });
    await act(async () => button(root, "Tạo dữ liệu tạm").props.onClick());
    expect(api.materializeMapping).toHaveBeenCalledWith("p-1", "b-1", expect.objectContaining({
      confirmation_decision_id: "cf-1", expected_selection_revision: 8,
    }));
    expect(root.root.findByProps({ className: "precase-materialized" }).children.join("")).toContain("Đã đưa 10 dòng tài sản vào vùng dữ liệu tạm");
  });

  it("explains a profile conflict without blaming another mapping selection", async () => {
    api.proposeMapping.mockRejectedValue(new ApiError("conflict", 409, "mapping_profile_conflict"));
    const root = await mount();
    await selectCandidate(root);
    await act(async () => button(root, "Tạo đề xuất ánh xạ").props.onClick());
    expect(JSON.stringify(root.toJSON())).toContain("Ký ức ánh xạ");
  });

  it("opens the session recovery state when confirmation loses authorization", async () => {
    const root = await mount();
    await selectCandidate(root);
    await act(async () => button(root, "Tạo đề xuất ánh xạ").props.onClick());
    act(() => root.root.findByProps({ className: "precase-review-check" }).findByType("input").props.onChange({ target: { checked: true } }));
    api.confirmMapping.mockRejectedValue(new ApiError("expired", 401));
    await act(async () => button(root, "Xác nhận ánh xạ").props.onClick());
    expect(JSON.stringify(root.toJSON())).toContain("Phiên làm việc đã hết hạn");
  });

  it("refreshes on CAS conflict without retrying confirmation", async () => {
    const root = await mount();
    await selectCandidate(root);
    await act(async () => button(root, "Tạo đề xuất ánh xạ").props.onClick());
    act(() => root.root.findByProps({ className: "precase-review-check" }).findByType("input").props.onChange({ target: { checked: true } }));
    api.confirmMapping.mockImplementation(async () => {
      serverRecovery = recovery("selected_unmaterialized", {
        selection_revision: 8, selected_confirmation_decision_id: "other-decision",
        mapping_snapshot: mappingSnapshot,
      });
      throw new ApiError("conflict", 409, "mapping_selection_revision_conflict");
    });
    await act(async () => button(root, "Xác nhận ánh xạ").props.onClick());
    expect(api.confirmMapping).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(root.toJSON())).toContain("Phiên bản chọn ánh xạ đã thay đổi");
    expect(button(root, "Xác nhận ánh xạ")).toBeUndefined();
  });

  it.each([
    ["unresolved_legacy_history", "Lịch sử ánh xạ cũ"],
    ["selected_recovery_required", "Dữ liệu tạm cũ"],
    ["stale_lineage", "Ánh xạ không còn khớp nguồn hiện hành"],
    ["selected_unmaterialized", "Tạo dữ liệu tạm"],
    ["materialized", "Đã đưa 4 dòng tài sản vào vùng dữ liệu tạm"],
  ])("renders authoritative recovery state %s", async (status, expected) => {
    serverRecovery = recovery(status, status === "selected_unmaterialized" || status === "materialized" ? {
      selected_confirmation_decision_id: "cf-1", selected_structure_snapshot_id: "st-1",
      mapping_snapshot: mappingSnapshot, materialized_asset_row_count: 4,
    } : {});
    const root = await mount();
    const rendered = status === "materialized"
      ? root.root.findByProps({ className: "precase-materialized" }).children.join("")
      : JSON.stringify(root.toJSON());
    expect(rendered).toContain(expected);
  });

  it("keeps a lost confirmation response from issuing a second decision", async () => {
    const root = await mount();
    await selectCandidate(root);
    await act(async () => button(root, "Tạo đề xuất ánh xạ").props.onClick());
    act(() => root.root.findByProps({ className: "precase-review-check" }).findByType("input").props.onChange({ target: { checked: true } }));
    api.confirmMapping.mockImplementation(async (_projectId, _batchId, payload) => {
      serverRecovery = recovery("selected_unmaterialized", {
        selection_revision: 8, selected_confirmation_decision_id: "cf-1",
        selected_command_id: payload.command_id, mapping_snapshot: mappingSnapshot,
      });
      throw new ApiError("network", 0);
    });
    await act(async () => button(root, "Xác nhận ánh xạ").props.onClick());
    expect(api.confirmMapping).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(root.toJSON())).toContain("Máy chủ đã ghi nhận xác nhận ánh xạ");
  });

  it("replays an uncommitted confirmation with its exact command after recovery GET", async () => {
    api.proposeMapping.mockImplementation(async (_projectId, _batchId, payload) => {
      serverRecovery = recovery("no_selection", { recent_proposals: [{
        proposal_decision_id: "pr-1", source_artifact_id: "s-1",
        structure_snapshot_id: "st-1", command_id: payload.command_id, terminal_outcomes: [],
      }] });
      return proposal;
    });
    const root = await mount();
    await selectCandidate(root);
    await act(async () => button(root, "Tạo đề xuất ánh xạ").props.onClick());
    act(() => root.root.findByProps({ className: "precase-review-check" }).findByType("input").props.onChange({ target: { checked: true } }));
    api.confirmMapping.mockImplementationOnce(async () => { throw new ApiError("network", 0); });
    api.confirmMapping.mockImplementationOnce(async (_projectId, _batchId, payload) => {
      serverRecovery = recovery("selected_unmaterialized", {
        selection_revision: 8, selected_confirmation_decision_id: "cf-1",
        selected_command_id: payload.command_id, mapping_snapshot: payload.mapping_snapshot,
      });
      return { decision_id: "cf-1" };
    });
    await act(async () => button(root, "Xác nhận ánh xạ").props.onClick());
    expect(api.confirmMapping).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(root.toJSON())).toContain("Kết quả thao tác chưa rõ");
    await act(async () => button(root, "Kiểm tra trạng thái").props.onClick());
    expect(api.confirmMapping).toHaveBeenCalledTimes(2);
    expect(api.confirmMapping.mock.calls[1][2]).toEqual(api.confirmMapping.mock.calls[0][2]);
    expect(JSON.stringify(root.toJSON())).toContain("Ánh xạ đã được người dùng xác nhận");
  });

  it("retires an uncertain confirmation after a newer server revision invalidates it", async () => {
    const root = await mount();
    await selectCandidate(root);
    await act(async () => button(root, "Tạo đề xuất ánh xạ").props.onClick());
    act(() => root.root.findByProps({ className: "precase-review-check" }).findByType("input").props.onChange({ target: { checked: true } }));
    api.confirmMapping.mockRejectedValueOnce(new ApiError("network", 0));
    await act(async () => button(root, "Xác nhận ánh xạ").props.onClick());
    serverRecovery = recovery("stale_lineage", { selection_revision: 8 });
    await act(async () => button(root, "Kiểm tra trạng thái").props.onClick());
    expect(api.confirmMapping).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(root.toJSON())).not.toContain("Kết quả thao tác chưa rõ");
    expect(JSON.stringify(root.toJSON())).toContain("Lệnh trước không còn áp dụng");
  });

  it("allows a newly reviewed structure to recover an occupied old selection", async () => {
    serverRecovery = recovery("selected_recovery_required", {
      selected_confirmation_decision_id: "old-cf", selected_structure_snapshot_id: "old-st",
      mapping_snapshot: mappingSnapshot,
    });
    const root = await mount();
    expect(JSON.stringify(root.toJSON())).not.toContain("Ánh xạ đã được người dùng xác nhận");
    await selectCandidate(root);
    await act(async () => button(root, "Tạo đề xuất ánh xạ").props.onClick());
    expect(api.proposeMapping).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(root.toJSON())).toContain("Đề xuất chưa có hiệu lực");
    expect(button(root, "Xác nhận ánh xạ")).toBeDefined();
  });

  it("allows a fresh proposal from the available source after stale lineage", async () => {
    serverRecovery = recovery("stale_lineage");
    const root = await mount();
    await selectCandidate(root);
    await act(async () => button(root, "Tạo đề xuất ánh xạ").props.onClick());
    expect(api.proposeMapping).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(root.toJSON())).toContain("Đề xuất chưa có hiệu lực");
  });

  it("offers customer memory only for a bound customer and still requires review", async () => {
    api.getProject.mockResolvedValue({ ...project, customer_id: "c-1" });
    api.proposeMapping.mockResolvedValue({ ...proposal, exact_profile_id: "profile-1" });
    const root = await mount();
    await selectCandidate(root);
    await act(async () => button(root, "Tạo đề xuất ánh xạ").props.onClick());
    const memory = root.root.findAllByType("select").find((item: any) =>
      item.props.value === "none" && item.findAllByType("option").some((option: any) => option.props.value === "customer"));
    expect(memory).toBeDefined();
    act(() => memory.props.onChange({ target: { value: "customer" } }));
    const replacement = root.root.findAllByType("select").find((item: any) =>
      item.findAllByType("option").some((option: any) => option.props.value === "profile-1"));
    expect(replacement).toBeDefined();
    act(() => replacement.props.onChange({ target: { value: "profile-1" } }));
    expect(button(root, "Xác nhận ánh xạ").props.disabled).toBe(true);
    act(() => root.root.findByProps({ className: "precase-review-check" }).findByType("input").props.onChange({ target: { checked: true } }));
    api.confirmMapping.mockResolvedValue({ decision_id: "cf-1" });
    await act(async () => button(root, "Xác nhận ánh xạ").props.onClick());
    expect(api.confirmMapping).toHaveBeenCalledWith("p-1", "b-1", expect.objectContaining({
      memory_scope: "customer", supersedes_profile_id: "profile-1",
    }));
  });

  it("recovers a lost materialization response and reloads selected staging from the server", async () => {
    serverRecovery = recovery("selected_unmaterialized", {
      selected_confirmation_decision_id: "cf-1", selected_structure_snapshot_id: "st-1",
      mapping_snapshot: mappingSnapshot,
    });
    const root = await mount();
    api.materializeMapping.mockImplementation(async () => {
      serverRecovery = recovery("materialized", {
        selection_revision: 8, selected_confirmation_decision_id: "cf-1",
        selected_structure_snapshot_id: "st-1", mapping_snapshot: mappingSnapshot,
        materialized_asset_row_count: 6, selected_usage_id: "u-1", current_staging_usage_id: "u-1",
      });
      throw new ApiError("network", 0);
    });
    await act(async () => button(root, "Tạo dữ liệu tạm").props.onClick());
    expect(api.materializeMapping).toHaveBeenCalledTimes(1);
    expect(root.root.findByProps({ className: "precase-materialized" }).children.join("")).toContain("6 dòng tài sản");
    let reloaded: any;
    await act(async () => {
      reloaded = create(React.createElement(PreliminaryIntakePage, {
        projectRef: "p-1", onNavigate: vi.fn(), onSessionExpired: vi.fn(),
      }));
    });
    expect(reloaded.root.findByProps({ className: "precase-materialized" }).children.join("")).toContain("6 dòng tài sản");
  });

  it("opens the permission state when materialization is forbidden", async () => {
    serverRecovery = recovery("selected_unmaterialized", {
      selected_confirmation_decision_id: "cf-1", mapping_snapshot: mappingSnapshot,
    });
    const root = await mount();
    api.materializeMapping.mockRejectedValue(new ApiError("forbidden", 403));
    await act(async () => button(root, "Tạo dữ liệu tạm").props.onClick());
    expect(JSON.stringify(root.toJSON())).toContain("Chưa có quyền truy cập");
  });

  it("replays an uncommitted materialization with the same command and selected revision", async () => {
    serverRecovery = recovery("selected_unmaterialized", {
      selected_confirmation_decision_id: "cf-1", selected_structure_snapshot_id: "st-1",
      mapping_snapshot: mappingSnapshot,
    });
    const root = await mount();
    api.materializeMapping.mockImplementationOnce(async () => { throw new ApiError("network", 0); });
    api.materializeMapping.mockImplementationOnce(async () => {
      serverRecovery = recovery("materialized", {
        selection_revision: 8, selected_confirmation_decision_id: "cf-1",
        mapping_snapshot: mappingSnapshot, materialized_asset_row_count: null,
      });
      return { usage_id: "u-1" };
    });
    await act(async () => button(root, "Tạo dữ liệu tạm").props.onClick());
    expect(api.materializeMapping).toHaveBeenCalledTimes(1);
    await act(async () => button(root, "Kiểm tra trạng thái").props.onClick());
    expect(api.materializeMapping).toHaveBeenCalledTimes(2);
    expect(api.materializeMapping.mock.calls[1][2]).toEqual(api.materializeMapping.mock.calls[0][2]);
    expect(root.root.findByProps({ className: "precase-materialized" }).children.join("")).toContain("chưa xác định số dòng");
  });

  it("retires an uncertain materialization after the selected revision changes", async () => {
    serverRecovery = recovery("selected_unmaterialized", {
      selected_confirmation_decision_id: "cf-1", mapping_snapshot: mappingSnapshot,
    });
    const root = await mount();
    api.materializeMapping.mockRejectedValueOnce(new ApiError("network", 0));
    await act(async () => button(root, "Tạo dữ liệu tạm").props.onClick());
    serverRecovery = recovery("selected_unmaterialized", {
      selection_revision: 8, selected_confirmation_decision_id: "cf-1",
      mapping_snapshot: mappingSnapshot,
    });
    await act(async () => button(root, "Kiểm tra trạng thái").props.onClick());
    expect(api.materializeMapping).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(root.toJSON())).not.toContain("Kết quả thao tác chưa rõ");
    expect(JSON.stringify(root.toJSON())).toContain("Lệnh trước không còn áp dụng");
  });
});
