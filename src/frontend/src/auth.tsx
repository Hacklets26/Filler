import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getToken, setToken, API_BASE, type Developer } from "./api";

interface Auth {
  me: Developer | null; ready: boolean;
  signIn: (token: string) => Promise<void>; signOut: () => void; setMe: (d: Developer) => void;
  loginUrl: string;
}
// The auth context is the single source of truth for the current developer session and login state.
const Ctx = createContext<Auth | null>(null);
export const useAuth = (): Auth => { const c = useContext(Ctx); if (!c) throw new Error("AuthProvider missing"); return c; };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Developer | null>(null);
  const [ready, setReady] = useState(false);

  const signOut = useCallback(() => { setToken(null); setMe(null); }, []);
  const signIn = useCallback(async (token: string) => { setToken(token); setMe(await api<Developer>("/me")); }, []);

  useEffect(() => {
    // Bootstrap the session once, then listen for forced logout events from the API layer.
    (async () => {
      if (getToken()) { try { setMe(await api<Developer>("/me")); } catch { setToken(null); } }
      setReady(true);
    })();
    window.addEventListener("PATCHWORK:unauthorized", signOut);
    return () => window.removeEventListener("PATCHWORK:unauthorized", signOut);
  }, [signOut]);

  return <Ctx.Provider value={{ me, ready, signIn, signOut, setMe, loginUrl: `${API_BASE}/auth/github/login` }}>{children}</Ctx.Provider>;
}
