import React from "react";
import { act, create } from "react-test-renderer";
import { beforeEach, describe, expect, it, vi } from "vitest";

const listProjects = vi.hoisted(() => vi.fn());
vi.mock("../../../api/projects", () => ({ listProjects }));

import { ProjectListPage } from "../ProjectListPage";

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

    expect(root.root.findByType("h2").children.join("")).toBe("Nhà máy An Phú");
    const button = root.root.findAllByType("button").find((item: any) =>
      item.children.includes("Không gian tài liệu"),
    );
    act(() => button.props.onClick());
    expect(navigate).toHaveBeenCalledWith("/workbench/projects/project-1/documents");
  });
});
