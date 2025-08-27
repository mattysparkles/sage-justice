import openai
import json
import os

def load_config():
    with open("config/settings.json") as f:
        return json.load(f)

def generate_reviews(prompt, count=5):
    config = load_config()
    openai.api_key = config["openai_api_key"]

    responses = []
    for _ in range(count):
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an assistant who writes unique, factual reviews for real experiences."},
                {"role": "user", "content": f"Write a unique negative review based on this prompt: {prompt}"}
            ],
            max_tokens=300
        )
        review = response["choices"][0]["message"]["content"]
        responses.append(review.strip())
    return responses
