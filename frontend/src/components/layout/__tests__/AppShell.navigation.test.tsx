import React from "react";
import { act, create, type ReactTestRenderer } from "react-test-renderer";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "../AppShell";

vi.mock("../../../i18n", () => ({ t: (key: string) => key }));
vi.mock("@fluentui/react-components", () => ({
  webLightTheme: {},
  FluentProvider: ({ children, theme, ...props }: any) => React.createElement("div", props, children),
  Button: ({ children, icon, appearance, ...props }: any) => React.createElement("button", props, icon, children),
}));

const account = {
  id: "user-1", email: "operator@example.com", full_name: "Valora Operator",
  organization_id: "org-1", organization_slug: "gia-lai", status: "active",
  roles: ["operator"], permissions: ["project:read", "project:update"],
};
const preferenceKey = "valora.ui.sidebar.compact";
type Query = { matches: boolean; listeners: Set<() => void> };
let viewport: number;
let storage: Map<string, string>;
let queries: Map<string, Query>;
let root: ReactTestRenderer | undefined;

const matches = (query: string) => viewport <= Number(query.match(/max-width:\s*(\d+)/)?.[1]);

beforeEach(() => {
  viewport = 1363;
  storage = new Map();
  queries = new Map();
  vi.stubGlobal("window", {
    localStorage: {
      getItem: vi.fn((key: string) => storage.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => { storage.set(key, value); }),
    },
    matchMedia: vi.fn((query: string) => {
      if (!queries.has(query)) queries.set(query, { matches: matches(query), listeners: new Set() });
      const state = queries.get(query)!;
      return {
        get matches() { return state.matches; },
        addEventListener: (_: string, listener: () => void) => state.listeners.add(listener),
        removeEventListener: (_: string, listener: () => void) => state.listeners.delete(listener),
      };
    }),
  });
});

afterEach(() => {
  act(() => { root?.unmount(); });
  root = undefined;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function renderShell(overrides: Partial<React.ComponentProps<typeof AppShell>> = {}) {
  const props = {
    account, currentPath: "/workbench/projects/example/overview", children: <p>Thông tin hồ sơ hiện tại</p>,
    onNavigate: vi.fn(), onLogout: vi.fn(), ...overrides,
  };
  act(() => { root = create(<AppShell {...props} />); });
  return props;
}

function toggle() {
  return root!.root.findAllByType("button").find((button) => button.props["aria-controls"] === "valora-sidebar")!;
}

function clickToggle() {
  act(() => { toggle().props.onClick(); });
}

function resizeTo(width: number) {
  viewport = width;
  act(() => {
    for (const [query, state] of queries) {
      const next = matches(query);
      if (next !== state.matches) {
        state.matches = next;
        state.listeners.forEach((listener) => listener());
      }
    }
  });
}

describe("AppShell inline navigation", () => {
  it("keeps one named sidebar toggle, all authorized links and logout available when compact", () => {
    const props = renderShell({ supplierSelectionAvailable: true });
    expect(toggle().props["aria-expanded"]).toBe(true);
    expect(root!.root.findAllByType("button").filter((button) => button.props["aria-controls"] === "valora-sidebar")).toHaveLength(1);
    const breadcrumb = root!.root.findAllByType("nav").find((nav) => nav.props["aria-label"] === "Vị trí hiện tại")!;
    expect(breadcrumb.findAllByType("button")).toHaveLength(0);

    clickToggle();
    expect(toggle().props["aria-expanded"]).toBe(false);
    expect(toggle().props["aria-label"]).toBe("Mở rộng điều hướng");
    expect(root!.root.findByType("aside").props.inert).toBeUndefined();
    const links = root!.root.findAllByType("a");
    expect(links.map((link) => link.props["aria-label"])).toEqual([
      "Quản lý yêu cầu sơ bộ", "nav.workbench", "nav.caseOverview", "Không gian tài liệu", "nav.nccSelection",
    ]);
    links.forEach((link) => expect(link.findByType("svg").props["aria-hidden"]).toBe("true"));
    const logout = root!.root.findAllByType("button").find((button) => button.props["aria-label"] === "Đăng xuất tài khoản operator@example.com")!;
    act(() => logout.props.onClick());
    expect(props.onLogout).toHaveBeenCalledOnce();
  });

  it("persists the desktop preference and restores it after visiting the phone layout", () => {
    renderShell();
    clickToggle();
    expect(storage.get(preferenceKey)).toBe("true");
    resizeTo(390);
    clickToggle();
    expect(toggle().props["aria-expanded"]).toBe(true);
    expect(storage.get(preferenceKey)).toBe("true");
    resizeTo(1363);
    expect(toggle().props["aria-expanded"]).toBe(false);
  });

  it("starts phones compact and collapses on route selection without changing a desktop preference", () => {
    viewport = 390;
    storage.set(preferenceKey, "false");
    const props = renderShell();
    expect(toggle().props["aria-expanded"]).toBe(false);
    clickToggle();
    expect(toggle().props["aria-expanded"]).toBe(true);
    const workbench = root!.root.findAllByType("a").find((link) => link.props["aria-label"] === "nav.workbench")!;
    act(() => workbench.props.onClick({ preventDefault: vi.fn() }));
    expect(props.onNavigate).toHaveBeenCalledWith("/workbench/projects/example");
    expect(toggle().props["aria-expanded"]).toBe(false);
    expect(storage.get(preferenceKey)).toBe("false");

    clickToggle();
    act(() => { root!.update(<AppShell {...props} currentPath="/workbench/projects/example/documents" />); });
    expect(toggle().props["aria-expanded"]).toBe(false);
  });

  it("uses a compact tablet default but honors an explicit wider navigation preference", () => {
    renderShell();
    resizeTo(832);
    expect(toggle().props["aria-expanded"]).toBe(false);
    clickToggle();
    resizeTo(1363);
    resizeTo(832);
    expect(toggle().props["aria-expanded"]).toBe(true);
  });

  it("still toggles if preference storage is unavailable", () => {
    vi.mocked(window.localStorage.getItem).mockImplementation(() => { throw new Error("Unavailable storage"); });
    vi.mocked(window.localStorage.setItem).mockImplementation(() => { throw new Error("Unavailable storage"); });
    renderShell();
    expect(() => clickToggle()).not.toThrow();
    expect(toggle().props["aria-expanded"]).toBe(false);
    clickToggle();
    expect(toggle().props["aria-expanded"]).toBe(true);
  });

  it("retains utility actions and removes its media listeners on unmount", () => {
    const recover = vi.fn();
    renderShell({ utilityActions: <button type="button" onClick={recover}>Khôi phục yêu cầu sơ bộ</button> });
    const recovery = root!.root.findAllByType("button").find((button) => button.props.children === "Khôi phục yêu cầu sơ bộ")!;
    act(() => recovery.props.onClick());
    expect(recover).toHaveBeenCalledOnce();
    act(() => { root!.unmount(); });
    root = undefined;
    for (const query of queries.values()) expect(query.listeners.size).toBe(0);
  });
});
