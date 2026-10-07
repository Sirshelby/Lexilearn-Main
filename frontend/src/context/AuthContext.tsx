import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, setAccessToken, setSessionExpiredHandler } from "../lib/api";
import type { AuthResponse, Learner, User } from "../lib/types";

type Status = "loading" | "signed_out" | "signed_in";

interface AuthState {
  status: Status;
  user: User | null;
  learner: Learner | null;
  setActiveLearner: (id: string) => void;
  signIn: (response: AuthResponse) => void;
  signOut: () => Promise<void>;
  replaceLearner: (learner: Learner) => void;
  reloadUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

// Which profile is selected isn't sensitive, so it's fine in localStorage.
const ACTIVE_KEY = "lexilearn.activeLearner";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [activeId, setActiveId] = useState<string | null>(() => localStorage.getItem(ACTIVE_KEY));

  const clear = useCallback(() => {
    setAccessToken(null);
    setUser(null);
    setStatus("signed_out");
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    setSessionExpiredHandler(clear);
    // Try to pick up an existing session from the refresh cookie.
    let cancelled = false;
    (async () => {
      const ok = await api.restoreSession();
      if (!ok) {
        if (!cancelled) setStatus("signed_out");
        return;
      }
      try {
        const me = await api.me();
        if (!cancelled) {
          setUser(me);
          setStatus("signed_in");
        }
      } catch {
        if (!cancelled) setStatus("signed_out");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [clear]);

  const signIn = useCallback((response: AuthResponse) => {
    setAccessToken(response.access_token);
    setUser(response.user);
    setStatus("signed_in");
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      clear();
    }
  }, [clear]);

  const setActiveLearner = useCallback((id: string) => {
    localStorage.setItem(ACTIVE_KEY, id);
    setActiveId(id);
  }, []);

  const replaceLearner = useCallback((learner: Learner) => {
    setUser((current) =>
      current ? { ...current, learners: current.learners.map((l) => (l.id === learner.id ? learner : l)) } : current,
    );
  }, []);

  const reloadUser = useCallback(async () => {
    setUser(await api.me());
  }, []);

  const learner = useMemo(() => {
    if (!user || user.learners.length === 0) return null;
    return user.learners.find((l) => l.id === activeId) ?? user.learners[0] ?? null;
  }, [user, activeId]);

  const value = useMemo(
    () => ({ status, user, learner, setActiveLearner, signIn, signOut, replaceLearner, reloadUser }),
    [status, user, learner, setActiveLearner, signIn, signOut, replaceLearner, reloadUser],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

/** For pages behind ProtectedRoute, where a learner is guaranteed. */
export function useLearner(): Learner {
  const { learner } = useAuth();
  if (!learner) throw new Error("No active learner");
  return learner;
}
