import { describe, it, expect, vi } from "vitest";
import React from "react";
import { create, act } from "react-test-renderer";
import { AppShell } from "../../layout/AppShell";

vi.mock("../../../i18n", () => ({ t: (k: string) => k }));
vi.mock("@astryxdesign/core/AppShell", () => ({
  AppShell: ({ children, sideNav }: any) => React.createElement("div", null, sideNav, children)
}));
vi.mock("@astryxdesign/core/SideNav", () => ({
  SideNav: ({ children }: any) => React.createElement("div", null, children),
  SideNavItem: ({ label, onClick }: any) =>
    React.createElement("button", { "data-testid": label, onClick }),
  SideNavSection: ({ children }: any) => React.createElement("div", null, children),
}));

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

  it("returns from project Overview to the same project's Workbench", () => {
    const nav = vi.fn();
    let root: any;
    act(() => {
      root = create(
        React.createElement(AppShell, { account, currentPath: "/workbench/projects/hd-98-test/overview", onLogout: vi.fn(), onNavigate: nav, children: null })
      );
    });
    const btn = root!.root.findAllByProps({ "data-testid": "nav.workbench" })[0];
    act(() => { btn.props.onClick(); });
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
    const btn = root!.root.findAllByProps({ "data-testid": "nav.caseOverview" })[0];
    act(() => { btn.props.onClick(); });
    expect(nav).toHaveBeenCalledWith("/workbench/projects/hd-98-test/overview");
  });

  it("navigates to /workbench/projects from a neutral route", () => {
    const nav = vi.fn();
    let root: any;
    act(() => {
      root = create(
        React.createElement(AppShell, { account, currentPath: "/workbench/queue", onLogout: vi.fn(), onNavigate: nav, children: null })
      );
    });
    const btn = root!.root.findAllByProps({ "data-testid": "nav.workbench" })[0];
    act(() => { btn.props.onClick(); });
    expect(nav).toHaveBeenCalledWith("/workbench/projects");
  });

  it("opens OneDrive documents for the current project", () => {
    const nav = vi.fn();
    let root: any;
    act(() => {
      root = create(
        React.createElement(AppShell, { account, currentPath: "/workbench/projects/hd-98-test", onLogout: vi.fn(), onNavigate: nav, children: null })
      );
    });
    const btn = root!.root.findAllByProps({ "data-testid": "Tài liệu OneDrive" })[0];
    act(() => { btn.props.onClick(); });
    expect(nav).toHaveBeenCalledWith("/workbench/projects/hd-98-test/documents");
  });
});
