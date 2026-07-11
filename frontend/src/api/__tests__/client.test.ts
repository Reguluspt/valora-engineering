import { request, ApiError } from "../client";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

describe("Central API Client Tests", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.stubGlobal("document", {
      cookie: ""
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("attaches CSRF header to state-mutating requests when cookie is present", async () => {
    document.cookie = "XSRF-TOKEN=test_csrf_token_value";
    
    const mockResponse = {
      status: 200,
      ok: true,
      json: async () => ({ success: true })
    };
    (fetch as any).mockResolvedValueOnce(mockResponse);

    await request("/api/v1/projects", { method: "POST", body: JSON.stringify({ name: "Valora" }) });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/projects"),
      expect.objectContaining({
        headers: expect.any(Headers),
        method: "POST"
      })
    );

    const calledHeaders = (fetch as any).mock.calls[0][1].headers;
    expect(calledHeaders.get("X-CSRF-Token")).toBe("test_csrf_token_value");
  });

  it("does not attach CSRF header to safe GET requests even if cookie is present", async () => {
    document.cookie = "XSRF-TOKEN=test_csrf_token_value";
    
    const mockResponse = {
      status: 200,
      ok: true,
      json: async () => ({ success: true })
    };
    (fetch as any).mockResolvedValueOnce(mockResponse);

    await request("/api/v1/projects", { method: "GET" });

    const calledHeaders = (fetch as any).mock.calls[0][1].headers;
    expect(calledHeaders.get("X-CSRF-Token")).toBeNull();
  });

  it("attempts to refresh token on 401 and retries original request exactly once", async () => {
    const mockResponse401 = {
      status: 401,
      ok: false,
      json: async () => ({ message: "Unauthorized" })
    };
    const mockResponseRefresh = {
      status: 200,
      ok: true,
      json: async () => ({ status: "ok" })
    };
    const mockResponseSuccess = {
      status: 200,
      ok: true,
      json: async () => ({ data: "success" })
    };

    (fetch as any)
      .mockResolvedValueOnce(mockResponse401) // 1st attempt: fails with 401
      .mockResolvedValueOnce(mockResponseRefresh) // refresh call: succeeds
      .mockResolvedValueOnce(mockResponseSuccess); // 2nd attempt: succeeds

    const result = await request("/api/v1/projects/1");
    expect(result).toEqual({ data: "success" });
    expect(fetch).toHaveBeenCalledTimes(3);
  });

  it("deduplicates concurrent 401 refresh calls into a single flight", async () => {
    const mockResponse401 = {
      status: 401,
      ok: false,
      json: async () => ({ message: "Unauthorized" })
    };
    const mockResponseRefresh = {
      status: 200,
      ok: true,
      json: async () => ({ status: "ok" })
    };
    const mockResponseSuccess = {
      status: 200,
      ok: true,
      json: async () => ({ data: "success" })
    };

    (fetch as any)
      .mockResolvedValueOnce(mockResponse401) // call 1 fails
      .mockResolvedValueOnce(mockResponse401) // call 2 fails
      .mockResolvedValueOnce(mockResponseRefresh) // single refresh flight
      .mockResolvedValueOnce(mockResponseSuccess) // call 1 retry succeeds
      .mockResolvedValueOnce(mockResponseSuccess); // call 2 retry succeeds

    const [res1, res2] = await Promise.all([
      request("/api/v1/projects/1"),
      request("/api/v1/projects/2")
    ]);

    expect(res1).toEqual({ data: "success" });
    expect(res2).toEqual({ data: "success" });
    
    // Total fetches: 2 (initial) + 1 (refresh) + 2 (retries) = 5
    expect(fetch).toHaveBeenCalledTimes(5);
  });

  it("does not attempt refresh on 403 CSRF error", async () => {
    const mockResponse403 = {
      status: 403,
      ok: false,
      json: async () => ({ detail: { code: "CSRF_ERROR", message: "CSRF invalid" } })
    };
    (fetch as any).mockResolvedValueOnce(mockResponse403);

    await expect(request("/api/v1/projects", { method: "POST" })).rejects.toThrow(ApiError);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("throws after one retry to prevent infinite loops", async () => {
    const mockResponse401 = {
      status: 401,
      ok: false,
      json: async () => ({ message: "Unauthorized" })
    };
    const mockResponseRefresh = {
      status: 200,
      ok: true,
      json: async () => ({ status: "ok" })
    };

    (fetch as any)
      .mockResolvedValueOnce(mockResponse401) // 1st attempt: 401
      .mockResolvedValueOnce(mockResponseRefresh) // refresh: 200
      .mockResolvedValueOnce(mockResponse401); // 2nd attempt: still 401

    await expect(request("/api/v1/projects/1")).rejects.toThrow(ApiError);
    expect(fetch).toHaveBeenCalledTimes(3);
  });

  it("clears state and redirects on refresh failure without looping", async () => {
    const mockResponse401 = {
      status: 401,
      ok: false,
      json: async () => ({ message: "Unauthorized" })
    };
    const mockResponseRefreshFail = {
      status: 401,
      ok: false,
      json: async () => ({ message: "Refresh expired" })
    };

    (fetch as any)
      .mockResolvedValueOnce(mockResponse401)
      .mockResolvedValueOnce(mockResponseRefreshFail);

    vi.stubGlobal("localStorage", {
      removeItem: vi.fn()
    });

    await expect(request("/api/v1/projects/1")).rejects.toThrow(ApiError);
    expect(localStorage.removeItem).toHaveBeenCalledWith("user");
  });
});
