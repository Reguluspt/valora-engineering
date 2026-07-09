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

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${BASE_URL}${normalizedPath}`;

  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  // Attach local development auth headers when in local trials
  const isDev = (import.meta as any).env?.DEV === true;
  const enableDevAuth = (import.meta as any).env?.VITE_ENABLE_DEV_AUTH === "true";
  const devUserId = (import.meta as any).env?.VITE_DEV_USER_ID;

  if (isDev && enableDevAuth && devUserId) {
    headers.set("X-User-Id", devUserId);
  }

  const response = await fetch(url, {
    ...options,
    headers
  }).catch((err) => {
    throw new ApiError(`Network connection error: ${err.message}`, 0);
  });

  if (!response.ok) {
    let errBody: any = null;
    try {
      errBody = await response.json();
    } catch {
      // Ignore parsing errors for non-json
    }

    const message = errBody?.detail || errBody?.message || `HTTP error ${response.status}`;
    const code = errBody?.code;
    throw new ApiError(message, response.status, code, errBody);
  }

  // Handle empty bodies
  if (response.status === 204) {
    return {} as T;
  }

  try {
    return await response.json();
  } catch (err: any) {
    throw new ApiError(`Invalid JSON response: ${err.message}`, response.status);
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
