import json
import random

def load_accounts(file_path="accounts/accounts.json"):
    with open(file_path) as f:
        return json.load(f)

def get_random_account():
    accounts = load_accounts()
    return random.choice(accounts)
