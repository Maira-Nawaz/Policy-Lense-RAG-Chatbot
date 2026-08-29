"use client";

import { useState } from "react";

import RequireAuth from "@/components/RequireAuth";
import HistorySidebar from "@/components/HistorySidebar";
import { HistorySelectionProvider } from "@/lib/HistorySelectionContext";

/**
 * Shared shell for every authenticated page (chat "/" and "/metrics"): the
 * sidebar (logo, collapse toggle, New chat, Metrics link, history list,
 * account footer) plus the mobile "open sidebar" strip, wrapping whichever
 * page's own content is passed in as `children`. Previously this lived
 * inside the chat page itself, which is why /metrics had no sidebar at all --
 * moving it here (a route-group layout that wraps both pages, but not
 * /login or /signup) makes it identical and shared instead of duplicated.
 *
 * The {children} wrapper below deliberately does NOT set overflow-y-auto --
 * the chat page manages its own split scroll regions (message list scrolls,
 * the input bar stays fixed), so each page decides its own overflow/height
 * behavior on its own root element; this wrapper only sizes the box.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <RequireAuth>
      <HistorySelectionProvider>
        <div className="flex h-full">
          <HistorySidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

          <div className="flex min-w-0 flex-1 flex-col">
            <div className="flex items-center border-b border-border bg-surface px-4 py-2 md:hidden">
              <button
                type="button"
                onClick={() => setSidebarOpen(true)}
                className="rounded-md border border-border px-3 py-1.5 text-sm text-ink-muted"
              >
                History
              </button>
            </div>

            <div className="min-h-0 flex-1">{children}</div>
          </div>
        </div>
      </HistorySelectionProvider>
    </RequireAuth>
  );
}
