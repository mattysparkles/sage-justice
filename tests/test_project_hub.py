import importlib
import os
import sys

sys.path.append(os.path.abspath("."))

from core import project_hub


def setup(tmp_path):
    project_hub.PROJECTS_FILE = tmp_path / "projects.json"
    project_hub.GLOBAL_SETTINGS_FILE = tmp_path / "settings.json"
    # reload to clear cached data if any
    importlib.reload(project_hub)
    project_hub.PROJECTS_FILE = tmp_path / "projects.json"
    project_hub.GLOBAL_SETTINGS_FILE = tmp_path / "settings.json"
    return project_hub


def test_template_site_schedule(tmp_path):
    ph = setup(tmp_path)
    ph.add_project("alpha")
    assert ph.list_projects() == ["alpha"]

    ph.add_template("alpha", "tmpl1")
    assert ph.list_templates("alpha") == ["tmpl1"]
    ph.add_site("alpha", "site1")
    assert ph.list_sites("alpha") == ["site1"]
    ph.set_schedule("alpha", "schedule.json")
    assert ph.get_schedule("alpha") == "schedule.json"

    ph.remove_template("alpha", "tmpl1")
    ph.remove_site("alpha", "site1")
    ph.clear_schedule("alpha")
    assert ph.list_templates("alpha") == []
    assert ph.list_sites("alpha") == []
    assert ph.get_schedule("alpha") is None

