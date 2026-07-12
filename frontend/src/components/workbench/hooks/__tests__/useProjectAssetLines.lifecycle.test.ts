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

  it("project A switches to B — rows reset", async () => {
    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("aaa")], total: 1, limit: 50, offset: 0 });
    const { result, switchTo } = renderPages("uuid-aaa-bbbb-4ccc-8ddd-eeeeAAAA");
    await vi.waitFor(() => expect(result.current.loading).toBe(false));

    (api.fetchProjectAssetLines as any).mockResolvedValueOnce({ items: [mk("bbb")], total: 1, limit: 50, offset: 0 });
    switchTo("uuid-aaa-bbbb-4ccc-8ddd-eeeeBBBB");
    await vi.waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.rows[0].project_asset_line_id).toBe("bbb");
  });

  it("hasMore false when consumed reaches total", async () => {
    (api.fetchProjectAssetLines as any).mockResolvedValue({ items: [mk("x")], total: 1, limit: 50, offset: 0 });
    const { result } = renderPages("uuid-aaa-bbbb-4ccc-8ddd-eeeeFIN");
    await vi.waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.hasMore).toBe(false);
  });
});
