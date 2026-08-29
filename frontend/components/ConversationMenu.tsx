"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError, archiveConversation, deleteConversation, reportConversation } from "@/lib/api";
import { ArchiveIcon, DotsHorizontalIcon, FlagIcon, ShareIcon, TrashIcon } from "./Icons";

interface ConversationMenuProps {
  conversationId: string;
  /** Called after a successful archive or delete -- the caller should start a fresh chat,
   * since the conversation just left the list (archived) or no longer exists (deleted). */
  onConversationRemoved: () => void;
}

/**
 * Share copies an auth-gated deep link (`/?conversation=<id>`) -- opening it only
 * actually loads the conversation if the person who opens it is signed in *and*
 * owns it (the existing /conversations/{id}/messages check already enforces
 * that). This is deliberately not a public link: a real public/cross-user share
 * would need its own access-control model and was flagged as a separate,
 * bigger feature rather than something to build silently here.
 */
export default function ConversationMenu({ conversationId, onConversationRemoved }: ConversationMenuProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [reportReason, setReportReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
        setReportOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function flashStatus(message: string) {
    setStatus(message);
    setTimeout(() => setStatus(null), 2500);
  }

  async function handleShare() {
    const url = `${window.location.origin}/?conversation=${encodeURIComponent(conversationId)}`;
    try {
      await navigator.clipboard.writeText(url);
      flashStatus("Link copied");
    } catch {
      flashStatus("Could not copy link");
    }
  }

  async function handleArchive() {
    setMenuOpen(false);
    setBusy(true);
    try {
      await archiveConversation(conversationId, true);
      onConversationRemoved();
    } catch (err) {
      flashStatus(err instanceof ApiError ? err.message : "Could not archive");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    setMenuOpen(false);
    if (!window.confirm("Delete this conversation? This can't be undone.")) return;

    setBusy(true);
    try {
      await deleteConversation(conversationId);
      onConversationRemoved();
    } catch (err) {
      flashStatus(err instanceof ApiError ? err.message : "Could not delete");
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmitReport() {
    setBusy(true);
    try {
      await reportConversation(conversationId, reportReason.trim() || null);
      setReportOpen(false);
      setMenuOpen(false);
      setReportReason("");
      flashStatus("Reported");
    } catch (err) {
      flashStatus(err instanceof ApiError ? err.message : "Could not report");
    } finally {
      setBusy(false);
    }
  }

  return (
    // No border/background of its own -- TopNav directly above already has a
    // bottom border, and stacking a second bordered bar right under it read
    // as two redundant lines. This just sits on the page background.
    <div className="flex items-center justify-end gap-2 px-4 py-2">
      {status && <span className="text-xs text-ink-faint">{status}</span>}

      <button
        type="button"
        onClick={handleShare}
        disabled={busy}
        className="flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium text-ink-muted transition-colors hover:border-accent/40 hover:text-ink disabled:opacity-50"
      >
        <ShareIcon className="h-3.5 w-3.5" />
        Share
      </button>

      <div ref={containerRef} className="relative">
        <button
          type="button"
          onClick={() => {
            setMenuOpen((prev) => !prev);
            setReportOpen(false);
          }}
          disabled={busy}
          aria-label="Conversation options"
          aria-expanded={menuOpen}
          className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-surface-raised hover:text-ink disabled:opacity-50"
        >
          <DotsHorizontalIcon className="h-4 w-4" />
        </button>

        {menuOpen && !reportOpen && (
          <div role="menu" className="absolute right-0 z-40 mt-2 w-44 rounded-lg border border-border bg-surface p-1 shadow-lg">
            <button
              type="button"
              onClick={handleArchive}
              className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-ink-muted transition-colors hover:bg-gray-50 hover:text-ink"
            >
              <ArchiveIcon className="h-4 w-4" />
              Archive
            </button>
            <button
              type="button"
              onClick={() => setReportOpen(true)}
              className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-ink-muted transition-colors hover:bg-gray-50 hover:text-ink"
            >
              <FlagIcon className="h-4 w-4" />
              Report
            </button>
            <button
              type="button"
              onClick={handleDelete}
              className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-red-600 transition-colors hover:bg-red-50"
            >
              <TrashIcon className="h-4 w-4" />
              Delete
            </button>
          </div>
        )}

        {menuOpen && reportOpen && (
          <div className="absolute right-0 z-40 mt-2 w-64 rounded-lg border border-border bg-surface p-3 shadow-lg">
            <p className="mb-1.5 text-xs font-medium text-ink-muted">Report this conversation</p>
            <textarea
              value={reportReason}
              onChange={(event) => setReportReason(event.target.value)}
              placeholder="Optional reason..."
              rows={2}
              className="mb-2 w-full rounded-md border border-border bg-surface-raised px-2 py-1.5 text-xs text-ink focus:border-accent focus:outline-none"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setReportOpen(false)}
                className="rounded-md px-2 py-1 text-xs text-ink-muted hover:text-ink"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmitReport}
                disabled={busy}
                className="rounded-md bg-accent px-2.5 py-1 text-xs font-medium text-white hover:bg-accent-hover disabled:opacity-50"
              >
                Submit
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
