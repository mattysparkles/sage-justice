import json

def load_template(path):
    with open(path, "r") as f:
        return json.load(f)

def save_template(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)