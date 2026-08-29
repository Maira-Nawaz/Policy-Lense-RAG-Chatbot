"""
Interface every embedding backend must implement, so ingest.py can swap
providers (Gemini today, something else later) without changing call sites.
"""
from typing import List, Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    @property
    def dimension(self) -> int:
        """Output vector size, e.g. 768. Must match the `chunks.embedding` column."""
        ...

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of *documents* (task_type RETRIEVAL_DOCUMENT), one vector per input text, same order."""
        ...

    def embed_query(self, text: str) -> List[float]:
        """Embed a single *query* string (task_type RETRIEVAL_QUERY). Asymmetric models like
        Gemini's produce different vectors for query vs. document text, so this is a distinct
        method rather than a flag on embed_texts.
        """
        ...
