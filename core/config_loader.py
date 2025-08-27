import json
from pathlib import Path
from typing import Any, Dict

_config_cache: dict[Path, Dict[str, Any]] = {}
_mtime_cache: dict[Path, float] = {}

def load_json_config(path: str | Path) -> Dict[str, Any]:
    """Load a JSON configuration file with basic caching."""
    p = Path(path)
    mtime = p.stat().st_mtime if p.exists() else 0
    cached = _config_cache.get(p)
    if cached is not None and _mtime_cache.get(p) == mtime:
        return cached
    with p.open() as f:
        data = json.load(f)
    _config_cache[p] = data
    _mtime_cache[p] = mtime
    return data
