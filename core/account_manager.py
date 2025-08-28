from __future__ import annotations

"""Account utilities backed by the central database."""

import csv
import io
import logging
from typing import Dict, List

from . import database


logger = logging.getLogger(__name__)

FIELDS = ["username", "password", "site_name", "login_url", "captcha", "phone"]


def load_accounts() -> list[dict]:
    return database.get_all_accounts()


def get_random_account() -> dict | None:
    return database.get_available_account()


def mark_account_failed(account_id: int) -> None:
    database.mark_account_failed(account_id)


def import_accounts_from_text(text: str) -> List[Dict[str, str]]:
    """Parse accounts from a CSV-formatted string.

    Each line must contain: username,password,site_name,login_url,captcha,phone.
    Lines missing username or password are skipped and an error is logged.
    """

    accounts: List[Dict[str, str]] = []
    reader = csv.DictReader(io.StringIO(text), fieldnames=FIELDS)
    for line_no, row in enumerate(reader, 1):
        username = (row.get("username") or "").strip()
        password = (row.get("password") or "").strip()
        if not username or not password:
            logger.error("Line %d missing username or password", line_no)
            continue
        account = {field: (row.get(field) or "").strip() or None for field in FIELDS}
        accounts.append(account)
    return accounts


def export_accounts_to_text(accounts: List[Dict[str, object]]) -> str:
    """Export accounts to CSV text in the same field order as import."""

    output = io.StringIO()
    writer = csv.writer(output)
    for acc in accounts:
        meta = acc.get("metadata") or {}
        writer.writerow([
            acc.get("username"),
            acc.get("password"),
            meta.get("site_name") or acc.get("site_name"),
            meta.get("login_url") or acc.get("login_url"),
            meta.get("captcha") or acc.get("captcha"),
            meta.get("phone") or acc.get("phone"),
        ])
    return output.getvalue()


def save_accounts(accounts: List[Dict[str, str]], category: str = "", health_status: str = "healthy") -> None:
    """Persist parsed accounts to the database."""

    for acc in accounts:
        metadata = {
            "site_name": acc.get("site_name"),
            "login_url": acc.get("login_url"),
            "captcha": acc.get("captcha"),
            "phone": acc.get("phone"),
        }
        database.add_account(
            acc["username"],
            acc["password"],
            category,
            health_status,
            metadata=metadata,
        )
