"""
One-time backfill for cost tracking (see PART 1's fix in rag_pipeline.py for
the live pipeline). Run this once, manually, after confirming the live fix
works on a fresh query:

    python3 backfill_costs.py

What it does, in order:
  1. Every query_logs row that has prompt_tokens/completion_tokens set but
     estimated_cost_usd still null (i.e. logged before the live fix existed)
     gets its cost computed from pricing.py and written in.
  2. Every eval_runs row gets its total_cost_usd re-summed from the (now
     backfilled) estimated_cost_usd of its eval_results' linked query_logs rows.

Rows/runs that can't be priced (missing provider, or a provider with no
pricing.py entry) are skipped with a printed note, not treated as fatal --
one bad row must not sink the whole backfill.
"""
import sys

from supabase import create_client

from config import get_settings
from pricing import PricingNotFoundError, estimate_cost_usd


def _get_client():
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def backfill_query_logs(client) -> tuple[int, int]:
    """Returns (updated_count, skipped_count)."""
    resp = (
        client.table("query_logs")
        .select("id, provider, prompt_tokens, completion_tokens")
        .is_("estimated_cost_usd", "null")
        .not_.is_("prompt_tokens", "null")
        .not_.is_("completion_tokens", "null")
        .execute()
    )
    rows = resp.data or []

    updated = 0
    skipped = 0
    for row in rows:
        provider = row.get("provider")
        if not provider:
            print(f"  skip query_logs.id={row['id']}: no provider recorded, can't price it")
            skipped += 1
            continue

        try:
            cost = estimate_cost_usd(provider, row["prompt_tokens"], row["completion_tokens"])
        except PricingNotFoundError as e:
            print(f"  skip query_logs.id={row['id']}: {e}")
            skipped += 1
            continue

        client.table("query_logs").update({"estimated_cost_usd": cost}).eq("id", row["id"]).execute()
        updated += 1

    return updated, skipped


def backfill_eval_runs(client) -> tuple[int, int]:
    """Returns (updated_count, skipped_count)."""
    eval_runs_resp = client.table("eval_runs").select("id").execute()
    eval_run_ids = [row["id"] for row in (eval_runs_resp.data or [])]

    updated = 0
    skipped = 0
    for eval_run_id in eval_run_ids:
        results_resp = (
            client.table("eval_results")
            .select("query_log_id")
            .eq("eval_run_id", eval_run_id)
            .execute()
        )
        query_log_ids = [r["query_log_id"] for r in (results_resp.data or []) if r.get("query_log_id")]

        if not query_log_ids:
            print(f"  skip eval_runs.id={eval_run_id}: no linked query_logs rows")
            skipped += 1
            continue

        logs_resp = (
            client.table("query_logs")
            .select("id, estimated_cost_usd")
            .in_("id", query_log_ids)
            .execute()
        )
        costs = [
            row["estimated_cost_usd"] for row in (logs_resp.data or []) if row.get("estimated_cost_usd") is not None
        ]

        if not costs:
            print(f"  skip eval_runs.id={eval_run_id}: none of its query_logs rows have a cost (even after backfill)")
            skipped += 1
            continue

        total_cost = sum(costs)
        client.table("eval_runs").update({"total_cost_usd": total_cost}).eq("id", eval_run_id).execute()
        updated += 1

    return updated, skipped


def main():
    client = _get_client()

    print("=== Step 1: backfilling query_logs.estimated_cost_usd ===")
    logs_updated, logs_skipped = backfill_query_logs(client)
    print(f"query_logs -- updated: {logs_updated}, skipped: {logs_skipped}\n")

    print("=== Step 2: re-summing eval_runs.total_cost_usd ===")
    runs_updated, runs_skipped = backfill_eval_runs(client)
    print(f"eval_runs -- updated: {runs_updated}, skipped: {runs_skipped}")

    if logs_skipped or runs_skipped:
        print(
            "\nSome rows were skipped (see notes above) -- usually a missing provider "
            "or a model not yet in pricing.py. Add the missing pricing.py entry and "
            "re-run this script if you want those backfilled too; it's safe to run "
            "again (already-priced rows are left untouched).",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
