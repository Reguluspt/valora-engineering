import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchProjectAssetLines } from "../assetLines";
import { request } from "../client";

vi.mock("../client", () => ({
  request: vi.fn()
}));

describe("fetchProjectAssetLines production behavior", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each([401, 403, 404, 500])("propagates API status %s without substituting data", async (status) => {
    const failure = Object.assign(new Error("request failed"), { status });
    vi.mocked(request).mockRejectedValueOnce(failure);

    await expect(fetchProjectAssetLines("project-1")).rejects.toBe(failure);
    expect(request).toHaveBeenCalledWith("/api/v1/projects/project-1/asset-lines");
  });
});
