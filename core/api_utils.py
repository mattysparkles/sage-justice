import json
import os
from pathlib import Path


def get_openai_api_key():
    """Retrieve the OpenAI API key from environment or config file."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key

    config_path = Path(__file__).resolve().parent.parent / "config" / "settings.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                api_key = data.get("openai_api_key")
                if api_key:
                    return api_key
        except json.JSONDecodeError:
            pass
    raise EnvironmentError(
        "OpenAI API key not found. Set OPENAI_API_KEY env variable or provide it in config/settings.json."
    )
