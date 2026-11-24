import React, { useState } from "react";
import { act, create } from "react-test-renderer";
import { afterEach, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ session: {} as any, page: vi.fn() }));
vi.mock("../auth/SessionProvider", () => ({ SessionProvider: ({ children }: any) => children, useSession: () => mocks.session }));
vi.mock("../components/layout/AppShell", () => ({ AppShell: ({ children, utilityActions }: any) => <main>{utilityActions}{children}</main> }));
vi.mock("../components/case-overview/useStageNavigation", () => ({ useStageNavigation: () => false }));
vi.mock("../components/precase/PreliminaryRequestCreatePage", () => ({ PreliminaryRequestCreatePage: (props: any) => { mocks.page(props); return <p>Create</p>; } }));
vi.mock("react-dom", async (importOriginal) => ({
  ...await importOriginal<typeof import("react-dom")>(),
  createPortal: (children: React.ReactNode) => children,
}));
vi.mock("../components/precase/PreliminaryAnalysisPage", () => ({
  analysisOwner: (account: { session_incarnation: string }) => account?.session_incarnation ?? null,
  clearLegacyAnalysisStorage: vi.fn(),
  PreliminaryAnalysisPage: ({ projectRef, active, onDirtyChange, onOwnerLost }: any) => {
    const [value, setValue] = useState("");
    return <section data-project={projectRef} hidden={!active}>
      <input value={value} onChange={(event) => {
        setValue(event.target.value);
        onDirtyChange(projectRef, true);
      }} />
      <button onClick={onOwnerLost}>Lose owner</button>
    </section>;
  },
}));
import { APP_ROUTES, projectPreliminaryAnalysisPath } from "../contracts/valoraV23";
import { App, AuthenticatedApp } from "../App";

afterEach(() => vi.unstubAllGlobals());

it("A26 App supplies authenticated actor/tenant scope and keeps recovery reachable", async () => {
  mocks.session = { account: { id: crypto.randomUUID(), organization_id: crypto.randomUUID(), permissions: ["project:create"] }, logout: vi.fn(), restore: vi.fn() };
  vi.stubGlobal("window", { location: { hash: `#${APP_ROUTES.preliminaryRequestCreate}` }, addEventListener: vi.fn(), removeEventListener: vi.fn() });
  let root: any;
  await act(async () => { root = create(<AuthenticatedApp />); });
  expect(mocks.page.mock.calls[0][0].scope).toEqual({ organization_id: mocks.session.account.organization_id, actor_user_id: mocks.session.account.id });
  expect(JSON.stringify(root.toJSON())).toContain("Khôi phục yêu cầu sơ bộ");
  await act(async () => root.unmount());
});

it("follows both history events and preserves only the dirty editors until individually discarded", async () => {
  const projectA = projectPreliminaryAnalysisPath("A");
  const projectB = projectPreliminaryAnalysisPath("B");
  const routeC = APP_ROUTES.preliminaryRequestCreate;
  const location = { hash: `#${projectA}` };
  const handlers = new Map<string, () => void>();
  const pushState = vi.fn((_state, _title, hash) => { location.hash = hash; });
  vi.stubGlobal("window", {
    location, history: { pushState },
    addEventListener: (type: string, handler: () => void) => { handlers.set(type, handler); },
    removeEventListener: (type: string) => { handlers.delete(type); },
  });
  const focus = vi.fn();
  class FocusTarget { focus = focus; }
  vi.stubGlobal("HTMLElement", FocusTarget);
  vi.stubGlobal("document", { createElement: () => ({ remove: vi.fn() }), activeElement: new FocusTarget() });
  mocks.session = {
    status: "authenticated",
    account: { id: "user", organization_id: "org", session_incarnation: "session-1", permissions: ["project:create"] },
    logout: vi.fn(), restore: vi.fn(),
  };

  let root!: ReturnType<typeof create>;
  await act(async () => { root = create(<App />); });
  const travel = async (path: string, ...events: string[]) => {
    await act(async () => {
      location.hash = `#${path}`;
      for (const event of events) handlers.get(event)!();
    });
  };
  const editor = (project: string) => root.root.findByProps({ "data-project": project });
  const value = (project: string) => editor(project).findByType("input").props.value;
  const edit = (project: string, price: string) => {
    act(() => editor(project).findByType("input").props.onChange({ target: { value: price } }));
  };
  const click = (label: string, node = root.root) => {
    act(() => node.findAllByType("button").find((button) => button.children.includes(label))!.props.onClick());
  };
  const recovery = (project: string) => root.root.findByProps({ "aria-label": `Bản nháp phân tích hồ sơ ${project}` });

  edit("A", "9876543");
  click("Khôi phục yêu cầu sơ bộ");
  click("Ở lại chỉnh sửa");
  expect(focus).toHaveBeenCalledTimes(1);
  expect(location.hash).toBe(`#${projectA}`);
  expect(value("A")).toBe("9876543");
  expect(pushState).not.toHaveBeenCalled();

  await travel(projectB, "popstate", "hashchange");
  expect(editor("A").props.hidden).toBe(true);
  expect(editor("B").props.hidden).toBe(false);
  expect(value("B")).toBe("");
  recovery("A");
  edit("B", "456");
  await travel(projectA, "hashchange");
  expect(value("A")).toBe("9876543");
  expect(editor("B").props.hidden).toBe(true);
  await travel(projectB, "popstate");
  expect(value("B")).toBe("456");
  expect(pushState).not.toHaveBeenCalled();

  click("Bỏ bản nháp", recovery("A"));
  expect(root.root.findAllByProps({ "data-project": "A" })).toHaveLength(0);
  expect(value("B")).toBe("456");
  click("Khôi phục yêu cầu sơ bộ");
  click("Rời đi và bỏ thay đổi");
  expect(pushState).toHaveBeenCalledExactlyOnceWith(null, "", `#${routeC}`);
  expect(root.root.findAllByProps({ "data-project": "B" })).toHaveLength(0);

  await travel(projectA, "popstate");
  expect(value("A")).toBe("");
  edit("A", "9876543");
  await travel(projectB, "hashchange");
  click("Lose owner", editor("B"));
  expect(root.root.findAllByProps({ "data-project": "A" })).toHaveLength(0);
  edit("B", "456");
  await travel(projectA, "popstate", "hashchange");
  recovery("B");
  mocks.session.account = { ...mocks.session.account, session_incarnation: "session-2" };
  await act(async () => root.update(<App />));
  expect(root.root.findAllByProps({ "data-project": "B" })).toHaveLength(0);
  expect(value("A")).toBe("");
  await act(async () => root.unmount());
});
