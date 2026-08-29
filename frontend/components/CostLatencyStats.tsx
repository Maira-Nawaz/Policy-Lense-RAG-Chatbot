import { ClockIcon } from "./Icons";

function formatLatency(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/**
 * Latency only -- per-answer cost was removed from this footer per feedback
 * (it read as noise next to the answer itself). Cost is still tracked end to
 * end (query_logs.estimated_cost_usd, summed into eval_runs.total_cost_usd on
 * the Metrics page); this component just no longer surfaces it per-message.
 */
export default function CostLatencyStats({ latencyMs }: { latencyMs: number }) {
  return (
    <div className="mt-3 flex items-center gap-4 text-xs text-ink-faint">
      <span className="inline-flex items-center gap-1" title="Response latency">
        <ClockIcon className="h-3.5 w-3.5" />
        {formatLatency(latencyMs)}
      </span>
    </div>
  );
}
