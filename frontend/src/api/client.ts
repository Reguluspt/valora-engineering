export class ApiError extends Error {
  status: number;
  code?: string;
  detail?: any;

  constructor(message: string, status: number, code?: string, detail?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

const BASE_URL = ((import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  if (match) return match[2];
  return null;
}

// Global promise to deduplicate concurrent refresh requests
let refreshPromise: Promise<any> | null = null;

export async function request<T>(path: string, options: RequestInit = {}, isRetry = false): Promise<T> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${BASE_URL}${normalizedPath}`;

  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  // Enforce synchronizer CSRF token in state-mutating requests
  const csrfToken = getCookie("XSRF-TOKEN");
  if (csrfToken && ["POST", "PUT", "PATCH", "DELETE"].includes(options.method || "GET")) {
    headers.set("X-CSRF-Token", csrfToken);
  }

  const fetchOptions: RequestInit = {
    ...options,
    headers,
    credentials: "include" // Always send and accept secure cookies
  };

  try {
    const response = await fetch(url, fetchOptions);

    if (response.status === 401 && !isRetry && path !== "/api/v1/auth/refresh" && path !== "/api/v1/auth/login") {
      // Access token expired, attempt refresh
      try {
        if (!refreshPromise) {
          refreshPromise = request("/api/v1/auth/refresh", { method: "POST" }, true)
            .finally(() => {
              refreshPromise = null;
            });
        }
        await refreshPromise;
      } catch (refreshErr) {
        // Refresh failed, clear frontend auth state/redirect
        if (typeof localStorage !== "undefined") {
          // Clear any local storage/session tokens if any (do not call logout without CSRF)
          localStorage.removeItem("user");
        }
        throw new ApiError("Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.", 401);
      }
      // A failure after refresh belongs to the retried request, especially for mutations.
      return await request<T>(path, options, true);
    }

    if (!response.ok) {
      let errBody: any = null;
      try {
        errBody = await response.json();
      } catch {
        // Ignore parsing errors
      }

      // Security: ensure cookies/secrets are never included in ApiError
      const message = errBody?.detail?.message
        || errBody?.detail?.detail
        || (typeof errBody?.detail === "string" ? errBody.detail : null)
        || errBody?.message
        || `HTTP error ${response.status}`;
      const code = errBody?.code || errBody?.detail?.code || errBody?.detail?.error_code;
      throw new ApiError(message, response.status, code, errBody);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(`Không thể kết nối mạng: ${err.message}`, 0);
  }
}

export async function requestBlob(path: string, isRetry = false): Promise<Blob> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  try {
    const response = await fetch(`${BASE_URL}${normalizedPath}`, { credentials: "include" });
    if (response.status === 401 && !isRetry) {
      await request("/api/v1/auth/refresh", { method: "POST" }, true);
      return requestBlob(path, true);
    }
    if (!response.ok) {
      let detail: any = null;
      try { detail = await response.json(); } catch { /* The server may return no JSON. */ }
      throw new ApiError(
        detail?.detail?.detail || (typeof detail?.detail === "string" ? detail.detail : null) || `HTTP error ${response.status}`,
        response.status,
        detail?.detail?.error_code,
        detail,
      );
    }
    return await response.blob();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError("Không thể tải tệp kết quả sơ bộ.", 0);
  }
}

export interface HealthResponse {
  status: string;
  database?: string;
}

export async function checkHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function getOpenApiSpec(): Promise<any> {
  return request<any>("/openapi.json");
}

export * from "./assetLines";
export * from "./projects";
export * from "./auth";
export * from "./m365";
