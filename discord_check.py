import random
import string
import time
import threading
import os
from typing import Tuple, Optional

try:
    from playwright.sync_api import sync_playwright, TimeoutError
except Exception:
    sync_playwright = None  # Playwright not installed

try:
    from . import proxy_manager
except Exception:
    import proxy_manager

# Module-level Playwright browser reuse
_pw = None
_browser = None
_pw_lock = threading.Lock()

# Optional env to enable proxies
_USE_PROXIES = os.environ.get('DISCORD_USE_PROXIES', '').lower() in ('1', 'true', 'yes')


def _random_email() -> str:
    s = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{s}@example.com"


def check_discord_username(username: str, headless: bool = True, timeout: int = 15) -> Tuple[bool, str]:
    """Best-effort check via Discord's public registration UI.

    Returns (available, reason). This is brittle and may break if Discord
    changes their frontend. It also requires `playwright` to be installed and
    browsers installed (`playwright install`). Use sparingly and respect rate
    limits and Discord's Terms of Service.
    """
    if sync_playwright is None:
        return False, 'playwright_missing'

    # basic sanity
    if not username or len(username) < 2:
        return False, 'invalid'

    try:
        global _pw, _browser
        with _pw_lock:
            if _pw is None:
                if sync_playwright is None:
                    return False, 'playwright_missing'
                _pw = sync_playwright().start()
            if _browser is None:
                _browser = _pw.chromium.launch(headless=headless)

        # Optionally use a proxy by creating a context with proxy settings
        context_args = {}
        proxy_used: Optional[str] = None
        if _USE_PROXIES:
            proxy = proxy_manager.get_proxy()
            if proxy:
                # proxy format expected like http://ip:port
                context_args['proxy'] = {'server': proxy}
                proxy_used = proxy

        context = _browser.new_context(**context_args)
        page = context.new_page()
        page.set_default_timeout(timeout * 1000)

        page.goto('https://discord.com/register')

        # Fill a placeholder email and password to make the form appear
        try:
            email_sel = 'input[type="email"]'
            if page.query_selector(email_sel):
                page.fill(email_sel, _random_email())
        except TimeoutError:
            pass

        # Insert username where possible. The registration flow may show
        # a username field or inline validation; try common selectors.
        username_selectors = [
            'input[name="username"]',
            'input[placeholder*="Username"]',
            'input[aria-label*="username"]',
            'input[type="text"]',
        ]

        found = False
        for sel in username_selectors:
            el = page.query_selector(sel)
            if el:
                try:
                    el.fill(username)
                    el.dispatch_event('blur')
                    found = True
                    break
                except Exception:
                    continue

        if not found:
            context.close()
            return False, 'no_selector'

        # Wait a short while for validation text to appear
        time.sleep(1.0)

        # Prefer text located near the username input (more reliable)
        try:
            parent_text = el.evaluate("e => { const f = e.closest('form') || e.parentElement; return f ? f.innerText.toLowerCase() : ''; }")
        except Exception:
            parent_text = ''

        # Also collect aria-live / alert region text which many sites use
        live_text = ''
        try:
            areas = page.query_selector_all('[aria-live], div[role="alert"]')
            pieces = []
            for a in areas:
                try:
                    pieces.append(a.inner_text().lower())
                except Exception:
                    continue
            live_text = '\n'.join(pieces)
        except Exception:
            live_text = ''

        # Full page fallback
        full_text = page.content().lower()
        context.close()

        # Consolidate the nearby text we trust most (parent + live regions)
        nearby = ' '.join([t for t in (parent_text, live_text) if t])

        # Conservative checks: only mark explicitly taken/available when the
        # nearby/form text contains the indicator. If only the full page shows
        # the phrase (likely in unrelated copy), return unknown so callers can
        # treat it as unchecked.
        taken_markers = ('already taken', 'is already taken', 'username is already', 'this username is taken', 'that username is taken')
        avail_markers = ('available', 'username is available', 'is available')

        if any(p in nearby for p in taken_markers):
            return False, 'taken'
        if any(p in nearby for p in avail_markers):
            return True, 'available'

        # If live areas indicate availability but nearby is empty, accept it
        if any(p in live_text for p in avail_markers) and not any(p in nearby for p in taken_markers):
            return True, 'available'

        if proxy_used:
            return False, f'unknown_via_proxy:{proxy_used}'
        return False, 'unknown'
    except Exception as exc:
        return False, f'error:{exc}'
