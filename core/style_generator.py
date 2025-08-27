import openai
import time

from core.api_utils import get_openai_api_key
from core.logger import logger
from core.retry_handler import retry


openai.api_key = get_openai_api_key()


tones = {
    "professional": "Write in a calm, factual tone suitable for a business or legal audience.",
    "emotional": "Write with raw, personal emotion and frustration.",
    "rhetorical": "Use rhetorical questions and sarcasm to emphasize injustice.",
    "legalese": "Write using formal legal language and ethical violations.",
    "outraged": "Write with high-impact, accusatory language.",
}


@retry(max_attempts=3, delay=2, backoff=2)
def _generate_single_review(prompt, tone_prompt):
    return openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": tone_prompt},
            {"role": "user", "content": f"Write a negative review based on: {prompt}"},
        ],
        max_tokens=300,
    )


def generate_styled_reviews(prompt, count=5, tone="professional"):
    tone_prompt = tones.get(tone, tones["professional"])

    responses = []
    for _ in range(count):
        try:
            response = _generate_single_review(prompt, tone_prompt)
            review = response["choices"][0]["message"]["content"]
            responses.append(review.strip())
            time.sleep(1)
        except Exception as e:
            logger.error(f"Failed to generate styled review: {e}")
    return responses
