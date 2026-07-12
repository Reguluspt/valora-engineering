import React, { useState } from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { create, act } from "react-test-renderer";
import { useResolvedProject } from "../useResolvedProject";
import * as projectsApi from "../../../../api/projects";

vi.mock("../../../../api/projects", () => ({ resolveProjectReference: vi.fn() }));

function renderWithRef(initialRef: string | null) {
  let currentRef = { value: initialRef };
  const result = { current: null as any };

  function TestComponent() {
    const [ref, setRef] = useState(initialRef);
    result.current = useResolvedProject(ref);
    (TestComponent as any).setRef = setRef;
    currentRef.value = ref;
    return null;
  }

  let root: any;
  act(() => { root = create(React.createElement(TestComponent)); });

  return {
    result,
    setRef: (newRef: string | null) => {
      act(() => { (TestComponent as any).setRef(newRef); });
    },
    unmount: () => { act(() => { root!.unmount(); }); },
  };
}

describe("useResolvedProject lifecycle", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it("null route — idle, no API request", () => {
    const { result } = renderWithRef(null);
    expect(result.current.state).toBe("idle");
    expect(result.current.projectId).toBeNull();
    expect(projectsApi.resolveProjectReference).not.toHaveBeenCalled();
  });

  it("valid UUID — ready without resolver API call", () => {
    const { result } = renderWithRef("aaaaaaaa-bbbb-4ccc-8ddd-eeee0000ffff");
    expect(result.current.state).toBe("ready");
    expect(result.current.projectId).toBe("aaaaaaaa-bbbb-4ccc-8ddd-eeee0000ffff");
    expect(projectsApi.resolveProjectReference).not.toHaveBeenCalled();
  });

  it("slug invokes resolveProjectReference exactly once", async () => {
    (projectsApi.resolveProjectReference as any).mockResolvedValue({
      project_id: "ur", display_name: "D"
    });
    const { result } = renderWithRef("my-slug");
    expect(result.current.state).toBe("loading");
    expect(projectsApi.resolveProjectReference).toHaveBeenCalledTimes(1);
    expect(projectsApi.resolveProjectReference).toHaveBeenCalledWith("my-slug");
    await vi.waitFor(() => expect(result.current.state).toBe("ready"), { timeout: 2000 });
    expect(result.current.projectId).toBe("ur");
  });

  it("retry invokes a second resolution", async () => {
    (projectsApi.resolveProjectReference as any).mockRejectedValue(new Error("fail"));
    const { result } = renderWithRef("s1");
    await vi.waitFor(() => expect(result.current.state).toBe("error"), { timeout: 2000 });
    const calls = (projectsApi.resolveProjectReference as any).mock.calls.length;
    (projectsApi.resolveProjectReference as any).mockResolvedValue({ project_id: "u2", display_name: "D2" });
    result.current.retry();
    await vi.waitFor(() => expect(projectsApi.resolveProjectReference).toHaveBeenCalledTimes(calls + 1), { timeout: 2000 });
  });

  it("slow A success cannot overwrite B", async () => {
    let ra: (v: any) => void = () => {};
    (projectsApi.resolveProjectReference as any).mockReturnValueOnce(new Promise<any>((r) => { ra = r; }));
    const { result, setRef } = renderWithRef("slug-A");
    expect(result.current.state).toBe("loading");

    (projectsApi.resolveProjectReference as any).mockResolvedValueOnce({ project_id: "u-b", display_name: "B" });
    setRef("slug-B");
    await vi.waitFor(() => expect(result.current.state).toBe("ready"), { timeout: 2000 });
    expect(result.current.projectId).toBe("u-b");

    ra!({ project_id: "stale-a", display_name: "A" });
    await new Promise((r) => setTimeout(r, 50));
    expect(result.current.projectId).toBe("u-b");
  });

  it("slow A rejection cannot overwrite B", async () => {
    let rj: (e: any) => void = () => {};
    (projectsApi.resolveProjectReference as any).mockReturnValueOnce(new Promise<any>((_, r) => { rj = r; }));
    const { result, setRef } = renderWithRef("sxa");
    expect(result.current.state).toBe("loading");

    (projectsApi.resolveProjectReference as any).mockResolvedValueOnce({ project_id: "u-c", display_name: "C" });
    setRef("sxc");
    await vi.waitFor(() => expect(result.current.state).toBe("ready"), { timeout: 2000 });

    rj!(new Error("fail"));
    await new Promise((r) => setTimeout(r, 50));
    expect(result.current.state).toBe("ready");
    expect(result.current.projectId).toBe("u-c");
  });

  it("C-9: unmount blocks late response after cleanup", async () => {
    let ra: (v: any) => void = () => {};
    (projectsApi.resolveProjectReference as any).mockReturnValueOnce(new Promise<any>((r) => { ra = r; }));
    const { result, unmount } = renderWithRef("slug-xx");
    expect(result.current.state).toBe("loading");
    unmount();
    await act(async () => { ra!({ project_id: "late-proj", display_name: "Late" }); });
    expect(result.current.state).toBe("loading");
    expect(result.current.projectId).toBeNull();
  });

  it("malformed UUID fails closed", () => {
    const { result } = renderWithRef("00000000-0000-0000-0000-000000000000");
    expect(result.current.state).toBe("error");
    expect(result.current.error!.title).toBe("Mã hồ sơ không hợp lệ");
    expect(projectsApi.resolveProjectReference).not.toHaveBeenCalled();
  });
});
