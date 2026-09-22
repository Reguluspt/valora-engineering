import React from "react";
import { act, create } from "react-test-renderer";
import { describe, expect, it, vi } from "vitest";

import { ApiErrorBanner } from "../ApiErrorBanner";
import { ConflictWarning } from "../ConflictWarning";
import { EmptyState } from "../EmptyState";
import { ErrorState } from "../ErrorState";
import { LoadingState } from "../LoadingState";
import { RbacLockNotice } from "../RbacLockNotice";
import { StatusBadge } from "../StatusBadge";

describe("shared cross-product states", () => {
  it("uses Vietnamese no-results defaults", () => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<EmptyState />);
    });

    expect(root!.root.findByProps({ "data-state": "EMPTY_NO_RESULTS" })).toBeDefined();
    expect(JSON.stringify(root!.toJSON())).toContain("Không tìm thấy dữ liệu phù hợp");
    expect(JSON.stringify(root!.toJSON())).not.toContain("No Data Found");
  });

  it.each([
    ["first-use", "EMPTY_FIRST_USE", "Chưa có dữ liệu"],
    ["not-applicable", "EMPTY_NOT_APPLICABLE", "Nội dung không áp dụng"],
    ["completed", "EMPTY_COMPLETED", "Đã hoàn tất"],
  ] as const)("renders the %s empty distinction", (kind, state, copy) => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<EmptyState kind={kind} />);
    });

    expect(root!.root.findByProps({ "data-state": state })).toBeDefined();
    expect(JSON.stringify(root!.toJSON())).toContain(copy);
    if (kind === "completed") {
      expect(root!.root.findByProps({ className: "valora-message valora-message--success" })).toBeDefined();
    }
  });

  it("uses scoped Vietnamese loading without fake progress", () => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<LoadingState scope="section" />);
    });
    const output = JSON.stringify(root!.toJSON());

    expect(root!.root.findByProps({ "data-state": "SECTION_LOADING" })).toBeDefined();
    expect(output).toContain("Đang cập nhật mục này");
    expect(output).not.toContain("Loading...");
    expect(output).not.toMatch(/\d+%/);
  });

  it("uses the canonical initial-loading state by default", () => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<LoadingState />);
    });

    expect(root!.root.findByProps({ "data-state": "INITIAL_LOADING" })).toBeDefined();
    expect(JSON.stringify(root!.toJSON())).toContain("Đang tải nội dung");
  });

  it("offers one scope-appropriate retry action for errors", () => {
    const retry = vi.fn();
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<ErrorState onRetry={retry} scope="section" />);
    });

    const button = root!.root.findByType("button");
    act(() => button.props.onClick());
    expect(root!.root.findByProps({ "data-state": "SECTION_ERROR" })).toBeDefined();
    expect(root!.root.findByProps({ className: "valora-message valora-message--error" })).toBeDefined();
    expect(button.props.children).toBe("Thử lại");
    expect(retry).toHaveBeenCalledOnce();
  });

  it("presents version conflict inline without technical headline or modal", () => {
    const resolve = vi.fn();
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<ConflictWarning onResolve={resolve} />);
    });
    const output = JSON.stringify(root!.toJSON());
    const button = root!.root.findByType("button");

    expect(root!.root.findByProps({ role: "alert" })).toBeDefined();
    expect(output).toContain("Dữ liệu đã thay đổi");
    expect(output).not.toContain("Stale Row Collision");
    expect(output).not.toContain("409");
    expect(button.props.children).toBe("Cập nhật dữ liệu");
  });

  it("keeps permission state distinct from empty state", () => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<RbacLockNotice permission="workbench:edit" />);
    });
    const output = JSON.stringify(root!.toJSON());

    expect(output).toContain("Tài khoản chưa được cấp quyền");
    expect(output).not.toContain("Chưa có dữ liệu");
    expect(output).not.toContain("workbench:edit");
  });

  it("gives the icon-only dismiss action an accessible name", () => {
    const dismiss = vi.fn();
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<ApiErrorBanner message="failed to fetch" onDismiss={dismiss} />);
    });

    const button = root!.root.findByProps({ "aria-label": "Đóng thông báo" });
    act(() => button.props.onClick());
    expect(dismiss).toHaveBeenCalledOnce();
  });

  it("uses semantic status classes while retaining a text label", () => {
    let root: ReturnType<typeof create>;
    act(() => {
      root = create(<StatusBadge label="Cần cập nhật" status="warning" />);
    });

    const badge = root!.root.findByType("span");
    expect(badge.props.className).toContain("valora-status--warning");
    expect(badge.props.children).toBe("Cần cập nhật");
  });
});
