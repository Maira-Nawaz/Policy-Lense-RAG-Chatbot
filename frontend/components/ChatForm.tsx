"use client";

import { FormEvent, useState } from "react";

import { SlidersIcon } from "./Icons";

const JURISDICTIONS = ["Any", "DE", "US", "UK"];
const SEGMENTS = ["Any", "enterprise", "smb", "full_time", "contractor"];

interface ChatFormProps {
  onSubmit: (question: string, jurisdiction: string | null, segment: string | null) => void;
  disabled: boolean;
}

export default function ChatForm({ onSubmit, disabled }: ChatFormProps) {
  const [question, setQuestion] = useState("");
  const [jurisdiction, setJurisdiction] = useState("Any");
  const [segment, setSegment] = useState("Any");
  const [optionsOpen, setOptionsOpen] = useState(false);

  const filtersActive = jurisdiction !== "Any" || segment !== "Any";

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || disabled) return;

    onSubmit(trimmed, jurisdiction === "Any" ? null : jurisdiction, segment === "Any" ? null : segment);
    setQuestion("");
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 border-t border-border bg-surface p-4">
      {optionsOpen && (
        <div className="flex flex-col gap-3 rounded-lg border border-border bg-surface-raised p-3 sm:flex-row">
          <label className="flex flex-1 flex-col gap-1 text-xs font-medium text-ink-muted">
            Jurisdiction
            <select
              value={jurisdiction}
              onChange={(event) => setJurisdiction(event.target.value)}
              className="rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none"
            >
              {JURISDICTIONS.map((option) => (
                <option key={option} value={option}>
                  {option === "Any" ? "Any" : option}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-1 flex-col gap-1 text-xs font-medium text-ink-muted">
            Segment
            <select
              value={segment}
              onChange={(event) => setSegment(event.target.value)}
              className="rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none"
            >
              {SEGMENTS.map((option) => (
                <option key={option} value={option}>
                  {option === "Any" ? "Any" : option}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setOptionsOpen((prev) => !prev)}
          aria-expanded={optionsOpen}
          aria-label="Jurisdiction and segment options"
          className={`relative flex items-center justify-center rounded-md border px-3 text-ink-muted transition-colors hover:text-ink ${
            optionsOpen ? "border-accent/50 bg-surface-raised text-ink" : "border-border"
          }`}
        >
          <SlidersIcon className="h-4 w-4" />
          {filtersActive && !optionsOpen && (
            <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-accent" aria-hidden="true" />
          )}
        </button>

        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask a policy question..."
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
