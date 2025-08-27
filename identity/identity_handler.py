
import random, json

class IdentityHandler:
    def __init__(self, identity_file='config/identities.json'):
        with open(identity_file, 'r') as f:
            self.identities = json.load(f)
        self.index = 0

    def get_next_identity(self):
        identity = self.identities[self.index % len(self.identities)]
        self.index += 1
        return identity
