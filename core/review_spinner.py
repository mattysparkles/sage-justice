"""Generate alternative phrasings for existing reviews with tone control."""

from __future__ import annotations

import openai
import random

from core.api_utils import get_openai_api_key, get_openai_model
from core.logger import logger
from core.retry_handler import retry
from core.style_generator import tones
from openai.error import OpenAIError


openai.api_key = get_openai_api_key()


@retry(max_attempts=3, delay=2, backoff=2)
def _create_variants(prompt: str, n: int, tone: str | None):
    messages = []
    if tone and tone in tones:
        tone_prompt = random.choice(tones[tone])
        messages.append(
            {
                "role": "system",
                "content": f"{tone_prompt} Rewrite the provided review text into a new variation while preserving its facts.",
            }
        )
    else:
        messages.append(
            {
                "role": "system",
                "content": "Rewrite the provided review text into a new variation while preserving its facts.",
            }
        )
    messages.append({"role": "user", "content": prompt})
    try:
        return openai.ChatCompletion.create(
            model=get_openai_model(),
            messages=messages,
            n=n,
        )
    except OpenAIError as e:
        logger.error(f"OpenAI request failed: {e}")
        raise


def generate_variants(prompt: str, n: int = 3, tone: str | None = None):
    responses = _create_variants(prompt, n, tone)
    return [choice["message"]["content"].strip() for choice in responses["choices"]]
