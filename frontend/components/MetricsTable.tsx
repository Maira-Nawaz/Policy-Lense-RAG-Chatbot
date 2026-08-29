import type { EvalRun } from "@/lib/types";

type NumericMetricKey =
  | "retrieval_precision"
  | "retrieval_recall"
  | "groundedness_rate"
  | "refusal_correctness"
  | "p50_latency_ms"
  | "p95_latency_ms"
  | "total_cost_usd";

interface MetricDef {
  key: NumericMetricKey;
  label: string;
  format: (value: number | null) => string;
  higherIsBetter: boolean;
}

function formatPercent(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function formatMs(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value)} ms`;
}

function formatCost(value: number | null): string {
  // Bare "—", consistent with every other null metric in this table (and no
  // longer a long "(not tracked yet)" string, which was itself forcing this
  // column wider than everything else now that cost tracking mostly works).
  if (value === null || value === undefined) return "—";
  return `$${value.toFixed(4)}`;
}

// Compact form ("Aug 28, 9:35 AM") instead of toLocaleString()'s full
// "8/28/2026, 9:35:54 AM" -- meaningfully narrower, and the widest column in
// the table. Full precision is still one hover away via the title attribute.
function formatRunTimestamp(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// Short header labels -- the full metric name is still spelled out in the
// stat cards above the table; here it's just trading verbosity for width so
// the whole table fits without a horizontal scrollbar at a normal window size.
const METRICS: MetricDef[] = [
  { key: "retrieval_precision", label: "Precision", format: formatPercent, higherIsBetter: true },
  { key: "retrieval_recall", label: "Recall", format: formatPercent, higherIsBetter: true },
  { key: "groundedness_rate", label: "Groundedness", format: formatPercent, higherIsBetter: true },
  { key: "refusal_correctness", label: "Refusal", format: formatPercent, higherIsBetter: true },
  { key: "p50_latency_ms", label: "p50", format: formatMs, higherIsBetter: false },
  { key: "p95_latency_ms", label: "p95", format: formatMs, higherIsBetter: false },
  { key: "total_cost_usd", label: "Cost", format: formatCost, higherIsBetter: false },
];

export function Trend({
  current,
  previous,
  higherIsBetter,
}: {
  current: number | null;
  previous: number | null;
  higherIsBetter: boolean;
}) {
  if (current === null || current === undefined || previous === null || previous === undefined) {
    return null;
  }

  const delta = current - previous;
  if (Math.abs(delta) < 1e-9) {
    return <span className="ml-1.5 text-xs text-ink-faint">no change</span>;
  }

  const improved = higherIsBetter ? delta > 0 : delta < 0;
  const arrow = delta > 0 ? "▲" : "▼";

  return (
    <span className={`ml-1.5 text-xs font-medium ${improved ? "text-emerald-600" : "text-red-600"}`}>
      {arrow}
    </span>
  );
}

export default function MetricsTable({ runs }: { runs: EvalRun[] }) {
  return (
    // White card, like the chat answer bubble -- not the dark chrome.
    <div className="overflow-x-auto rounded-lg border border-border bg-surface shadow-sm">
      <table className="w-full divide-y divide-gray-100 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="whitespace-nowrap px-3 py-2 text-left font-medium text-ink-muted">Run</th>
            {METRICS.map((metric) => (
              <th key={metric.key} className="whitespace-nowrap px-3 py-2 text-left font-medium text-ink-muted">
                {metric.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {runs.map((run, index) => {
            // Runs are sorted newest-first, so the next array element is the
            // chronologically previous run -- what each metric is trended against.
            const previous = runs[index + 1];

            return (
              <tr key={run.id} className={index === 0 ? "bg-gray-50/60" : undefined}>
                <td
                  className="whitespace-nowrap px-3 py-2.5 text-ink"
                  title={new Date(run.run_timestamp).toLocaleString()}
                >
                  {formatRunTimestamp(run.run_timestamp)}
                  {index === 0 && (
                    <span className="ml-2 rounded-full bg-accent px-2 py-0.5 text-xs font-medium text-white">
                      Latest
                    </span>
                  )}
                </td>
                {METRICS.map((metric) => {
                  const value = run[metric.key];
                  const previousValue = previous ? previous[metric.key] : null;
                  return (
                    <td key={metric.key} className="whitespace-nowrap px-3 py-2.5 text-ink">
                      {metric.format(value)}
                      {previous && (
                        <Trend current={value} previous={previousValue} higherIsBetter={metric.higherIsBetter} />
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
