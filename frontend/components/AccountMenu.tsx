"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/AuthContext";
import { supabase } from "@/lib/supabaseClient";
import { DotsHorizontalIcon } from "./Icons";

interface AccountMenuProps {
  /** Hides the name/dots when the sidebar is collapsed to an icon rail. */
  collapsed?: boolean;
}

// The compact ChatGPT-style row pinned to the bottom of the sidebar -- the
// sole account access point now (a duplicate top-right green panel was
// removed from TopNav; this was always the same dropdown content either way).
export default function AccountMenu({ collapsed = false }: AccountMenuProps) {
  const { user } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const fullName = (user?.user_metadata?.full_name as string | undefined) || null;
  const email = user?.email ?? "";
  const displayName = fullName || email || "Account";
  const initial = (fullName || email || "?").trim().charAt(0).toUpperCase();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleSignOut() {
    setOpen(false);
    await supabase.auth.signOut();
    router.replace("/login");
  }

  if (!user) return null;

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        aria-haspopup="menu"
        className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left transition-colors hover:bg-white"
      >
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-semibold text-white">
          {initial}
        </span>
        {!collapsed && (
          <>
            <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink">{displayName}</span>
            <DotsHorizontalIcon className="h-4 w-4 shrink-0 text-ink-muted" />
          </>
        )}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute bottom-full left-0 z-40 mb-2 w-56 rounded-lg border border-border bg-surface p-1 shadow-lg"
        >
          <div className="border-b border-gray-100 px-3 py-2">
            {fullName && <p className="truncate text-sm font-medium text-ink">{fullName}</p>}
            <p className="truncate text-xs text-ink-muted">{email}</p>
          </div>
          <button
            type="button"
            role="menuitem"
            onClick={handleSignOut}
            className="mt-1 w-full rounded-md px-3 py-2 text-left text-sm text-ink-muted transition-colors hover:bg-gray-50 hover:text-ink"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
