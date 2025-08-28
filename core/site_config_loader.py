
import json
from pathlib import Path

from .template_registry import register_site_templates

class SiteConfigLoader:
    def __init__(self, templates_path="templates", config_path="config/templates.json"):
        self.templates_path = Path(templates_path)
        self.config_path = Path(config_path)
        self.site_templates = {}

    def load_templates(self):
        # Ensure templates are registered before loading
        register_site_templates(self.templates_path / "sites", self.config_path)

        for template_file in self.templates_path.rglob("*.json"):
            with open(template_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    print(f"Warning: Failed to parse {template_file}")
                    continue

            # Handle a single site config stored as an object
            if isinstance(data, dict):
                key = data.get("site_key", template_file.stem)
                self.site_templates[key] = data
                continue

            # Handle a list of site configs (e.g. review_site_templates.json)
            if isinstance(data, list):
                for entry in data:
                    if not isinstance(entry, dict):
                        print(
                            f"Warning: Unexpected entry in {template_file}; expected object, got {type(entry).__name__}"
                        )
                        continue
                    key = entry.get("site_key")
                    if not key:
                        print(f"Warning: Missing 'site_key' in entry from {template_file}")
                        continue
                    self.site_templates[key] = entry
                continue

            print(
                f"Warning: Unexpected JSON format in {template_file}; expected object or list, got {type(data).__name__}"
            )
        return self.site_templates
