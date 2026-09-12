import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchCaseState } from "../caseState";
import { request } from "../client";

vi.mock("../client", () => ({ request: vi.fn() }));

describe("fetchCaseState", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls the accepted project case-state endpoint", async () => {
    const projection = { case_version: "a".repeat(64) };
    vi.mocked(request).mockResolvedValueOnce(projection);

    await expect(fetchCaseState("project-1")).resolves.toBe(projection);
    expect(request).toHaveBeenCalledWith(
      "/api/v1/projects/project-1/case-state",
      { signal: undefined }
    );
  });

  it("propagates projection failures without substituting legacy state", async () => {
    const failure = Object.assign(new Error("projection unavailable"), { status: 500 });
    vi.mocked(request).mockRejectedValueOnce(failure);

    await expect(fetchCaseState("project-1")).rejects.toBe(failure);
  });
});
