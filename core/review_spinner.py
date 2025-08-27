"""Generate alternative phrasings for existing reviews."""

import openai

from core.api_utils import get_openai_api_key, get_openai_model
from core.logger import logger
from core.retry_handler import retry
from openai.error import OpenAIError


openai.api_key = get_openai_api_key()


@retry(max_attempts=3, delay=2, backoff=2)
def _create_variants(prompt, n):
    try:
        return openai.ChatCompletion.create(
            model=get_openai_model(),
            messages=[{"role": "user", "content": prompt}],
            n=n,
        )
    except OpenAIError as e:
        logger.error(f"OpenAI request failed: {e}")
        raise


def generate_variants(prompt, n=3):
    responses = _create_variants(prompt, n)
    return [choice["message"]["content"] for choice in responses["choices"]]
