import openai
import time

from core.api_utils import get_openai_api_key
from core.logger import logger
from core.retry_handler import retry


openai.api_key = get_openai_api_key()


@retry(max_attempts=3, delay=2, backoff=2)
def _generate_single_review(prompt):
    return openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an assistant who writes unique, factual reviews for real experiences."},
            {"role": "user", "content": f"Write a unique negative review based on this prompt: {prompt}"},
        ],
        max_tokens=300,
    )


def generate_reviews(prompt, count=5):
    responses = []
    for _ in range(count):
        try:
            response = _generate_single_review(prompt)
            review = response["choices"][0]["message"]["content"]
            responses.append(review.strip())
            time.sleep(1)
        except Exception as e:
            logger.error(f"Failed to generate review: {e}")
    return responses
