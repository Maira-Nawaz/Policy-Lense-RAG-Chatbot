"use client";

import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import type { Session, User } from "@supabase/supabase-js";

import { supabase } from "./supabaseClient";

interface AuthContextValue {
  session: Session | null;
  user: User | null;
  loading: boolean;
}

const AuthContext = createContext<AuthContextValue>({ session: null, user: null, loading: true });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    // Initial check on load -- getSession() reads the persisted session (from
    // localStorage) without a network round trip in the common case. The
    // .catch() matters: without it, a rejected promise (bad env var, network
    // hiccup) would leave `loading` stuck true forever with no error shown --
    // RequireAuth would then show its loading state indefinitely.
    supabase.auth
      .getSession()
      .then(({ data }) => {
        if (mounted) {
          setSession(data.session);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error("supabase.auth.getSession() failed:", err);
        if (mounted) {
          setSession(null);
          setLoading(false);
        }
      });

    // Keeps state in sync afterwards: sign-in, sign-out, token refresh, etc.
    const { data: listener } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
      setLoading(false);
    });

    return () => {
      mounted = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  return (
    <AuthContext.Provider value={{ session, user: session?.user ?? null, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
