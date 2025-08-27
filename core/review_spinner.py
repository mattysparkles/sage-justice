import openai

from core.api_utils import get_openai_api_key
from core.logger import logger
from core.retry_handler import retry


openai.api_key = get_openai_api_key()


@retry(max_attempts=3, delay=2, backoff=2)
def _create_variants(prompt, n):
    return openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        n=n,
    )


def generate_variants(prompt, n=3):
    try:
        responses = _create_variants(prompt, n)
        return [choice["message"]["content"] for choice in responses["choices"]]
    except Exception as e:
        logger.error(f"Failed to generate variants: {e}")
        return []
