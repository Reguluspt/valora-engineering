import { request, ApiError } from "../src/api/client";

describe("Dev Auth API Header Attachment tests", () => {
  let originalFetch: typeof global.fetch;

  beforeAll(() => {
    originalFetch = global.fetch;
  });

  afterAll(() => {
    global.fetch = originalFetch;
  });

  it("attaches X-User-Id in dev mode when enabled", async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: "ok" }),
      headers: new Headers()
    });
    global.fetch = mockFetch as any;

    // Simulate dev mode variables
    const originalMeta = (import.meta as any).env;
    (import.meta as any).env = {
      DEV: true,
      VITE_ENABLE_DEV_AUTH: "true",
      VITE_DEV_USER_ID: "511bcf70-5bfa-4c47-b892-06b2a0e2de70"
    };

    try {
      await request("/test-endpoint");
      expect(mockFetch).toHaveBeenCalled();
      const calledHeaders: Headers = mockFetch.mock.calls[0][1].headers;
      expect(calledHeaders.get("X-User-Id")).toBe("511bcf70-5bfa-4c47-b892-06b2a0e2de70");
    } finally {
      (import.meta as any).env = originalMeta;
    }
  });

  it("does not attach X-User-Id when disabled", async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: "ok" }),
      headers: new Headers()
    });
    global.fetch = mockFetch as any;

    const originalMeta = (import.meta as any).env;
    (import.meta as any).env = {
      DEV: true,
      VITE_ENABLE_DEV_AUTH: "false",
      VITE_DEV_USER_ID: "511bcf70-5bfa-4c47-b892-06b2a0e2de70"
    };

    try {
      await request("/test-endpoint");
      expect(mockFetch).toHaveBeenCalled();
      const calledHeaders: Headers = mockFetch.mock.calls[0][1].headers;
      expect(calledHeaders.get("X-User-Id")).toBeNull();
    } finally {
      (import.meta as any).env = originalMeta;
    }
  });

  it("does not attach X-User-Id in production builds", async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: "ok" }),
      headers: new Headers()
    });
    global.fetch = mockFetch as any;

    const originalMeta = (import.meta as any).env;
    (import.meta as any).env = {
      DEV: false,
      VITE_ENABLE_DEV_AUTH: "true",
      VITE_DEV_USER_ID: "511bcf70-5bfa-4c47-b892-06b2a0e2de70"
    };

    try {
      await request("/test-endpoint");
      expect(mockFetch).toHaveBeenCalled();
      const calledHeaders: Headers = mockFetch.mock.calls[0][1].headers;
      expect(calledHeaders.get("X-User-Id")).toBeNull();
    } finally {
      (import.meta as any).env = originalMeta;
    }
  });
});
