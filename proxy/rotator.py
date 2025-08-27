
import random, time
import requests

class ProxyRotator:
    def __init__(self, proxy_list):
        self.proxy_list = proxy_list
        self.index = 0

    def get_proxy(self):
        proxy = self.proxy_list[self.index % len(self.proxy_list)]
        self.index += 1
        return proxy

    def test_proxy(self, proxy):
        try:
            r = requests.get("https://httpbin.org/ip", proxies={"http": proxy, "https": proxy}, timeout=5)
            return r.json()
        except Exception:
            return None
