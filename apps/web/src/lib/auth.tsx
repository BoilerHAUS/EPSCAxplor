"use client";

/**
 * Auth context for the EPSCAxplor frontend.
 *
 * The access JWT lives in memory only (inside apiClient) — never
 * localStorage. Sessions survive page loads via the httpOnly refresh
 * cookie: on mount the provider attempts a silent refresh, and while
 * authenticated it schedules the next refresh shortly before the
 * access token's expires_in elapses.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { apiClient } from "./api-client";

/** Refresh this many seconds before the access token expires. */
const REFRESH_MARGIN_SECONDS = 60;
/** Never schedule a refresh sooner than this, to avoid tight loops. */
const MIN_REFRESH_DELAY_SECONDS = 10;

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthContextValue {
  status: AuthStatus;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // clearTimeout can't cancel a refresh that is already in flight when the
  // provider unmounts; this flag stops its continuation from setting state
  // or scheduling an orphaned timer.
  const disposedRef = useRef(false);

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimerRef.current !== null) {
      clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
  }, []);

  const scheduleRefresh = useCallback(
    (expiresInSeconds: number) => {
      clearRefreshTimer();
      const delaySeconds = Math.max(
        expiresInSeconds - REFRESH_MARGIN_SECONDS,
        MIN_REFRESH_DELAY_SECONDS,
      );
      refreshTimerRef.current = setTimeout(() => {
        void apiClient
          .refresh()
          .then((tokens) => {
            if (!disposedRef.current) scheduleRefresh(tokens.expires_in);
          })
          .catch(() => {
            if (!disposedRef.current) setStatus("unauthenticated");
          });
      }, delaySeconds * 1000);
    },
    [clearRefreshTimer],
  );

  useEffect(() => {
    disposedRef.current = false;
    apiClient
      .refresh()
      .then((tokens) => {
        if (disposedRef.current) return;
        setStatus("authenticated");
        scheduleRefresh(tokens.expires_in);
      })
      .catch(() => {
        if (!disposedRef.current) setStatus("unauthenticated");
      });
    return () => {
      disposedRef.current = true;
      clearRefreshTimer();
    };
  }, [scheduleRefresh, clearRefreshTimer]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await apiClient.login(email, password);
      setStatus("authenticated");
      scheduleRefresh(tokens.expires_in);
    },
    [scheduleRefresh],
  );

  const logout = useCallback(async () => {
    clearRefreshTimer();
    try {
      await apiClient.logout();
    } finally {
      setStatus("unauthenticated");
    }
  }, [clearRefreshTimer]);

  return <AuthContext.Provider value={{ status, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
