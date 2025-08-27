import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
import json
import random

def post_review(site_template_path, review_text):
    with open(site_template_path) as f:
        template = json.load(f)

    driver = webdriver.Chrome()
    driver.get(template["url"])
    time.sleep(3)

    # Load XPaths
    fields = template["fields"]
    review_field = driver.find_element(By.XPATH, fields["review_text"])
    review_field.send_keys(review_text)
    time.sleep(1)

    submit_button = driver.find_element(By.XPATH, fields["submit_button"])
    submit_button.click()
    time.sleep(3)

    print("Review posted.")
    driver.quit()

def schedule_reviews(review_site_pairs, delay_seconds=86400):
    def runner():
        for pair in review_site_pairs:
            review, site = pair
            print(f"Posting review to {site}")
            post_review(site, review)
            time.sleep(delay_seconds + random.randint(-60, 60))  # +/- 1 min jitter

    threading.Thread(target=runner).start()
