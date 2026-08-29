"use client";

import { useState } from "react";

import type { Exchange } from "@/lib/types";
import BehaviorBadge from "./BehaviorBadge";
import CostLatencyStats from "./CostLatencyStats";
import FeedbackButtons from "./FeedbackButtons";
import { CopyIcon, RetryIcon } from "./Icons";
import MarkdownAnswer from "./MarkdownAnswer";

interface ChatMessageProps {
  exchange: Exchange;
  /** Re-runs this exact question. Omitted for reconstructed/read-only history views. */
  onRetry?: () => void;
}

export default function ChatMessage({ exchange, onRetry }: ChatMessageProps) {
  const { question, jurisdictionLabel, segmentLabel, loading, error, response } = exchange;
  const scope = [jurisdictionLabel, segmentLabel].filter(Boolean).join(" · ");
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    if (!response) return;
    try {
      await navigator.clipboard.writeText(response.answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access denied/unavailable -- not worth surfacing as an error state.
    }
  }

  return (
    <div className="space-y-2">
      {/* Question bubble */}
      <div className="ml-auto max-w-2xl rounded-2xl rounded-tr-sm bg-accent px-4 py-2.5 text-sm text-white">
        <p>{question}</p>
        {scope && <p className="mt-1 text-xs text-white/70">{scope}</p>}
      </div>

      {/* Answer bubble */}
      <div className="max-w-2xl rounded-2xl rounded-tl-sm border border-border bg-surface px-4 py-3 shadow-sm">
        {loading && <p className="text-sm text-ink-muted">Thinking, this can take several seconds...</p>}

        {error && (
          <div className="text-sm">
            <p className="font-medium text-red-600">Something went wrong.</p>
            <p className="mt-1 text-red-500">{error}</p>
          </div>
        )}

        {response && (
          <>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <BehaviorBadge behavior={response.behavior} />
            </div>

            <MarkdownAnswer text={response.answer} />

            {/* Quiet footnote-style citations -- deliberately more muted than
                the answer text above, so they read as a reference, not content. */}
            {response.cited_documents.length > 0 && (
              <div className="mt-4 border-t border-gray-100 pt-3">
                <p className="text-[11px] font-medium uppercase tracking-wide text-ink-faint">Sources</p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {response.cited_documents.map((doc) => (
                    <span
                      key={doc}
                      className="rounded-full bg-gray-100 px-2.5 py-0.5 text-[11px] text-ink-faint"
                    >
                      {doc}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <CostLatencyStats latencyMs={response.latency_ms} />

            <div className="mt-3 flex items-center gap-2">
              {response.behavior === "answer" && response.query_log_id && (
                <FeedbackButtons
                  queryLogId={response.query_log_id}
                  initialFeedback={exchange.initialFeedback}
                />
              )}

              <button
                type="button"
                onClick={handleCopy}
                aria-label="Copy answer"
                title={copied ? "Copied" : "Copy answer"}
                className="rounded-md border border-border p-1.5 text-ink-muted transition-colors hover:border-accent/40 hover:text-ink"
              >
                <CopyIcon className="h-3.5 w-3.5" />
              </button>

              {onRetry && (
                <button
                  type="button"
                  onClick={onRetry}
                  disabled={loading}
                  aria-label="Retry"
                  title="Retry"
                  className="rounded-md border border-border p-1.5 text-ink-muted transition-colors hover:border-accent/40 hover:text-ink disabled:opacity-50"
                >
                  <RetryIcon className="h-3.5 w-3.5" />
                </button>
              )}

              {copied && <span className="text-xs text-ink-faint">Copied</span>}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
