import React from "react";
import { act, create } from "react-test-renderer";
import { describe, expect, it, vi } from "vitest";

import { WorkbenchSessionStatus } from "../WorkbenchSessionStatus";

const baseProps = {
  loading: false,
  error: null,
  rbacError: null,
  conflictError: false,
  sessionId: "session-technical",
  rowVersion: 4,
  lastHeartbeat: "10:30",
  onRetry: vi.fn(),
};

describe("WorkbenchSessionStatus", () => {
  it("renders a lightweight loading message while preserving the shell", () => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<WorkbenchSessionStatus {...baseProps} loading />);
    });

    expect(JSON.stringify(root!.toJSON())).toContain("Đang chuẩn bị phiên làm việc");
    expect(root!.root.findByProps({ role: "status" })).toBeDefined();
  });

  it("defers permission failure to the dedicated RBAC notice", () => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<WorkbenchSessionStatus {...baseProps} rbacError="forbidden" />);
    });

    expect(root!.toJSON()).toBeNull();
  });

  it("defers version conflict to the dedicated conflict notice", () => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<WorkbenchSessionStatus {...baseProps} conflictError />);
    });

    expect(root!.toJSON()).toBeNull();
  });

  it("keeps one retry action for an initialization error", () => {
    const retry = vi.fn();
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(
        <WorkbenchSessionStatus
          {...baseProps}
          error="failed to fetch"
          onRetry={retry}
          sessionId={undefined}
        />,
      );
    });

    const button = root!.root.findByType("button");
    act(() => button.props.onClick());
    expect(button.props.children).toBe("Thử lại kết nối");
    expect(retry).toHaveBeenCalledOnce();
  });

  it("does not hide a session failure when a previous session id remains", () => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<WorkbenchSessionStatus {...baseProps} error="failed to fetch" />);
    });

    expect(JSON.stringify(root!.toJSON())).toContain("Không thể kết nối với máy chủ");
    expect(root!.root.findByType("button").props.children).toBe("Thử lại kết nối");
  });

  it("shows usable session status without technical identifiers", () => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<WorkbenchSessionStatus {...baseProps} />);
    });
    const output = JSON.stringify(root!.toJSON());

    expect(output).toContain("Phiên làm việc đang hoạt động");
    expect(output).toContain("10:30");
    expect(output).not.toContain("session-technical");
    expect(output).not.toContain("row_version");
  });
});
