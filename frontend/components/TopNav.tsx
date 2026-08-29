"use client";

import { usePathname } from "next/navigation";

// Second line's wording is deliberately factual/specific to what the app does
// (retrieval-augmented, refuses when unsure) rather than generic AI marketing
// copy -- per-page, since the breadcrumb it replaces was also page-specific.
const PAGE_DESCRIPTIONS: Record<string, string> = {
  "/": "Ask questions about company policy -- answers are grounded in real documents, not guesses.",
  "/metrics": "Evaluation results across retrieval, groundedness, and refusal accuracy.",
};

// No account menu here -- it was a duplicate of the one already pinned to the
// bottom of the sidebar, and this bar plus ConversationMenu right below it
// were already two stacked bordered bars; removing it just leaves the brand.
export default function TopNav() {
  const pathname = usePathname();
  const description = PAGE_DESCRIPTIONS[pathname];

  return (
    <header className="border-b border-gray-300 bg-surface">
      <div className="flex w-full items-center gap-6 px-6 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-ink">PolicyLens</span>
            <span className="rounded-full bg-accent-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent">
              RAG Assistant
            </span>
          </div>
          {description && <p className="truncate text-xs text-ink-muted">{description}</p>}
        </div>
      </div>
    </header>
  );
}
