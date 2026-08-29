"""
Central configuration for PolicyLens (ingestion and query-time pipelines).

Loads .env and exposes a single Settings instance. Fails fast with a clear
error if a required variable is missing or was left as its placeholder value,
rather than letting a script fail later with a confusing Supabase/Gemini error.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# Values that mean "the user copied .env.example but never filled this in".
_PLACEHOLDER_VALUES = {
    "",
    "YOUR_SERVICE_ROLE_KEY",
    "YOUR_DB_PASSWORD",
}


class ConfigError(RuntimeError):
    pass


def _require(name: str) -> str:
    value = os.getenv(name, "")
    if value.strip() in _PLACEHOLDER_VALUES or "YOUR_" in value:
        raise ConfigError(
            f"Required environment variable {name} is missing or still a placeholder. "
            f"Set it in .env before running the ingestion pipeline."
        )
    return value


def _require_int(name: str) -> int:
    raw = _require(name)
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(f"Environment variable {name}={raw!r} is not a valid integer.")


def _optional(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or "YOUR_" in value:
        return default
    return value


class Settings:
    def __init__(self):
        self.SUPABASE_URL = _require("SUPABASE_URL")
        self.SUPABASE_SERVICE_KEY = _require("SUPABASE_SERVICE_KEY")
        self.GEMINI_API_KEY = _require("GEMINI_API_KEY")
        self.EMBEDDING_MODEL = _require("EMBEDDING_MODEL")
        self.CHUNK_MAX_TOKENS = _require_int("CHUNK_MAX_TOKENS")
        self.CHUNK_OVERLAP_TOKENS = _require_int("CHUNK_OVERLAP_TOKENS")
        # Falls back to a sensible default rather than _require(), since
        # GeminiChatProvider itself defaults to the same model.
        self.GENERATION_MODEL = _optional("GENERATION_MODEL", "gemini-2.0-flash")
        # Deliberately independent of GENERATION_MODEL -- the judge is a distinct
        # concern (see judge.py) and may want a different/cheaper model.
        self.JUDGE_MODEL = _optional("JUDGE_MODEL", "gemini-2.0-flash")


# Instantiated lazily by callers (not at import time) so importing this module
# never raises just because .env isn't ready yet -- only get_settings() does.
def get_settings() -> Settings:
    return Settings()
