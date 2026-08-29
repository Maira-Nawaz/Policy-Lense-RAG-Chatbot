import type {
  Conversation,
  EvalRun,
  FeedbackRequestBody,
  HistoryItem,
  QueryRequestBody,
  QueryResult,
} from "./types";
import { supabase } from "./supabaseClient";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function getAccessToken(): Promise<string | null> {
  // Reads the persisted session -- no network round trip in the common case
  // (only refreshes over the network if the token is actually expired).
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getAccessToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { ...headers, ...(init?.headers as Record<string, string> | undefined) },
    });
  } catch {
    // Network-level failure (backend down, wrong URL, CORS, etc.) -- fetch()
    // throws here rather than giving us a Response, so there's no status code yet.
    throw new ApiError(
      `Could not reach the PolicyLens API at ${API_BASE_URL}. Is the backend running?`,
      0,
    );
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? body.error ?? detail;
    } catch {
      // Error response wasn't JSON -- fall back to statusText above.
    }
    throw new ApiError(String(detail), res.status);
  }

  return (await res.json()) as T;
}

export function postQuery(body: QueryRequestBody): Promise<QueryResult> {
  return request<QueryResult>("/query", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function postFeedback(body: FeedbackRequestBody): Promise<{ status: string }> {
  return request<{ status: string }>("/feedback", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getHistory(limit = 20): Promise<HistoryItem[]> {
  return request<HistoryItem[]>(`/history?limit=${limit}`);
}

export function getConversations(limit = 20): Promise<Conversation[]> {
  return request<Conversation[]>(`/conversations?limit=${limit}`);
}

export function getConversationMessages(conversationId: string): Promise<HistoryItem[]> {
  return request<HistoryItem[]>(`/conversations/${encodeURIComponent(conversationId)}/messages`);
}

export function getEvalRuns(limit = 10): Promise<EvalRun[]> {
  return request<EvalRun[]>(`/eval-runs?limit=${limit}`);
}

export function deleteConversation(conversationId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/conversations/${encodeURIComponent(conversationId)}`, {
    method: "DELETE",
  });
}

export function archiveConversation(conversationId: string, archived = true): Promise<{ status: string }> {
  return request<{ status: string }>(`/conversations/${encodeURIComponent(conversationId)}/archive`, {
    method: "POST",
    body: JSON.stringify({ archived }),
  });
}

export function reportConversation(conversationId: string, reason: string | null): Promise<{ status: string }> {
  return request<{ status: string }>(`/conversations/${encodeURIComponent(conversationId)}/report`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}
