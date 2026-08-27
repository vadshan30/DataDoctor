import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import * as authApi from "../api/auth";
import type { AuthResponse } from "../types/api";

interface AuthContextValue {
  session: AuthResponse | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, fullName: string) => Promise<void>;
  signInAsGuest: () => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthResponse | null>(() => {
    const saved = localStorage.getItem("datadoctor_session");
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(false);

  const saveSession = (next: AuthResponse) => {
    localStorage.setItem("datadoctor_token", next.access_token);
    localStorage.setItem("datadoctor_session", JSON.stringify(next));
    setSession(next);
  };
  const signIn = async (email: string, password: string) => { setLoading(true); try { saveSession(await authApi.login(email, password)); } finally { setLoading(false); } };
  const signUp = async (email: string, password: string, fullName: string) => { setLoading(true); try { await authApi.register(email, password, fullName); saveSession(await authApi.login(email, password)); } finally { setLoading(false); } };
  const signInAsGuest = async () => { setLoading(true); try { saveSession(await authApi.guest()); } finally { setLoading(false); } };
  const signOut = () => { localStorage.removeItem("datadoctor_token"); localStorage.removeItem("datadoctor_session"); setSession(null); };

  useEffect(() => { const handler = () => signOut(); window.addEventListener("datadoctor:unauthorized", handler); return () => window.removeEventListener("datadoctor:unauthorized", handler); }, []);
  return <AuthContext.Provider value={{ session, loading, signIn, signUp, signOut, signInAsGuest }}>{children}</AuthContext.Provider>;
}

export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error("useAuth must be used inside AuthProvider"); return value; }
