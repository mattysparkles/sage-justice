import os
from typing import List


class ProxyManager:
    """Manage list of proxies with persistence to disk."""

    def __init__(self, path: str):
        self.path = path
        self.proxies: List[str] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    self.proxies = [line.strip() for line in f if line.strip()]
            except Exception:
                # If file is corrupt or unreadable, start with empty list
                self.proxies = []
        else:
            self.proxies = []

    def _save(self) -> None:
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                for proxy in self.proxies:
                    f.write(proxy + '\n')
        except Exception as e:
            # Raise to allow calling code to handle
            raise e

    def add_proxy(self, proxy: str) -> None:
        proxy = proxy.strip()
        if proxy and proxy not in self.proxies:
            self.proxies.append(proxy)
            self._save()

    def remove_proxy(self, proxy: str) -> None:
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            self._save()
