from selenium import webdriver
from selenium.webdriver.common.by import By
import json
import time

def record_fields(site_name, site_url):
    driver = webdriver.Chrome()
    driver.get(site_url)
    print(f"Navigate to the review form for {site_name}.")
    input("Press Enter once you've hovered over all necessary fields and are ready to record XPaths...")

    fields = {}
    while True:
        field_name = input("Enter a field label (e.g., review_text, submit_button), or 'done' to finish: ").strip()
        if field_name.lower() == "done":
            break
        xpath = input(f"Enter the XPath for '{field_name}': ").strip()
        fields[field_name] = xpath

    template = {
        "site": site_name,
        "url": site_url,
        "fields": fields
    }

    with open(f"templates/{site_name.lower().replace(' ', '_')}.json", "w") as f:
        json.dump(template, f, indent=2)

    print(f"Template saved to templates/{site_name.lower().replace(' ', '_')}.json")
    driver.quit()
