import json
import time
from pathlib import Path

# Cache the configuration and reload only when the file changes
_CONFIG_CACHE = None
_CONFIG_MTIME = 0
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "agent_config.json"

def load_config():
    """Load the agent configuration with simple caching.

    The JSON file is only read when it changes on disk.
    """
    global _CONFIG_CACHE, _CONFIG_MTIME
    mtime = CONFIG_PATH.stat().st_mtime
    if _CONFIG_CACHE is None or mtime != _CONFIG_MTIME:
        with CONFIG_PATH.open() as f:
            _CONFIG_CACHE = json.load(f)
        _CONFIG_MTIME = mtime
    return _CONFIG_CACHE

def heartbeat():
    while True:
        config = load_config()
        print(f"Heartbeat from {config['agent_name']} at {time.ctime()}")
        time.sleep(config['heartbeat_interval'])

if __name__ == "__main__":
    heartbeat()
