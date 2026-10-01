import React from "react";
import { act, create } from "react-test-renderer";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  fetchCaseState: vi.fn(), getProject: vi.fn(), getPreliminaryResult: vi.fn(),
  generatePreliminaryResult: vi.fn(), downloadPreliminaryResult: vi.fn(),
  searchActiveCustomers: vi.fn(), getCustomer: vi.fn(), bindPreliminaryCustomer: vi.fn(),
  commitOfficialIntake: vi.fn(),
}));
vi.mock("../../../api/caseState", () => ({ fetchCaseState: api.fetchCaseState }));
vi.mock("../../../api/projects", () => ({ getProject: api.getProject }));
vi.mock("../../../api/preliminaryCompletion", () => api);
vi.mock("../../workbench/project-context", () => ({
  useResolvedProject: () => ({ state: "ready", projectId: "project-1" }),
}));

import { ApiError } from "../../../api/client";
import { PreliminaryCompletionPage } from "../PreliminaryCompletionPage";

const result = {
  id: "result-2", project_id: "project-1", version: 2,
  original_filename: "result-2.xlsx", content_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  file_size_bytes: 512, content_checksum_sha256: "b".repeat(64), source_snapshot_sha256: "a".repeat(64),
  created_at: "2026-09-30T12:00:00Z",
};
const customer = {
  id: "customer-1", legal_name: "Công ty Thiết bị Việt", display_name: null,
  tax_code: "0101234567", contact_phone: "0900123456", address: null, status: "active",
};

function state() {
  return {
    case_version: "a".repeat(64), current_stage: "PRELIMINARY_READY",
    next_action: { kind: "PENDING", stage: "PRELIMINARY_READY", semantic_route_key: "preliminary_ready_pending", validation_issue_id: null },
    stages: [
      { stage: "PRELIMINARY_ANALYSIS", result: "COMPLETE" },
      { stage: "PRELIMINARY_READY", result: "INCOMPLETE" },
      { stage: "OFFICIAL_INTAKE", result: "INCOMPLETE" },
    ],
    blockers: [], warnings: [], stale: [], capabilities: [],
    preliminary: {
      project_id: "project-1", project_row_version: 7, customer_id: null,
      current_preliminary_import_batch_id: "batch-1", current_source_artifact_id: "source-1",
      current_preliminary_analysis_snapshot_id: "analysis-2", current_preliminary_analysis_version: 2,
      current_preliminary_result_artifact_id: null, current_preliminary_result_version: null,
      official_intake_commit_id: null,
    },
  };
}

describe("PreliminaryCompletionPage", () => {
  let serverState: ReturnType<typeof state>;
  let project: { id: string; row_version: number; customer_id: string | null; code: string; name: string };
  let stored: Map<string, string>;

  beforeEach(() => {
    vi.resetAllMocks();
    serverState = state();
    project = { id: "project-1", row_version: 7, customer_id: null, code: "HS-01", name: "Máy cắt" };
    stored = new Map();
    vi.stubGlobal("sessionStorage", {
      getItem: (key: string) => stored.get(key) || null,
      setItem: (key: string, value: string) => stored.set(key, value),
      removeItem: (key: string) => stored.delete(key),
    });
    vi.stubGlobal("crypto", { randomUUID: () => "command-1" });
    api.fetchCaseState.mockImplementation(async () => serverState);
    api.getProject.mockImplementation(async () => project);
    api.getPreliminaryResult.mockResolvedValue(result);
    api.getCustomer.mockResolvedValue(customer);
    api.searchActiveCustomers.mockResolvedValue([customer]);
  });
  afterEach(() => vi.unstubAllGlobals());

  function readyResult() {
    serverState.preliminary.current_preliminary_result_artifact_id = "result-2";
    serverState.preliminary.current_preliminary_result_version = 2;
    serverState.stages[1].result = "COMPLETE";
    serverState.next_action = { kind: "PENDING", stage: "OFFICIAL_INTAKE", semantic_route_key: "official_intake_pending", validation_issue_id: null };
  }

  function boundCustomer() {
    serverState.preliminary.customer_id = "customer-1";
    project.customer_id = "customer-1";
  }

  async function mount(permissions = ["project:read", "project:update", "master_data:customer:read", "project:preliminary_result:generate", "project:official_intake:commit"]) {
    let root: ReturnType<typeof create>;
    await act(async () => {
      root = create(<PreliminaryCompletionPage projectRef="project-1" permissions={permissions} onNavigate={vi.fn()} onSessionExpired={vi.fn()} />);
    });
    return root!;
  }

  function button(root: ReturnType<typeof create>, label: string) {
    return root.root.findAllByType("button").find((node) => node.children.includes(label));
  }

  it("requires the selected Analysis and explicit confirmation before generation", async () => {
    const root = await mount();
    expect(button(root, "Tạo kết quả sơ bộ")).toBeDefined();
    expect(api.generatePreliminaryResult).not.toHaveBeenCalled();
    act(() => button(root, "Tạo kết quả sơ bộ")?.props.onClick());
    api.generatePreliminaryResult.mockImplementation(async () => {
      readyResult();
      return { id: "result-2", version: 2 };
    });
    await act(async () => button(root, "Xác nhận")?.props.onClick());
    expect(api.generatePreliminaryResult).toHaveBeenCalledWith("project-1", {
      preliminary_analysis_snapshot_id: "analysis-2", expected_project_version: 7,
      idempotency_key: "g11j-command-1", confirmed: true,
    });
    expect(api.getPreliminaryResult).toHaveBeenCalledWith("project-1", "result-2");
    expect(button(root, "Tạo kết quả sơ bộ")).toBeUndefined();
    expect(button(root, "Tải tệp Excel")).toBeDefined();
  });

  it("recovers an unknown uncommitted Result response with the same command identity", async () => {
    const root = await mount();
    act(() => button(root, "Tạo kết quả sơ bộ")?.props.onClick());
    api.generatePreliminaryResult.mockRejectedValueOnce(new ApiError("offline", 0));
    await act(async () => button(root, "Xác nhận")?.props.onClick());
    expect(button(root, "Thử lại cùng lệnh")).toBeDefined();
    expect(button(root, "Tạo kết quả sơ bộ")).toBeUndefined();
    const original = api.generatePreliminaryResult.mock.calls[0][1].idempotency_key;
    api.generatePreliminaryResult.mockImplementationOnce(async () => { readyResult(); return { id: "result-2", version: 2 }; });
    await act(async () => button(root, "Thử lại cùng lệnh")?.props.onClick());
    expect(api.generatePreliminaryResult.mock.calls[1][1].idempotency_key).toBe(original);
    expect(stored.size).toBe(0);
  });

  it("restores an unknown Result attempt after navigation without allocating a new key", async () => {
    const first = await mount();
    act(() => button(first, "Tạo kết quả sơ bộ")?.props.onClick());
    api.generatePreliminaryResult.mockRejectedValueOnce(new ApiError("offline", 0));
    await act(async () => button(first, "Xác nhận")?.props.onClick());
    const original = api.generatePreliminaryResult.mock.calls[0][1].idempotency_key;
    act(() => first.unmount());
    const restored = await mount();
    expect(button(restored, "Tạo kết quả sơ bộ")).toBeUndefined();
    api.generatePreliminaryResult.mockImplementationOnce(async () => { readyResult(); return { id: "result-2", version: 2 }; });
    await act(async () => button(restored, "Thử lại cùng lệnh")?.props.onClick());
    expect(api.generatePreliminaryResult.mock.calls[1][1].idempotency_key).toBe(original);
  });

  it("does not send a mutation if the browser cannot persist its command identity", async () => {
    const root = await mount();
    act(() => button(root, "Tạo kết quả sơ bộ")?.props.onClick());
    vi.stubGlobal("sessionStorage", {
      getItem: () => null, setItem: () => { throw new Error("storage disabled"); }, removeItem: () => undefined,
    });
    await act(async () => button(root, "Xác nhận")?.props.onClick());
    expect(api.generatePreliminaryResult).not.toHaveBeenCalled();
    expect(JSON.stringify(root.toJSON())).toContain("chưa lưu được lần thử");
  });

  it("selects an active master Customer and requires a separate confirmed bind", async () => {
    readyResult();
    const root = await mount();
    expect(button(root, "Chuyển sang thẩm định chính thức")).toBeUndefined();
    await act(async () => button(root, "Tìm khách hàng")?.props.onClick());
    expect(api.searchActiveCustomers).toHaveBeenCalledWith("");
    act(() => root.root.findAllByType("input").find((node) => node.props.type === "radio")?.props.onChange());
    act(() => button(root, "Gắn khách hàng đã chọn")?.props.onClick());
    expect(api.bindPreliminaryCustomer).not.toHaveBeenCalled();
    api.bindPreliminaryCustomer.mockImplementation(async () => {
      boundCustomer(); serverState.preliminary.project_row_version = 8; project.row_version = 8;
      return { target_customer_id: "customer-1" };
    });
    await act(async () => button(root, "Xác nhận")?.props.onClick());
    expect(api.bindPreliminaryCustomer).toHaveBeenCalledWith("project-1", {
      customer_id: "customer-1", expected_project_version: 7, idempotency_key: "g11j-command-1",
    });
    expect(button(root, "Gắn khách hàng đã chọn")).toBeUndefined();
    expect(button(root, "Chuyển sang thẩm định chính thức")).toBeDefined();
  });

  it("reconciles a lost Customer response from Case State without rebinding", async () => {
    readyResult();
    const root = await mount();
    await act(async () => button(root, "Tìm khách hàng")?.props.onClick());
    act(() => root.root.findAllByType("input").find((node) => node.props.type === "radio")?.props.onChange());
    act(() => button(root, "Gắn khách hàng đã chọn")?.props.onClick());
    api.bindPreliminaryCustomer.mockImplementationOnce(async () => {
      boundCustomer(); serverState.preliminary.project_row_version = 8; project.row_version = 8;
      throw new ApiError("offline", 0);
    });
    await act(async () => button(root, "Xác nhận")?.props.onClick());
    expect(stored.size).toBe(0);
    expect(api.bindPreliminaryCustomer).toHaveBeenCalledTimes(1);
    expect(button(root, "Gắn khách hàng đã chọn")).toBeUndefined();
  });

  it("commits exact Result and version only after confirmation, then freezes the surface", async () => {
    readyResult(); boundCustomer();
    const root = await mount();
    act(() => button(root, "Chuyển sang thẩm định chính thức")?.props.onClick());
    expect(api.commitOfficialIntake).not.toHaveBeenCalled();
    api.commitOfficialIntake.mockImplementation(async () => {
      serverState.preliminary.official_intake_commit_id = "commit-1";
      serverState.stages[2].result = "COMPLETE";
      return { id: "commit-1" };
    });
    await act(async () => button(root, "Xác nhận chuyển chính thức")?.props.onClick());
    expect(api.commitOfficialIntake).toHaveBeenCalledWith("project-1", {
      preliminary_result_artifact_id: "result-2", expected_preliminary_result_version: 2,
      expected_project_version: 7, idempotency_key: "g11j-command-1", confirmed: true,
    });
    expect(JSON.stringify(root.toJSON())).toContain("Đã tiếp nhận chính thức");
    expect(JSON.stringify(root.toJSON())).toContain("Kết quả sơ bộ & tiếp nhận");
    expect(button(root, "Chuyển sang thẩm định chính thức")).toBeUndefined();
    expect(button(root, "Gắn khách hàng đã chọn")).toBeUndefined();
    expect(button(root, "Tải tệp Excel")).toBeDefined();
  });

  it("retries unknown uncommitted Intake with the exact same payload", async () => {
    readyResult(); boundCustomer();
    const root = await mount();
    act(() => button(root, "Chuyển sang thẩm định chính thức")?.props.onClick());
    api.commitOfficialIntake.mockRejectedValueOnce(new ApiError("offline", 0));
    await act(async () => button(root, "Xác nhận chuyển chính thức")?.props.onClick());
    const original = api.commitOfficialIntake.mock.calls[0][1];
    expect(button(root, "Thử lại cùng lệnh")).toBeDefined();
    api.commitOfficialIntake.mockImplementationOnce(async () => {
      serverState.preliminary.official_intake_commit_id = "commit-1";
      return { id: "commit-1" };
    });
    await act(async () => button(root, "Thử lại cùng lệnh")?.props.onClick());
    expect(api.commitOfficialIntake.mock.calls[1][1]).toEqual(original);
    expect(stored.size).toBe(0);
  });

  it("shows server blockers and warnings separately and withholds Intake", async () => {
    readyResult(); boundCustomer();
    serverState.blockers = [{ id: "blocking-1", target_type: "project", target_id: "project-1", severity: "blocking", status: "open", row_version: 1 }] as never[];
    serverState.warnings = [{ id: "warning-1", target_type: "project", target_id: "project-1", severity: "warning", status: "open", row_version: 1 }] as never[];
    serverState.next_action = { kind: "BLOCKER", stage: "OFFICIAL_INTAKE", semantic_route_key: null, validation_issue_id: "blocking-1" };
    const root = await mount();
    expect(button(root, "Chuyển sang thẩm định chính thức")).toBeUndefined();
    expect(JSON.stringify(root.toJSON())).toContain("Cảnh báo được giữ riêng");
    expect(JSON.stringify(root.toJSON())).toContain("Đang có vấn đề ngăn tiếp nhận chính thức");
    expect(button(root, "Xem vấn đề tại Tổng quan")).toBeDefined();
  });

  it("does not describe an unavailable Result as an ordinary generation step", async () => {
    serverState.stages[1].result = "NOT_AVAILABLE";
    serverState.next_action = { kind: "UNAVAILABLE", stage: "PRELIMINARY_READY", semantic_route_key: null, validation_issue_id: null };
    const root = await mount();
    const rendered = JSON.stringify(root.toJSON());
    expect(rendered).toContain("chưa khả dụng từ bằng chứng hiện hành");
    expect(rendered).not.toContain("Tạo tệp kết quả sơ bộ từ đúng bản phân tích này");
    expect(button(root, "Tạo kết quả sơ bộ")).toBeUndefined();
  });

  it("keeps immutable Result readback when Customer detail permission is absent", async () => {
    readyResult(); boundCustomer();
    serverState.preliminary.official_intake_commit_id = "commit-1";
    api.getCustomer.mockRejectedValue(new ApiError("forbidden", 403));
    const root = await mount();
    const rendered = JSON.stringify(root.toJSON());
    expect(rendered).toContain("Đã tiếp nhận chính thức");
    expect(rendered).toContain("Customer đã gắn với hồ sơ");
    expect(rendered).toContain("Đã gắn · chưa xem được");
    expect(button(root, "Tải tệp Excel")).toBeDefined();
    expect(button(root, "Chuyển sang thẩm định chính thức")).toBeUndefined();
  });

  it("does not show commands without their existing server permissions", async () => {
    const ready = await mount(["project:read"]);
    expect(button(ready, "Tạo kết quả sơ bộ")).toBeUndefined();
    expect(JSON.stringify(ready.toJSON())).toContain("chưa có quyền tạo kết quả sơ bộ");
    act(() => ready.unmount());
    readyResult(); boundCustomer();
    const intake = await mount(["project:read", "project:update"]);
    expect(button(intake, "Chuyển sang thẩm định chính thức")).toBeUndefined();
    expect(JSON.stringify(intake.toJSON())).toContain("chưa có quyền chuyển sang thẩm định chính thức");
    act(() => intake.unmount());
    serverState.preliminary.customer_id = null;
    project.customer_id = null;
    const binding = await mount(["project:read"]);
    expect(button(binding, "Tìm khách hàng")).toBeUndefined();
    expect(button(binding, "Gắn khách hàng đã chọn")).toBeUndefined();
    expect(JSON.stringify(binding.toJSON())).toContain("chưa có quyền gắn Customer");
  });

  it("identifies a server-side permission revocation instead of reporting an unknown command result", async () => {
    const root = await mount();
    act(() => button(root, "Tạo kết quả sơ bộ")?.props.onClick());
    api.generatePreliminaryResult.mockRejectedValueOnce(new ApiError("forbidden", 403));
    await act(async () => button(root, "Xác nhận")?.props.onClick());
    expect(JSON.stringify(root.toJSON())).toContain("Tài khoản chưa có quyền thực hiện lệnh này");
    expect(api.generatePreliminaryResult).toHaveBeenCalledTimes(1);
  });

  it("requires Customer master read permission before showing search and identifies a revoked read permission", async () => {
    readyResult();
    const noRead = await mount(["project:read", "project:update"]);
    expect(button(noRead, "Tìm khách hàng")).toBeUndefined();
    expect(JSON.stringify(noRead.toJSON())).toContain("chưa có quyền tìm Customer");
    act(() => noRead.unmount());
    const revoked = await mount();
    api.searchActiveCustomers.mockRejectedValueOnce(new ApiError("forbidden", 403));
    await act(async () => button(revoked, "Tìm khách hàng")?.props.onClick());
    expect(JSON.stringify(revoked.toJSON())).toContain("không còn quyền tìm Customer");
    expect(api.searchActiveCustomers).toHaveBeenCalledTimes(1);
  });

  it("keeps immutable Result readback when bound Customer detail is temporarily unavailable", async () => {
    readyResult(); boundCustomer();
    serverState.preliminary.official_intake_commit_id = "commit-1";
    api.getCustomer.mockRejectedValue(new ApiError("unavailable", 503));
    const root = await mount();
    const rendered = JSON.stringify(root.toJSON());
    expect(rendered).toContain("Đã tiếp nhận chính thức");
    expect(rendered).toContain("chưa đọc được chi tiết hiện hành");
    expect(button(root, "Tải tệp Excel")).toBeDefined();
    expect(button(root, "Chuyển sang thẩm định chính thức")).toBeUndefined();
  });
});
