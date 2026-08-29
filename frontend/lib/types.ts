// Mirrors the Pydantic models in api/main.py -- keep in sync with that file.

export type Behavior = "answer" | "clarify" | "refuse" | "error";

export interface QueryRequestBody {
  question: string;
  jurisdiction?: string | null;
  segment?: string | null;
  department?: string | null;
  conversation_id?: string | null;
}

export interface QueryResult {
  behavior: Behavior;
  answer: string;
  cited_documents: string[];
  retrieved_chunk_ids: string[];
  latency_ms: number;
  query_log_id: string | null;
  // Always null until rag_pipeline computes a real cost -- see CostLatencyStats.
  estimated_cost_usd: number | null;
}

export interface FeedbackRequestBody {
  query_log_id: string;
  feedback: "thumbs_up" | "thumbs_down";
  comment?: string | null;
}

export interface HistoryItem {
  id: string;
  timestamp: string;
  query_text: string;
  jurisdiction_given: string | null;
  segment_given: string | null;
  behavior: Behavior;
  answer_text: string | null;
  cited_documents: string[];
  latency_ms: number | null;
  user_feedback: string | null;
  estimated_cost_usd: number | null;
}

// One entry in the sidebar's "Recent questions" list -- one per conversation
// thread, not one per question (that's what HistoryItem/the old /history was).
export interface Conversation {
  conversation_id: string;
  title: string;
  last_activity: string;
  message_count: number;
}

export interface EvalRun {
  id: string;
  run_timestamp: string;
  config_snapshot: Record<string, unknown> | null;
  retrieval_precision: number | null;
  retrieval_recall: number | null;
  groundedness_rate: number | null;
  refusal_correctness: number | null;
  p50_latency_ms: number | null;
  p95_latency_ms: number | null;
  total_cost_usd: number | null;
  notes: string | null;
}

// One question/answer pair as displayed in the chat panel. Not a backend type --
// this is the frontend's own state shape, built either from a live /query call
// or reconstructed from a fetched conversation message.
export interface Exchange {
  id: string;
  question: string;
  // Raw codes (e.g. "DE"/"enterprise"), kept alongside the display labels
  // below so Retry can re-send the exact same request.
  jurisdiction: string | null;
  segment: string | null;
  jurisdictionLabel: string;
  segmentLabel: string;
  loading: boolean;
  error: string | null;
  response: QueryResult | null;
  // Only set when reconstructed from a past conversation, so FeedbackButtons
  // can start in its "already submitted" state instead of showing live
  // buttons again.
  initialFeedback?: string | null;
}
