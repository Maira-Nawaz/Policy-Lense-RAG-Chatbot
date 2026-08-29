import type { Behavior } from "@/lib/types";

// Soft solid fills, not outlines -- outlines were specifically to stay legible
// against the near-black theme; on a light/white surface a muted pastel fill
// reads cleaner and matches the screenshot's own citation-pill style.
const STYLES: Record<Behavior, { label: string; className: string }> = {
  answer: { label: "Answered", className: "bg-emerald-50 text-emerald-700" },
  clarify: { label: "Needs clarification", className: "bg-amber-50 text-amber-700" },
  refuse: { label: "Refused", className: "bg-orange-50 text-orange-700" },
  error: { label: "Error", className: "bg-red-50 text-red-700" },
};

export default function BehaviorBadge({ behavior }: { behavior: Behavior }) {
  const style = STYLES[behavior] ?? STYLES.error;

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style.className}`}
    >
      {style.label}
    </span>
  );
}
