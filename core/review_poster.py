"""Simplified review posting utilities using site registry data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
except Exception:  # pragma: no cover - Selenium may not be installed
    webdriver = None  # type: ignore
    By = None  # type: ignore

from .site_registry import get_site


def load_site_config(name: str) -> dict[str, Any]:
    """Load full site configuration by name."""
    return get_site(name)


def _perform_step(driver: webdriver.Remote, step: str, selectors: dict[str, str], text: str) -> None:
    parts = step.split()
    if not parts:
        return
    action = parts[0]
    if action == "open":
        return
    key = parts[-1]
    sel = selectors.get(key)
    if not sel:
        return
    elem = driver.find_element(By.CSS_SELECTOR, sel)
    if action == "click":
        elem.click()
    elif action == "fill":
        elem.clear()
        elem.send_keys(text)


def post_review(site_name: str, review_text: str) -> None:
    """Basic Selenium routine executing navigation steps defined for the site."""
    if webdriver is None:
        raise RuntimeError("Selenium is required for posting reviews")
    config = load_site_config(site_name)
    driver = webdriver.Chrome()
    driver.get(config["url"])
    selectors = config.get("selectors", {})
    for step in config.get("navigation_steps", []):
        if step == "open url":
            continue
        _perform_step(driver, step, selectors, review_text)
    driver.quit()
