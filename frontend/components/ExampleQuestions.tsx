interface ExampleQuestion {
  preview: string;
  question: string;
  jurisdiction: string | null;
  segment: string | null;
}

// The chip itself shows a short, real question -- not a one-word category
// label that only made sense once you hovered to see the tooltip. Each spans
// a different policy area so the set shows the app's actual breadth.
const EXAMPLES: ExampleQuestion[] = [
  {
    preview: "Refund policy for enterprise customers in Germany?",
    question: "What is our refund policy for enterprise customers in Germany?",
    jurisdiction: "DE",
    segment: "enterprise",
  },
  {
    preview: "How much annual leave for full-time US employees?",
    question: "How much annual leave do full-time employees get in the US?",
    jurisdiction: "US",
    segment: "full_time",
  },
  {
    preview: "Receipt requirements for UK expense claims?",
    question: "What's the receipt requirement for expense claims in the UK?",
    jurisdiction: "UK",
    segment: null,
  },
  {
    preview: "How long is customer data retained in Germany?",
    question: "How long is customer data retained after account closure in Germany?",
    jurisdiction: "DE",
    segment: null,
  },
];

interface ExampleQuestionsProps {
  onSelect: (question: string, jurisdiction: string | null, segment: string | null) => void;
}

export default function ExampleQuestions({ onSelect }: ExampleQuestionsProps) {
  return (
    <div className="mt-5">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-faint">Try asking</p>
      <div className="flex max-w-xl flex-wrap justify-center gap-2">
        {EXAMPLES.map((example) => (
          <button
            key={example.preview}
            type="button"
            onClick={() => onSelect(example.question, example.jurisdiction, example.segment)}
            className="rounded-full border border-border bg-surface px-3 py-1.5 text-xs font-medium text-ink-muted transition-colors hover:border-accent/40 hover:text-ink"
          >
            {example.preview}
          </button>
        ))}
      </div>
    </div>
  );
}
