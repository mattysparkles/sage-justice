"""Agent runner for automated review posting using Selenium."""

from __future__ import annotations

import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    import undetected_chromedriver as uc
except Exception:  # pragma: no cover - optional dependency
    uc = None  # type: ignore

from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.chrome.options import Options  # type: ignore
from selenium.webdriver.chrome.service import Service  # type: ignore
from webdriver_manager.chrome import ChromeDriverManager  # type: ignore

# Basic set of user agents for simple rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]


class ReviewPoster:
    """Automate review posting for a site defined by configuration."""

    def __init__(
        self,
        site_config: dict[str, Any],
        review_data: dict[str, Any],
        account: dict[str, str],
        proxy: Optional[str] = None,
    ) -> None:
        self.site_config = site_config
        self.review_data = review_data
        self.account = account
        self.proxy = proxy
        self.driver: Optional[webdriver.Remote] = None
        self.start_time = datetime.utcnow()
        self.result = "Fail"
        self.error: Optional[str] = None
        self._step_index = 0

        logs_path = Path("logs")
        logs_path.mkdir(exist_ok=True)
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.log_file = logs_path / f"agent_{timestamp}.log"

        self.logger = logging.getLogger(f"ReviewPoster_{timestamp}")
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    # ------------------------------------------------------------------
    # Driver loading
    def load_driver(self) -> None:
        """Set up Selenium driver with proxy and random user agent."""
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
        if self.proxy:
            options.add_argument(f"--proxy-server={self.proxy}")
        if uc:
            self.driver = uc.Chrome(options=options)
        else:  # pragma: no cover - requires browser in environment
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)

    # ------------------------------------------------------------------
    # Navigation helpers
    def _perform_step(self, step: str) -> None:
        selectors = self.site_config.get("selectors", {})
        parts = step.split()
        if not parts:
            return
        action = parts[0]
        if action == "wait":
            seconds = float(parts[1]) if len(parts) > 1 else 1
            time.sleep(seconds)
            return
        key = parts[-1]
        selector = selectors.get(key)
        if not selector or not self.driver:
            return
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        if action == "click":
            element.click()
        elif action == "fill":
            element.clear()
            if key == "username_field":
                element.send_keys(self.account.get("email", ""))
            elif key == "password_field":
                element.send_keys(self.account.get("password", ""))
            elif key == "rating_field":
                rating = str(self.review_data.get("rating", ""))
                element.send_keys(rating)
            elif key == "review_textarea":
                element.send_keys(self.review_data.get("text", ""))
            else:
                element.send_keys(self.review_data.get(key, ""))
        time.sleep(self.site_config.get("step_wait", 1))

    # ------------------------------------------------------------------
    def login(self) -> None:
        """Handle login flow using selectors."""
        if not self.driver:
            raise RuntimeError("Driver not loaded")
        self.driver.get(self.site_config.get("url"))
        steps = self.site_config.get("navigation_steps", [])
        for i, step in enumerate(steps):
            self._perform_step(step)
            if "review_textarea" in step or "rating_field" in step:
                self._step_index = i + 1
                break

    # ------------------------------------------------------------------
    def post_review(self) -> None:
        """Complete review form and submit."""
        steps = self.site_config.get("navigation_steps", [])
        for step in steps[self._step_index:]:
            self._perform_step(step)

    # ------------------------------------------------------------------
    def handle_captcha(self) -> None:  # pragma: no cover - stub
        """Optional CAPTCHA handling stub."""
        self.logger.info("CAPTCHA handling not implemented")

    # ------------------------------------------------------------------
    def capture_screenshot(self, filename: str) -> Path:
        """Capture screenshot of current browser state."""
        if not self.driver:
            raise RuntimeError("Driver not loaded")
        path = Path("logs") / filename
        self.driver.save_screenshot(str(path))
        return path

    # ------------------------------------------------------------------
    def log_result(self) -> None:
        self.logger.info("Start time: %s", self.start_time.isoformat())
        self.logger.info("Site: %s", self.site_config.get("site"))
        self.logger.info("Account: %s", self.account.get("email"))
        self.logger.info("Proxy: %s", self.proxy or "None")
        self.logger.info("Result: %s", self.result)
        if self.error:
            self.logger.error("Error: %s", self.error)

    # ------------------------------------------------------------------
    def run(self, max_retries: int = 3) -> None:
        """Execute full posting pipeline with basic retry logic."""
        for attempt in range(1, max_retries + 1):
            try:
                self.load_driver()
                self.login()
                self.post_review()
                self.result = "Success"
                break
            except Exception as exc:  # pragma: no cover - depends on Selenium
                self.error = str(exc)
                self.logger.exception("Attempt %s failed", attempt)
                if self.driver:
                    screenshot = self.capture_screenshot(f"failure_{attempt}.png")
                    self.logger.info("Saved screenshot to %s", screenshot)
                if attempt == max_retries:
                    self.result = "Fail"
            finally:
                if self.driver:
                    self.driver.quit()
        self.log_result()


def run_posting_agent(
    site_file: str,
    review_obj: dict[str, Any],
    account: dict[str, str],
    proxy: Optional[str] = None,
) -> ReviewPoster:
    """CLI callable helper to execute the ReviewPoster."""
    with open(site_file, encoding="utf-8") as f:
        site_config = json.load(f)
    poster = ReviewPoster(site_config, review_obj, account, proxy)
    poster.run()
    return poster


if __name__ == "__main__":  # pragma: no cover - CLI entry
    import argparse

    parser = argparse.ArgumentParser(description="Automated review poster")
    parser.add_argument("site_file", help="Path to site configuration JSON")
    parser.add_argument("review", help="JSON string for review data")
    parser.add_argument("email", help="Account email")
    parser.add_argument("password", help="Account password")
    parser.add_argument("--proxy", help="Proxy server", default=None)
    args = parser.parse_args()

    review_data = json.loads(args.review)
    account_data = {"email": args.email, "password": args.password}
    run_posting_agent(args.site_file, review_data, account_data, proxy=args.proxy)
