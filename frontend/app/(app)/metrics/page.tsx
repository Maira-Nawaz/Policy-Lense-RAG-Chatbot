"use client";

import { useEffect, useState } from "react";

import { ApiError, getEvalRuns } from "@/lib/api";
import type { EvalRun } from "@/lib/types";
import MetricsTable from "@/components/MetricsTable";
import StatCard from "@/components/StatCard";

function formatPercent(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export default function MetricsPage() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getEvalRuns(10)
      .then((data) => {
        if (!cancelled) setRuns(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Could not load eval runs.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const latest = runs[0];
  const previous = runs[1];

  return (
    // h-full + its own overflow-y-auto -- the shared (app) layout doesn't
    // impose scrolling itself, since the chat page needs different (split)
    // scroll behavior; this page manages its own, same pattern as chat.
    <div className="h-full overflow-y-auto">
      <div className="px-6 py-8">
        <h1 className="text-lg font-semibold text-ink">Evaluation history</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Retrieval, groundedness, and refusal-correctness scores for each run of the gold eval set,
          most recent first.
        </p>

        <div className="mt-6">
          {loading && <p className="text-sm text-ink-faint">Loading...</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
          {!loading && !error && runs.length === 0 && (
            <p className="text-sm text-ink-faint">No eval runs yet -- run run_eval.py to populate this page.</p>
          )}

          {!loading && !error && latest && (
            <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatCard
                label="Retrieval precision"
                value={formatPercent(latest.retrieval_precision)}
                current={latest.retrieval_precision}
                previous={previous ? previous.retrieval_precision : null}
                higherIsBetter
              />
              <StatCard
                label="Retrieval recall"
                value={formatPercent(latest.retrieval_recall)}
                current={latest.retrieval_recall}
                previous={previous ? previous.retrieval_recall : null}
                higherIsBetter
              />
              <StatCard
                label="Groundedness rate"
                value={formatPercent(latest.groundedness_rate)}
                current={latest.groundedness_rate}
                previous={previous ? previous.groundedness_rate : null}
                higherIsBetter
              />
              <StatCard
                label="Refusal correctness"
                value={formatPercent(latest.refusal_correctness)}
                current={latest.refusal_correctness}
                previous={previous ? previous.refusal_correctness : null}
                higherIsBetter
              />
            </div>
          )}

          {!loading && !error && runs.length > 0 && <MetricsTable runs={runs} />}
        </div>
      </div>
    </div>
  );
}
