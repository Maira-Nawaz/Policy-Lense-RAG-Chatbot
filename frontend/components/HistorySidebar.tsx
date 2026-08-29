"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { ApiError, deleteConversation, getConversationMessages, getConversations } from "@/lib/api";
import type { Conversation } from "@/lib/types";
import { useAuth } from "@/lib/AuthContext";
import { useChatReset } from "@/lib/ChatResetContext";
import { useHistorySelection } from "@/lib/HistorySelectionContext";
import { getPinnedIds, togglePin } from "@/lib/pinnedConversations";
import AccountMenu from "./AccountMenu";
import {
  ChartBarIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  DotsHorizontalIcon,
  PinIcon,
  PlusIcon,
  SearchIcon,
  ShieldCheckIcon,
  TrashIcon,
} from "./Icons";

const COLLAPSED_STORAGE_KEY = "policylens.historySidebarCollapsed";
const DEFAULT_HISTORY_LIMIT = 20;
const EXPANDED_HISTORY_LIMIT = 100;

const BUCKET_ORDER = ["Today", "Yesterday", "Previous 7 days", "Older"] as const;

function getDateBucket(dateStr: string): (typeof BUCKET_ORDER)[number] {
  const date = new Date(dateStr);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday);
  startOfYesterday.setDate(startOfYesterday.getDate() - 1);
  const startOfWeek = new Date(startOfToday);
  startOfWeek.setDate(startOfWeek.getDate() - 7);

  if (date >= startOfToday) return "Today";
  if (date >= startOfYesterday) return "Yesterday";
  if (date >= startOfWeek) return "Previous 7 days";
  return "Older";
}

function groupByBucket(conversations: Conversation[]): [string, Conversation[]][] {
  const groups: Partial<Record<(typeof BUCKET_ORDER)[number], Conversation[]>> = {};
  for (const conversation of conversations) {
    const bucket = getDateBucket(conversation.last_activity);
    (groups[bucket] ??= []).push(conversation);
  }
  // Conversations already arrive sorted by last_activity desc, so each
  // bucket's internal order is preserved -- only the bucket order is fixed here.
  return BUCKET_ORDER.filter((bucket) => groups[bucket]?.length).map((bucket) => [bucket, groups[bucket]!]);
}

interface HistorySidebarProps {
  open: boolean;
  onClose: () => void;
}

export default function HistorySidebar({ open, onClose }: HistorySidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openingId, setOpeningId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [historyLimit, setHistoryLimit] = useState(DEFAULT_HISTORY_LIMIT);
  const [pinnedIds, setPinnedIds] = useState<string[]>([]);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const pathname = usePathname();
  const router = useRouter();
  const { user } = useAuth();
  const { startNewChat, activeConversationId, setActiveConversationId } = useChatReset();
  const { selectConversation } = useHistorySelection();

  // Desktop-only collapse (icon rail vs. full list), independent of the
  // mobile slide-over `open`/`onClose` above. Persisted so a reload doesn't
  // reopen a sidebar the user deliberately tucked away.
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem(COLLAPSED_STORAGE_KEY);
    if (stored !== null) setCollapsed(stored === "true");
  }, []);

  useEffect(() => {
    if (user) setPinnedIds(getPinnedIds(user.id));
  }, [user]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpenMenuId(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      window.localStorage.setItem(COLLAPSED_STORAGE_KEY, String(next));
      return next;
    });
  }

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    getConversations(historyLimit)
      .then((data) => {
        if (!cancelled) setConversations(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Could not load conversations.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // Re-fetch whenever the active conversation changes (a new question just
    // got logged, or a fresh "New chat" conversation might get its first
    // message soon) so the list doesn't go stale during the session, and
    // whenever historyLimit grows via "See all".
  }, [activeConversationId, historyLimit]);

  function handleNewChat() {
    startNewChat();
    router.push("/");
    onClose();
  }

  async function handleSelectConversation(conversationId: string) {
    setOpeningId(conversationId);
    try {
      const messages = await getConversationMessages(conversationId);
      selectConversation(conversationId, messages);
      // Make this the active thread -- a follow-up question should continue
      // it, not start a new conversation_id.
      setActiveConversationId(conversationId);
      router.push("/");
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load that conversation.");
    } finally {
      setOpeningId(null);
    }
  }

  function handleTogglePin(conversationId: string) {
    if (!user) return;
    setPinnedIds(togglePin(user.id, conversationId));
    setOpenMenuId(null);
  }

  async function handleDelete(conversationId: string) {
    setOpenMenuId(null);
    if (!window.confirm("Delete this conversation? This can't be undone.")) return;

    try {
      await deleteConversation(conversationId);
      setConversations((prev) => prev.filter((c) => c.conversation_id !== conversationId));
      if (conversationId === activeConversationId) {
        // The conversation currently open in the main panel just got deleted --
        // don't leave the user looking at a thread that no longer exists.
        startNewChat();
        router.push("/");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete that conversation.");
    }
  }

  const searchLower = search.trim().toLowerCase();
  const filtered = searchLower
    ? conversations.filter((c) => c.title.toLowerCase().includes(searchLower))
    : conversations;
  const pinned = filtered.filter((c) => pinnedIds.includes(c.conversation_id));
  const unpinned = filtered.filter((c) => !pinnedIds.includes(c.conversation_id));
  const buckets = groupByBucket(unpinned);
  const canSeeAll = !loading && !error && historyLimit < EXPANDED_HISTORY_LIMIT && conversations.length >= historyLimit;

  function renderRow(conversation: Conversation, isPinned: boolean) {
    return (
      <li key={conversation.conversation_id} className="group relative">
        <button
          type="button"
          onClick={() => handleSelectConversation(conversation.conversation_id)}
          disabled={openingId !== null}
          className="w-full rounded-md py-2 pl-2 pr-8 text-left hover:bg-white disabled:opacity-60"
        >
          <p className="truncate text-sm text-ink">
            {openingId === conversation.conversation_id ? "Loading…" : conversation.title}
          </p>
          <div className="mt-1 flex items-center justify-between gap-2">
            <p className="truncate text-xs text-ink-faint">
              {new Date(conversation.last_activity).toLocaleString()}
            </p>
            {conversation.message_count > 1 && (
              <span className="shrink-0 text-xs text-ink-faint">{conversation.message_count} messages</span>
            )}
          </div>
        </button>

        <button
          type="button"
          onClick={() => setOpenMenuId((prev) => (prev === conversation.conversation_id ? null : conversation.conversation_id))}
          aria-label="Conversation options"
          className="absolute right-1 top-1/2 -translate-y-1/2 rounded-md p-1 text-ink-faint opacity-0 hover:bg-white hover:text-ink group-hover:opacity-100"
        >
          <DotsHorizontalIcon className="h-3.5 w-3.5" />
        </button>

        {openMenuId === conversation.conversation_id && (
          <div
            ref={menuRef}
            role="menu"
            className="absolute right-1 top-8 z-40 w-36 rounded-lg border border-border bg-surface p-1 shadow-lg"
          >
            <button
              type="button"
              onClick={() => handleTogglePin(conversation.conversation_id)}
              className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-xs text-ink-muted hover:bg-gray-50 hover:text-ink"
            >
              <PinIcon className="h-3.5 w-3.5" />
              {isPinned ? "Unpin" : "Pin"}
            </button>
            <button
              type="button"
              onClick={() => handleDelete(conversation.conversation_id)}
              className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-xs text-red-600 hover:bg-red-50"
            >
              <TrashIcon className="h-3.5 w-3.5" />
              Delete
            </button>
          </div>
        )}
      </li>
    );
  }

  return (
    <>
      {/* Backdrop, mobile only -- clicking it closes the sidebar */}
      {open && (
        <div
          className="fixed inset-0 z-20 bg-black/50 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-72 flex-col border-r border-border bg-surface-raised transition-[transform,width] md:static md:z-auto md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        } ${collapsed ? "md:w-14" : "md:w-72"}`}
      >
        {/* Logo + wordmark + collapse toggle, clustered at top-left */}
        <div className="flex items-center gap-1.5 border-b border-border px-3 py-3">
          <ShieldCheckIcon className="h-5 w-5 shrink-0 text-accent" />
          {!collapsed && <span className="text-sm font-semibold text-ink">PolicyLens</span>}
          <button
            type="button"
            onClick={toggleCollapsed}
            aria-label={collapsed ? "Expand history sidebar" : "Collapse history sidebar"}
            className="ml-auto hidden rounded-md p-1 text-ink-muted hover:bg-white hover:text-ink md:inline-flex"
          >
            {collapsed ? <ChevronRightIcon className="h-4 w-4" /> : <ChevronLeftIcon className="h-4 w-4" />}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="ml-auto text-xs font-medium text-ink-muted hover:text-ink md:hidden"
          >
            Close
          </button>
        </div>

        {/* Primary actions -- Claude/ChatGPT-style, above the thread list */}
        <div className="flex flex-col gap-1 p-2">
          <button
            type="button"
            onClick={handleNewChat}
            title="New chat"
            className="flex items-center gap-2 rounded-md px-2 py-2 text-sm font-medium text-ink-muted transition-colors hover:bg-white hover:text-ink"
          >
            <PlusIcon className="h-4 w-4 shrink-0" />
            {!collapsed && "New chat"}
          </button>
          <Link
            href="/metrics"
            onClick={onClose}
            title="Metrics"
            className={`flex items-center gap-2 rounded-md px-2 py-2 text-sm font-medium transition-colors ${
              pathname === "/metrics"
                ? "bg-accent-muted text-accent"
                : "text-ink-muted hover:bg-white hover:text-ink"
            }`}
          >
            <ChartBarIcon className="h-4 w-4 shrink-0" />
            {!collapsed && "Metrics"}
          </Link>
        </div>

        {!collapsed && (
          <div className="px-2 pb-2">
            <div className="relative">
              <SearchIcon className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-faint" />
              <input
                type="text"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search"
                className="w-full rounded-md border border-border bg-white py-1.5 pl-8 pr-2 text-sm text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none"
              />
            </div>
          </div>
        )}

        {collapsed ? (
          <button
            type="button"
            onClick={toggleCollapsed}
            className="hidden flex-1 md:block"
            aria-label="Expand history sidebar"
            title="Recent questions"
          />
        ) : (
          // min-h-0 so this scrolls internally instead of growing to fit every
          // conversation and pushing the account footer below out of view.
          <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
            {loading && <p className="px-2 py-3 text-sm text-ink-faint">Loading...</p>}
            {error && <p className="px-2 py-3 text-sm text-red-600">{error}</p>}
            {!loading && !error && filtered.length === 0 && (
              <p className="px-2 py-3 text-sm text-ink-faint">
                {search ? "No matching conversations." : "No conversations yet."}
              </p>
            )}

            {pinned.length > 0 && (
              <div className="mb-3">
                <p className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-ink-faint">Pinned</p>
                <ul className="space-y-1">{pinned.map((c) => renderRow(c, true))}</ul>
              </div>
            )}

            {buckets.map(([bucket, items]) => (
              <div key={bucket} className="mb-3">
                <p className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-ink-faint">{bucket}</p>
                <ul className="space-y-1">{items.map((c) => renderRow(c, false))}</ul>
              </div>
            ))}

            {canSeeAll && (
              <button
                type="button"
                onClick={() => setHistoryLimit(EXPANDED_HISTORY_LIMIT)}
                className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium text-ink-muted hover:text-ink"
              >
                See all
                <ChevronRightIcon className="h-3 w-3" />
              </button>
            )}
          </div>
        )}

        {/* Footer account access -- a second entry point to the same dropdown
            as the top-right one, pinned to the bottom regardless of list length. */}
        <div className="border-t border-border p-2">
          <AccountMenu collapsed={collapsed} />
        </div>
      </aside>
    </>
  );
}
