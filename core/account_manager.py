from __future__ import annotations

"""Account utilities backed by the central database."""

from . import database


def load_accounts() -> list[dict]:
    return database.get_all_accounts()


def get_random_account() -> dict | None:
    return database.get_available_account()


def mark_account_failed(account_id: int) -> None:
    database.mark_account_failed(account_id)
