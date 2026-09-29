import React from "react";
import { act, create } from "react-test-renderer";
import { beforeEach, describe, expect, it, vi } from "vitest";

const listProjects = vi.hoisted(() => vi.fn());
const resolveProjectReference = vi.hoisted(() => vi.fn());
const getProject = vi.hoisted(() => vi.fn());
vi.mock("../../../api/projects", () => ({ listProjects, resolveProjectReference, getProject }));

import { ApiError } from "../../../api/client";
import { ProjectListPage } from "../ProjectListPage";
import { APP_ROUTES } from "../../../contracts/valoraV23";

describe("ProjectListPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders real projects and opens the provider-neutral document workspace route", async () => {
    listProjects.mockResolvedValue([
      {
        id: "project-1",
        code: "HS-2026-01",
        name: "Nhà máy An Phú",
        description: "Hồ sơ tài sản",
        status: "draft",
        row_version: 3,
      },
    ]);
    const navigate = vi.fn();
    let root: any;
    await act(async () => {
      root = create(React.createElement(ProjectListPage, { onNavigate: navigate }));
    });

    expect(root.root.findAllByType("strong")[0].children.join("")).toBe("Nhà máy An Phú");
    const button = root.root.findAllByType("button").find((item: any) =>
      item.children.includes("Không gian tài liệu"),
    );
    act(() => button.props.onClick());
    expect(navigate).toHaveBeenCalledWith("/workbench/projects/project-1/documents");
    const overview = root.root.findAllByType("button").find((item: any) =>
      item.children.includes("Mở tổng quan"),
    );
    act(() => overview.props.onClick());
    expect(navigate).toHaveBeenCalledWith("/workbench/projects/project-1/overview");
    const createRequest = root.root.findAllByType("button").find((item: any) =>
      item.children.includes("Tạo yêu cầu sơ bộ"),
    );
    act(() => createRequest.props.onClick());
    expect(navigate).toHaveBeenCalledWith(APP_ROUTES.preliminaryRequestCreate);
    expect(JSON.stringify(root.toJSON())).not.toContain("Phiên bản 3");
  });

  it("distinguishes initial loading from an empty project list", async () => {
    listProjects.mockImplementation(() => new Promise(() => {}));
    let root: any;
    await act(async () => {
      root = create(React.createElement(ProjectListPage, { onNavigate: vi.fn() }));
    });
    expect(root.root.findAllByProps({ "data-state": "INITIAL_LOADING" })).toHaveLength(1);
    expect(root.root.findAllByProps({ "data-state": "EMPTY_FIRST_USE" })).toHaveLength(0);
  });

  it("shows an error with a real retry that loads projects", async () => {
    listProjects.mockRejectedValueOnce(new Error("network"));
    listProjects.mockResolvedValueOnce([{
      id: "project-1", code: "HS-2026-01", name: "Nhà máy An Phú", description: null,
      status: "draft", row_version: 3,
    }]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(ProjectListPage, { onNavigate: vi.fn() }));
    });
    expect(root.root.findAllByProps({ "data-state": "PAGE_ERROR" })).toHaveLength(1);
    const retry = root.root.findAllByType("button").find((item: any) =>
      item.children.includes("Thử lại"),
    );
    await act(async () => retry.props.onClick());
    expect(listProjects).toHaveBeenCalledTimes(2);
    expect(root.root.findAllByType("strong")[0].children.join("")).toBe("Nhà máy An Phú");
  });

  it("uses a first-use state for a successful empty response", async () => {
    listProjects.mockResolvedValue([]);
    let root: any;
    await act(async () => {
      root = create(React.createElement(ProjectListPage, { onNavigate: vi.fn() }));
    });
    expect(root.root.findAllByProps({ "data-state": "EMPTY_FIRST_USE" })).toHaveLength(1);
    expect(root.root.findAllByProps({ "data-state": "PAGE_ERROR" })).toHaveLength(0);
    expect(JSON.stringify(root.toJSON())).toContain("Tạo yêu cầu sơ bộ để bắt đầu");
    const createRequest = root.root.findAllByType("button").find((item: any) =>
      item.children.includes("Tạo yêu cầu sơ bộ"),
    );
    expect(createRequest).toBeDefined();
  });

  it("verifies a specific code through the read API, beyond the first list page", async () => {
    resolveProjectReference.mockResolvedValue({ project_id: "project-101", matched_by: "code" });
    getProject.mockResolvedValue({
      id: "project-101", code: "SB-2026-001", name: "Nhà máy An Phú", description: null,
      status: "draft", row_version: 1,
    });
    const navigate = vi.fn();
    let root: any;
    await act(async () => {
      root = create(React.createElement(ProjectListPage, {
        onNavigate: navigate, verificationCode: "SB-2026-001",
      }));
    });
    expect(resolveProjectReference).toHaveBeenCalledWith("SB-2026-001");
    expect(getProject).toHaveBeenCalledWith("project-101");
    expect(listProjects).not.toHaveBeenCalled();
    expect(root.root.findAllByType("strong")[0].children.join("")).toBe("Nhà máy An Phú");
    expect(root.root.findByType("header").findByType("span").children.join(""))
      .toBe("Kiểm tra mã hồ sơ SB-2026-001");
  });

  it("shows an honest no-result state and allows another read after a 404", async () => {
    resolveProjectReference.mockRejectedValueOnce(new ApiError("not found", 404));
    resolveProjectReference.mockResolvedValueOnce({ project_id: "project-101", matched_by: "code" });
    getProject.mockResolvedValue({
      id: "project-101", code: "SB-2026-001", name: "Nhà máy An Phú", description: null,
      status: "draft", row_version: 1,
    });
    let root: any;
    await act(async () => {
      root = create(React.createElement(ProjectListPage, {
        onNavigate: vi.fn(), verificationCode: "SB-2026-001",
      }));
    });
    expect(root.root.findAllByProps({ "data-state": "EMPTY_NO_RESULTS" })).toHaveLength(1);
    expect(JSON.stringify(root.toJSON())).toContain("Chưa tìm thấy mã hồ sơ này lúc này");
    const retry = root.root.findAllByType("button").find((item: any) =>
      item.children.includes("Kiểm tra lại"),
    );
    await act(async () => retry.props.onClick());
    expect(resolveProjectReference).toHaveBeenCalledTimes(2);
    expect(root.root.findAllByType("strong")[0].children.join("")).toBe("Nhà máy An Phú");
  });
});
