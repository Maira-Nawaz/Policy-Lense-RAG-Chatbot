"""
Rule-based check for whether a query needs jurisdiction clarification before
retrieval even runs. Deliberately not an LLM call: it must be fast, free, and
deterministic, since it gates every request.
"""

# Substrings that suggest the query is about a policy area known to vary by
# jurisdiction (matches the corpus's 5 policy areas: refunds, data retention,
# PTO, expense reimbursement, data privacy / subject access requests).
#
# Grouped by area for readability, but matching itself is a flat "does any of
# these appear" check -- detect_ambiguity doesn't need to know which area matched.
_JURISDICTION_SENSITIVE_KEYWORDS = [
    # refunds
    "refund",
    "money back",
    "cancel",
    "cancellation",
    "reimburse",  # colloquial for "refund" too; overlaps with expense_reimbursement
    # data retention
    "retention",
    # PTO
    "pto",
    "leave",
    "vacation",
    "time off",
    "holiday",
    # expense reimbursement
    "expense",
    # data privacy / subject access requests
    "privacy",
    "data subject",
    "personal data",
    "access request",
]


def detect_ambiguity(query: str, jurisdiction_given, segment_given) -> dict:
    """Flag queries that need a jurisdiction before they can be answered confidently.

    Returns:
        {"is_ambiguous": bool, "reason": str | None}
    """
    if jurisdiction_given:
        return {"is_ambiguous": False, "reason": None}

    query_lower = query.lower()
    matched = next((kw for kw in _JURISDICTION_SENSITIVE_KEYWORDS if kw in query_lower), None)

    if matched:
        return {
            "is_ambiguous": True,
            "reason": (
                f"Query appears to be about '{matched}', a policy area that varies by "
                f"jurisdiction, but no jurisdiction was specified."
            ),
        }

    return {"is_ambiguous": False, "reason": None}
