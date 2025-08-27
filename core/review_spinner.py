import openai

def generate_variants(prompt, n=3):
    openai.api_key = "sk-PLACEHOLDER"
    responses = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        n=n
    )
    return [choice['message']['content'] for choice in responses['choices']]
