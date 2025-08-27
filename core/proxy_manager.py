import random

def load_proxies(file_path="config/proxies.txt"):
    with open(file_path) as f:
        return [line.strip() for line in f if line.strip()]

def get_random_proxy():
    proxies = load_proxies()
    return random.choice(proxies)
