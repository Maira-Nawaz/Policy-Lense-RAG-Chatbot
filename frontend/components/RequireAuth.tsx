"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/AuthContext";

/**
 * Wrap a page's content in this to require a session. Redirects to /login as
 * soon as we know there isn't one -- shows a loading state until then so the
 * protected content never flashes on screen first.
 */
export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const { session, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !session) {
      router.replace("/login");
    }
  }, [loading, session, router]);

  if (loading || !session) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-ink-faint">
        <p>Loading...</p>
      </div>
    );
  }

  return <>{children}</>;
}
