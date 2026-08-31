"""
Evaluation harness for PolicyLens, per the Architecture Design Document, Section 7.

Runs every item in eval/eval_set.json through rag_pipeline.answer_query(), scores
retrieval (precision/recall against expected_doc_ids), behavior correctness
(answer/clarify/refuse vs. expected_behavior), and groundedness (via judge.py for
actual "answer" results only), then writes one eval_results row per item and one
aggregate eval_runs row.

Usage:
    python3 run_eval.py                # full 35-item run
    python3 run_eval.py --limit 5      # first 5 items only, for harness debugging
    python3 run_eval.py --delay 5      # more pacing between items (free-tier rate limits)
"""
import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path

from supabase import create_client

import rag_pipeline
from config import get_settings
from judge import judge_groundedness

EVAL_SET_PATH = Path(__file__).parent / "eval" / "eval_set.json"

# expected_behavior values that are scored together as "did the system correctly
# decline to give a confident single-jurisdiction answer" (architecture doc Sec. 7).
REFUSAL_LIKE_BEHAVIORS = {"refuse", "clarify"}


# --------------------------------------------------------------------------
# Supabase lookups
# --------------------------------------------------------------------------

def _fetch_chunk_details(client, chunk_ids):
    """Resolve retrieved chunk ids to their text + owning document's external_id/title.

    One query for both retrieval scoring (needs external_id) and judge context
    (needs chunk_text), rather than two separate round trips. Order is preserved
    to match `chunk_ids`; ids that no longer resolve (shouldn't happen, but a
    deleted/re-ingested doc could cause it) are silently skipped.
    """
    if not chunk_ids:
        return []

    resp = (
        client.table("chunks")
        .select("id, chunk_text, documents(external_id, title)")
        .in_("id", chunk_ids)
        .execute()
    )
    by_id = {row["id"]: row for row in (resp.data or [])}

    details = []
    for chunk_id in chunk_ids:
        row = by_id.get(chunk_id)
        if not row:
            continue
        doc = row.get("documents")
        if isinstance(doc, list):  # supabase-py may return the embedded relation as a list
            doc = doc[0] if doc else None
        details.append(
            {
                "chunk_id": chunk_id,
                "external_id": (doc or {}).get("external_id"),
                "title": (doc or {}).get("title"),
                "chunk_text": row.get("chunk_text", ""),
            }
        )
    return details


def _fetch_previous_eval_run(client):
    resp = (
        client.table("eval_runs")
        .select("*")
        .order("run_timestamp", desc=True)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


# --------------------------------------------------------------------------
# Per-item scoring
# --------------------------------------------------------------------------

def _score_retrieval(expected_doc_ids, retrieved_external_ids):
    """Precision/recall/correctness for one answerable gold item.

    Convention: if nothing was retrieved at all, precision and recall are both
    0.0 (not undefined) -- a total retrieval miss should score as a miss, not
    be excluded from the average.
    """
    expected = set(expected_doc_ids)
    retrieved = set(retrieved_external_ids)
    matched = expected & retrieved

    recall = len(matched) / len(expected) if expected else None
    precision = (len(matched) / len(retrieved)) if retrieved else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "retrieval_correct": expected.issubset(retrieved),
    }


def _behavior_correct(expected_behavior, actual_behavior):
    # A system failure is never "correct", even if the gold item happened to
    # expect refuse/clarify -- an error is not the same thing as a deliberate refusal.
    if actual_behavior == "error":
        return False
    return actual_behavior == expected_behavior


def _percentile(values, pct):
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * (pct / 100)
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return values[int(k)]
    return values[lo] * (hi - k) + values[hi] * (k - lo)


def _run_item(client, item):
    """Run one gold item through the pipeline and score it. Returns a dict with
    everything needed for both the eval_results row and console reporting.
    """
    result = rag_pipeline.answer_query(
        item["question"],
        jurisdiction=item.get("jurisdiction_given"),
        segment=item.get("segment_given"),
    )
    actual_behavior = result["behavior"]

    chunk_details = _fetch_chunk_details(client, result.get("retrieved_chunk_ids", []))
    retrieved_external_ids = [c["external_id"] for c in chunk_details if c["external_id"]]

    retrieval_score = None
    if item["expected_behavior"] == "answer":
        retrieval_score = _score_retrieval(item["expected_doc_ids"], retrieved_external_ids)

    groundedness = None
    if actual_behavior == "answer":
        groundedness = judge_groundedness(item["question"], result["answer"], chunk_details)

    return {
        "item": item,
        "result": result,
        "actual_behavior": actual_behavior,
        "behavior_correct": _behavior_correct(item["expected_behavior"], actual_behavior),
        "retrieval_score": retrieval_score,
        "groundedness": groundedness,
    }


# --------------------------------------------------------------------------
# Console reporting
# --------------------------------------------------------------------------

def _print_progress(index, total, run_result):
    item = run_result["item"]
    result = run_result["result"]
    actual = run_result["actual_behavior"]

    if actual == "error":
        status = "SYSTEM FAILURE"
    elif run_result["behavior_correct"]:
        status = "PASS"
    else:
        status = "FAIL"

    line = (
        f"[{index}/{total}] {item['id']} ({item['category']}) "
        f"expected={item['expected_behavior']} actual={actual} -> {status} "
        f"({result.get('latency_ms')} ms)"
    )

    if run_result["groundedness"] and run_result["groundedness"]["score"] is not None:
        line += f"  grounded={run_result['groundedness']['grounded']} score={run_result['groundedness']['score']:.2f}"
    if actual == "error":
        line += f"  error={result.get('error_detail')}"

    print(line)


def _print_category_breakdown(run_results):
    by_category = {}
    for r in run_results:
        by_category.setdefault(r["item"]["category"], []).append(r)

    print("\n--- By category ---")
    for category in sorted(by_category):
        items = by_category[category]
        correct = sum(1 for r in items if r["behavior_correct"])
        print(f"  {category}: {correct}/{len(items)} correct")


def _print_delta(previous, current):
    if previous is None:
        print("\n(no previous eval_runs row -- this is the first tracked run)")
        return

    print("\n--- Delta vs. previous run ---")
    fields = [
        ("retrieval_precision", "Retrieval precision"),
        ("retrieval_recall", "Retrieval recall"),
        ("groundedness_rate", "Groundedness rate"),
        ("refusal_correctness", "Refusal correctness"),
        ("p50_latency_ms", "p50 latency (ms)"),
        ("p95_latency_ms", "p95 latency (ms)"),
    ]
    for key, label in fields:
        prev_value = previous.get(key)
        curr_value = current.get(key)
        if prev_value is None or curr_value is None:
            print(f"  {label}: {curr_value} (previous: {prev_value})")
            continue
        delta = curr_value - prev_value
        sign = "+" if delta >= 0 else ""
        print(f"  {label}: {curr_value:.3f} ({sign}{delta:.3f})" if isinstance(curr_value, float)
              else f"  {label}: {curr_value} ({sign}{delta})")


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------

def _aggregate(run_results):
    answerable = [r for r in run_results if r["item"]["expected_behavior"] == "answer"]
    refusal_like = [r for r in run_results if r["item"]["expected_behavior"] in REFUSAL_LIKE_BEHAVIORS]
    answered = [r for r in run_results if r["actual_behavior"] == "answer"]
    graded = [r for r in answered if r["groundedness"] and r["groundedness"]["score"] is not None]

    # retrieval_score is None for items that hit a harness-level system failure
    # (e.g. a transient network error) before retrieval could even run -- skip
    # those rather than let one flaky item crash the whole run's aggregation.
    precisions = [r["retrieval_score"]["precision"] for r in answerable if r["retrieval_score"]]
    recalls = [r["retrieval_score"]["recall"] for r in answerable if r["retrieval_score"]]
    latencies = [r["result"]["latency_ms"] for r in run_results if r["result"].get("latency_ms") is not None]
    # Each run_result["result"] is exactly the dict answer_query() returned for
    # that item, which is also what got written to that item's query_logs row
    # -- summing it here in memory is equivalent to (and cheaper than) reading
    # it back out of query_logs by query_log_id, since it's the same value.
    costs = [r["result"]["estimated_cost_usd"] for r in run_results if r["result"].get("estimated_cost_usd") is not None]

    return {
        "retrieval_precision": statistics.mean(precisions) if precisions else None,
        "retrieval_recall": statistics.mean(recalls) if recalls else None,
        "groundedness_rate": statistics.mean(r["groundedness"]["score"] for r in graded) if graded else None,
        "refusal_correctness": (
            sum(1 for r in refusal_like if r["behavior_correct"]) / len(refusal_like) if refusal_like else None
        ),
        # int() to match the eval_runs.p50_latency_ms/p95_latency_ms `int` columns --
        # _percentile can return a float due to linear interpolation between ranks.
        "p50_latency_ms": round(_percentile(latencies, 50)) if latencies else None,
        "p95_latency_ms": round(_percentile(latencies, 95)) if latencies else None,
        # NOTE: this only sums the *generation* cost from each item's own
        # answer_query() call -- it does not include judge_groundedness()'s own
        # generation calls (judge.py doesn't track/return token counts today),
        # so this understates the true cost of running the eval harness itself.
        "total_cost_usd": sum(costs) if costs else None,
    }


def _build_config_snapshot(settings):
    return {
        "embedding_model": settings.EMBEDDING_MODEL,
        "generation_model": settings.GENERATION_MODEL,
        "judge_model": settings.JUDGE_MODEL,
        "rerank_refusal_threshold": rag_pipeline.RERANK_REFUSAL_THRESHOLD,
        "top_k": rag_pipeline.TOP_K,
        "match_count": rag_pipeline.MATCH_COUNT,
        "chunk_max_tokens": settings.CHUNK_MAX_TOKENS,
        "chunk_overlap_tokens": settings.CHUNK_OVERLAP_TOKENS,
    }


def main():
    parser = argparse.ArgumentParser(description="Run the PolicyLens gold eval set through the RAG pipeline.")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N items (for debugging the harness).")
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds to sleep between items, to stay under free-tier rate limits (default: 2).",
    )
    args = parser.parse_args()

    settings = get_settings()
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    eval_set = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    items = eval_set["items"]
    if args.limit is not None:
        items = items[: args.limit]

    previous_run = _fetch_previous_eval_run(client)

    print(f"Running {len(items)} eval item(s)...\n")

    run_results = []
    for index, item in enumerate(items, start=1):
        try:
            run_result = _run_item(client, item)
        except Exception as e:
            # _run_item itself failing (not answer_query -- that already catches its own
            # errors into behavior="error") means something in the harness broke, e.g. the
            # judge's API call exhausting retries. Record it as a system failure and continue
            # -- one bad item must not sink a 35-item run.
            print(f"[{index}/{len(items)}] {item['id']}: HARNESS ERROR -- {e}", file=sys.stderr)
            run_result = {
                "item": item,
                "result": {"behavior": "error", "answer": None, "latency_ms": None, "retrieved_chunk_ids": [], "query_log_id": None},
                "actual_behavior": "error",
                "behavior_correct": False,
                "retrieval_score": None,
                "groundedness": None,
            }

        run_results.append(run_result)
        _print_progress(index, len(items), run_result)

        # Each item makes 2 LLM calls (generate + judge) -- pace them proactively
        # rather than relying entirely on reactive 429 retries.
        if args.delay > 0 and index < len(items):
            time.sleep(args.delay)

    aggregates = _aggregate(run_results)
    config_snapshot = _build_config_snapshot(settings)

    eval_run_resp = (
        client.table("eval_runs")
        .insert({**aggregates, "config_snapshot": config_snapshot})
        .execute()
    )
    eval_run_id = eval_run_resp.data[0]["id"]

    eval_results_rows = [
        {
            "eval_run_id": eval_run_id,
            "eval_item_id": r["item"]["id"],
            "expected_behavior": r["item"]["expected_behavior"],
            "actual_behavior": r["actual_behavior"],
            "retrieval_correct": r["retrieval_score"]["retrieval_correct"] if r["retrieval_score"] else None,
            "groundedness_score": r["groundedness"]["score"] if r["groundedness"] else None,
            "behavior_correct": r["behavior_correct"],
            "query_log_id": r["result"].get("query_log_id"),
        }
        for r in run_results
    ]
    client.table("eval_results").insert(eval_results_rows).execute()

    # --- Summary ---
    print("\n=== Summary ===")
    print(f"Items run: {len(run_results)}")
    system_failures = [r for r in run_results if r["actual_behavior"] == "error"]
    print(f"System failures (not eval misses): {len(system_failures)}")
    behavior_correct_count = sum(1 for r in run_results if r["behavior_correct"])
    print(f"Behavior correct: {behavior_correct_count}/{len(run_results)}")

    def _fmt(value):
        return f"{value:.3f}" if isinstance(value, float) else str(value)

    print(f"Retrieval precision: {_fmt(aggregates['retrieval_precision'])}")
    print(f"Retrieval recall: {_fmt(aggregates['retrieval_recall'])}")
    print(f"Groundedness rate: {_fmt(aggregates['groundedness_rate'])}")
    print(f"Refusal correctness: {_fmt(aggregates['refusal_correctness'])}")
    print(f"p50 latency: {aggregates['p50_latency_ms']} ms")
    print(f"p95 latency: {aggregates['p95_latency_ms']} ms")
    total_cost = aggregates["total_cost_usd"]
    cost_note = "generation only -- excludes judge_groundedness() calls" if total_cost is not None else "no priced calls"
    print(f"Total cost (USD): {_fmt(total_cost)} ({cost_note})")

    _print_category_breakdown(run_results)
    _print_delta(previous_run, aggregates)

    print(f"\neval_runs.id = {eval_run_id}")


if __name__ == "__main__":
    main()
