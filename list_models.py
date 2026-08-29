"""
Lists every Gemini model currently available to this API key, straight from the
API -- so we stop hardcoding model names from docs/web search that can quietly
go stale when Google retires a model mid-project.

Usage:
    python3 list_models.py
"""
import json

from google import genai

from config import get_settings


def _model_actions(model):
    """The field name for "what this model can do" has moved between SDK/API
    versions, so check a few known candidates instead of assuming one.
    """
    for attr in ("supported_actions", "supported_generation_methods"):
        value = getattr(model, attr, None)
        if value is not None:
            return value
    return None


def main():
    settings = get_settings()
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    print("Fetching live model list from the Gemini API...\n")

    count = 0
    for model in client.models.list():
        count += 1
        name = getattr(model, "name", "<unknown>")
        actions = _model_actions(model)

        generates = actions is not None and "generateContent" in actions
        embeds = actions is not None and "embedContent" in actions

        print(name)
        print(f"  generateContent: {generates}   embedContent: {embeds}")
        if actions is not None:
            print(f"  supported_actions: {actions}")

        # Full raw shape too -- so if the fields above are wrong for your SDK
        # version, the real field names are right here rather than guessed at.
        if hasattr(model, "model_dump"):
            print(f"  raw: {json.dumps(model.model_dump(), default=str)}")
        else:
            print(f"  raw: {model!r}")
        print()

    print(f"--- {count} model(s) total ---")


if __name__ == "__main__":
    main()
