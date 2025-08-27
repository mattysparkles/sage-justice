import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
import json
import random

from core.proxy_manager import get_random_proxy
from core.account_manager import get_random_account
from core.log_manager import log_post

def post_review(site_template_path, review_text, proxy=None, account=None, headless=False):
    """Post a single review using a site template.

    Parameters are optional to avoid breaking existing callers. When not
    provided, a random proxy and account are selected for the session.
    """

    with open(site_template_path, "r", encoding="utf-8") as f:
        template = json.load(f)

    proxy = proxy or get_random_proxy()
    account = account or get_random_account()

    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(template["url"])
        time.sleep(3)

        # Basic login placeholder if credentials supplied
        if account:
            user = account.get("username") or account.get("user")
            password = account.get("password")
            if user and password:
                # Sites vary; this is a stub where actual login logic would go
                pass

        fields = template["fields"]
        review_field = driver.find_element(By.XPATH, fields["review_text"])
        review_field.send_keys(review_text)
        time.sleep(1)

        submit_button = driver.find_element(By.XPATH, fields["submit_button"])
        submit_button.click()
        time.sleep(3)

        log_post(template.get("url", site_template_path), review_text, True)
        print("Review posted.")
    except Exception as exc:  # pragma: no cover - best effort logging
        log_post(template.get("url", site_template_path), review_text, False, str(exc))
        print(f"Failed to post review: {exc}")
    finally:
        driver.quit()

def schedule_reviews(review_site_pairs, delay_seconds=86400):
    def runner():
        for pair in review_site_pairs:
            review, site = pair
            print(f"Posting review to {site}")
            post_review(site, review)
            time.sleep(delay_seconds + random.randint(-60, 60))  # +/- 1 min jitter

    threading.Thread(target=runner).start()
