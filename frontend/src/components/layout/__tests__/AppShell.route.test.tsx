import { describe, it, expect, vi } from "vitest";
import React from "react";
import { create, act } from "react-test-renderer";
import { AppShell } from "../../layout/AppShell";

vi.mock("../../../i18n", () => ({ t: (k: string) => k }));

describe("AppShell routing", () => {
  const account = {
    id: "user-1",
    email: "operator@example.com",
    full_name: "Valora Operator",
    organization_id: "org-1",
    organization_slug: "gia-lai",
    status: "active",
    roles: ["operator"],
    permissions: ["project:read", "project:update"],
  };

  const findLink = (root: any, label: string) =>
    root.root.findAllByType("a").find((link: any) => link.props.children === label);

  it("renders named semantic navigation with hash links and aria-current", () => {
    let root: any;
    act(() => {
      root = create(
        React.createElement(AppShell, { account, currentPath: "/workbench/projects/hd-98-test/overview", onLogout: vi.fn(), onNavigate: vi.fn(), children: null })
      );
    });

    expect(root!.root.findByType("nav").props["aria-label"]).toBe("Điều hướng chính");
    expect(root!.root.findByType("main").props["aria-label"]).toBe("Nội dung chính");
    expect(findLink(root!, "nav.caseOverview").props["aria-current"]).toBe("page");
    expect(findLink(root!, "nav.workbench").props["aria-current"]).toBeUndefined();
    expect(root!.root.findAllByType("a").every((link: any) => link.props.href.startsWith("#/"))).toBe(true);
  });

  it("returns from project Overview to the same project's Workbench", () => {
    const nav = vi.fn();
    let root: any;
    act(() => {
      root = create(
        React.createElement(AppShell, { account, currentPath: "/workbench/projects/hd-98-test/overview", onLogout: vi.fn(), onNavigate: nav, children: null })
      );
    });
    const link = findLink(root!, "nav.workbench");
    act(() => { link.props.onClick({ preventDefault: vi.fn() }); });
    expect(nav).toHaveBeenCalledWith("/workbench/projects/hd-98-test");
  });

  it("opens Overview while preserving the current project reference", () => {
    const nav = vi.fn();
    let root: any;
    act(() => {
      root = create(
        React.createElement(AppShell, { account, currentPath: "/workbench/projects/hd-98-test", onLogout: vi.fn(), onNavigate: nav, children: null })
      );
    });
    const link = findLink(root!, "nav.caseOverview");
    act(() => { link.props.onClick({ preventDefault: vi.fn() }); });
    expect(nav).toHaveBeenCalledWith("/workbench/projects/hd-98-test/overview");
  });

  it("navigates to /workbench/projects from a neutral route", () => {
    const nav = vi.fn();
    let root: any;
    act(() => {
      root = create(
        React.createElement(AppShell, { account, currentPath: "/missing", onLogout: vi.fn(), onNavigate: nav, children: null })
      );
    });
    const link = findLink(root!, "nav.workbench");
    act(() => { link.props.onClick({ preventDefault: vi.fn() }); });
    expect(nav).toHaveBeenCalledWith("/workbench/projects");
  });

  it("opens the provider-neutral document workspace for the current project", () => {
    const nav = vi.fn();
    let root: any;
    act(() => {
      root = create(
        React.createElement(AppShell, { account, currentPath: "/workbench/projects/hd-98-test", onLogout: vi.fn(), onNavigate: nav, children: null })
      );
    });
    const link = findLink(root!, "Không gian tài liệu");
    act(() => { link.props.onClick({ preventDefault: vi.fn() }); });
    expect(nav).toHaveBeenCalledWith("/workbench/projects/hd-98-test/documents");
  });

  it("opens NCC Selection while preserving the current project reference", () => {
    const nav = vi.fn();
    let root: any;
    act(() => {
      root = create(
        React.createElement(AppShell, { account, currentPath: "/workbench/projects/hd-98-test", onLogout: vi.fn(), onNavigate: nav, children: null })
      );
    });
    const link = findLink(root!, "nav.nccSelection");
    act(() => { link.props.onClick({ preventDefault: vi.fn() }); });
    expect(nav).toHaveBeenCalledWith("/workbench/projects/hd-98-test/ncc-selection");
  });

  it("does not render legacy global review or validation navigation", () => {
    let root: any;
    act(() => {
      root = create(
        React.createElement(AppShell, { account, currentPath: "/workbench/projects/hd-98-test", onLogout: vi.fn(), onNavigate: vi.fn(), children: null })
      );
    });

    const labels = root!.root.findAllByType("a").map((link: any) => link.props.children);
    expect(labels).not.toContain("review.queue");
    expect(labels).not.toContain("review.submitQc");
    expect(labels).not.toContain("nav.validate");
    expect(labels).not.toContain("nav.errorDashboard");
    expect(labels).not.toContain("nav.submitReview");
  });

  it("keeps an accessible logout action", () => {
    const logout = vi.fn();
    let root: any;
    act(() => {
      root = create(
        React.createElement(AppShell, { account, currentPath: "/workbench/projects", onLogout: logout, onNavigate: vi.fn(), children: null })
      );
    });

    const button = root!.root.findByProps({ "aria-label": "Đăng xuất tài khoản operator@example.com" });
    act(() => { button.props.onClick(); });
    expect(logout).toHaveBeenCalledOnce();
  });
});
