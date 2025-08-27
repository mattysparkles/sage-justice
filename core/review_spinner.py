import openai

from core.api_utils import get_openai_api_key
from core.logger import logger
from core.retry_handler import retry
from openai.error import OpenAIError


openai.api_key = get_openai_api_key()


@retry(max_attempts=3, delay=2, backoff=2)
def _create_variants(prompt, n):
    try:
        return openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            n=n,
        )
    except OpenAIError as e:
        logger.error(f"OpenAI request failed: {e}")
        raise


def generate_variants(prompt, n=3):
    try:
        responses = _create_variants(prompt, n)
        return [choice["message"]["content"] for choice in responses["choices"]]
    except Exception as e:
        logger.error(f"Failed to generate variants: {e}")
        return []
