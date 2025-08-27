"""Utilities for accessing OpenAI configuration values."""

import json
import os
from pathlib import Path
from typing import Any, Dict


CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _load_settings() -> Dict[str, Any]:
    """Load settings from `settings.local.json` or fallback to `settings.json`."""
    for name in ("settings.local.json", "settings.json"):
        path = CONFIG_DIR / name
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def get_openai_api_key() -> str:
    """Retrieve the OpenAI API key from environment or config file."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key

    api_key = _load_settings().get("openai_api_key")
    if api_key:
        return api_key
    raise EnvironmentError(
        "OpenAI API key not found. Set OPENAI_API_KEY env variable or provide it in config/settings.local.json.",
    )


def get_openai_model(default: str = "gpt-4") -> str:
    """Return the OpenAI model name from config or a default."""
    model = _load_settings().get("model")
    return model or default

