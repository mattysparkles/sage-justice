import json, time
from config.agent_config import load_config

def load_config():
    with open('config/agent_config.json') as f:
        return json.load(f)

def heartbeat():
    config = load_config()
    while True:
        print(f"Heartbeat from {config['agent_name']} at {time.ctime()}")
        time.sleep(config['heartbeat_interval'])

if __name__ == "__main__":
    heartbeat()