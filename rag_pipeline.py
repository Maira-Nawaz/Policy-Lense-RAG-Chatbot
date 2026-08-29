"""
Query-time retrieval + generation for PolicyLens.

answer_query() is the single entry point: it decides between clarify / refuse /
answer / error, and every call is logged to query_logs regardless of outcome.

Providers and the Supabase client are created lazily on first use (not at
import time) so importing this module never requires .env to be ready, and are
cached afterwards so repeated calls (e.g. from the eval harness) don't pay
reconnect / model-load cost each time.
"""
import sys
import time

from supabase import create_client

from ambiguity import detect_ambiguity
from config import get_settings
from pricing import PricingNotFoundError, estimate_cost_usd
from providers.gemini_chat import GeminiChatProvider
from providers.gemini_embedding import GeminiEmbeddingProvider
from reranker import rerank

MATCH_COUNT = 10
TOP_K = 3

# Reranker cross-encoder score below which we refuse rather than answer.
# Starting point only -- tune against eval/eval_set.json once the harness exists.
RERANK_REFUSAL_THRESHOLD = 0.0

KNOWN_JURISDICTIONS = ["DE", "US", "UK"]

SYSTEM_INSTRUCTION = (
    "You are PolicyLens, an internal assistant that answers employee questions about "
    "company policy using ONLY the policy excerpts given to you as context.\n"
    "Rules:\n"
    "1. Answer strictly from the provided context. Do not use outside knowledge.\n"
    "2. Cite the document title(s) you drew the answer from.\n"
    "3. If the context does not fully answer the question, say so explicitly rather than "
    "guessing or extrapolating from a similar-but-different policy.\n"
)

# Lazily-initialized singletons -- see module docstring.
_settings = None
_supabase_client = None
_embedding_provider = None
_chat_provider = None


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


def _get_embedding_provider():
    global _embedding_provider
    if _embedding_provider is None:
        settings = _get_settings()
        _embedding_provider = GeminiEmbeddingProvider(settings.GEMINI_API_KEY, settings.EMBEDDING_MODEL)
    return _embedding_provider


def _get_chat_provider():
    global _chat_provider
    if _chat_provider is None:
        settings = _get_settings()
        _chat_provider = GeminiChatProvider(settings.GEMINI_API_KEY, settings.GENERATION_MODEL)
    return _chat_provider


def _elapsed_ms(start):
    return int((time.monotonic() - start) * 1000)


def _clarification_message():
    return (
        "This depends on jurisdiction, and none was specified. Could you tell me which "
        f"jurisdiction applies -- {', '.join(KNOWN_JURISDICTIONS)}?"
    )


def _no_document_message(jurisdiction, segment):
    scope_parts = []
    if jurisdiction:
        scope_parts.append(f"jurisdiction '{jurisdiction}'")
    if segment:
        scope_parts.append(f"segment '{segment}'")
    scope = f" for {' / '.join(scope_parts)}" if scope_parts else ""

    return (
        f"I couldn't find a policy document{scope} that addresses this question. Rather than "
        f"guess based on a similar policy, I'm flagging this as unanswered -- please confirm "
        f"the jurisdiction/segment or check with the owning department."
    )


def _build_prompt(query, chunks):
    """Build the (messages, system_instruction) pair for the chat provider."""
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        meta = (
            f"Document: {chunk.get('title', 'Unknown')}\n"
            f"Jurisdiction: {chunk.get('jurisdiction', 'Unknown')} | "
            f"Segment: {chunk.get('segment') or 'N/A'} | "
            f"Effective: {chunk.get('effective_from', '?')} to {chunk.get('effective_to') or 'present'}"
        )
        blocks.append(f"[Excerpt {i}]\n{meta}\n\n{chunk.get('chunk_text', '')}")

    context_text = "\n\n---\n\n".join(blocks)
    user_content = f"Context (policy excerpts):\n\n{context_text}\n\nQuestion: {query}"

    return [{"role": "user", "content": user_content}], SYSTEM_INSTRUCTION


def _extract_cited_documents(top_chunks, answer_text):
    """Only count a document as cited if its title actually appears in the generated
    text -- listing every retrieved document regardless of use would misrepresent
    groundedness whenever retrieval brings back noise alongside the right document.
    """
    answer_lower = answer_text.lower()
    titles = {chunk["title"] for chunk in top_chunks if chunk.get("title")}
    cited = sorted(title for title in titles if title.lower() in answer_lower)

    if not cited:
        print("Warning: model did not cite any retrieved document title in its answer", file=sys.stderr)

    return cited


def _retrieve_and_generate(query, jurisdiction, segment, department, as_of_date, start, debug=False):
    """Steps b-h of the pipeline: embed, retrieve, rerank, generate."""
    embedding_provider = _get_embedding_provider()
    query_embedding = embedding_provider.embed_query(query)

    rpc_params = {
        "query_embedding": query_embedding,
        "match_count": MATCH_COUNT,
        "filter_jurisdiction": jurisdiction,
        "filter_segment": segment,
        "filter_department": department,
    }
    # Only include as_of_date when explicitly given -- a Postgres function's default
    # (current_date) only kicks in when the param is omitted, not when it's null, and
    # passing null here would fail every effective_from <= as_of_date comparison.
    if as_of_date is not None:
        rpc_params["as_of_date"] = as_of_date

    client = _get_supabase_client()
    rpc_response = client.rpc("match_chunks", rpc_params).execute()
    candidates = rpc_response.data or []

    if not candidates:
        return {
            "behavior": "refuse",
            "answer": _no_document_message(jurisdiction, segment),
            "retrieved_chunk_ids": [],
            "latency_ms": _elapsed_ms(start),
        }

    reranked = rerank(query, candidates, text_key="chunk_text")
    top_chunks = reranked[:TOP_K]

    # Captured before truncation so --debug can show the full score gap between the
    # relevant and irrelevant candidates that TOP_K/RERANK_REFUSAL_THRESHOLD cut between.
    debug_candidates = (
        [{"title": c.get("title"), "rerank_score": c["rerank_score"]} for c in reranked]
        if debug
        else None
    )

    if top_chunks[0]["rerank_score"] < RERANK_REFUSAL_THRESHOLD:
        result = {
            "behavior": "refuse",
            "answer": _no_document_message(jurisdiction, segment),
            "retrieved_chunk_ids": [c["chunk_id"] for c in top_chunks],
            "latency_ms": _elapsed_ms(start),
        }
        if debug:
            result["debug_candidates"] = debug_candidates
        return result

    messages, system_instruction = _build_prompt(query, top_chunks)
    chat_provider = _get_chat_provider()
    generation = chat_provider.generate(messages, system_instruction=system_instruction)

    # Computed once here since a real generation call happened (and cost real
    # tokens) regardless of which branch below the response ends up taking.
    # Best-effort: a pricing gap must never break an otherwise-successful
    # answer, so this degrades to None (rendered as "no cost shown", not a
    # fabricated $0.00) rather than raising.
    settings = _get_settings()
    try:
        estimated_cost_usd = estimate_cost_usd(
            settings.GENERATION_MODEL, generation["prompt_tokens"], generation["completion_tokens"]
        )
    except PricingNotFoundError as e:
        print(f"Warning: {e}", file=sys.stderr)
        estimated_cost_usd = None

    cited_documents = _extract_cited_documents(top_chunks, generation["text"])

    if not cited_documents:
        # The model produced an answer but didn't name any of the documents it was
        # given, despite being instructed to. That's the same signature as it having
        # silently blended/inferred from a similar-but-wrong document rather than the
        # right one -- treat it as a refusal rather than return an uncitable "answer".
        result = {
            "behavior": "refuse",
            "answer": _no_document_message(jurisdiction, segment),
            "retrieved_chunk_ids": [c["chunk_id"] for c in top_chunks],
            "latency_ms": _elapsed_ms(start),
            "forced_refusal_no_citation": True,
            "prompt_tokens": generation["prompt_tokens"],
            "completion_tokens": generation["completion_tokens"],
            "estimated_cost_usd": estimated_cost_usd,
        }
        if debug:
            result["debug_candidates"] = debug_candidates
        return result

    result = {
        "behavior": "answer",
        "answer": generation["text"],
        "retrieved_chunk_ids": [c["chunk_id"] for c in top_chunks],
        "cited_documents": cited_documents,
        "prompt_tokens": generation["prompt_tokens"],
        "completion_tokens": generation["completion_tokens"],
        "latency_ms": _elapsed_ms(start),
        "estimated_cost_usd": estimated_cost_usd,
    }
    if debug:
        result["debug_candidates"] = debug_candidates
    return result


def _log_query(query, jurisdiction, segment, result, user_id=None, conversation_id=None):
    """Best-effort write to query_logs. A logging failure must never take down
    a request that otherwise succeeded, so this only warns on stderr.

    Returns the inserted row's id (for callers -- e.g. the eval harness -- that
    need to link back to this exact call), or None if the insert failed.
    """
    try:
        client = _get_supabase_client()
        behavior = result.get("behavior")
        row = {
            "query_text": query,
            "jurisdiction_given": jurisdiction,
            "segment_given": segment,
            "user_id": user_id,
            "conversation_id": conversation_id,
            # No jurisdiction-resolution logic beyond the caller's input exists yet;
            # this mirrors jurisdiction_given until that changes.
            "resolved_jurisdiction": jurisdiction,
            "retrieved_chunk_ids": result.get("retrieved_chunk_ids", []),
            "answer_text": result.get("answer"),
            "is_refusal": behavior == "refuse",
            "is_clarification": behavior == "clarify",
            "latency_ms": result.get("latency_ms"),
            "prompt_tokens": result.get("prompt_tokens"),
            "completion_tokens": result.get("completion_tokens"),
            "estimated_cost_usd": result.get("estimated_cost_usd"),
            # A real (billable) generation call happened whenever prompt_tokens is
            # set -- that includes the forced-refusal-on-no-citation case, not just
            # "answer" -- so record which model actually served it in both cases.
            "provider": _get_settings().GENERATION_MODEL if result.get("prompt_tokens") is not None else None,
            "error_message": result.get("error_detail"),
        }
        resp = client.table("query_logs").insert(row).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception as log_error:
        print(f"Warning: failed to write query_logs row: {log_error}", file=sys.stderr)
        return None


def answer_query(
    query: str,
    jurisdiction: str = None,
    segment: str = None,
    department: str = None,
    as_of_date: str = None,
    debug: bool = False,
    user_id: str = None,
    conversation_id: str = None,
) -> dict:
    """Answer one query end to end. Always returns a dict with a "behavior" key
    of "clarify", "refuse", "answer", or "error", and logs the call.

    as_of_date (optional, "YYYY-MM-DD"): query the corpus as it stood on a past
    date instead of today -- e.g. for eval or for debugging version-conflict
    handling. Left as None for normal use, which resolves to current_date in SQL.

    debug: when True, includes a "debug_candidates" key (title + rerank_score for
    every reranked candidate, before truncation to TOP_K) for manual inspection.
    Not written to query_logs.

    user_id (optional): the Supabase Auth user id making this call, if any. Stored
    on the query_logs row so a user can be shown only their own history; None for
    unauthenticated callers (e.g. the eval harness, which has no notion of a user).

    conversation_id (optional): groups this call with other calls in the same
    conversation thread (see migration_003_add_conversation_id.sql). The caller
    (the frontend) owns generating/tracking this; None for legacy-style single-
    shot calls (e.g. the eval harness), which is exactly the "legacy row" case
    /conversations groups by the row's own id instead.

    The returned dict also includes "query_log_id" -- the id of the query_logs row
    written for this call (None if that write failed), so callers like the eval
    harness can link back to it without matching on text/timestamp.
    """
    start = time.monotonic()

    ambiguity = detect_ambiguity(query, jurisdiction, segment)
    if ambiguity["is_ambiguous"]:
        result = {
            "behavior": "clarify",
            "answer": _clarification_message(),
            "retrieved_chunk_ids": [],
            "latency_ms": _elapsed_ms(start),
        }
        result["query_log_id"] = _log_query(
            query, jurisdiction, segment, result, user_id=user_id, conversation_id=conversation_id
        )
        return result

    try:
        result = _retrieve_and_generate(query, jurisdiction, segment, department, as_of_date, start, debug=debug)
    except Exception as e:
        result = {
            "behavior": "error",
            "answer": (
                "Sorry, something went wrong while trying to answer this question. "
                "This is a system failure, not a policy determination -- please try again."
            ),
            "error_detail": str(e),
            "retrieved_chunk_ids": [],
            "latency_ms": _elapsed_ms(start),
        }

    result["query_log_id"] = _log_query(
        query, jurisdiction, segment, result, user_id=user_id, conversation_id=conversation_id
    )
    return result
