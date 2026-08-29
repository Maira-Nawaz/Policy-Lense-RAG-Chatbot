import { Trend } from "./MetricsTable";

interface StatCardProps {
  label: string;
  value: string;
  current: number | null;
  previous: number | null;
  higherIsBetter: boolean;
}

export default function StatCard({ label, value, current, previous, higherIsBetter }: StatCardProps) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4 shadow-sm">
      <p className="text-xs font-medium text-ink-muted">{label}</p>
      <p className="mt-1 flex items-baseline text-2xl font-semibold text-ink">
        {value}
        {previous !== null && <Trend current={current} previous={previous} higherIsBetter={higherIsBetter} />}
      </p>
    </div>
  );
}
