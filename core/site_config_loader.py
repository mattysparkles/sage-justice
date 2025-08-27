
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
                    self.site_templates[template_file.stem] = json.load(f)
                except json.JSONDecodeError:
                    print(f"Warning: Failed to parse {template_file}")
        return self.site_templates
