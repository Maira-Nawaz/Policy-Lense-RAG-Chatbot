"""
FastAPI layer over rag_pipeline.answer_query(), so a frontend can call PolicyLens
over HTTP. Deliberately non-streaming for now -- streaming is a separate,
later improvement.

Run locally with (from the project root, so `rag_pipeline` etc. are importable):
    uvicorn api.main:app --reload --port 8000

Nothing here eagerly loads models or connects to Supabase at import/startup time --
rag_pipeline (and this module's own small Supabase client for /feedback) already
initialize lazily on first use, so the process starts instantly and only pays
model-load cost on the first real request.
"""
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from supabase import create_client

import rag_pipeline
from config import get_settings

ALLOWED_FEEDBACK_VALUES = {"thumbs_up", "thumbs_down"}
CONVERSATION_TITLE_MAX_LENGTH = 60

app = FastAPI(title="PolicyLens API")

# Wide open for now -- we don't know the deployed frontend's domain yet.
# Tighten allow_origins once that's fixed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Without this, an unhandled exception (e.g. a DB error) propagates out
    of the route handler as a bare 500 that never passes back through
    CORSMiddleware's normal response path -- so it comes back with no
    Access-Control-Allow-Origin header at all. Browsers then report that as a
    CORS failure ("blocked by CORS policy"), which is deeply misleading when
    the real problem is a server-side error with nothing to do with CORS.
    Catching it here and returning a normal JSONResponse lets it flow back
    through the middleware stack properly, so the browser sees the real
    error instead of a confusing CORS message.
    """
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": str(exc)},
    )


# --------------------------------------------------------------------------
# Request/response models
# --------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str
    jurisdiction: Optional[str] = None
    segment: Optional[str] = None
    department: Optional[str] = None
    # Groups this call into a conversation thread (see migration_003). The
    # frontend generates and owns this -- a fresh uuid on page load/"New chat",
    # reused for every follow-up in the same thread.
    conversation_id: Optional[str] = None


class QueryResponse(BaseModel):
    behavior: str  # "answer" | "clarify" | "refuse" | "error"
    answer: str
    cited_documents: List[str] = []
    retrieved_chunk_ids: List[str] = []
    latency_ms: int
    query_log_id: Optional[str] = None
    # Always null today -- nothing in rag_pipeline computes this yet (no
    # per-token pricing table wired up; see run_eval.py's own TODO on the same
    # gap). Included so the frontend can show a real number the moment cost
    # tracking exists, without another round of plumbing.
    estimated_cost_usd: Optional[float] = None


class FeedbackRequest(BaseModel):
    query_log_id: str
    feedback: str  # "thumbs_up" | "thumbs_down"
    comment: Optional[str] = None


class HistoryItem(BaseModel):
    id: str
    timestamp: str
    query_text: str
    jurisdiction_given: Optional[str] = None
    segment_given: Optional[str] = None
    behavior: str  # "answer" | "clarify" | "refuse" | "error"
    answer_text: Optional[str] = None
    # Not persisted in query_logs (see _log_query in rag_pipeline.py) -- always
    # empty for now. Reconstructing it would need an extra chunks/documents join
    # per row; left as a TODO if the history sidebar ends up needing it.
    cited_documents: List[str] = []
    latency_ms: Optional[int] = None
    user_feedback: Optional[str] = None
    estimated_cost_usd: Optional[float] = None


class ConversationSummary(BaseModel):
    conversation_id: str
    title: str
    last_activity: str
    message_count: int


class ArchiveRequest(BaseModel):
    archived: bool = True


class ReportRequest(BaseModel):
    reason: Optional[str] = None


# --------------------------------------------------------------------------
# Lazy Supabase client for /feedback -- mirrors rag_pipeline.py's own lazy-init
# pattern rather than reaching into that module's private client.
# --------------------------------------------------------------------------

_settings = None
_supabase_client = None


def _get_settings():
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


def _get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        settings = _get_settings()
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return _supabase_client


def _derive_behavior(row: Dict[str, Any]) -> str:
    """Reconstruct the "behavior" label from query_logs columns.

    This is the exact inverse of how rag_pipeline._log_query writes a result:
    is_refusal = behavior == "refuse", is_clarification = behavior == "clarify",
    error_message set only when behavior == "error". Whichever of those is set
    wins; "answer" is the row that set none of them.
    """
    if row.get("error_message"):
        return "error"
    if row.get("is_refusal"):
        return "refuse"
    if row.get("is_clarification"):
        return "clarify"
    return "answer"


def _truncate_title(text: str) -> str:
    text = text.strip()
    if len(text) <= CONVERSATION_TITLE_MAX_LENGTH:
        return text
    return text[: CONVERSATION_TITLE_MAX_LENGTH - 1].rstrip() + "…"


def get_current_user(authorization: str = Header(None)) -> Dict[str, Any]:
    """FastAPI dependency: verifies the "Authorization: Bearer <access_token>"
    header against Supabase Auth and returns {"id", "email", "full_name"}.

    Verification is delegated entirely to the Supabase SDK's auth.get_user() --
    it calls Supabase Auth's own /auth/v1/user endpoint with the given token
    rather than us decoding/verifying the JWT locally, so there's no local
    secret-key or expiry-checking logic to get wrong here.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

    token = authorization[len("Bearer "):].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    client = _get_supabase_client()
    try:
        auth_response = client.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = getattr(auth_response, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    metadata = user.user_metadata or {}
    return {
        "id": user.id,
        "email": user.email,
        "full_name": metadata.get("full_name"),
    }


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        result = rag_pipeline.answer_query(
            request.question,
            jurisdiction=request.jurisdiction,
            segment=request.segment,
            department=request.department,
            user_id=current_user["id"],
            conversation_id=request.conversation_id,
        )
    except Exception as e:
        # answer_query() already catches its own internal failures into a
        # behavior="error" result, so reaching here means something unexpected
        # broke outside that -- return a clean JSON error, not a raw stack trace.
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "detail": str(e)},
        )

    return QueryResponse(
        behavior=result["behavior"],
        answer=result.get("answer", ""),
        cited_documents=result.get("cited_documents", []),
        retrieved_chunk_ids=result.get("retrieved_chunk_ids", []),
        latency_ms=result.get("latency_ms", 0),
        query_log_id=result.get("query_log_id"),
        estimated_cost_usd=result.get("estimated_cost_usd"),
    )


@app.post("/feedback")
def feedback(request: FeedbackRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    if request.feedback not in ALLOWED_FEEDBACK_VALUES:
        raise HTTPException(
            status_code=400,
            detail=f"feedback must be one of {sorted(ALLOWED_FEEDBACK_VALUES)}",
        )

    client = _get_supabase_client()

    # Ownership must be checked before the update, and as a separate read --
    # an update filtered by both id and user_id would return no rows for both
    # "doesn't exist" and "belongs to someone else", and those need different
    # status codes (404 vs 403).
    existing = (
        client.table("query_logs")
        .select("id, user_id")
        .eq("id", request.query_log_id)
        .maybe_single()
        .execute()
    )
    row = existing.data if existing else None
    if row is None:
        raise HTTPException(status_code=404, detail="query_log_id not found")
    if row.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="This query_log_id does not belong to you")

    value = f"{request.feedback}: {request.comment}" if request.comment else request.feedback

    resp = (
        client.table("query_logs")
        .update({"user_feedback": value})
        .eq("id", request.query_log_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="query_log_id not found")

    return {"status": "ok"}


HISTORY_SELECT_FIELDS = (
    "id, timestamp, query_text, jurisdiction_given, segment_given, conversation_id, "
    "is_refusal, is_clarification, error_message, answer_text, latency_ms, "
    "user_feedback, estimated_cost_usd"
)


def _row_to_history_item(row: Dict[str, Any]) -> HistoryItem:
    return HistoryItem(
        id=row["id"],
        timestamp=row["timestamp"],
        query_text=row["query_text"],
        jurisdiction_given=row.get("jurisdiction_given"),
        segment_given=row.get("segment_given"),
        behavior=_derive_behavior(row),
        answer_text=row.get("answer_text"),
        latency_ms=row.get("latency_ms"),
        user_feedback=row.get("user_feedback"),
        estimated_cost_usd=row.get("estimated_cost_usd"),
    )


@app.get("/history", response_model=List[HistoryItem])
def history(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Most recent query_logs rows for the current user, newest first.

    Superseded by /conversations + /conversations/{id}/messages for the
    sidebar (one flat row per question vs. one row per conversation thread),
    but left in place and working in case anything else still depends on it.
    """
    client = _get_supabase_client()
    resp = (
        client.table("query_logs")
        .select(HISTORY_SELECT_FIELDS)
        .eq("user_id", current_user["id"])
        .order("timestamp", desc=True)
        .limit(limit)
        .execute()
    )

    return [_row_to_history_item(row) for row in (resp.data or [])]


@app.get("/conversations", response_model=List[ConversationSummary])
def conversations(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """One row per distinct conversation, most recent activity first.

    query_logs has no dedicated conversations table, so this groups in Python
    rather than SQL -- fetches a bounded window of the user's own rows and
    aggregates them here. Fine for an internal tool's per-user row counts;
    would want a real SQL aggregate (or a conversations table) if that stops
    being true.

    Legacy rows predating migration_003 have conversation_id = null -- each
    such row is grouped as its own single-message conversation, keyed by its
    own id, rather than merged together or dropped.
    """
    client = _get_supabase_client()
    resp = (
        client.table("query_logs")
        .select("id, conversation_id, query_text, timestamp")
        .eq("user_id", current_user["id"])
        .eq("archived", False)
        .order("timestamp", desc=False)  # ascending: first message of each conversation seen first
        .limit(2000)  # safety bound on the aggregation window, see docstring
        .execute()
    )

    grouped: Dict[str, Dict[str, Any]] = {}
    for row in resp.data or []:
        key = row.get("conversation_id") or row["id"]
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = {
                "conversation_id": key,
                "title": _truncate_title(row["query_text"]),
                "last_activity": row["timestamp"],
                "message_count": 1,
            }
        else:
            existing["message_count"] += 1
            existing["last_activity"] = row["timestamp"]  # rows are ascending -- last write wins

    ordered = sorted(grouped.values(), key=lambda c: c["last_activity"], reverse=True)
    return [ConversationSummary(**c) for c in ordered[:limit]]


@app.get("/conversations/{conversation_id}/messages", response_model=List[HistoryItem])
def conversation_messages(
    conversation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """All query_logs rows for one conversation, oldest first (so the thread
    reads top to bottom in order). `conversation_id` is either a real
    query_logs.conversation_id, or -- for a legacy pre-migration_003 row --
    that row's own id (see /conversations above).

    Scoped to user_id throughout: a conversation_id that exists but belongs to
    someone else simply matches no rows here, same as one that doesn't exist
    at all -- not distinguished, so as not to confirm/deny another user's data.
    """
    client = _get_supabase_client()

    resp = (
        client.table("query_logs")
        .select(HISTORY_SELECT_FIELDS)
        .eq("user_id", current_user["id"])
        .eq("conversation_id", conversation_id)
        .order("timestamp", desc=False)
        .execute()
    )
    rows = resp.data or []

    if not rows:
        # Not a real conversation_id -- maybe it's a legacy row's own id instead.
        legacy = (
            client.table("query_logs")
            .select(HISTORY_SELECT_FIELDS)
            .eq("user_id", current_user["id"])
            .eq("id", conversation_id)
            .is_("conversation_id", "null")
            .maybe_single()
            .execute()
        )
        if legacy and legacy.data:
            rows = [legacy.data]

    return [_row_to_history_item(row) for row in rows]


def _find_conversation_row_ids(client, conversation_id: str, user_id: str) -> List[str]:
    """query_logs.id values belonging to this conversation for this user --
    same dual lookup as /conversations/{id}/messages (a real conversation_id
    match, or the legacy single-row case where the path param is actually a
    row's own id), but only the ids, for the delete/archive/report endpoints
    below to act on. Empty list if nothing matches (not found, or not owned
    by this user -- the two are deliberately not distinguished here either).
    """
    resp = (
        client.table("query_logs")
        .select("id")
        .eq("user_id", user_id)
        .eq("conversation_id", conversation_id)
        .execute()
    )
    rows = resp.data or []
    if rows:
        return [row["id"] for row in rows]

    legacy = (
        client.table("query_logs")
        .select("id")
        .eq("user_id", user_id)
        .eq("id", conversation_id)
        .is_("conversation_id", "null")
        .maybe_single()
        .execute()
    )
    if legacy and legacy.data:
        return [legacy.data["id"]]
    return []


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    client = _get_supabase_client()
    row_ids = _find_conversation_row_ids(client, conversation_id, current_user["id"])
    if not row_ids:
        raise HTTPException(status_code=404, detail="conversation not found")

    client.table("query_logs").delete().in_("id", row_ids).execute()
    return {"status": "ok"}


@app.post("/conversations/{conversation_id}/archive")
def archive_conversation(
    conversation_id: str,
    request: ArchiveRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    client = _get_supabase_client()
    row_ids = _find_conversation_row_ids(client, conversation_id, current_user["id"])
    if not row_ids:
        raise HTTPException(status_code=404, detail="conversation not found")

    client.table("query_logs").update({"archived": request.archived}).in_("id", row_ids).execute()
    return {"status": "ok"}


@app.post("/conversations/{conversation_id}/report")
def report_conversation(
    conversation_id: str,
    request: ReportRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Persists a report flag + optional reason -- there's no admin review UI
    anywhere in this app yet, so this is only useful today via someone
    querying query_logs.reported directly in Supabase. Flagged as a known
    limitation, not silently pretended to be a full moderation feature.
    """
    client = _get_supabase_client()
    row_ids = _find_conversation_row_ids(client, conversation_id, current_user["id"])
    if not row_ids:
        raise HTTPException(status_code=404, detail="conversation not found")

    client.table("query_logs").update(
        {"reported": True, "report_reason": request.reason}
    ).in_("id", row_ids).execute()
    return {"status": "ok"}


@app.get("/eval-runs")
def eval_runs(limit: int = Query(default=10, ge=1, le=100)) -> List[Dict[str, Any]]:
    """Most recent eval_runs rows, newest first -- powers the metrics page.

    Returned as-is (all columns, no response_model) since eval_runs' shape --
    including config_snapshot's jsonb contents -- is already fully defined by
    schema.sql / run_eval.py and duplicating it here would just be another
    place to keep in sync.
    """
    client = _get_supabase_client()
    resp = (
        client.table("eval_runs")
        .select("*")
        .order("run_timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data or []
