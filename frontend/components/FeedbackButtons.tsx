"use client";

import { useState } from "react";

import { ApiError, postFeedback } from "@/lib/api";
import ThumbIcon from "./ThumbIcon";

interface FeedbackButtonsProps {
  queryLogId: string;
  initialFeedback?: string | null;
}

export default function FeedbackButtons({ queryLogId, initialFeedback }: FeedbackButtonsProps) {
  const [submitted, setSubmitted] = useState(Boolean(initialFeedback));
  const [submitting, setSubmitting] = useState<"thumbs_up" | "thumbs_down" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleClick(value: "thumbs_up" | "thumbs_down") {
    setSubmitting(value);
    setError(null);
    try {
      await postFeedback({ query_log_id: queryLogId, feedback: value });
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not submit feedback.");
    } finally {
      setSubmitting(null);
    }
  }

  if (submitted) {
    return <p className="text-xs text-ink-faint">Thanks for your feedback.</p>;
  }

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={() => handleClick("thumbs_up")}
        disabled={submitting !== null}
        aria-label="Thumbs up"
        className="rounded-md border border-border p-1.5 text-ink-muted hover:border-accent/40 hover:text-ink disabled:opacity-50"
      >
        <ThumbIcon direction="up" />
      </button>
      <button
        type="button"
        onClick={() => handleClick("thumbs_down")}
        disabled={submitting !== null}
        aria-label="Thumbs down"
        className="rounded-md border border-border p-1.5 text-ink-muted hover:border-accent/40 hover:text-ink disabled:opacity-50"
      >
        <ThumbIcon direction="down" />
      </button>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}
