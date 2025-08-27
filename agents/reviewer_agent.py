import openai
import time
from core.review_generator import generate_review
from config.settings import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def reviewer_agent(prompt, tone='professional'):
    review = generate_review(prompt, tone)
    log_review(prompt, review, tone)
    return review

def log_review(prompt, review, tone):
    with open("logs/remote_agent.log", "a", encoding="utf-8") as log:
        log.write(f"[{time.ctime()}] Tone: {tone}\nPrompt: {prompt}\nReview: {review}\n\n")