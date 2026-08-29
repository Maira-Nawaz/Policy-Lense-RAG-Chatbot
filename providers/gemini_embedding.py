"""
Gemini implementation of EmbeddingProvider, using the current `google-genai` SDK
(not the deprecated `google-generativeai` package).
"""
import re
import time

from google import genai
from google.genai import types

EXPECTED_DIMENSION = 768
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0

# Used when a 429 doesn't carry a parseable retryDelay -- free-tier quota windows
# are typically ~60s, so a short exponential backoff just burns through retries
# without ever actually waiting long enough to matter.
RATE_LIMIT_FALLBACK_WAIT_SECONDS = 20.0

# Matches e.g. "retryDelay": "13s" (also 'retryDelay': 13s or retryDelay=13s) inside
# whatever the SDK's stringified error/response happens to look like.
_RETRY_DELAY_RE = re.compile(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", re.IGNORECASE)


class EmbeddingError(RuntimeError):
    pass


def _is_rate_limit_error(error) -> bool:
    code = getattr(error, "code", None)
    status = getattr(error, "status", None)
    text = str(error)
    return code == 429 or status == "RESOURCE_EXHAUSTED" or "429" in text or "RESOURCE_EXHAUSTED" in text


def _parse_retry_delay_seconds(error):
    """Extract the server-suggested retry delay (e.g. from a RetryInfo detail
    embedded in the error) if present. Returns None if it can't be found.
    """
    match = _RETRY_DELAY_RE.search(str(error))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


class GeminiEmbeddingProvider:
    def __init__(self, api_key: str, model: str):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    @property
    def dimension(self) -> int:
        return EXPECTED_DIMENSION

    def embed_texts(self, texts):
        """Embed each text individually (the API is called one text at a time,
        per requirements), retrying transient failures with exponential backoff.
        """
        return [self._embed_one(text, task_type="RETRIEVAL_DOCUMENT") for text in texts]

    def embed_query(self, text: str):
        """Embed a single search query. Gemini's embedding models are asymmetric --
        query and document text must be embedded with different task_type values to
        land in the same similarity space -- so this is kept separate from embed_texts.
        """
        return self._embed_one(text, task_type="RETRIEVAL_QUERY")

    def _embed_one(self, text: str, task_type: str):
        last_error = None
        backoff = INITIAL_BACKOFF_SECONDS

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = self._client.models.embed_content(
                    model=self._model,
                    contents=text,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=EXPECTED_DIMENSION,
                    ),
                )
                embedding = result.embeddings[0].values

                if len(embedding) != EXPECTED_DIMENSION:
                    raise EmbeddingError(
                        f"Gemini returned a {len(embedding)}-dimensional embedding, "
                        f"expected {EXPECTED_DIMENSION}. Check EMBEDDING_MODEL / the "
                        f"chunks.embedding column dimension."
                    )

                return embedding

            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    if _is_rate_limit_error(e):
                        wait = _parse_retry_delay_seconds(e) or RATE_LIMIT_FALLBACK_WAIT_SECONDS
                        time.sleep(wait)
                    else:
                        time.sleep(backoff)
                        backoff *= 2

        raise EmbeddingError(
            f"Failed to embed text after {MAX_RETRIES} attempts: {last_error}"
        ) from last_error
