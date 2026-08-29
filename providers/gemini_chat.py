"""
Gemini implementation of ChatProvider, using the current `google-genai` SDK.
"""
import re
import time

from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-2.0-flash"
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0

# Used when a 429 doesn't carry a parseable retryDelay -- free-tier quota windows
# are typically ~60s, so a short exponential backoff just burns through retries
# without ever actually waiting long enough to matter.
RATE_LIMIT_FALLBACK_WAIT_SECONDS = 20.0

_ROLE_MAP = {"user": "user", "assistant": "model", "model": "model"}

# Matches e.g. "retryDelay": "13s" (also 'retryDelay': 13s or retryDelay=13s) inside
# whatever the SDK's stringified error/response happens to look like.
_RETRY_DELAY_RE = re.compile(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", re.IGNORECASE)


class ChatError(RuntimeError):
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


class GeminiChatProvider:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(self, messages, system_instruction=None, **kwargs):
        contents = self._to_contents(messages)
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            **kwargs,
        )

        last_error = None
        backoff = INITIAL_BACKOFF_SECONDS

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=config,
                )
                return self._parse_response(response, messages)
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    if _is_rate_limit_error(e):
                        wait = _parse_retry_delay_seconds(e) or RATE_LIMIT_FALLBACK_WAIT_SECONDS
                        time.sleep(wait)
                    else:
                        time.sleep(backoff)
                        backoff *= 2

        raise ChatError(
            f"Failed to generate a response after {MAX_RETRIES} attempts: {last_error}"
        ) from last_error

    @staticmethod
    def _to_contents(messages):
        return [
            types.Content(role=_ROLE_MAP.get(m["role"], "user"), parts=[types.Part(text=m["content"])])
            for m in messages
        ]

    @staticmethod
    def _parse_response(response, messages):
        text = response.text or ""

        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        completion_tokens = getattr(usage, "candidates_token_count", None) if usage else None

        if prompt_tokens is None:
            # Fallback: rough word-count estimate when the API doesn't report usage.
            prompt_tokens = sum(len(m["content"].split()) for m in messages)
        if completion_tokens is None:
            completion_tokens = len(text.split())

        return {
            "text": text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
