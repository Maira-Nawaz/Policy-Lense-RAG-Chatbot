"""
USD-per-million-token pricing for Gemini models, used to estimate the cost of
each answer_query() call (and, via backfill_costs.py, historical rows).

Rates below are the standard (non-batch) tier, cross-checked against
https://ai.google.dev/gemini-api/docs/pricing directly on 2026-08-28. Google
changes these over time -- if a number here looks stale, re-check that page
before trusting it.
"""

# {model: {"input": USD per 1M input/prompt tokens, "output": USD per 1M output/completion tokens}}
# Embedding models have no "output" (there's no completion, just an input
# embed), so their entries set "output" to 0.0.
PRICING_PER_MILLION_TOKENS = {
    # Sourced directly from the pricing page on 2026-08-28.
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
    "gemini-3.5-flash": {"input": 1.50, "output": 9.00},
    # Introductory pricing through 2026-12-31; steps up to $1.50/$7.50 on
    # 2027-01-01 per the same pricing page -- update this then.
    "gemini-3.6-flash": {"input": 0.75, "output": 3.75},
    "gemini-embedding-001": {"input": 0.15, "output": 0.0},
    # "-latest" is a rolling alias -- Google prices whatever concrete model it
    # currently points to, not the alias name itself, so there's no page to
    # confirm this against directly. This uses the gemini-2.5-flash-lite rate
    # as a best-effort placeholder. If GENERATION_MODEL/JUDGE_MODEL in .env is
    # still "gemini-flash-lite-latest", verify which concrete model that
    # currently resolves to (e.g. via list_models.py) and correct this if it's
    # actually pointing at something pricier, like 3.1-flash-lite.
    "gemini-flash-lite-latest": {"input": 0.10, "output": 0.40},
}


class PricingNotFoundError(KeyError):
    """Raised when `model` has no entry in PRICING_PER_MILLION_TOKENS.

    Callers that want cost tracking to be best-effort (never crash the actual
    request over a pricing gap) should catch this specifically, rather than
    let a lookup miss silently turn into a wrong $0.00.
    """


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """USD cost estimate for one generation (or embedding) call."""
    if model not in PRICING_PER_MILLION_TOKENS:
        raise PricingNotFoundError(f"No pricing entry for model {model!r}")

    rates = PRICING_PER_MILLION_TOKENS[model]
    input_cost = (prompt_tokens / 1_000_000) * rates["input"]
    output_cost = (completion_tokens / 1_000_000) * rates["output"]
    return input_cost + output_cost
