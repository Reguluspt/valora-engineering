import { request } from "./client";

export interface AccountContext {
  id: string;
  email: string;
  full_name: string;
  organization_id: string;
  organization_slug: string;
  status: string;
  roles: string[];
  permissions: string[];
}

export interface LoginRequest {
  organization_slug: string;
  email: string;
  password: string;
}

export async function getCurrentAccount(): Promise<AccountContext> {
  return request<AccountContext>("/api/v1/auth/me");
}

export async function login(payload: LoginRequest): Promise<AccountContext> {
  await request<{ status: string }>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return getCurrentAccount();
}

export async function logout(): Promise<void> {
  await request<void>("/api/v1/auth/logout", { method: "POST" });
}
