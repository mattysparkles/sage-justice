# Utilities for managing site configuration registry
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

SITE_DIR = Path("templates/sites")
REGISTRY_PATH = Path("config/site_registry.json")


def load_registry() -> List[Dict[str, Any]]:
    if REGISTRY_PATH.exists():
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except json.JSONDecodeError:
            pass
    return []


def save_registry(data: List[Dict[str, Any]]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def build_registry_from_files() -> List[Dict[str, Any]]:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    registry: List[Dict[str, Any]] = []
    for file in SITE_DIR.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            continue
        registry.append(
            {
                "name": data.get("site", file.stem),
                "filename": file.name,
                "category": data.get("category", ""),
                "requires_login": bool(data.get("requires_login", False)),
                "captcha": data.get("captcha", "none"),
            }
        )
    save_registry(registry)
    return registry


def get_sites() -> List[Dict[str, Any]]:
    registry = load_registry()
    if not registry:
        registry = build_registry_from_files()
    return registry


def get_site(site_name: str) -> Dict[str, Any]:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    path = SITE_DIR / site_name
    if not path.exists():
        path = SITE_DIR / f"{site_name}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_site(data: Dict[str, Any]) -> str:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    name = data.get("site")
    if not name:
        raise ValueError("'site' field required")
    filename = f"{name.lower().replace(' ', '_')}.json"
    path = SITE_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    registry = [r for r in load_registry() if r.get("filename") != filename and r.get("name") != name]
    registry.append(
        {
            "name": name,
            "filename": filename,
            "category": data.get("category", ""),
            "requires_login": bool(data.get("requires_login", False)),
            "captcha": data.get("captcha", "none"),
        }
    )
    save_registry(registry)
    return filename


def delete_site(name_or_filename: str) -> None:
    registry = load_registry()
    new_registry: List[Dict[str, Any]] = []
    target_file: Path | None = None
    for entry in registry:
        if name_or_filename in (entry.get("name"), entry.get("filename")):
            target_file = SITE_DIR / entry["filename"]
        else:
            new_registry.append(entry)
    if target_file and target_file.exists():
        target_file.unlink()
    save_registry(new_registry)


def import_site(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return save_site(data)


def export_site(name: str, destination: Path) -> None:
    data = get_site(name)
    with open(destination, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
