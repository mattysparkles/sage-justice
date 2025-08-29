"""Utility for registering site templates in config/templates.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict

TEMPLATES_DIR = Path("templates/sites")
CONFIG_PATH = Path("config/templates.json")


def register_site_templates(templates_dir: Path = TEMPLATES_DIR, config_path: Path = CONFIG_PATH) -> None:
    """Ensure site templates are listed in the config file.

    This function scans ``templates_dir`` for ``*.json`` files and records
    their metadata in ``config_path``. Existing entries are preserved and
    only missing templates are appended. Each entry contains the template
    ``name`` (derived from the filename) and its ``filename`` for lookup.
    """
    entries: List[Dict[str, str]] = []
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    entries = data
        except json.JSONDecodeError:
            # Invalid JSON -> start fresh
            entries = []

    known = {e.get("filename") for e in entries if isinstance(e, dict)}
    updated = False

    for tmpl_file in templates_dir.glob("*.json"):
        if tmpl_file.name in known:
            continue
        entry = {
            "name": tmpl_file.stem.replace("_", " ").title(),
            "filename": tmpl_file.name,
        }
        entries.append(entry)
        updated = True

    if updated or not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)

__all__ = ["register_site_templates"]
