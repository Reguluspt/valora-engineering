import React from "react";
import { act, create } from "react-test-renderer";
import { beforeEach, describe, expect, it, vi } from "vitest";

const createProject = vi.hoisted(() => vi.fn());
vi.mock("../../../api/projects", () => ({ createProject }));

import { ApiError } from "../../../api/client";
import { projectListVerificationPath } from "../../../contracts/valoraV23";
import { PreliminaryRequestCreatePage } from "../PreliminaryRequestCreatePage";

describe("PreliminaryRequestCreatePage", () => {
  beforeEach(() => vi.clearAllMocks());

  function mount(onNavigate = vi.fn(), onSessionExpired = vi.fn()) {
    let root: any;
    act(() => {
      root = create(React.createElement(PreliminaryRequestCreatePage, { onNavigate, onSessionExpired }));
    });
    return { root, onNavigate, onSessionExpired };
  }

  function fill(root: any) {
    act(() => {
      root.root.findByProps({ name: "code" }).props.onChange({ target: { value: " SB-2026-001 " } });
      root.root.findByProps({ name: "name" }).props.onChange({ target: { value: " Nhà máy An Phú " } });
      root.root.findByProps({ name: "description" }).props.onChange({ target: { value: " Danh mục máy móc " } });
    });
  }

  it("creates an unbound Pre-case request and returns to the project list", async () => {
    createProject.mockResolvedValue({ id: "project-1", customer_id: null });
    const { root, onNavigate } = mount();
    fill(root);

    await act(async () => {
      await root.root.findByType("form").props.onSubmit({ preventDefault: vi.fn() });
    });

    expect(createProject).toHaveBeenCalledWith({
      code: "SB-2026-001",
      name: "Nhà máy An Phú",
      description: "Danh mục máy móc",
      customer_id: null,
    });
    expect(onNavigate).toHaveBeenCalledWith("/workbench/projects");
  });

  it("rejects whitespace-only required fields without sending a command", async () => {
    const { root } = mount();
    act(() => {
      root.root.findByProps({ name: "code" }).props.onChange({ target: { value: "  " } });
      root.root.findByProps({ name: "name" }).props.onChange({ target: { value: "Tên hợp lệ" } });
    });
    await act(async () => {
      await root.root.findByType("form").props.onSubmit({ preventDefault: vi.fn() });
    });
    expect(createProject).not.toHaveBeenCalled();
    expect(root.root.findByProps({ role: "alert" }).children.join("")).toContain("bắt buộc");
  });

  it("sends null for an omitted optional description", async () => {
    createProject.mockResolvedValue({ id: "project-1", customer_id: null });
    const { root } = mount();
    act(() => {
      root.root.findByProps({ name: "code" }).props.onChange({ target: { value: " SB-1 " } });
      root.root.findByProps({ name: "name" }).props.onChange({ target: { value: " Tên " } });
    });
    await act(async () => {
      await root.root.findByType("form").props.onSubmit({ preventDefault: vi.fn() });
    });
    expect(createProject).toHaveBeenCalledWith({
      code: "SB-1", name: "Tên", description: null, customer_id: null,
    });
  });

  it.each([
    [403, "chưa có quyền"],
    [422, "chưa hợp lệ"],
  ])("presents HTTP %i as a correctable error", async (status, message) => {
    createProject.mockRejectedValue(new ApiError("known", status));
    const { root, onNavigate } = mount();
    fill(root);
    await act(async () => {
      await root.root.findByType("form").props.onSubmit({ preventDefault: vi.fn() });
    });
    expect(root.root.findByProps({ role: "alert" }).children.join("")).toContain(message);
    expect(onNavigate).not.toHaveBeenCalled();
    expect(createProject).toHaveBeenCalledTimes(1);
  });

  it("keeps a 5xx mutation result uncertain and offers list verification", async () => {
    createProject.mockRejectedValue(new ApiError("server", 500));
    const { root } = mount();
    fill(root);
    await act(async () => {
      await root.root.findByType("form").props.onSubmit({ preventDefault: vi.fn() });
    });
    expect(root.root.findByProps({ role: "alert" }).children.join("")).toContain("Chưa xác định");
    expect(root.root.findAllByType("button").some((button: any) =>
      button.children.includes("Tạo yêu cầu sơ bộ"),
    )).toBe(false);
  });

  it.each([
    [408, new ApiError("timeout", 408)],
    [0, new Error("unexpected transport failure")],
  ])("treats an unproven mutation result (%i) as uncertain", async (_status, error) => {
    createProject.mockRejectedValue(error);
    const { root } = mount();
    fill(root);
    await act(async () => {
      await root.root.findByType("form").props.onSubmit({ preventDefault: vi.fn() });
    });
    expect(root.root.findByProps({ role: "alert" }).children.join("")).toContain("Chưa xác định");
    expect(root.root.findAllByType("button").some((button: any) =>
      button.children.includes("Tạo yêu cầu sơ bộ"),
    )).toBe(false);
  });

  it("offers authentication recovery for an expired session", async () => {
    createProject.mockRejectedValue(new ApiError("expired", 401));
    const { root, onNavigate, onSessionExpired } = mount();
    fill(root);
    await act(async () => {
      await root.root.findByType("form").props.onSubmit({ preventDefault: vi.fn() });
    });
    const login = root.root.findAllByType("button").find((button: any) =>
      button.children.includes("Đăng nhập lại"),
    );
    expect(login).toBeDefined();
    act(() => login.props.onClick());
    expect(onSessionExpired).toHaveBeenCalledTimes(1);
    expect(onNavigate).toHaveBeenCalledWith("/workbench/projects");
    expect(createProject).toHaveBeenCalledTimes(1);
  });

  it("does not send overlapping create commands before the first result arrives", async () => {
    let resolveCreate: (value: unknown) => void = () => {};
    createProject.mockImplementation(() => new Promise((resolve) => { resolveCreate = resolve; }));
    const { root } = mount();
    fill(root);
    const submit = root.root.findByType("form").props.onSubmit;
    act(() => {
      void submit({ preventDefault: vi.fn() });
      void submit({ preventDefault: vi.fn() });
    });
    expect(createProject).toHaveBeenCalledTimes(1);
    await act(async () => resolveCreate({ id: "project-1", customer_id: null }));
  });

  it("keeps a known duplicate-code failure reviewable without navigating", async () => {
    createProject.mockRejectedValue(new ApiError("duplicate", 409));
    const { root, onNavigate } = mount();
    fill(root);

    await act(async () => {
      await root.root.findByType("form").props.onSubmit({ preventDefault: vi.fn() });
    });

    expect(root.root.findByProps({ role: "alert" }).children.join("")).toContain("Mã hồ sơ đã tồn tại");
    expect(onNavigate).not.toHaveBeenCalled();
    const submit = root.root.findAllByType("button").find((button: any) =>
      button.children.includes("Tạo yêu cầu sơ bộ")
    );
    expect(submit.props.disabled).toBe(false);
  });

  it("does not blindly retry when mutation commit status is uncertain", async () => {
    createProject.mockRejectedValue(new ApiError("network", 0));
    const { root, onNavigate } = mount();
    fill(root);

    await act(async () => {
      await root.root.findByType("form").props.onSubmit({ preventDefault: vi.fn() });
    });

    expect(root.root.findByProps({ role: "alert" }).children.join("")).toContain(
      "Chưa xác định yêu cầu đã được tạo hay chưa"
    );
    expect(root.root.findAllByType("button").some((button: any) =>
      button.children.includes("Tạo yêu cầu sơ bộ")
    )).toBe(false);

    const recovery = root.root.findAllByType("button").find((button: any) =>
      button.children.includes("Về danh sách hồ sơ để kiểm tra")
    );
    act(() => recovery.props.onClick());
    expect(onNavigate).toHaveBeenCalledWith(projectListVerificationPath("SB-2026-001"));
    expect(createProject).toHaveBeenCalledTimes(1);
  });
});
