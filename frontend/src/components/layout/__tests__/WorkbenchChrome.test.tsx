import React from "react";
import { act, create } from "react-test-renderer";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WorkbenchFooter } from "../WorkbenchFooter";
import { WorkbenchHeader } from "../WorkbenchHeader";

const client = vi.hoisted(() => ({ checkHealth: vi.fn() }));

vi.mock("../../../api/client", () => ({ checkHealth: client.checkHealth }));

describe("Workbench shared chrome", () => {
  beforeEach(() => {
    client.checkHealth.mockReset();
    client.checkHealth.mockResolvedValue({ status: "healthy" });
  });

  it("shows current project and connection facts without QC affordances", async () => {
    let root: ReturnType<typeof create>;
    await act(async () => {
      root = create(<WorkbenchHeader projectTitle="Hồ sơ GL-01" />);
    });
    const output = JSON.stringify(root!.toJSON());

    expect(output).toContain("Hồ sơ GL-01");
    expect(output).toContain("Đã kết nối máy chủ");
    expect(output).not.toContain("Gửi kiểm soát chất lượng");
    expect(output).not.toContain("Gửi KSCL");
  });

  it("shows an explicit disconnected status when the health check fails", async () => {
    client.checkHealth.mockRejectedValueOnce(new Error("offline"));
    let root: ReturnType<typeof create>;
    await act(async () => {
      root = create(<WorkbenchHeader projectTitle="Hồ sơ GL-01" />);
    });

    expect(JSON.stringify(root!.toJSON())).toContain("Mất kết nối máy chủ");
  });

  it("keeps draft checkpoint facts and removes approval or assignment controls", () => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(
        <WorkbenchFooter
          checkpoint={{ id: "cp-1", status: "dirty", timestamp: "10:20" }}
          draftsCount={2}
          onAutosaveMock={vi.fn()}
        />,
      );
    });
    const output = JSON.stringify(root!.toJSON());

    expect(output).toContain("2 thay đổi chưa lưu");
    expect(output).toContain("Chưa lưu");
    expect(output).toContain("Điểm lưu nháp");
    expect(output).not.toContain("Xem trước phê duyệt");
    expect(output).not.toContain("Phân công");
  });

  it.each([
    ["idle", "Chờ"],
    ["dirty", "Chưa lưu"],
    ["checkpointed", "Đã lưu"],
    ["conflict", "Xung đột"],
  ] as const)("maps the %s checkpoint fact without changing its meaning", (status, label) => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(
        <WorkbenchFooter checkpoint={{ id: "cp-1", status, timestamp: "10:20" }} />,
      );
    });

    expect(JSON.stringify(root!.toJSON())).toContain(label);
  });
});
