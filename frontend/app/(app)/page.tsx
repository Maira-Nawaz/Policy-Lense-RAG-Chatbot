"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { ApiError, getConversationMessages, postQuery } from "@/lib/api";
import type { Exchange, HistoryItem } from "@/lib/types";
import { useAuth } from "@/lib/AuthContext";
import { useChatReset } from "@/lib/ChatResetContext";
import { useHistorySelection } from "@/lib/HistorySelectionContext";
import ChatForm from "@/components/ChatForm";
import ChatMessage from "@/components/ChatMessage";
import ConversationMenu from "@/components/ConversationMenu";
import ExampleQuestions from "@/components/ExampleQuestions";

const JURISDICTION_LABELS: Record<string, string> = {
  DE: "Germany",
  US: "United States",
  UK: "United Kingdom",
};

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function historyItemToExchange(item: HistoryItem): Exchange {
  return {
    id: `history-${item.id}`,
    question: item.query_text,
    jurisdiction: item.jurisdiction_given,
    segment: item.segment_given,
    jurisdictionLabel: item.jurisdiction_given ? JURISDICTION_LABELS[item.jurisdiction_given] ?? item.jurisdiction_given : "",
    segmentLabel: item.segment_given ?? "",
    loading: false,
    error: null,
    initialFeedback: item.user_feedback,
    response: {
      behavior: item.behavior,
      answer: item.answer_text ?? "(no answer text recorded)",
      cited_documents: item.cited_documents,
      // /conversations/{id}/messages doesn't return chunk ids (see
      // api/main.py's HistoryItem) -- left empty rather than faked.
      retrieved_chunk_ids: [],
      latency_ms: item.latency_ms ?? 0,
      query_log_id: item.id,
      estimated_cost_usd: item.estimated_cost_usd,
    },
  };
}

export default function ChatPage() {
  const { user } = useAuth();
  const fullName = user?.user_metadata?.full_name as string | undefined;
  // Just the first name for the welcome line -- "Welcome, Maira" reads better
  // than "Welcome, Maira Nawaz". Falls back to the full email if there's no
  // full_name on the account at all (nothing sensible to split there).
  const welcomeName = fullName ? fullName.trim().split(/\s+/)[0] : user?.email || "";

  const { resetToken, activeConversationId, startNewChat, setActiveConversationId } = useChatReset();
  const { pendingConversation, clearPendingConversation } = useHistorySelection();
  const searchParams = useSearchParams();
  const [exchanges, setExchanges] = useState<Exchange[]>([]);

  // "New chat" bumps resetToken -- this is what actually clears the
  // conversation when you're already on this page (a plain navigation to "/"
  // wouldn't remount this component or its state).
  useEffect(() => {
    setExchanges([]);
  }, [resetToken]);

  // Share deep link: /?conversation=<id>. Only ever actually loads the thread
  // if the person opening it is signed in *and* owns it -- the same user_id
  // scoping /conversations/{id}/messages already enforces. Anyone else just
  // sees an empty result and lands on a normal fresh chat, silently.
  useEffect(() => {
    const deepLinkId = searchParams.get("conversation");
    if (!deepLinkId) return;

    let cancelled = false;
    getConversationMessages(deepLinkId)
      .then((messages) => {
        if (cancelled || messages.length === 0) return;
        setExchanges(messages.map(historyItemToExchange));
        setActiveConversationId(deepLinkId);
      })
      .catch(() => {
        // Doesn't exist / not owned by this user -- fail quietly into a fresh chat.
      });

    return () => {
      cancelled = true;
    };
    // Deep link is a one-time load trigger on arrival, not a param to keep re-syncing against.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const busy = exchanges.some((exchange) => exchange.loading);

  async function runQuery(exchangeId: string, question: string, jurisdiction: string | null, segment: string | null) {
    try {
      const response = await postQuery({
        question,
        jurisdiction,
        segment,
        conversation_id: activeConversationId,
      });
      setExchanges((prev) =>
        prev.map((exchange) =>
          exchange.id === exchangeId ? { ...exchange, loading: false, error: null, response } : exchange,
        ),
      );
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Unexpected error contacting the API.";
      setExchanges((prev) =>
        prev.map((exchange) => (exchange.id === exchangeId ? { ...exchange, loading: false, error: message } : exchange)),
      );
    }
  }

  async function handleSubmit(question: string, jurisdiction: string | null, segment: string | null) {
    const id = newId();

    setExchanges((prev) => [
      ...prev,
      {
        id,
        question,
        jurisdiction,
        segment,
        jurisdictionLabel: jurisdiction ? JURISDICTION_LABELS[jurisdiction] ?? jurisdiction : "",
        segmentLabel: segment ?? "",
        loading: true,
        error: null,
        response: null,
      },
    ]);

    await runQuery(id, question, jurisdiction, segment);
  }

  function handleRetry(exchangeId: string) {
    const target = exchanges.find((exchange) => exchange.id === exchangeId);
    if (!target) return;

    setExchanges((prev) =>
      prev.map((exchange) =>
        exchange.id === exchangeId ? { ...exchange, loading: true, error: null, response: null } : exchange,
      ),
    );
    runQuery(exchangeId, target.question, target.jurisdiction, target.segment);
  }

  // The sidebar (which now lives in the shared layout) sets
  // `pendingConversation` when a past conversation is clicked -- possibly from
  // another page (e.g. /metrics). This *replaces* the displayed thread (it's a
  // whole different conversation, not another message in the current one),
  // then clears the pending value so it doesn't re-fire on unrelated renders.
  useEffect(() => {
    if (pendingConversation) {
      setExchanges(pendingConversation.messages.map(historyItemToExchange));
      clearPendingConversation();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingConversation]);

  return (
    <div className="flex h-full flex-col">
      {exchanges.length > 0 && (
        <ConversationMenu conversationId={activeConversationId} onConversationRemoved={startNewChat} />
      )}

      {/* min-h-0 is essential here: a flex item's default min-height is "auto"
          (content-based), which would let this grow to fit every message
          instead of respecting flex-1 + overflow-y-auto -- that's exactly what
          was pushing ChatForm (and the whole page) out of view on long chats. */}
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {exchanges.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center px-4 text-center text-sm text-ink-faint">
            {welcomeName && <p className="mb-1.5 text-xl font-semibold text-ink">Welcome, {welcomeName}</p>}
            <p>Tip: including a jurisdiction and segment gets you the most precise answer.</p>
            <ExampleQuestions onSelect={handleSubmit} />
          </div>
        ) : (
          <div className="space-y-6">
            {exchanges.map((exchange) => (
              <ChatMessage key={exchange.id} exchange={exchange} onRetry={() => handleRetry(exchange.id)} />
            ))}
          </div>
        )}
      </div>

      <ChatForm onSubmit={handleSubmit} disabled={busy} />
    </div>
  );
}
