import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { create, act } from "react-test-renderer";
import { useProjectAssetLines } from "../useProjectAssetLines";
import * as api from "../../../../api/assetLines";

vi.mock("../../../../api/assetLines", () => ({ fetchProjectAssetLines: vi.fn() }));

const mk = (id: string) => ({
  id, project_id: "p", asset_name: "A", description: null, quantity: 1,
  unit_id: null, raw_price: null, raw_price_currency_id: null,
  appraised_unit_price: 100, appraised_currency_id: null,
  review_status: "raw", validation_status: "valid",
  brand_id: null, manufacturer_id: null, version_token: "1",
});

function renderPages(initialId: string) {
  const result = { current: null as any };
  function TestComponent({ pid }: { pid: string }) {
    result.current = useProjectAssetLines(pid);
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

describe("useProjectAssetLines lifecycle", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it("initial request uses limit 50 and offset 0", async () => {
    (api.fetchProjectAssetLines as any).mockResolvedValue({ items: [mk("a1")], total: 1, limit: 50, offset: 0 });
    renderPages("uuid-aaa-bbbb-4ccc-8ddd-eeee11111111");
    await vi.waitFor(() => {
      expect(api.fetchProjectAssetLines).toHaveBeenCalledWith(
        "uuid-aaa-bbbb-4ccc-8ddd-eeee11111111", { limit: 50, offset: 0 }
      );
    });
  });

  it("loadMore uses consumed offset", async () => {
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("a1")], total: 55, limit: 50, offset: 0 });
    const { result } = renderPages("uuid-aaa-bbbb-4ccc-8ddd-eeeeP1");
    await vi.waitFor(() => expect(result.current.loading).toBe(false));
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("a2")], total: 55, limit: 50, offset: 1 });
    result.current.loadMore();
    await vi.waitFor(() => {
      expect(api.fetchProjectAssetLines).toHaveBeenLastCalledWith(
        "uuid-aaa-bbbb-4ccc-8ddd-eeeeP1", { limit: 50, offset: 1 }
      );
    });
  });

  it("duplicates within page zero removed", async () => {
    (api.fetchProjectAssetLines as any).mockResolvedValue({ items: [mk("d"), mk("d"), mk("u")], total: 3, limit: 50, offset: 0 });
    const { result } = renderPages("uuid-aaa-bbbb-4ccc-8ddd-eeeeDED");
    await vi.waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.rows.length).toBe(2);
  });

  it("duplicates within a later page removed", async () => {
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("a"), mk("b")], total: 5, limit: 2, offset: 0 });
    const { result } = renderPages("uuid-aaa-bbbb-4ccc-8ddd-eeeeLDP1");
    await vi.waitFor(() => expect(result.current.loading).toBe(false));
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("c"), mk("c"), mk("d")], total: 5, limit: 3, offset: 2 });
    result.current.loadMore();
    await vi.waitFor(() => expect(result.current.loadingMore).toBe(false));
    expect(result.current.rows.length).toBe(4);
  });

  it("cross-page dedup: repeated ID from page one removed in page two", async () => {
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("x"), mk("y")], total: 4, limit: 2, offset: 0 });
    const { result } = renderPages("uuid-aaa-bbbb-4ccc-8ddd-eeeeXDP1");
    await vi.waitFor(() => expect(result.current.loading).toBe(false));
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("y"), mk("z")], total: 4, limit: 2, offset: 2 });
    result.current.loadMore();
    await vi.waitFor(() => expect(result.current.loadingMore).toBe(false));
    expect(result.current.rows.length).toBe(3);
  });

  it("consumed offset uses raw response length despite dedup", async () => {
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("dup"), mk("dup"), mk("uniq")], total: 50, limit: 3, offset: 0 });
    const { result } = renderPages("uuid-aaa-bbbb-4ccc-8ddd-eeeeRAWOF");
    await vi.waitFor(() => expect(result.current.loading).toBe(false));
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("z")], total: 50, limit: 3, offset: 3 });
    result.current.loadMore();
    await vi.waitFor(() => {
      expect(api.fetchProjectAssetLines).toHaveBeenLastCalledWith(
        "uuid-aaa-bbbb-4ccc-8ddd-eeeeRAWOF", { limit: 50, offset: 3 }
      );
    });
  });

  it("line_no uses raw API page offset", async () => {
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("a"), mk("b")], total: 4, limit: 2, offset: 0 });
    const { result } = renderPages("uuid-aaa-bbbb-4ccc-8ddd-eeeeLINE");
    await vi.waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.rows[0].line_no).toBe(1);
    expect(result.current.rows[1].line_no).toBe(2);
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("c")], total: 4, limit: 2, offset: 2 });
    result.current.loadMore();
    await vi.waitFor(() => expect(result.current.loadingMore).toBe(false));
    expect(result.current.rows[2].line_no).toBe(3);
  });

  it("hasMore false blocks further loadMore attempts", async () => {
    (api.fetchProjectAssetLines as any).mockResolvedValue({ items: [mk("only")], total: 1, limit: 50, offset: 0 });
    const { result } = renderPages("uuid-aaa-bbbb-4ccc-8ddd-eeeeFULL");
    await vi.waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.hasMore).toBe(false);
    const callCount = (api.fetchProjectAssetLines as any).mock.calls.length;
    result.current.loadMore();
    expect((api.fetchProjectAssetLines as any).mock.calls.length).toBe(callCount);
  });

  it("project A switches to B — rows reset", async () => {
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("aaa")], total: 1, limit: 50, offset: 0 });
    const { result, switchTo } = renderPages("uuid-aaa-bbbb-4ccc-8ddd-eeeeAAAA");
    await vi.waitFor(() => expect(result.current.loading).toBe(false));
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("bbb")], total: 1, limit: 50, offset: 0 });
    switchTo("uuid-aaa-bbbb-4ccc-8ddd-eeeeBBBB");
    await vi.waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.rows[0].project_asset_line_id).toBe("bbb");
  });

  it("immediate reset on A-to-B before B resolves", async () => {
    let ra: (v: any) => void = () => {};
    (api.fetchProjectAssetLines as any).mockReturnValueOnce(new Promise<any>((r) => { ra = r; }));
    const { result, switchTo } = renderPages("uuid-aaa-bbbb-4ccc-8ddd-eeeeIMR1");
    await vi.waitFor(() => expect(api.fetchProjectAssetLines).toHaveBeenCalledTimes(1));
    let rb: (v: any) => void = () => {};
    (api.fetchProjectAssetLines as any).mockReturnValueOnce(new Promise<any>((r) => { rb = r; }));
    switchTo("uuid-aaa-bbbb-4ccc-8ddd-eeeeIMR2");
    expect(result.current.rows).toEqual([]);
    expect(result.current.totalCount).toBe(0);
    expect(result.current.hasMore).toBe(false);
    expect(result.current.loading).toBe(true);
    rb!({ items: [mk("bbb")], total: 1, limit: 50, offset: 0 });
    await vi.waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.rows[0].project_asset_line_id).toBe("bbb");
    ra!({ items: [mk("stale")], total: 5, limit: 50, offset: 0 });
    await new Promise((r) => setTimeout(r, 50));
    expect(result.current.rows[0].project_asset_line_id).toBe("bbb");
  });

  it("retry clears state and requests page zero", async () => {
    (api.fetchProjectAssetLines as any).mockRejectedValueOnce(new Error("fail"));
    const { result } = renderPages("uuid-aaa-bbbb-4ccc-8ddd-eeeeRETRY");
    await vi.waitFor(() => {
      expect(result.current.errorMsg).toContain("fail");
    });
    (api.fetchProjectAssetLines as any).mockClear();
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("r1"), mk("r2")], total: 2, limit: 50, offset: 0 });
    result.current.retry();
    expect(result.current.loading).toBe(true);
    expect(result.current.rows).toEqual([]);
    expect(result.current.totalCount).toBe(0);
    expect(result.current.hasMore).toBe(false);
    expect(result.current.errorMsg).toBeNull();
    await vi.waitFor(() => {
      expect(api.fetchProjectAssetLines).toHaveBeenCalledWith(
        "uuid-aaa-bbbb-4ccc-8ddd-eeeeRETRY", { limit: 50, offset: 0 }
      );
    });
  });

  it("C-8: concurrent loadMore produces exactly one API request", async () => {
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("a1"), mk("a2")], total: 55, limit: 2, offset: 0 });
    const { result } = renderPages("aaaaaaaa-bbbb-4ccc-8ddd-eeeeCONC01");
    await vi.waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.hasMore).toBe(true);

    let resolveP2: (v: any) => void = () => {};
    (api.fetchProjectAssetLines as any).mockReturnValueOnce(new Promise<any>((r) => { resolveP2 = r; }));
    act(() => { result.current.loadMore(); });
    act(() => { result.current.loadMore(); });
    expect(api.fetchProjectAssetLines).toHaveBeenCalledTimes(2);
    resolveP2!({ items: [mk("a3")], total: 55, limit: 2, offset: 2 });
    await act(async () => {});
    expect(result.current.loadingMore).toBe(false);
    expect(result.current.rows.length).toBe(3);
  });
});
