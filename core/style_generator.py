import openai
import json
import random

def load_config():
    with open("config/settings.json") as f:
        return json.load(f)

def generate_styled_reviews(prompt, count=5, tone="professional"):
    config = load_config()
    openai.api_key = config["openai_api_key"]

    tones = {
        "professional": "Write in a calm, factual tone suitable for a business or legal audience.",
        "emotional": "Write with raw, personal emotion and frustration.",
        "rhetorical": "Use rhetorical questions and sarcasm to emphasize injustice.",
        "legalese": "Write using formal legal language and ethical violations.",
        "outraged": "Write with high-impact, accusatory language."
    }

    tone_prompt = tones.get(tone, tones["professional"])

    responses = []
    for _ in range(count):
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": tone_prompt},
                {"role": "user", "content": f"Write a negative review based on: {prompt}"}
            ],
            max_tokens=300
        )
        review = response["choices"][0]["message"]["content"]
        responses.append(review.strip())
    return responses
