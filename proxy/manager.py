from __future__ import annotations

from typing import Optional

from core import database


class ProxyManager:
    """Retrieve and assign proxies from the SQLite database."""

    def __init__(self) -> None:
        pass

    def get_proxy(
        self, level: str = "global", target: str | int | None = None
    ) -> Optional[str]:
        proxy = database.fetch_proxy_for_scope(level, target)
        if not proxy:
            proxy = database.fetch_proxy()
        if proxy:
            return f"{proxy['ip_address']}:{proxy['port']}"
        return None

    def assign_proxy(
        self,
        proxy_id: int,
        level: str,
        target: str | int | None = None,
        weight: int = 1,
        priority: int = 0,
    ) -> None:
        """Assign a proxy to a scope."""
        database.assign_proxy(proxy_id, level, target, weight, priority)

    def remove_assignment(
        self, proxy_id: int, level: str, target: str | int | None = None
    ) -> None:
        """Remove a proxy assignment from a scope."""
        database.remove_proxy_assignment(proxy_id, level, target)
