import threading
import urllib.request
import requests


_DIRECT_SERVICES = [
    'https://api.ipify.org?format=json',
    'https://ipinfo.io/json',
    'https://api.myip.com',
]

_PROXY_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
             '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')


def _extract_ip(data):
    if isinstance(data, dict):
        return data.get('ip') or data.get('query') or data.get('YourFuckingIPAddress')
    return None


def _system_proxies():
    try:
        proxies = urllib.request.getproxies()
        return {k: v for k, v in proxies.items() if k in ('http', 'https')}
    except Exception:
        return {}


class IPFetcher:
    def __init__(self):
        self.direct_ip = "获取中..."
        self.proxy_ip = "获取中..."
        self.has_proxy = bool(_system_proxies())
        self._lock = threading.Lock()
        self._busy_direct = False
        self._busy_proxy = False

    def refresh(self):
        if not self._busy_direct:
            self._busy_direct = True
            threading.Thread(target=self._fetch_direct, daemon=True).start()
        if not self._busy_proxy:
            self._busy_proxy = True
            threading.Thread(target=self._fetch_proxy, daemon=True).start()

    def _fetch_direct(self):
        ip = self._fetch(proxies={'http': None, 'https': None})
        with self._lock:
            self.direct_ip = ip
        self._busy_direct = False

    def _fetch_proxy(self):
        proxies = _system_proxies()
        self.has_proxy = bool(proxies)
        if not proxies:
            with self._lock:
                self.proxy_ip = "未配置代理"
            self._busy_proxy = False
            return
        ip = self._fetch(proxies=proxies)
        with self._lock:
            self.proxy_ip = ip
        self._busy_proxy = False

    @staticmethod
    def _fetch(proxies):
        headers = {'User-Agent': _PROXY_UA}
        for url in _DIRECT_SERVICES:
            try:
                r = requests.get(url, proxies=proxies, headers=headers, timeout=6)
                if r.status_code != 200:
                    continue
                data = r.json()
                ip = _extract_ip(data)
                if ip:
                    return ip
            except Exception:
                continue
        return "无法获取"

    def get(self):
        with self._lock:
            return self.direct_ip, self.proxy_ip
