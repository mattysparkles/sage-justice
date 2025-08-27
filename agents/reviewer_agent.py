import openai
import time

from core.api_utils import get_openai_api_key
from core.review_generator import generate_reviews


openai.api_key = get_openai_api_key()

def reviewer_agent(prompt, tone="professional"):
    """Generate a single review and log the result."""
    review = generate_reviews(prompt, count=1)[0]
    log_review(prompt, review, tone)
    return review

def log_review(prompt, review, tone):
    with open("logs/remote_agent.log", "a", encoding="utf-8") as log:
        log.write(f"[{time.ctime()}] Tone: {tone}\nPrompt: {prompt}\nReview: {review}\n\n")
