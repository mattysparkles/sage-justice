from __future__ import annotations

"""Backward compatible proxy utilities using the central database."""

from . import database


def load_proxies(file_path: str | None = None) -> list[str]:
    """Return all proxies stored in the database."""
    with database.get_connection() as conn:
        rows = conn.execute("SELECT ip_address, port FROM proxies").fetchall()
    return [f"{r['ip_address']}:{r['port']}" for r in rows]


def get_random_proxy() -> str | None:
    proxy = database.fetch_proxy()
    if proxy:
        return f"{proxy['ip_address']}:{proxy['port']}"
    return None
