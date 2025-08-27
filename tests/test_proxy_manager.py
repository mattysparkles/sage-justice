import os
import sys

sys.path.append(os.path.abspath("."))

from proxy.manager import ProxyManager


def test_add_remove_proxy_persists(tmp_path):
    file_path = tmp_path / "proxies.txt"
    manager = ProxyManager(path=str(file_path))

    manager.add_proxy("http://1.2.3.4:8080")
    assert manager.proxies == ["http://1.2.3.4:8080"]
    assert file_path.read_text().strip() == "http://1.2.3.4:8080"

    manager.add_proxy("http://1.2.3.5:8080")
    manager.remove_proxy("http://1.2.3.4:8080")
    assert manager.proxies == ["http://1.2.3.5:8080"]
    assert file_path.read_text().strip() == "http://1.2.3.5:8080"
