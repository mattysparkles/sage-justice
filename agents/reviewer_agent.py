import json
import openai
import os
import time
from core.review_generator import generate_reviews


def load_api_key():
    """Fetch the OpenAI API key from the environment or settings.json."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            with open("config/settings.json", "r", encoding="utf-8") as f:
                api_key = json.load(f).get("openai_api_key")
        except FileNotFoundError:
            api_key = None
    return api_key


openai.api_key = load_api_key()

def reviewer_agent(prompt, tone="professional"):
    """Generate a single review and log the result."""
    review = generate_reviews(prompt, count=1)[0]
    log_review(prompt, review, tone)
    return review

def log_review(prompt, review, tone):
    with open("logs/remote_agent.log", "a", encoding="utf-8") as log:
        log.write(f"[{time.ctime()}] Tone: {tone}\nPrompt: {prompt}\nReview: {review}\n\n")
