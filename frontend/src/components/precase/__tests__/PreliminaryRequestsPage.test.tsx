import React from "react";
import { act, create } from "react-test-renderer";
import { beforeEach, describe, expect, it, vi } from "vitest";

const listPreliminaryRequests = vi.hoisted(() => vi.fn());
vi.mock("../../../api/preliminaryIntake", () => ({ listPreliminaryRequests }));

import { ApiError } from "../../../api/client";
import { projectPreliminaryIntakePath } from "../../../contracts/valoraV23";
import { PreliminaryRequestsPage } from "../PreliminaryRequestsPage";

describe("PreliminaryRequestsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  async function mount() {
    const onNavigate = vi.fn();
    const onSessionExpired = vi.fn();
    let root: any;
    await act(async () => {
      root = create(React.createElement(PreliminaryRequestsPage, { onNavigate, onSessionExpired }));
    });
    return { root, onNavigate, onSessionExpired };
  }

  it("shows server-projected rows and opens the project intake route without reading Project.status", async () => {
    listPreliminaryRequests.mockResolvedValue({
      page: 1, page_size: 25, total: 2,
      items: [
        { project_id: "p-1", code: "SB-1", name: "Yêu cầu một", customer_id: null,
          current_batch_id: null, has_retained_batches: true,
          current_source_artifact_id: null, current_source_state: null },
        { project_id: "p-2", code: "SB-2", name: "Yêu cầu hai", customer_id: "c-1",
          current_batch_id: "b-2", has_retained_batches: true,
          current_source_artifact_id: "s-2", current_source_state: "available" },
      ],
    });
    const { root, onNavigate } = await mount();
    const text = JSON.stringify(root.toJSON());
    expect(text).toContain("Chưa xác định batch hiện hành");
    expect(text).toContain("Tệp nguồn sẵn sàng");
    expect(text).toContain("Chưa gắn");
    expect(text).toContain("Đã gắn");
    const open = root.root.findAllByType("button").filter((button: any) => button.children.includes("Mở nhập liệu"));
    act(() => open[0].props.onClick());
    expect(onNavigate).toHaveBeenCalledWith(projectPreliminaryIntakePath("p-1"));
    expect(listPreliminaryRequests).toHaveBeenCalledWith(1);
  });

  it("shows first-use guidance from an authoritative empty result", async () => {
    listPreliminaryRequests.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25 });
    const { root } = await mount();
    expect(JSON.stringify(root.toJSON())).toContain("Chưa có yêu cầu sơ bộ");
  });

  it("presents permission and session failures", async () => {
    listPreliminaryRequests.mockRejectedValueOnce(new ApiError("forbidden", 403));
    const forbidden = await mount();
    expect(JSON.stringify(forbidden.root.toJSON())).toContain("Chưa có quyền xem yêu cầu sơ bộ");
    listPreliminaryRequests.mockRejectedValueOnce(new ApiError("expired", 401));
    const expired = await mount();
    expect(JSON.stringify(expired.root.toJSON())).toContain("Phiên làm việc đã hết hạn");
    const login = expired.root.root.findAllByType("button").find((button: any) => button.children.includes("Đăng nhập lại"));
    act(() => login.props.onClick());
    expect(expired.onSessionExpired).toHaveBeenCalledTimes(1);
  });
});
