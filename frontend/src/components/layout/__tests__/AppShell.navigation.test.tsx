import React from "react";
import { act, create, type ReactTestRenderer } from "react-test-renderer";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "../AppShell";
import { SidebarCollapseContext } from "../SidebarCollapseContext";

vi.mock("../../../i18n", () => ({ t: (key: string) => key }));
vi.mock("@fluentui/react-components", () => ({
  webLightTheme: {},
  useModalAttributes: () => ({ modalAttributes: { "data-testid": "modal-focus-boundary" } }),
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

function renderShell(overrides: Partial<React.ComponentProps<typeof AppShell>> = {}, createNodeMock?: (element: React.ReactElement) => unknown) {
  const props = {
    account, currentPath: "/workbench/projects/example/overview", children: <p>Thông tin hồ sơ hiện tại</p>,
    onNavigate: vi.fn(), onLogout: vi.fn(), ...overrides,
  };
  act(() => { root = create(<AppShell {...props} />, { createNodeMock }); });
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

function renderSwipeShell() {
  viewport = 195;
  let activeElement: MockElement | null = null;
  class MockElement {
    focus = vi.fn(() => { activeElement = this; });
  }
  const source = new MockElement();
  const opener = new MockElement();
  const closer = Object.assign(new MockElement(), { scrollIntoView: vi.fn() });
  const workspace = Object.assign(new MockElement(), {
    contains: (element: MockElement) => element === source,
    getBoundingClientRect: () => ({ top: 54 - window.scrollY }),
  });
  let finishClosing!: () => void;
  const finished = new Promise<void>((resolve) => { finishClosing = resolve; });
  vi.stubGlobal("HTMLElement", MockElement);
  vi.stubGlobal("document", { get activeElement() { return activeElement; } });
  const scrollTo = vi.fn();
  Object.assign(window, { scrollY: 600, scrollTo });
  const props = renderShell({}, (element) => {
    if (element.type === "main") return workspace;
    if (element.type === "aside") return { contains: () => false, getAnimations: () => [{ finished }] };
    const label = (element.props as { "aria-label"?: string })["aria-label"];
    if (label === "Mở điều hướng") return opener;
    if (label === "Đóng điều hướng") return closer;
    return null;
  });
  source.focus();
  source.focus.mockClear();
  const sidebar = () => root!.root.findByType("aside");
  const edge = () => root!.root.findByProps({ className: "sidebar-edge-swipe" });
  const point = (clientX: number, clientY = 120) => ({ pointerType: "touch", pointerId: 7, isPrimary: true, clientX, clientY });
  const swipeOpen = () => {
    const handlers = edge().props;
    act(() => {
      handlers.onPointerDown(point(4));
      handlers.onPointerMove(point(19));
      handlers.onPointerUp(point(54));
    });
  };
  const settle = async () => { await act(async () => finishClosing()); };
  return { props, sidebar, edge, point, swipeOpen, settle, source, opener, closer, scrollTo };
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

  it("collapses on request without persisting it and leaves the manual toggle usable", () => {
    function ExpandTable() {
      const collapse = React.useContext(SidebarCollapseContext);
      return <button onClick={collapse}>Mở rộng bảng</button>;
    }
    storage.set(preferenceKey, "false");
    renderShell({ children: <ExpandTable /> });
    const expand = root!.root.findAllByType("button").find(node => node.props.children === "Mở rộng bảng")!;
    act(() => { expand.props.onClick(); expand.props.onClick(); });
    expect(toggle().props["aria-expanded"]).toBe(false);
    expect(storage.get(preferenceKey)).toBe("false");
    expect(window.localStorage.setItem).not.toHaveBeenCalled();
    clickToggle();
    expect(toggle().props["aria-expanded"]).toBe(true);
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

  it("makes expanded phone navigation modal and restores focus on Escape and backdrop dismissal", () => {
    viewport = 680;
    const focus = vi.fn();
    renderShell({}, (element) => element.props["aria-controls"] === "valora-sidebar" ? { focus } : null);
    const sidebar = () => root!.root.findByType("aside");
    const workspace = () => root!.root.findByProps({ className: "app-workspace" });
    clickToggle();
    expect(sidebar().props).toMatchObject({ role: "dialog", "aria-modal": true, "data-testid": "modal-focus-boundary" });
    expect(workspace().props.inert).toBe(true);
    expect(focus).toHaveBeenCalledOnce();

    const preventDefault = vi.fn();
    act(() => sidebar().props.onKeyDown({
      key: "Escape", target: {}, currentTarget: { contains: () => true }, preventDefault, stopPropagation: vi.fn(),
    }));
    expect(preventDefault).toHaveBeenCalledOnce();
    expect(workspace().props.inert).toBeUndefined();
    expect(focus).toHaveBeenCalledTimes(2);

    clickToggle();
    const scrim = root!.root.findByProps({ className: "sidebar-overlay-scrim" });
    act(() => scrim.props.onClick());
    expect(sidebar().props.role).toBeUndefined();
    expect(toggle().props["aria-expanded"]).toBe(false);
    expect(focus).toHaveBeenCalledTimes(4);

    resizeTo(681);
    clickToggle();
    expect(toggle().props["aria-expanded"]).toBe(true);
    expect(sidebar().props.role).toBeUndefined();
    expect(workspace().props.inert).toBeUndefined();
  });

  it.each([239, 240])("retracts at %i CSS px and restores the prior phone and desktop states", (width) => {
    viewport = 241;
    storage.set(preferenceKey, "false");
    renderShell();
    clickToggle();
    expect(toggle().props["aria-expanded"]).toBe(true);

    resizeTo(width);
    const sidebar = root!.root.findByType("aside");
    const opener = root!.root.findByProps({ className: "sidebar-toggle sidebar-open-trigger", type: "button" });
    expect(sidebar.props.inert).toBe(true);
    expect(opener.props["aria-label"]).toBe("Mở điều hướng");
    expect(opener.props["aria-expanded"]).toBe(false);
    act(() => opener.props.onClick());
    expect(sidebar.props.inert).toBeUndefined();
    expect(toggle().props["aria-label"]).toBe("Đóng điều hướng");
    expect(toggle().props["aria-expanded"]).toBe(true);
    clickToggle();
    expect(sidebar.props.inert).toBe(true);

    resizeTo(241);
    expect(sidebar.props.inert).toBeUndefined();
    expect(toggle().props["aria-expanded"]).toBe(true);
    expect(toggle().props["aria-label"]).toBe("Thu gọn điều hướng");
    resizeTo(1363);
    expect(toggle().props["aria-expanded"]).toBe(true);
    expect(storage.get(preferenceKey)).toBe("false");
    expect(window.localStorage.setItem).not.toHaveBeenCalled();
  });

  it("closes extreme navigation after choosing a route and starts retracted on reentry", () => {
    viewport = 240;
    const props = renderShell();
    const open = () => {
      const opener = root!.root.findAllByType("button").find((button) => button.props["aria-label"] === "Mở điều hướng")!;
      act(() => opener.props.onClick());
    };
    open();
    const link = root!.root.findAllByType("a").find((anchor) => anchor.props["aria-label"] === "nav.workbench")!;
    act(() => link.props.onClick({ preventDefault: vi.fn() }));
    expect(props.onNavigate).toHaveBeenCalledWith("/workbench/projects/example");
    expect(root!.root.findByType("aside").props.inert).toBe(true);
    open();
    act(() => { root!.update(<AppShell {...props} currentPath="/workbench/projects/example/documents" />); });
    expect(root!.root.findByType("aside").props.inert).toBe(true);
    open();
    resizeTo(241);
    resizeTo(240);
    expect(root!.root.findByType("aside").props.inert).toBe(true);
  });

  it.each(["Escape", "button"])("restores the swipe source and document position after closing with %s", async (method) => {
    const shell = renderSwipeShell();
    shell.swipeOpen();
    expect(shell.sidebar().props.inert).toBeUndefined();
    expect(shell.closer.focus).toHaveBeenCalledWith({ preventScroll: true });
    expect(shell.closer.scrollIntoView).toHaveBeenCalledOnce();
    Object.assign(window, { scrollY: 0 });
    if (method === "Escape") {
      const target = {};
      act(() => shell.sidebar().props.onKeyDown({
        key: "Escape", target, currentTarget: { contains: (node: unknown) => node === target }, stopPropagation: vi.fn(),
      }));
    } else {
      clickToggle();
    }
    expect(shell.sidebar().props.inert).toBe(true);
    expect(shell.scrollTo).not.toHaveBeenCalled();
    expect(shell.source.focus).not.toHaveBeenCalled();
    await shell.settle();
    expect(shell.source.focus).toHaveBeenCalledWith({ preventScroll: true });
    expect(shell.scrollTo).toHaveBeenCalledWith({ top: 600, behavior: "instant" });
  });

  it("returns focus to the opener after a button activation", () => {
    const shell = renderSwipeShell();
    const opener = root!.root.findByProps({ className: "sidebar-toggle sidebar-open-trigger", type: "button" });
    act(() => opener.props.onClick());
    expect(shell.closer.focus).toHaveBeenCalledWith();
    clickToggle();
    expect(shell.opener.focus).toHaveBeenCalledWith({ preventScroll: true });
    expect(shell.scrollTo).not.toHaveBeenCalled();
  });

  it("accepts swipes from the edge and clears pointer state on cancel, vertical motion and breakpoint exit", () => {
    const shell = renderSwipeShell();
    expect(shell.sidebar().props.onPointerDown).toBeUndefined();
    const handlers = shell.edge().props;
    act(() => {
      handlers.onPointerDown(shell.point(4));
      handlers.onPointerMove(shell.point(19));
      handlers.onPointerCancel(shell.point(19));
      handlers.onPointerUp(shell.point(54));
      handlers.onPointerDown(shell.point(4));
      handlers.onPointerMove(shell.point(5, 150));
      handlers.onPointerUp(shell.point(54));
    });
    expect(shell.sidebar().props.inert).toBe(true);
    act(() => {
      handlers.onPointerDown(shell.point(4));
      handlers.onPointerMove(shell.point(19));
    });
    resizeTo(241);
    resizeTo(195);
    act(() => shell.edge().props.onPointerUp(shell.point(54)));
    expect(shell.sidebar().props.inert).toBe(true);
    shell.swipeOpen();
    expect(shell.sidebar().props.inert).toBeUndefined();
  });

  it.each(["resize", "unmount", "route change"])("discards pending restoration on %s", async (interruption) => {
    const shell = renderSwipeShell();
    shell.swipeOpen();
    clickToggle();
    if (interruption === "resize") resizeTo(241);
    if (interruption === "unmount") {
      act(() => root!.unmount());
      root = undefined;
    }
    if (interruption === "route change") {
      act(() => { root!.update(<AppShell {...shell.props} currentPath="/workbench/projects/example/documents" />); });
    }
    await shell.settle();
    expect(shell.scrollTo).not.toHaveBeenCalled();
    expect(shell.source.focus).not.toHaveBeenCalled();
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
