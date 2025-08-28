
import json
from pathlib import Path

class SiteConfigLoader:
    def __init__(self, templates_path="templates"):
        self.templates_path = Path(templates_path)
        self.site_templates = {}

    def load_templates(self):
        for template_file in self.templates_path.glob("*.json"):
            with open(template_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    print(f"Warning: Failed to parse {template_file}")
                    continue

            if isinstance(data, dict):
                self.site_templates[template_file.stem] = data
            else:
                print(
                    f"Warning: Unexpected JSON format in {template_file}; expected object, got {type(data).__name__}"
                )
        return self.site_templates
