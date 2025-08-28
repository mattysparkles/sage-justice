from __future__ import annotations

"""Utilities for generating aggregate reports from posted review logs."""

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logger import logger

LOG_FILE = Path("output/post_log.csv")


def _load_rows(start: Optional[datetime] = None, end: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Load log rows filtered by optional UTC datetime range."""
    rows: List[Dict[str, Any]] = []
    if not LOG_FILE.exists():
        logger.warning("post_log.csv not found at %s", LOG_FILE)
        return rows

    with LOG_FILE.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            ts_str = r.get("timestamp") or r.get("time")
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str)
            except Exception:
                logger.debug("Skipping row with invalid timestamp: %s", r)
                continue
            if start and ts < start:
                continue
            if end and ts > end:
                continue
            r["timestamp"] = ts
            rows.append(r)
    return rows


def generate_report(start: Optional[datetime] = None, end: Optional[datetime] = None) -> Dict[str, Any]:
    """Return summary statistics for posts between *start* and *end*."""
    logger.info("Generating report from %s to %s", start, end)
    rows = _load_rows(start, end)
    total = len(rows)
    site_counter: Counter[str] = Counter(r.get("site", "unknown") for r in rows)
    date_counter: Counter[str] = Counter(r["timestamp"].date().isoformat() for r in rows)
    status_counter: Counter[str] = Counter(r.get("status", "unknown") for r in rows)
    tone_counter: Counter[str] = Counter(r.get("tone", "unknown") for r in rows)
    account_counter: Counter[str] = Counter(r.get("account") for r in rows if r.get("account"))
    proxy_counter: Counter[str] = Counter(r.get("proxy") for r in rows if r.get("proxy"))

    success = status_counter.get("SUCCESS", 0)
    fail = status_counter.get("FAIL", 0)
    success_rate = success / total if total else 0.0
    fail_rate = fail / total if total else 0.0

    report = {
        "total_posted": total,
        "success": success,
        "fail": fail,
        "success_rate": success_rate,
        "fail_rate": fail_rate,
        "by_site": dict(site_counter),
        "by_date": dict(date_counter),
        "by_status": dict(status_counter),
        "by_tone": dict(tone_counter),
        "top_accounts": account_counter.most_common(5),
        "top_proxies": proxy_counter.most_common(5),
    }

    logger.info("Report generated with %s records", total)
    return report

__all__ = ["generate_report"]
