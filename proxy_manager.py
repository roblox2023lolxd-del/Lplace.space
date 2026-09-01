import time
import requests
import os
from typing import List, Optional

# Simple proxy list fetcher + cache. Default source returns plain text of ip:port lines.
DEFAULT_PROXY_SOURCE = os.environ.get('PROXY_SOURCE_URL', 'https://www.proxy-list.download/api/v1/get?type=http')
PROXY_REFRESH_TTL = int(os.environ.get('PROXY_REFRESH_TTL', '300'))

_proxy_cache: List[str] = []
_proxy_cache_at: float = 0.0


def fetch_proxies(source_url: Optional[str] = None, timeout: int = 8) -> List[str]:
    global _proxy_cache, _proxy_cache_at
    src = source_url or DEFAULT_PROXY_SOURCE
    now = time.monotonic()
    if _proxy_cache and now - _proxy_cache_at < PROXY_REFRESH_TTL:
        return _proxy_cache
    try:
        r = requests.get(src, timeout=timeout, headers={'User-Agent': 'SpaceGen/1.0'})
        r.raise_for_status()
        lines = [line.strip() for line in r.text.splitlines() if line.strip()]
        # Normalize to http://ip:port
        proxies = []
        for line in lines:
            p = line
            if not p.startswith('http'):
                p = 'http://' + p
            proxies.append(p)
        _proxy_cache = proxies
        _proxy_cache_at = now
        return proxies
    except Exception:
        return _proxy_cache or []


def get_proxy() -> Optional[str]:
    """Return one proxy URL or None."""
    ps = fetch_proxies()
    if not ps:
        return None
    # simple rotation: pop first and append
    p = ps.pop(0)
    ps.append(p)
    return p