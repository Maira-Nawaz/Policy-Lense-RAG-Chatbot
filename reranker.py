"""
Cross-encoder reranking for retrieval candidates.

Vector similarity search is a fast first pass but scores query and chunk
independently; a cross-encoder scores the (query, chunk) pair jointly and is
much better at judging actual relevance. Runs locally on CPU -- no API key.
"""
from sentence_transformers import CrossEncoder

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Loaded once at import time -- loading a CrossEncoder per call would dominate latency.
_model = CrossEncoder(MODEL_NAME)


def rerank(query, candidates, text_key="chunk_text"):
    """Score and sort candidates by relevance to query.

    Args:
        query: the search query text.
        candidates: list of dicts, each containing at least `text_key`.
        text_key: which field in each candidate dict holds the text to score.

    Returns:
        The same dicts, each with a "rerank_score" field added, sorted descending
        by that score. Empty input returns an empty list.
    """
    if not candidates:
        return []

    pairs = [(query, candidate[text_key]) for candidate in candidates]
    scores = _model.predict(pairs)

    for candidate, score in zip(candidates, scores):
        candidate["rerank_score"] = float(score)

    return sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
