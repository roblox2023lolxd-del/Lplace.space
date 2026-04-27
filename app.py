from flask import Flask, render_template_string, request, jsonify
import requests
import random
import string
import logging
import os
import re
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

# ── Logging setup ─────────────────────────────────────────────────────────────

LOG_DIR  = os.environ.get('LOG_DIR', 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'security.log')
os.makedirs(LOG_DIR, exist_ok=True)

_fmt = logging.Formatter(
    '%(asctime)s  %(levelname)-8s  %(name)s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

_file_handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=5)
_file_handler.setFormatter(_fmt)
security_logger.addHandler(_file_handler)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)
security_logger.addHandler(_console_handler)

logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(levelname)-8s  %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
app.logger.setLevel(logging.INFO)


def _ip() -> str:
    return request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown').split(',')[0].strip()


# ── VPN / proxy detection ─────────────────────────────────────────────────────
# Uses ipapi.is (free, no key needed). Results cached in-memory for 10 min.

import time

_vpn_cache: dict[str, tuple[bool, float]] = {}  # ip -> (is_vpn, timestamp)
VPN_CACHE_TTL = 600  # seconds

_PRIVATE = re.compile(
    r'^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|::1$|localhost)'
)


def _is_vpn(ip: str) -> bool:
    """
    Returns True if the IP looks like a VPN/proxy/Tor/relay.
    Falls back to False on any error so legitimate users aren't blocked.
    """
    if _PRIVATE.match(ip):
        return False

    now    = time.monotonic()
    cached = _vpn_cache.get(ip)
    if cached and now - cached[1] < VPN_CACHE_TTL:
        return cached[0]

    try:
        resp = requests.get(
            f'https://api.ipapi.is/?q={ip}',
            timeout=4,
            headers={'Accept': 'application/json'},
        )
        resp.raise_for_status()
        d = resp.json()

        flagged = any([
            d.get('is_vpn'),
            d.get('is_proxy'),
            d.get('is_tor'),
            d.get('is_relay'),
        ])
        _vpn_cache[ip] = (flagged, now)

        if flagged:
            flags = [k for k in ('is_vpn', 'is_proxy', 'is_tor', 'is_relay') if d.get(k)]
            security_logger.warning('VPN_DETECTED  ip=%s  flags=%s', ip, ','.join(flags))
        else:
            security_logger.info('IP_CLEAN  ip=%s', ip)

        return flagged

    except requests.RequestException as exc:
        security_logger.error('VPN_CHECK_ERROR  ip=%s  error=%s', ip, exc)
        return False  # fail open — don't punish users if detection API is down


# ── Platform definitions ──────────────────────────────────────────────────────

PLATFORMS = {
    'roblox':  {'label': 'Roblox',   'min': 3,  'max': 20, 'check': True},
    'discord': {'label': 'Discord',  'min': 2,  'max': 32, 'check': False},
    'tiktok':  {'label': 'TikTok',   'min': 2,  'max': 24, 'check': False},
    'youtube': {'label': 'YouTube',  'min': 3,  'max': 30, 'check': False},
    'twitch':  {'label': 'Twitch',   'min': 4,  'max': 25, 'check': False},
    'steam':   {'label': 'Steam',    'min': 3,  'max': 32, 'check': False},
}

VALID_STYLES    = {'unique', 'rank', 'aesthetic', 'leet', 'themed', 'custom'}
VALID_PLATFORMS = set(PLATFORMS.keys())

# ── Word lists ────────────────────────────────────────────────────────────────

PREFIXES = ['pro', 'elite', 'mega', 'ultra', 'super', 'god', 'king', 'dark',
            'light', 'fire', 'ice', 'shadow', 'storm', 'star', 'galaxy',
            'dragon', 'ninja', 'samurai', 'phantom', 'cosmic', 'void', 'neon',
            'hyper', 'lunar', 'solar', 'toxic', 'cyber', 'arcane', 'silent']
SUFFIXES = ['gamer', 'player', 'pro', 'master', 'ninja', 'boss', 'hero',
            'legend', 'warrior', 'slayer', 'star', 'bolt', 'blade', 'flame',
            'frost', 'void', 'aura', 'edge', 'peak', 'apex', 'fox', 'wolf',
            'hawk', 'viper', 'ghost', 'pulse', 'spark', 'drift', 'surge']
LEET_MAP = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7'}
THEMES   = {
    'space':   ['star', 'galaxy', 'cosmo', 'nova', 'orbit', 'nebula', 'comet', 'pulsar'],
    'fantasy': ['elf', 'dragon', 'wizard', 'quest', 'myth', 'rune', 'arcane', 'phantom'],
    'gaming':  ['pixel', 'level', 'quest', 'spawn', 'glitch', 'respawn', 'loot', 'frag'],
    'nature':  ['storm', 'river', 'peak', 'frost', 'ember', 'tide', 'ridge', 'flare'],
    'cyber':   ['cyber', 'neon', 'byte', 'grid', 'node', 'hex', 'cipher', 'vector'],
}


# ── Validation ────────────────────────────────────────────────────────────────

def _is_valid(username: str, platform: str) -> bool:
    p = PLATFORMS[platform]
    if not p['min'] <= len(username) <= p['max']:
        return False
    if platform == 'roblox':
        if username.startswith('_') or username.endswith('_'):
            return False
        if username.count('_') > 1:
            return False
        return all(c.isalnum() or c == '_' for c in username)
    elif platform == 'discord':
        return bool(re.match(r'^[a-z0-9_.]+$', username))
    elif platform == 'tiktok':
        return bool(re.match(r'^[a-zA-Z0-9_.]+$', username))
    elif platform == 'youtube':
        return bool(re.match(r'^[a-zA-Z0-9_\-]+$', username))
    elif platform == 'twitch':
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
    elif platform == 'steam':
        return bool(re.match(r'^[a-zA-Z0-9_\-]+$', username))
    return False


# ── Generation ────────────────────────────────────────────────────────────────

def _sep(platform: str) -> str:
    seps = {
        'roblox': ['_'],
        'discord': ['_', '.'],
        'tiktok':  ['_', '.'],
        'youtube': ['_', '-'],
        'twitch':  ['_'],
        'steam':   ['_', '-'],
    }
    return random.choice(seps.get(platform, ['_']))


def _maybe_sep(username: str, platform: str, prob: float = 0.25) -> str:
    if not any(c in username for c in '_.-') and random.random() < prob and len(username) > 4:
        pos = random.randint(1, len(username) - 2)
        username = username[:pos] + _sep(platform) + username[pos:]
    return username


def _fit(username: str, target: int) -> str:
    if len(username) > target:
        return username[:target]
    if len(username) < target:
        username += ''.join(random.choices(string.digits, k=target - len(username)))
    return username


def _generate_one(style: str, length: int, base: str | None, platform: str) -> str | None:
    p      = PLATFORMS[platform]
    length = max(p['min'], min(p['max'], length))

    if style == 'unique':
        chars    = string.ascii_lowercase + string.digits
        username = ''.join(random.choices(chars, k=length))
        username = _maybe_sep(username, platform, 0.3)
        if len(username) > p['max']:
            return None

    elif style == 'rank':
        username = random.choice(PREFIXES) + random.choice(SUFFIXES)
        username = _fit(username, length)
        username = _maybe_sep(username, platform, 0.2)

    elif style == 'aesthetic':
        consonants = 'bcdfghjklmnpqrstvwxyz'
        half       = length // 2
        part1      = ''.join(random.choices(consonants + string.digits, k=half))
        part2      = ''.join(random.choices(consonants + string.digits, k=length - half))
        username   = part1 + _sep(platform) + part2

    elif style == 'leet':
        base_word = (base or ''.join(random.choices(string.ascii_lowercase, k=4))).lower()
        username  = ''.join(LEET_MAP.get(c, c) for c in base_word)
        username  = _fit(username, length)
        username  = _maybe_sep(username, platform, 0.4)

    elif style == 'themed':
        theme_words = THEMES.get((base or '').lower(), random.choice(list(THEMES.values())))
        username    = random.choice(theme_words) + random.choice(PREFIXES + SUFFIXES)
        username    = _fit(username, length)

    elif style == 'custom' and base:
        sep = _sep(platform)
        variations = [
            base + ''.join(random.choices(string.digits, k=random.randint(1, 3))),
            ''.join(random.choices(string.ascii_lowercase, k=1)) + base,
            base + sep + ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(1, 3))),
            base + random.choice(SUFFIXES),
            random.choice(PREFIXES) + base,
        ]
        username = random.choice(variations)
        username = _fit(username, length)

    else:
        return None

    return username if _is_valid(username, platform) else None


def generate_usernames(style: str, length: int, platform: str,
                       base: str | None = None, count: int = 10) -> list[str]:
    results: set[str] = set()
    attempts = 0
    while len(results) < count and attempts < count * 50:
        attempts += 1
        candidate = _generate_one(style, length, base, platform)
        if candidate:
            results.add(candidate)
    return list(results)


# ── Availability (Roblox only) ────────────────────────────────────────────────

ROBLOX_API = 'https://users.roblox.com/v1/usernames/users'


def check_availability(usernames: list[str], platform: str) -> dict:
    if platform != 'roblox':
        return {'available': usernames, 'taken': [], 'unchecked': True}

    available, taken = [], []
    for i in range(0, len(usernames), 100):
        batch   = usernames[i:i + 100]
        payload = {'usernames': batch, 'excludeBannedUsers': True}
        try:
            resp = requests.post(ROBLOX_API, json=payload, timeout=8)
            resp.raise_for_status()
            found = {u['requestedUsername'].lower() for u in resp.json().get('data', [])}
            for un in batch:
                (taken if un.lower() in found else available).append(un)
            security_logger.info('AVAIL_CHECK  platform=roblox  batch=%d  taken=%d  available=%d',
                                 len(batch),
                                 sum(1 for u in batch if u.lower() in found),
                                 sum(1 for u in batch if u.lower() not in found))
        except requests.RequestException as exc:
            security_logger.error('ROBLOX_API_ERROR  error=%s', exc)
            app.logger.error('Roblox API error: %s', exc)
            taken.extend(batch)

    return {'available': available, 'taken': taken, 'unchecked': False}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/check-ip', methods=['GET'])
def check_ip():
    """Called by the frontend on page load to show the VPN warning banner."""
    ip  = _ip()
    vpn = _is_vpn(ip)
    return jsonify({'vpn': vpn, 'ip': ip})


@app.route('/generate', methods=['POST'])
def generate():
    ip   = _ip()
    data = request.get_json(force=True, silent=True)

    if data is None:
        security_logger.warning('BAD_REQUEST  ip=%s  reason=invalid_json', ip)
        return jsonify({'error': 'Invalid JSON'}), 400

    # Re-check VPN on generate too — blocks attempts to bypass by calling
    # the API directly without the frontend warning.
    if _is_vpn(ip):
        security_logger.warning('GENERATE_BLOCKED_VPN  ip=%s', ip)
        return jsonify({'error': 'vpn_detected'}), 403

    platform = data.get('platform', 'roblox')
    if platform not in VALID_PLATFORMS:
        security_logger.warning('INVALID_INPUT  ip=%s  field=platform  value=%r', ip, platform)
        return jsonify({'error': 'Invalid platform'}), 400

    raw_style = data.get('style', 'unique')
    if raw_style not in VALID_STYLES:
        security_logger.warning('INVALID_INPUT  ip=%s  field=style  value=%r', ip, raw_style)
        return jsonify({'error': 'Invalid style'}), 400

    p = PLATFORMS[platform]
    try:
        length = max(p['min'], min(p['max'], int(data.get('length', 8))))
        count  = max(1, min(50, int(data.get('count', 10))))
    except (TypeError, ValueError):
        security_logger.warning('INVALID_INPUT  ip=%s  reason=non_numeric', ip)
        return jsonify({'error': 'length and count must be integers'}), 400

    raw_base = (data.get('base') or '').strip()
    base     = raw_base or None

    if base and (len(base) > 50 or any(c in base for c in '<>"\';&')):
        security_logger.warning('SUSPICIOUS_INPUT  ip=%s  field=base  value=%r', ip, base[:80])
        return jsonify({'error': 'Invalid base word'}), 400

    security_logger.info('GENERATE_REQUEST  ip=%s  platform=%s  style=%s  length=%d  count=%d  base=%r',
                         ip, platform, raw_style, length, count, base)

    usernames  = generate_usernames(raw_style, length, platform, base, count)
    avail_data = check_availability(usernames, platform)

    security_logger.info('GENERATE_RESULT  ip=%s  platform=%s  generated=%d  available=%d  taken=%d',
                         ip, platform, len(usernames), len(avail_data['available']), len(avail_data['taken']))

    return jsonify({
        'generated': usernames,
        'available': avail_data['available'],
        'taken':     avail_data['taken'],
        'unchecked': avail_data.get('unchecked', False),
        'platform':  platform,
    })


# ── HTML Template ─────────────────────────────────────────────────────────────

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Space Gen &mdash; Username Generator</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg:       #f4f4f5;
  --surface:  #ffffff;
  --border:   #e4e4e7;
  --text:     #18181b;
  --muted:    #71717a;
  --green:    #16a34a;
  --green-bg: #dcfce7;
  --red:      #dc2626;
  --red-bg:   #fee2e2;
  --blue:     #2563eb;
  --blue-bg:  #eff6ff;
  --accent:   #7c3aed;
  --radius:   10px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg:       #0f0f11;
    --surface:  #18181b;
    --border:   #3f3f46;
    --text:     #fafafa;
    --muted:    #a1a1aa;
    --green:    #4ade80;
    --green-bg: #052e16;
    --red:      #f87171;
    --red-bg:   #450a0a;
    --blue:     #60a5fa;
    --blue-bg:  #1e3a5f;
    --accent:   #a78bfa;
  }
}
body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }

.header {
  background: var(--surface); border-bottom: 1px solid var(--border);
  padding: 0 1.5rem; display: flex; align-items: center; gap: 0.75rem; height: 56px;
}
.logo { font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; color: var(--accent); }
.logo span { color: var(--text); font-weight: 400; }
.tagline { font-size: 0.8125rem; color: var(--muted); }

.tabs-wrap { background: var(--surface); border-bottom: 1px solid var(--border); overflow-x: auto; -webkit-overflow-scrolling: touch; }
.tabs { display: flex; max-width: 860px; margin: 0 auto; padding: 0 1rem; }
.tab {
  padding: 0 1.125rem; height: 44px; display: flex; align-items: center; gap: 5px;
  font-size: 0.875rem; font-weight: 500; cursor: pointer; white-space: nowrap;
  border: none; border-bottom: 2px solid transparent;
  color: var(--muted); background: none; transition: color 0.15s;
}
.tab:hover { color: var(--text); }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }

.page { max-width: 860px; margin: 0 auto; padding: 1.5rem 1rem 3rem; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; }

.notice { border-radius: 8px; padding: 0.75rem 1rem; font-size: 0.8125rem; margin-bottom: 1.25rem; display: flex; gap: 8px; align-items: flex-start; }
.notice-warn { background: #fefce8; border: 1px solid #fde047; color: #713f12; }
.notice-info { background: var(--blue-bg); border: 1px solid var(--blue); color: var(--blue); }
@media (prefers-color-scheme: dark) {
  .notice-warn { background: #1c1400; border-color: #713f12; color: #fde68a; }
  .notice-info { background: #1e3a5f; border-color: #2563eb; color: #93c5fd; }
}

.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 520px) { .grid2 { grid-template-columns: 1fr; } }
.field { display: flex; flex-direction: column; gap: 6px; }
.field label { font-size: 0.8125rem; color: var(--muted); }
.field input, .field select {
  padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px;
  background: var(--surface); color: var(--text); font-size: 0.875rem; width: 100%;
}
.field input:focus, .field select:focus { outline: 2px solid var(--accent); outline-offset: -1px; }

.btn {
  width: 100%; margin-top: 1.25rem; padding: 10px; border: 1px solid var(--border);
  border-radius: 8px; background: var(--surface); color: var(--text);
  font-size: 0.875rem; font-weight: 500; cursor: pointer; transition: background 0.15s;
}
.btn:hover { background: var(--bg); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.results { margin-top: 1.5rem; }
.results-meta { display: flex; justify-content: space-between; align-items: center; font-size: 0.8125rem; color: var(--muted); margin-bottom: 0.75rem; }
.un-list { display: flex; flex-direction: column; gap: 6px; }
.un-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface);
}
.un-row:hover { border-color: #a1a1aa; }
.un-name { font-family: ui-monospace, monospace; font-size: 0.875rem; word-break: break-all; }
.un-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; margin-left: 8px; }
.badge { font-size: 0.6875rem; font-weight: 600; padding: 2px 8px; border-radius: 20px; white-space: nowrap; }
.badge-avail   { background: var(--green-bg); color: var(--green); }
.badge-taken   { background: var(--red-bg);   color: var(--red); }
.badge-unknown { background: var(--blue-bg);  color: var(--blue); }
.copy-btn {
  font-size: 0.75rem; padding: 3px 8px; border: 1px solid var(--border);
  border-radius: 6px; background: transparent; color: var(--muted); cursor: pointer; white-space: nowrap;
}
.copy-btn:hover { background: var(--bg); }
.summary { text-align: right; font-size: 0.8125rem; color: var(--muted); margin-top: 0.75rem; }
.error { color: var(--red); font-size: 0.875rem; margin-top: 1rem; }
.spinner {
  display: inline-block; width: 14px; height: 14px; border: 2px solid var(--border);
  border-top-color: var(--accent); border-radius: 50%;
  animation: spin 0.6s linear infinite; margin-right: 6px; vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }

#vpn-banner { display: none; }
.vpn-banner {
  background: #450a0a; border-bottom: 3px solid #dc2626;
  padding: 0.875rem 1.5rem; display: flex; align-items: flex-start; gap: 12px;
  color: #fca5a5; font-size: 0.875rem; line-height: 1.5;
}
@media (prefers-color-scheme: light) {
  .vpn-banner { background: #fee2e2; border-bottom-color: #b91c1c; color: #7f1d1d; }
}
.vpn-icon { font-size: 20px; flex-shrink: 0; line-height: 1.4; }
.vpn-title { font-weight: 600; font-size: 0.9375rem; margin-bottom: 3px; color: #f87171; }
@media (prefers-color-scheme: light) { .vpn-title { color: #991b1b; } }
.vpn-steps { margin: 6px 0 0 1.25rem; }
.vpn-steps li { margin-bottom: 2px; }
</style>
</head>
<body>

<div id="vpn-banner">
  <div class="vpn-banner">
    <div class="vpn-icon">&#128274;</div>
    <div>
      <div class="vpn-title">VPN or proxy detected &mdash; please disable it</div>
      <div>Space Gen requires a direct connection to check username availability and protect against abuse.
      Your request will not go through while a VPN, proxy, or Tor is active.</div>
      <ol class="vpn-steps">
        <li>Disconnect from your VPN, proxy, or Tor browser.</li>
        <li>Reload this page.</li>
        <li>If you believe this is a mistake, your ISP or network may be flagged &mdash; try a different network.</li>
      </ol>
    </div>
  </div>
</div>

<div class="header">
  <div class="logo">Space<span>Gen</span></div>
  <div class="tagline">Username generator for every platform</div>
</div>

<div class="tabs-wrap">
  <div class="tabs" id="tabs">
    <button class="tab active" data-platform="roblox">&#127918; Roblox</button>
    <button class="tab" data-platform="discord">&#128172; Discord</button>
    <button class="tab" data-platform="tiktok">&#127925; TikTok</button>
    <button class="tab" data-platform="youtube">&#128250; YouTube</button>
    <button class="tab" data-platform="twitch">&#127897; Twitch</button>
    <button class="tab" data-platform="steam">&#127760; Steam</button>
  </div>
</div>

<div class="page">
  <div class="card">
    <div id="platform-notice"></div>

    <div class="grid2">
      <div class="field">
        <label for="length" id="length-label">Length</label>
        <input type="number" id="length" min="3" max="20" value="8">
      </div>
      <div class="field">
        <label for="count">How many to generate</label>
        <input type="number" id="count" min="1" max="50" value="10">
      </div>
    </div>

    <div class="field" style="margin-top:1rem">
      <label for="style">Style</label>
      <select id="style">
        <option value="unique">Unique (random)</option>
        <option value="rank">Rank names (e.g. ProGamer)</option>
        <option value="aesthetic">Aesthetic (minimal)</option>
        <option value="leet">Leet speak (3l33t style)</option>
        <option value="themed">Themed (space / fantasy / gaming / nature / cyber)</option>
        <option value="custom">Custom (based on your word)</option>
      </select>
    </div>

    <div class="field" id="base-wrap" style="display:none; margin-top:1rem">
      <label for="base" id="base-label">Base word or theme</label>
      <input type="text" id="base" placeholder="e.g. shadow or space">
    </div>

    <button class="btn" id="gen-btn">Generate &amp; check availability</button>
    <p class="error" id="error-msg" style="display:none"></p>
  </div>

  <div id="results"></div>
</div>

<script>
const PLATFORM_META = {
  roblox:  { min: 3,  max: 20, check: true,  label: 'Roblox' },
  discord: { min: 2,  max: 32, check: false, label: 'Discord' },
  tiktok:  { min: 2,  max: 24, check: false, label: 'TikTok' },
  youtube: { min: 3,  max: 30, check: false, label: 'YouTube' },
  twitch:  { min: 4,  max: 25, check: false, label: 'Twitch' },
  steam:   { min: 3,  max: 32, check: false, label: 'Steam' },
};

const NOTICES = {
  roblox:  ['warn', 'Availability checked live via Roblox\'s API. Usernames from banned/deleted accounts may appear available — always verify in Roblox\'s username change screen before spending Robux.'],
  discord: ['info', 'Discord has no public availability API. Names are generated to match Discord\'s format rules — check availability manually in Discord settings.'],
  tiktok:  ['info', 'TikTok has no public availability API. Names are generated to match TikTok\'s format rules — check availability manually in the TikTok app.'],
  youtube: ['info', 'YouTube has no public availability API. Names are generated to match YouTube\'s handle rules — check availability manually in YouTube Studio.'],
  twitch:  ['info', 'Twitch has no public availability API. Names are generated to match Twitch\'s format rules — check availability manually on Twitch.'],
  steam:   ['info', 'Steam has no public availability API. Names are generated to match Steam\'s format rules — check availability manually in Steam settings.'],
};

let currentPlatform = 'roblox';

document.getElementById('tabs').addEventListener('click', e => {
  const tab = e.target.closest('[data-platform]');
  if (!tab) return;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  currentPlatform = tab.dataset.platform;
  updatePlatformUI();
  document.getElementById('results').innerHTML = '';
  savePrefs();
});

function updatePlatformUI() {
  const meta   = PLATFORM_META[currentPlatform];
  const [type, text] = NOTICES[currentPlatform];
  const lenInput = document.getElementById('length');

  document.getElementById('length-label').textContent = `Length (${meta.min}\u2013${meta.max})`;
  lenInput.min = meta.min;
  lenInput.max = meta.max;
  const cur = parseInt(lenInput.value);
  if (cur < meta.min) lenInput.value = meta.min;
  if (cur > meta.max) lenInput.value = Math.min(meta.max, 8);

  document.getElementById('platform-notice').innerHTML =
    `<div class="notice notice-${type}">&#9432;&nbsp;${text}</div>`;

  document.getElementById('gen-btn').textContent =
    meta.check ? 'Generate & check availability' : 'Generate usernames';
}

const styleEl  = document.getElementById('style');
const baseWrap = document.getElementById('base-wrap');
const baseLabel = document.getElementById('base-label');

styleEl.addEventListener('change', () => { toggleBase(); savePrefs(); });

function toggleBase() {
  const v = styleEl.value;
  baseWrap.style.display = (v === 'custom' || v === 'themed') ? 'flex' : 'none';
  baseLabel.textContent = v === 'themed'
    ? 'Theme (space, fantasy, gaming, nature, cyber)' : 'Your base word';
}

function savePrefs() {
  localStorage.setItem('spaceGen', JSON.stringify({
    platform: currentPlatform,
    length:   document.getElementById('length').value,
    count:    document.getElementById('count').value,
    style:    styleEl.value,
    base:     document.getElementById('base').value,
  }));
}

function loadPrefs() {
  const saved = JSON.parse(localStorage.getItem('spaceGen') || '{}');
  if (saved.platform && PLATFORM_META[saved.platform]) {
    currentPlatform = saved.platform;
    document.querySelectorAll('.tab').forEach(t =>
      t.classList.toggle('active', t.dataset.platform === currentPlatform));
  }
  if (saved.length) document.getElementById('length').value = saved.length;
  if (saved.count)  document.getElementById('count').value  = saved.count;
  if (saved.style)  styleEl.value = saved.style;
  if (saved.base)   document.getElementById('base').value   = saved.base;
  updatePlatformUI();
  toggleBase();
}

['length','count','base'].forEach(id =>
  document.getElementById(id).addEventListener('input', savePrefs)
);

const genBtn    = document.getElementById('gen-btn');
const errorMsg  = document.getElementById('error-msg');
const resultsEl = document.getElementById('results');

genBtn.addEventListener('click', async () => {
  errorMsg.style.display = 'none';
  genBtn.disabled = true;
  genBtn.innerHTML = '<span class="spinner"></span>Generating\u2026';

  const payload = {
    platform: currentPlatform,
    length:   parseInt(document.getElementById('length').value) || 8,
    count:    parseInt(document.getElementById('count').value)  || 10,
    style:    styleEl.value,
    base:     document.getElementById('base').value.trim(),
  };

  try {
    const resp = await fetch('/generate', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      if (err.error === 'vpn_detected') {
        document.getElementById('vpn-banner').style.display = 'block';
        throw new Error('VPN or proxy detected. Please disable it and try again.');
      }
      throw new Error('Server error ' + resp.status);
    }
    const data = await resp.json();
    renderResults(data);
  } catch (err) {
    errorMsg.textContent = 'Something went wrong: ' + err.message;
    errorMsg.style.display = 'block';
  } finally {
    genBtn.disabled = false;
    const meta = PLATFORM_META[currentPlatform];
    genBtn.textContent = meta.check ? 'Generate & check availability' : 'Generate usernames';
  }
});

function renderResults(data) {
  const availSet   = new Set((data.available || []).map(s => s.toLowerCase()));
  const unchecked  = data.unchecked;
  const total      = data.generated.length;
  const availCount = data.available.length;
  const platLabel  = PLATFORM_META[data.platform]?.label || data.platform;

  const rows = data.generated.map(un => {
    const isAvail = availSet.has(un.toLowerCase());
    let badge, copy = '';

    if (unchecked) {
      badge = '<span class="badge badge-unknown">Not checked</span>';
      copy  = `<button class="copy-btn" onclick="copyName(this,'${un}')">Copy</button>`;
    } else if (isAvail) {
      badge = '<span class="badge badge-avail">Available</span>';
      copy  = `<button class="copy-btn" onclick="copyName(this,'${un}')">Copy</button>`;
    } else {
      badge = '<span class="badge badge-taken">Taken</span>';
    }

    return `<div class="un-row">
      <span class="un-name">${un}</span>
      <div class="un-right">${badge}${copy}</div>
    </div>`;
  }).join('');

  const metaRight = unchecked
    ? `${total} generated`
    : `${availCount} of ${total} available`;

  resultsEl.innerHTML = `
    <div class="results">
      <div class="results-meta">
        <span>${styleEl.options[styleEl.selectedIndex].text} &middot; ${platLabel}</span>
        <span>${metaRight}</span>
      </div>
      <div class="un-list">${rows}</div>
      ${unchecked ? '<p class="summary">Availability not checked &mdash; copy and verify manually.</p>'
                  : `<p class="summary">${availCount} available &middot; ${total - availCount} taken</p>`}
    </div>`;
}

function copyName(btn, name) {
  navigator.clipboard.writeText(name).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 1500);
  });
}

// ── VPN check on page load ──
(async () => {
  try {
    const resp = await fetch('/check-ip');
    if (!resp.ok) return;
    const data = await resp.json();
    if (data.vpn) {
      document.getElementById('vpn-banner').style.display = 'block';
      document.getElementById('gen-btn').disabled = true;
    }
  } catch (_) { /* fail open */ }
})();

loadPrefs();
</script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_ENV') == 'development', host='0.0.0.0', port=5000)