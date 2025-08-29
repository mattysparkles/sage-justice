"""Project resource management with global fallbacks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECTS_FILE = Path("config/projects.json")
GLOBAL_SETTINGS_FILE = Path("config/settings.json")


def _load_projects() -> List[Dict[str, Any]]:
    try:
        with PROJECTS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def _save_projects(data: List[Dict[str, Any]]) -> None:
    PROJECTS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_projects() -> List[str]:
    return [p.get("name", "") for p in _load_projects()]


def get_project(name: str) -> Optional[Dict[str, Any]]:
    for proj in _load_projects():
        if proj.get("name") == name:
            return proj
    return None


def add_project(name: str) -> None:
    data = _load_projects()
    if any(p.get("name") == name for p in data):
        return
    data.append({"name": name, "resources": {}, "constraints": {}, "status": "active"})
    _save_projects(data)


def rename_project(old: str, new: str) -> None:
    data = _load_projects()
    for proj in data:
        if proj.get("name") == old:
            proj["name"] = new
            break
    _save_projects(data)


def delete_project(name: str) -> None:
    data = [p for p in _load_projects() if p.get("name") != name]
    _save_projects(data)


def add_resource(project: str, kind: str, value: Any) -> bool:
    data = _load_projects()
    for proj in data:
        if proj.get("name") == project:
            resources = proj.setdefault("resources", {})
            existing = resources.setdefault(kind, [] if isinstance(value, (dict, str)) else [])
            constraint = proj.get("constraints", {}).get(kind)
            if constraint is not None and isinstance(existing, list) and len(existing) >= constraint:
                return False
            if isinstance(existing, list):
                existing.append(value)
            else:
                resources[kind] = value
            _save_projects(data)
            return True
    return False


def get_resource(project: str, kind: str) -> Any:
    proj = get_project(project)
    if proj:
        resources = proj.get("resources", {})
        if kind in resources and resources[kind] is not None:
            return resources[kind]
    try:
        with GLOBAL_SETTINGS_FILE.open("r", encoding="utf-8") as f:
            settings = json.load(f)
        return settings.get(kind)
    except FileNotFoundError:
        return None


def set_status(project: str, status: str) -> None:
    data = _load_projects()
    for proj in data:
        if proj.get("name") == project:
            proj["status"] = status
            break
    _save_projects(data)


def get_status(project: str) -> str:
    proj = get_project(project)
    return proj.get("status", "unknown") if proj else "unknown"


def enforce_constraints(project: str) -> bool:
    proj = get_project(project)
    if not proj:
        return True
    constraints = proj.get("constraints", {})
    resources = proj.get("resources", {})
    for kind, limit in constraints.items():
        if isinstance(limit, int):
            current = len(resources.get(kind, [])) if isinstance(resources.get(kind), list) else 0
            if current > limit:
                return False
    return True


# --- Template Management -------------------------------------------------

def list_templates(project: str) -> List[str]:
    """Return templates assigned to a project."""
    proj = get_project(project)
    if not proj:
        return []
    return proj.get("resources", {}).get("templates", [])


def add_template(project: str, template: str) -> bool:
    """Assign a template to a project."""
    data = _load_projects()
    for proj in data:
        if proj.get("name") == project:
            resources = proj.setdefault("resources", {})
            templates = resources.setdefault("templates", [])
            if template not in templates:
                templates.append(template)
                _save_projects(data)
            return True
    return False


def remove_template(project: str, template: str) -> bool:
    """Remove a template from a project."""
    data = _load_projects()
    for proj in data:
        if proj.get("name") == project:
            templates = proj.setdefault("resources", {}).setdefault("templates", [])
            if template in templates:
                templates.remove(template)
                _save_projects(data)
            return True
    return False


# --- Site Management ------------------------------------------------------

def list_sites(project: str) -> List[str]:
    """Return sites associated with a project."""
    proj = get_project(project)
    if not proj:
        return []
    return proj.get("resources", {}).get("sites", [])


def add_site(project: str, site: str) -> bool:
    """Assign a site to a project."""
    data = _load_projects()
    for proj in data:
        if proj.get("name") == project:
            resources = proj.setdefault("resources", {})
            sites = resources.setdefault("sites", [])
            if site not in sites:
                sites.append(site)
                _save_projects(data)
            return True
    return False


def remove_site(project: str, site: str) -> bool:
    """Remove a site association from a project."""
    data = _load_projects()
    for proj in data:
        if proj.get("name") == project:
            sites = proj.setdefault("resources", {}).setdefault("sites", [])
            if site in sites:
                sites.remove(site)
                _save_projects(data)
            return True
    return False


# --- Schedule Configuration ----------------------------------------------

def get_schedule(project: str) -> Any:
    """Get schedule configuration for a project."""
    proj = get_project(project)
    if not proj:
        return None
    return proj.get("resources", {}).get("schedule")


def set_schedule(project: str, schedule: Any) -> bool:
    """Set schedule configuration for a project."""
    data = _load_projects()
    for proj in data:
        if proj.get("name") == project:
            resources = proj.setdefault("resources", {})
            resources["schedule"] = schedule
            _save_projects(data)
            return True
    return False


def clear_schedule(project: str) -> bool:
    """Remove schedule configuration from a project."""
    data = _load_projects()
    for proj in data:
        if proj.get("name") == project:
            resources = proj.setdefault("resources", {})
            if "schedule" in resources:
                resources.pop("schedule")
                _save_projects(data)
            return True
    return False
