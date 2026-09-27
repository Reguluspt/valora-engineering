import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { ApiError } from "../api/client";
import {
  AccountContext,
  getCurrentAccount,
  login as loginRequest,
  LoginRequest,
  logout as logoutRequest,
} from "../api/auth";

type SessionStatus = "loading" | "authenticated" | "unauthenticated" | "error";

interface SessionContextValue {
  account: AccountContext | null;
  status: SessionStatus;
  error: string | null;
  login: (payload: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  restore: () => Promise<void>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

function errorMessage(error: unknown): string {
  if (error instanceof ApiError && typeof error.message === "string") return error.message;
  return "Không thể kết nối với máy chủ. Vui lòng thử lại.";
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [account, setAccount] = useState<AccountContext | null>(null);
  const [status, setStatus] = useState<SessionStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  const restore = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const current = await getCurrentAccount();
      setAccount(current);
      setStatus("authenticated");
    } catch (cause) {
      setAccount(null);
      if (cause instanceof ApiError && cause.status === 401) {
        setStatus("unauthenticated");
      } else {
        setError(errorMessage(cause));
        setStatus("error");
      }
    }
  }, []);

  useEffect(() => {
    void restore();
  }, [restore]);

  const login = useCallback(async (payload: LoginRequest) => {
    setStatus("loading");
    setError(null);
    try {
      const current = await loginRequest(payload);
      setAccount(current);
      setStatus("authenticated");
    } catch (cause) {
      setAccount(null);
      setError(errorMessage(cause));
      setStatus("unauthenticated");
      throw cause;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } catch {
      // The server may already have invalidated the session; local access still ends now.
    } finally {
      setAccount(null);
      setError(null);
      setStatus("unauthenticated");
    }
  }, []);

  const value = useMemo(
    () => ({ account, status, error, login, logout, restore }),
    [account, status, error, login, logout, restore],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used within SessionProvider");
  return value;
}
