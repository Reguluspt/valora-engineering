import React, { useState } from "react";
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

  it("valid project UUID is sent to createSession", async () => {
    (api.createSession as any).mockResolvedValue({ id: "s1", row_version: 1 });
    const { result } = renderSession("aaaaaaaa-bbbb-4ccc-8ddd-eeee0000ffff");
    await vi.waitFor(() => expect(api.createSession).toHaveBeenCalledWith({
      project_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeee0000ffff"
    }));
    expect(result.current.session?.id).toBe("s1");
  });

  it("invalid project ID sends no request", () => {
    renderSession("00000000-0000-0000-0000-000000000000");
    expect(api.createSession).not.toHaveBeenCalled();
  });

  it("A-to-B clears A and ignores delayed A response", async () => {
    let ra: (v: any) => void = () => {};
    (api.createSession as any).mockReturnValueOnce(new Promise<any>((r) => { ra = r; }));
    const { result, switchTo } = renderSession("aaaaaaaa-bbbb-4ccc-8ddd-eeeeAAAABBBB");

    (api.createSession as any).mockResolvedValueOnce({ id: "s-b", row_version: 1 });
    switchTo("aaaaaaaa-bbbb-4ccc-8ddd-eeeeCCCCDDDD");
    await vi.waitFor(() => expect(api.createSession).toHaveBeenCalledTimes(2));

    ra!({ id: "stale-a", row_version: 1 });
    await new Promise((r) => setTimeout(r, 50));
    expect(result.current.session?.id).toBe("s-b");
  });
});
