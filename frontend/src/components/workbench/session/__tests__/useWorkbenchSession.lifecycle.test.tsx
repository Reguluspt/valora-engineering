import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { create, act } from "react-test-renderer";
import { useWorkbenchSession } from "../useWorkbenchSession";
import { isValidProjectUuid } from "../../validators";
import * as api from "../../../../api/workbenchSession";

vi.mock("../../../../api/workbenchSession", () => ({
  createSession: vi.fn(),
  sendHeartbeat: vi.fn().mockResolvedValue({ id: "hb", row_version: 2 }),
}));

const PROJ_A = "aaaaaaaa-bbbb-4ccc-8ddd-eeee11111111";
const PROJ_B = "aaaaaaaa-bbbb-4ccc-8ddd-eeee22222222";
const PROJ_C = "aaaaaaaa-bbbb-4ccc-8ddd-eeee33333333";
const INVALID = "00000000-0000-0000-0000-000000000000";

describe("useWorkbenchSession lifecycle", () => {
  beforeEach(() => { vi.clearAllMocks(); });
  afterEach(() => { vi.useRealTimers(); });

  it("PROJ_A, PROJ_B, PROJ_C are valid UUIDs", () => {
    expect(isValidProjectUuid(PROJ_A)).toBe(true);
    expect(isValidProjectUuid(PROJ_B)).toBe(true);
    expect(isValidProjectUuid(PROJ_C)).toBe(true);
  });

  function render(initialId: string) {
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

  it("valid project UUID calls createSession", () => {
    (api.createSession as any).mockResolvedValue({ id: "s1", row_version: 1 });
    render(PROJ_A);
    expect(api.createSession).toHaveBeenCalledWith({ project_id: PROJ_A });
  });

  it("invalid project ID sends no request", () => {
    render(INVALID);
    expect(api.createSession).not.toHaveBeenCalled();
  });

  it("A-to-invalid does not call createSession again", () => {
    (api.createSession as any).mockResolvedValue({ id: "s-a", row_version: 1 });
    const { switchTo } = render(PROJ_A);
    (api.createSession as any).mockClear();
    switchTo(INVALID);
    expect(api.createSession).not.toHaveBeenCalled();
  });

  it("C-2: stale A response cannot overwrite B", async () => {
    let resolveA: (v: any) => void = () => {};
    (api.createSession as any).mockReturnValueOnce(new Promise<any>((r) => { resolveA = r; }));
    const { result, switchTo } = render(PROJ_A);
    expect(api.createSession).toHaveBeenCalledTimes(1);
    (api.createSession as any).mockResolvedValueOnce({ id: "session-b", row_version: 1 });
    switchTo(PROJ_B);
    await act(async () => {});
    expect(result.current.session?.id).toBe("session-b");
    resolveA!({ id: "session-a-stale", row_version: 1 });
    await act(async () => {});
    expect(result.current.session?.id).toBe("session-b");
  });

  it("C-3: A-to-invalid ignores stale A response", async () => {
    let resolveA: (v: any) => void = () => {};
    (api.createSession as any).mockReturnValueOnce(new Promise<any>((r) => { resolveA = r; }));
    const { result, switchTo } = render(PROJ_A);
    expect(api.createSession).toHaveBeenCalledTimes(1);
    switchTo(INVALID);
    (api.createSession as any).mockClear();
    expect(api.createSession).not.toHaveBeenCalled();
    expect(result.current.session).toBeNull();
    resolveA!({ id: "stale-a", row_version: 1 });
    await act(async () => {});
    expect(result.current.session).toBeNull();
  });

  it("C-4: immediate clearing with established session A", async () => {
    (api.createSession as any).mockResolvedValue({ id: "session-a", row_version: 1 });
    const { result, switchTo } = render(PROJ_A);
    await act(async () => {});
    expect(result.current.session?.id).toBe("session-a");
    let resolveB: (v: any) => void = () => {};
    (api.createSession as any).mockReturnValueOnce(new Promise<any>((r) => { resolveB = r; }));
    switchTo(PROJ_B);
    expect(result.current.session).toBeNull();
    expect(result.current.loading).toBe(true);
    resolveB!({ id: "session-b-final", row_version: 1 });
    await act(async () => {});
    expect(result.current.session?.id).toBe("session-b-final");
  });

  it("C-5: heartbeat interval cleanup on project change", async () => {
    vi.useFakeTimers();
    (api.createSession as any).mockResolvedValue({ id: "s-a", row_version: 1 });
    const { result, switchTo } = render(PROJ_A);
    await act(async () => {});
    act(() => { vi.advanceTimersByTime(15000); });
    expect(api.sendHeartbeat).toHaveBeenCalledTimes(1);
    (api.createSession as any).mockResolvedValueOnce({ id: "s-b", row_version: 1 });
    switchTo(PROJ_B);
    await act(async () => {});
    (api.sendHeartbeat as any).mockClear();
    act(() => { vi.advanceTimersByTime(15000); });
    expect(api.sendHeartbeat).toHaveBeenCalledTimes(1);
  });

  it("C-6: stale heartbeat response cannot update newer session", async () => {
    vi.useFakeTimers();
    (api.createSession as any).mockResolvedValue({ id: "session-a", row_version: 1 });
    let resolveHb: (v: any) => void = () => {};
    (api.sendHeartbeat as any).mockImplementation(() => new Promise<any>((r) => { resolveHb = r; }));
    const { result, switchTo } = render(PROJ_A);
    await act(async () => {});
    act(() => { vi.advanceTimersByTime(15000); });
    expect(api.sendHeartbeat).toHaveBeenCalledTimes(1);
    (api.sendHeartbeat as any).mockResolvedValue({ id: "s-b-hb", row_version: 2 });
    (api.createSession as any).mockResolvedValueOnce({ id: "session-b", row_version: 1 });
    switchTo(PROJ_B);
    await act(async () => {});
    resolveHb!({ id: "stale-hb-a", row_version: 99 });
    await act(async () => {});
    expect(result.current.session?.id).toBe("session-b");
    expect(result.current.session?.row_version).toBe(1);
  });

  it("C-7: unmount heartbeat cleanup", async () => {
    vi.useFakeTimers();
    (api.createSession as any).mockResolvedValue({ id: "session-a", row_version: 1 });
    let resolveHb: (v: any) => void = () => {};
    (api.sendHeartbeat as any).mockImplementation(() => new Promise<any>((r) => { resolveHb = r; }));
    const { result, unmount } = render(PROJ_A);
    await act(async () => {});
    (api.sendHeartbeat as any).mockClear();
    unmount();
    act(() => { vi.advanceTimersByTime(60000); });
    expect(api.sendHeartbeat).not.toHaveBeenCalled();
    await act(async () => { resolveHb!({ id: "post-unmount", row_version: 1 }); });
  });
});
