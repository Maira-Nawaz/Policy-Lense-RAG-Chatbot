"""
Deterministic, rule-based extraction of jurisdiction/segment from a question's
natural-language text -- lets a user type "for enterprise customers in
Germany" directly instead of picking from dropdowns.

Consistent with ambiguity.py's existing approach: plain keyword matching, not
an LLM call, so this stays fast, free, and reproducible. Only used as a
fallback in api/main.py's /query handler when the caller didn't already pass
an explicit jurisdiction/segment -- test_query.py and run_eval.py call
rag_pipeline.answer_query() directly and always pass explicit values, so they
never go through this module at all.
"""
import re

# Checked in order; first match wins. None of these currently overlap, but the
# fixed order keeps behavior deterministic if that ever changes.
_JURISDICTION_PATTERNS = [
    (r"\bgermany\b", "DE"),
    (r"\bgerman\b", "DE"),
    (r"\bde\b", "DE"),
    (r"\bunited states\b", "US"),
    (r"\busa\b", "US"),
    (r"\bamerican\b", "US"),
    # Also catches the standalone code "us" -- unavoidably also matches the
    # pronoun "us" (e.g. "can you help us"). A known tradeoff of plain keyword
    # matching; not worth a heavier NLP approach for this internal tool.
    (r"\bus\b", "US"),
    (r"\bunited kingdom\b", "UK"),
    (r"\bbritain\b", "UK"),
    (r"\bbritish\b", "UK"),
    (r"\buk\b", "UK"),
]

_SEGMENT_PATTERNS = [
    (r"\benterprise\b", "enterprise"),
    (r"\bsmall business\b", "smb"),
    (r"\bsmb\b", "smb"),
    (r"\bfull-time\b", "full_time"),
    (r"\bfull time\b", "full_time"),
    (r"\bcontractors?\b", "contractor"),
]


def _first_match(text_lower: str, patterns):
    for pattern, value in patterns:
        if re.search(pattern, text_lower):
            return value
    return None


def extract_jurisdiction_segment(question: str) -> dict:
    """Best-effort extraction from a question's own wording.

    Returns {"jurisdiction": "DE" | "US" | "UK" | None, "segment": str | None}.
    Either field is None when no keyword matched -- callers should treat that
    the same as a jurisdiction/segment never having been given at all (e.g.
    rag_pipeline's existing ambiguity detection still triggers "clarify" when
    jurisdiction ends up None here and the question is jurisdiction-sensitive).
    """
    question_lower = question.lower()
    return {
        "jurisdiction": _first_match(question_lower, _JURISDICTION_PATTERNS),
        "segment": _first_match(question_lower, _SEGMENT_PATTERNS),
    }
