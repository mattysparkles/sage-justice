import json
from selenium.webdriver.common.by import By

class FieldMapper:
    def __init__(self, driver):
        self.driver = driver
        self.mapping = {}

    def record_field(self, field_name, by, selector):
        self.mapping[field_name] = {"by": by, "selector": selector}

    def save_mapping(self, filename):
        with open(filename, 'w') as f:
            json.dump(self.mapping, f, indent=2)

    def load_mapping(self, filename):
        with open(filename, 'r') as f:
            self.mapping = json.load(f)

    def fill_field(self, field_name, value):
        field_info = self.mapping.get(field_name)
        if field_info:
            element = self.driver.find_element(getattr(By, field_info["by"]), field_info["selector"])
            element.clear()
            element.send_keys(value)