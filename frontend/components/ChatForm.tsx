"use client";

import { FormEvent, useState } from "react";

interface ChatFormProps {
  onSubmit: (question: string) => void;
  disabled: boolean;
}

export default function ChatForm({ onSubmit, disabled }: ChatFormProps) {
  const [question, setQuestion] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || disabled) return;

    onSubmit(trimmed);
    setQuestion("");
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 border-t border-border bg-surface p-4">
      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask a policy question -- mention a country or customer segment if relevant..."
          disabled={disabled}
          className="flex-1 rounded-md border border-border bg-surface-raised px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={disabled || !question.trim()}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {disabled ? "Asking..." : "Ask"}
        </button>
      </div>
    </form>
  );
}
