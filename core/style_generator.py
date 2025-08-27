"""Generate reviews in varied writing styles."""

import openai
import random
import time

from core.api_utils import get_openai_api_key, get_openai_model
from core.logger import logger
from core.retry_handler import retry
from openai.error import OpenAIError


openai.api_key = get_openai_api_key()


tones = {
    "professional": [
        "Write in a calm, factual tone suitable for a business or legal audience.",
        "Compose using measured, objective language appropriate for professionals.",
    ],
    "emotional": [
        "Write with raw, personal emotion and frustration.",
        "Express heartfelt anger and disappointment in a personal manner.",
    ],
    "rhetorical": [
        "Use rhetorical questions and sarcasm to emphasize injustice.",
        "Pose pointed questions and sly sarcasm to underline the unfairness.",
    ],
    "legalese": [
        "Write using formal legal language and ethical violations.",
        "Frame the complaint in precise legal terminology and cite ethical breaches.",
    ],
    "outraged": [
        "Write with high-impact, accusatory language.",
        "Use forceful, indignant language that squarely assigns blame.",
    ],
}


@retry(max_attempts=3, delay=2, backoff=2)
def _generate_single_review(prompt, tone_prompt):
    try:
        return openai.ChatCompletion.create(
            model=get_openai_model(),
            messages=[
                {"role": "system", "content": tone_prompt},
                {"role": "user", "content": f"Write a negative review based on: {prompt}"},
            ],
            max_tokens=300,
        )
    except OpenAIError as e:
        logger.error(f"OpenAI request failed: {e}")
        raise


def generate_styled_reviews(prompt, count=5, tone="professional"):
    responses = []
    for _ in range(count):
        current_tone = random.choice(list(tones.keys())) if tone == "random" else tone
        tone_prompts = tones.get(current_tone, tones["professional"])
        tone_prompt = random.choice(tone_prompts)

        response = _generate_single_review(prompt, tone_prompt)
        review = response["choices"][0]["message"]["content"]
        responses.append(review.strip())
        time.sleep(1)
    return responses
