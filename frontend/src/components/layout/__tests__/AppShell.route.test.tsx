import { describe, it, expect, vi } from "vitest";
import React from "react";
import { create, act } from "react-test-renderer";
import { AppShell } from "../../layout/AppShell";

vi.mock("../../../i18n", () => ({ t: (k: string) => k }));
vi.mock("@astryxdesign/core/AppShell", () => ({
  AppShell: ({ children }: any) => React.createElement("div", null, children)
}));
vi.mock("@astryxdesign/core/SideNav", () => ({
  SideNav: ({ children }: any) => React.createElement("div", null, children),
  SideNavItem: ({ label, onClick }: any) =>
    React.createElement("button", { "data-testid": label, onClick }),
  SideNavSection: ({ children }: any) => React.createElement("div", null, children),
}));

describe("AppShell routing", () => {
  it("returns from project Overview to the same project's Workbench", () => {
    const nav = vi.fn();
    let root: any;
    act(() => {
      root = create(
        React.createElement(AppShell, { currentPath: "/workbench/projects/hd-98-test/overview", onNavigate: nav, children: null })
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
        React.createElement(AppShell, { currentPath: "/workbench/projects/hd-98-test", onNavigate: nav, children: null })
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
        React.createElement(AppShell, { currentPath: "/workbench/queue", onNavigate: nav, children: null })
      );
    });
    const btn = root!.root.findAllByProps({ "data-testid": "nav.workbench" })[0];
    act(() => { btn.props.onClick(); });
    expect(nav).toHaveBeenCalledWith("/workbench/projects");
  });
});
