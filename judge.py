"""
LLM-as-judge groundedness scoring for the evaluation harness.

Deliberately keeps its own GeminiChatProvider instance rather than reusing
rag_pipeline's cached one -- judging is a distinct concern (different prompt,
potentially a different/cheaper model via JUDGE_MODEL) from answer generation.
"""
import json
import sys

from config import get_settings
from providers.gemini_chat import GeminiChatProvider

JUDGE_SYSTEM_INSTRUCTION = (
    "You are a strict evaluator for an internal policy question-answering system. Given a "
    "question, a generated answer, and the context it was retrieved from, decide whether every "
    "factual claim in the answer is actually supported by that context. Judge only against the "
    "given context -- do not use outside knowledge of policy or law.\n\n"
    "Respond with ONLY a single JSON object, no markdown fences and no extra text, in exactly "
    "this shape:\n"
    '{"grounded": true or false, "score": <number 0.0-1.0>, "rationale": "one or two sentences"}\n\n'
    "score is the fraction of the answer's claims that are supported by the context "
    "(1.0 = fully grounded, 0.0 = fabricated or unsupported)."
)

STRICT_RETRY_SUFFIX = (
    "\n\nYour previous response could not be parsed as JSON. Respond with NOTHING but the raw "
    "JSON object itself -- no markdown code fences, no commentary before or after it."
)

FALLBACK_RESULT = {"grounded": None, "score": None, "rationale": "judge parsing failed"}

# Lazily-initialized singleton -- see module docstring for why this isn't rag_pipeline's.
_judge_chat_provider = None


def _get_judge_chat_provider():
    global _judge_chat_provider
    if _judge_chat_provider is None:
        settings = get_settings()
        _judge_chat_provider = GeminiChatProvider(settings.GEMINI_API_KEY, settings.JUDGE_MODEL)
    return _judge_chat_provider


def _build_judge_prompt(question, answer, context_chunks):
    context_text = "\n\n---\n\n".join(
        f"[Context {i}] ({chunk.get('title', 'Unknown')})\n{chunk.get('chunk_text', '')}"
        for i, chunk in enumerate(context_chunks, start=1)
    )
    return (
        f"Question: {question}\n\n"
        f"Generated answer: {answer}\n\n"
        f"Retrieved context:\n\n{context_text}"
    )


def _parse_judge_response(text):
    """Raises on anything that isn't the expected JSON shape; caller handles fallback."""
    text = text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[len("json"):]
        text = text.strip()

    data = json.loads(text)
    score = float(data["score"])
    score = max(0.0, min(1.0, score))

    return {
        "grounded": bool(data["grounded"]),
        "score": score,
        "rationale": str(data.get("rationale", "")),
    }


def judge_groundedness(question: str, answer: str, context_chunks: list) -> dict:
    """Ask the judge model whether `answer` is grounded in `context_chunks`.

    Tries once with the normal prompt, and once more with a stricter
    JSON-only instruction if the first response didn't parse. Falls back to
    a null-scored result (rather than raising) if both attempts fail to parse --
    an eval run should still complete even if the judge misbehaves on one item.
    """
    chat_provider = _get_judge_chat_provider()
    user_prompt = _build_judge_prompt(question, answer, context_chunks)
    messages = [{"role": "user", "content": user_prompt}]

    last_parse_error = None
    for system_instruction in (JUDGE_SYSTEM_INSTRUCTION, JUDGE_SYSTEM_INSTRUCTION + STRICT_RETRY_SUFFIX):
        generation = chat_provider.generate(messages, system_instruction=system_instruction)
        try:
            return _parse_judge_response(generation["text"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as parse_error:
            last_parse_error = parse_error

    print(f"Warning: groundedness judge response unparseable after 2 attempts: {last_parse_error}", file=sys.stderr)
    return dict(FALLBACK_RESULT)
