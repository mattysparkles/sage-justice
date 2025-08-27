import json
from selenium.webdriver.common.by import By

class FieldMapper:
    def __init__(self, driver):
        self.driver = driver
        self.field_map = {}

    def map_field(self, field_name, strategy, identifier):
        self.field_map[field_name] = {"by": strategy, "value": identifier}

    def save_map(self, path='config/fieldmap.json'):
        with open(path, 'w') as f:
            json.dump(self.field_map, f, indent=2)

    def load_map(self, path='config/fieldmap.json'):
        with open(path, 'r') as f:
            self.field_map = json.load(f)

    def fill_fields(self, data):
        for field, val in data.items():
            meta = self.field_map.get(field)
            if meta:
                elem = self.driver.find_element(getattr(By, meta['by']), meta['value'])
                elem.clear()
                elem.send_keys(val)