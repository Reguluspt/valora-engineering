import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { create, act } from "react-test-renderer";
import { useWorkbenchSession } from "../useWorkbenchSession";
import * as api from "../../../../api/workbenchSession";

vi.mock("../../../../api/workbenchSession", () => ({
  createSession: vi.fn(),
  sendHeartbeat: vi.fn().mockResolvedValue({ id: "hb", row_version: 2 }),
}));

function renderSession(initialId: string) {
  const result = { current: null as any };
  function TestComponent({ pid }: { pid: string }) {
    result.current = useWorkbenchSession(pid);
    return null;
  }
  let root: any;
  act(() => { root = create(React.createElement(TestComponent, { pid: initialId })); });
  return {
    result,
    switchTo: (newId: string) => {
      act(() => { root!.update(React.createElement(TestComponent, { pid: newId })); });
    },
    unmount: () => { act(() => { root!.unmount(); }); },
  };
}

describe("useWorkbenchSession lifecycle", () => {
  beforeEach(() => { vi.clearAllMocks(); });
  afterEach(() => { vi.useRealTimers(); });

  it("valid project UUID calls createSession", () => {
    (api.createSession as any).mockResolvedValue({ id: "s1", row_version: 1 });
    renderSession("aaaaaaaa-bbbb-4ccc-8ddd-eeee0000ffff");
    expect(api.createSession).toHaveBeenCalledWith({ project_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeee0000ffff" });
  });

  it("invalid project ID sends no request", () => {
    renderSession("00000000-0000-0000-0000-000000000000");
    expect(api.createSession).not.toHaveBeenCalled();
  });

  it("A-to-B: Session B is requested after switch", () => {
    (api.createSession as any).mockResolvedValue({ id: "s-a", row_version: 1 });
    const { switchTo } = renderSession("aaaaaaaa-bbbb-4ccc-8ddd-eeeeAAAABBBB");
    expect(api.createSession).toHaveBeenCalledTimes(1);
    (api.createSession as any).mockResolvedValueOnce({ id: "s-b", row_version: 1 });
    switchTo("aaaaaaaa-bbbb-4ccc-8ddd-eeeeCCCCDDDD");
    expect(api.createSession).toHaveBeenCalledTimes(2);
  });

  it("A-to-invalid does not call createSession again", () => {
    (api.createSession as any).mockResolvedValue({ id: "s-a", row_version: 1 });
    const { switchTo } = renderSession("aaaaaaaa-bbbb-4ccc-8ddd-eeeeEEEEFFFF");
    (api.createSession as any).mockClear();
    switchTo("00000000-0000-0000-0000-000000000000");
    expect(api.createSession).not.toHaveBeenCalled();
  });

  it("switchTo invalid clears session state immediately", () => {
    (api.createSession as any).mockResolvedValue({ id: "s-a", row_version: 1 });
    const { result, switchTo } = renderSession("aaaaaaaa-bbbb-4ccc-8ddd-eeeeGGGGHHHH");
    switchTo("00000000-0000-0000-0000-000000000000");
    expect(result.current.session).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it("switchTo project B clears session immediately", () => {
    (api.createSession as any).mockResolvedValue({ id: "s-a", row_version: 1 });
    const { result, switchTo } = renderSession("aaaaaaaa-bbbb-4ccc-8ddd-eeeeIIIJJJJ");
    switchTo("aaaaaaaa-bbbb-4ccc-8ddd-eeeeKKKKLLLL");
    expect(result.current.session).toBeNull();
  });
});
