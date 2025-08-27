import time
from pathlib import Path

from core.config_loader import load_json_config

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "agent_config.json"


def heartbeat():
    while True:
        config = load_json_config(CONFIG_PATH)
        print(f"Heartbeat from {config['agent_name']} at {time.ctime()}")
        time.sleep(config.get('heartbeat_interval', 60))

if __name__ == "__main__":
    heartbeat()
