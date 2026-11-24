import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

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
  const authGeneration = useRef(0);
  const mutationPending = useRef(false);

  const restore = useCallback(async () => {
    if (mutationPending.current) return;
    const generation = ++authGeneration.current;
    setStatus("loading");
    setError(null);
    try {
      const current = await getCurrentAccount();
      if (generation !== authGeneration.current) return;
      setAccount(current);
      setStatus("authenticated");
    } catch (cause) {
      if (generation !== authGeneration.current) return;
      if (cause instanceof ApiError && (cause.status === 401 || cause.status === 403)) {
        setAccount(null);
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
    if (mutationPending.current) return;
    const generation = ++authGeneration.current;
    mutationPending.current = true;
    setAccount(null);
    setStatus("loading");
    setError(null);
    try {
      const current = await loginRequest(payload);
      if (generation !== authGeneration.current) return;
      setAccount(current);
      setStatus("authenticated");
    } catch (cause) {
      if (generation !== authGeneration.current) return;
      setAccount(null);
      setError(errorMessage(cause));
      setStatus("unauthenticated");
      throw cause;
    } finally {
      if (generation === authGeneration.current) mutationPending.current = false;
    }
  }, []);

  const logout = useCallback(async () => {
    if (mutationPending.current) return;
    ++authGeneration.current;
    mutationPending.current = true;
    setAccount(null);
    setError(null);
    setStatus("unauthenticated");
    try {
      await logoutRequest();
    } catch {
      // Local access ends even when the server cannot acknowledge logout.
    } finally {
      mutationPending.current = false;
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
