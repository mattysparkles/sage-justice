from __future__ import annotations

from typing import Optional

from core import database


class ProxyManager:
    """Retrieve proxies from the SQLite database."""

    def __init__(self) -> None:
        pass

    def get_proxy(self) -> Optional[str]:
        proxy = database.fetch_proxy()
        if proxy:
            return f"{proxy['ip_address']}:{proxy['port']}"
        return None
