from flask import Flask, render_template_string, request, jsonify
import requests
import random
import string
import logging
import os
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

# Security logger — goes to rotating file + console
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

_file_handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=5)
_file_handler.setFormatter(_fmt)
security_logger.addHandler(_file_handler)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_fmt)
security_logger.addHandler(_console_handler)

# Flask app logger mirrors the same format
logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(levelname)-8s  %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
app.logger.setLevel(logging.INFO)


def _ip() -> str:
    """Return the real client IP, respecting X-Forwarded-For if present."""
    return request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown').split(',')[0].strip()


VALID_STYLES = {'unique', 'rank', 'aesthetic', 'leet', 'themed', 'custom'}

ROBLOX_API = 'https://users.roblox.com/v1/usernames/users'

PREFIXES = ['pro', 'elite', 'mega', 'ultra', 'super', 'god', 'king', 'dark',
            'light', 'fire', 'ice', 'shadow', 'storm', 'star', 'galaxy',
            'dragon', 'ninja', 'samurai', 'phantom', 'cosmic']
SUFFIXES = ['gamer', 'player', 'pro', 'master', 'ninja', 'boss', 'hero',
            'legend', 'warrior', 'slayer', 'star', 'bolt', 'blade', 'flame',
            'frost', 'void', 'aura', 'edge', 'peak', 'apex']
LEET_MAP = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7'}
THEMES = {
    'space':   ['star', 'galaxy', 'cosmo', 'nova', 'orbit', 'nebula', 'comet'],
    'fantasy': ['elf', 'dragon', 'wizard', 'quest', 'myth', 'rune', 'arcane'],
    'gaming':  ['pixel', 'level', 'quest', 'spawn', 'glitch', 'respawn', 'loot'],
}


# ── Validation ────────────────────────────────────────────────────────────────

def is_valid_username(username: str) -> bool:
    """Roblox rules: 3–20 chars, alphanumeric + at most one underscore,
    underscore cannot be first or last character."""
    if not 3 <= len(username) <= 20:
        return False
    if username.startswith('_') or username.endswith('_'):
        return False
    if username.count('_') > 1:
        return False
    if not all(c.isalnum() or c == '_' for c in username):
        return False
    return True


# ── Generation ────────────────────────────────────────────────────────────────

def _maybe_insert_underscore(username: str, probability: float = 0.25) -> str:
    """Optionally insert a single underscore at a safe interior position."""
    if '_' not in username and random.random() < probability and len(username) > 4:
        pos = random.randint(1, len(username) - 2)
        username = username[:pos] + '_' + username[pos:]
    return username


def _fit_to_length(username: str, target: int) -> str:
    """Truncate or pad a username to exactly `target` characters with digits."""
    if len(username) > target:
        return username[:target]
    if len(username) < target:
        username += ''.join(random.choices(string.digits, k=target - len(username)))
    return username


def _generate_one(style: str, length: int, base: str | None) -> str | None:
    """Return one candidate username or None if generation fails for this attempt."""
    length = max(3, min(20, length))

    if style == 'unique':
        chars = string.ascii_lowercase + string.digits
        username = ''.join(random.choices(chars, k=length))
        username = _maybe_insert_underscore(username, 0.3)
        if len(username) > 20:
            return None

    elif style == 'rank':
        username = random.choice(PREFIXES) + random.choice(SUFFIXES)
        username = _fit_to_length(username, length)
        username = _maybe_insert_underscore(username, 0.2)

    elif style == 'aesthetic':
        consonants = 'bcdfghjklmnpqrstvwxyz'
        half = length // 2
        part1 = ''.join(random.choices(consonants + string.digits, k=half))
        part2 = ''.join(random.choices(consonants + string.digits, k=length - half))
        username = part1 + '_' + part2

    elif style == 'leet':
        base_word = (base or ''.join(random.choices(string.ascii_lowercase, k=4))).lower()
        username = ''.join(LEET_MAP.get(c, c) for c in base_word)
        username = _fit_to_length(username, length)
        username = _maybe_insert_underscore(username, 0.4)

    elif style == 'themed':
        theme_words = THEMES.get((base or '').lower(), random.choice(list(THEMES.values())))
        username = random.choice(theme_words) + random.choice(PREFIXES + SUFFIXES)
        username = _fit_to_length(username, length)

    elif style == 'custom' and base:
        variations = [
            base + ''.join(random.choices(string.digits, k=random.randint(1, 3))),
            ''.join(random.choices(string.ascii_lowercase, k=1)) + base,
            base + '_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(1, 3))),
            base + random.choice(SUFFIXES),
            random.choice(PREFIXES) + base,
        ]
        username = random.choice(variations)
        username = _fit_to_length(username, length)

    else:
        return None

    return username if is_valid_username(username) else None


def generate_usernames(style: str, length: int, base: str | None = None, count: int = 10) -> list[str]:
    """Generate `count` unique valid usernames. Gives up after 500 attempts."""
    results: set[str] = set()
    attempts = 0
    max_attempts = count * 50  # prevent infinite loops

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        candidate = _generate_one(style, length, base)
        if candidate:
            results.add(candidate)

    return list(results)


# ── Availability check ────────────────────────────────────────────────────────

def check_availability(usernames: list[str]) -> dict:
    """Return {'available': [...], 'taken': [...]} by querying Roblox in batches."""
    available, taken = [], []
    batch_size = 100  # Roblox accepts up to 100 per request

    for i in range(0, len(usernames), batch_size):
        batch = usernames[i:i + batch_size]
        payload = {'usernames': batch, 'excludeBannedUsers': True}
        try:
            resp = requests.post(ROBLOX_API, json=payload, timeout=8)
            resp.raise_for_status()
            found_names = {u['requestedUsername'].lower() for u in resp.json().get('data', [])}
            for un in batch:
                (taken if un.lower() in found_names else available).append(un)
            security_logger.info('AVAIL_CHECK  batch_size=%d  taken=%d  available=%d',
                                 len(batch),
                                 sum(1 for u in batch if u.lower() in found_names),
                                 sum(1 for u in batch if u.lower() not in found_names))
        except requests.RequestException as exc:
            security_logger.error('ROBLOX_API_ERROR  error=%s', exc)
            app.logger.error('Roblox API error: %s', exc)
            # On error, mark whole batch as unknown (treat as taken to be safe)
            taken.extend(batch)

    return {'available': available, 'taken': taken}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/generate', methods=['POST'])
def generate():
    """JSON endpoint consumed by the frontend."""
    ip = _ip()

    data = request.get_json(force=True, silent=True)
    if data is None:
        security_logger.warning('BAD_REQUEST  ip=%s  reason=invalid_json', ip)
        return jsonify({'error': 'Invalid JSON'}), 400

    raw_style = data.get('style', 'unique')
    if raw_style not in VALID_STYLES:
        security_logger.warning('INVALID_INPUT  ip=%s  field=style  value=%r', ip, raw_style)
        return jsonify({'error': 'Invalid style'}), 400

    try:
        length = max(3, min(20, int(data.get('length', 8))))
        count  = max(1, min(50, int(data.get('count', 10))))
    except (TypeError, ValueError):
        security_logger.warning('INVALID_INPUT  ip=%s  reason=non_numeric_length_or_count', ip)
        return jsonify({'error': 'length and count must be integers'}), 400

    raw_base = (data.get('base') or '').strip()
    base = raw_base or None

    # Flag suspiciously long or script-looking base words
    if base and (len(base) > 50 or any(c in base for c in '<>"\';&')):
        security_logger.warning('SUSPICIOUS_INPUT  ip=%s  field=base  value=%r', ip, base[:80])
        return jsonify({'error': 'Invalid base word'}), 400

    security_logger.info('GENERATE_REQUEST  ip=%s  style=%s  length=%d  count=%d  base=%r',
                         ip, raw_style, length, count, base)

    usernames  = generate_usernames(raw_style, length, base, count)
    avail_data = check_availability(usernames)

    security_logger.info('GENERATE_RESULT  ip=%s  generated=%d  available=%d  taken=%d',
                         ip, len(usernames), len(avail_data['available']), len(avail_data['taken']))

    return jsonify({
        'generated': usernames,
        'available': avail_data['available'],
        'taken':     avail_data['taken'],
    })


# ── Template ──────────────────────────────────────────────────────────────────

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Roblox Username Generator</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg:      #f4f4f5;
    --surface: #ffffff;
    --border:  #e4e4e7;
    --text:    #18181b;
    --muted:   #71717a;
    --green:   #16a34a;
    --green-bg:#dcfce7;
    --red:     #dc2626;
    --red-bg:  #fee2e2;
    --accent:  #2563eb;
    --radius:  10px;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg:      #18181b;
      --surface: #27272a;
      --border:  #3f3f46;
      --text:    #fafafa;
      --muted:   #a1a1aa;
      --green:   #4ade80;
      --green-bg:#052e16;
      --red:     #f87171;
      --red-bg:  #450a0a;
      --accent:  #60a5fa;
    }
  }
  body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; padding: 2rem 1rem; }
  .page { max-width: 760px; margin: 0 auto; }
  h1 { font-size: 1.5rem; font-weight: 600; margin-bottom: 0.25rem; }
  .sub { font-size: 0.875rem; color: var(--muted); margin-bottom: 1.5rem; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; }
  .notice { background: #fefce8; border: 1px solid #fde047; border-radius: 8px; padding: 0.75rem 1rem;
            font-size: 0.8125rem; color: #713f12; margin-bottom: 1.25rem; display: flex; gap: 8px; }
  @media (prefers-color-scheme: dark) { .notice { background: #1c1400; border-color: #713f12; color: #fde68a; } }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
  @media (max-width: 520px) { .grid { grid-template-columns: 1fr; } }
  .field { display: flex; flex-direction: column; gap: 6px; }
  .field label { font-size: 0.8125rem; color: var(--muted); }
  .field input, .field select {
    padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px;
    background: var(--surface); color: var(--text); font-size: 0.875rem; width: 100%;
  }
  .field input:focus, .field select:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
  #base-wrap { margin-top: 1rem; }
  .btn {
    width: 100%; margin-top: 1.25rem; padding: 10px; border: 1px solid var(--border);
    border-radius: 8px; background: var(--surface); color: var(--text);
    font-size: 0.875rem; font-weight: 500; cursor: pointer; transition: background 0.15s;
  }
  .btn:hover { background: var(--bg); }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .results { margin-top: 1.5rem; }
  .results-meta { display: flex; justify-content: space-between; align-items: center;
                  font-size: 0.8125rem; color: var(--muted); margin-bottom: 0.75rem; }
  .un-list { display: flex; flex-direction: column; gap: 6px; }
  .un-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px;
    background: var(--surface);
  }
  .un-row:hover { border-color: #a1a1aa; }
  .un-name { font-family: ui-monospace, monospace; font-size: 0.875rem; }
  .un-right { display: flex; align-items: center; gap: 8px; }
  .badge { font-size: 0.6875rem; font-weight: 600; padding: 2px 8px; border-radius: 20px; }
  .badge-avail { background: var(--green-bg); color: var(--green); }
  .badge-taken { background: var(--red-bg); color: var(--red); }
  .copy-btn {
    font-size: 0.75rem; padding: 3px 8px; border: 1px solid var(--border);
    border-radius: 6px; background: transparent; color: var(--muted); cursor: pointer;
  }
  .copy-btn:hover { background: var(--bg); }
  .summary { text-align: right; font-size: 0.8125rem; color: var(--muted); margin-top: 0.75rem; }
  .error { color: var(--red); font-size: 0.875rem; margin-top: 1rem; }
  .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid var(--border);
             border-top-color: var(--accent); border-radius: 50%; animation: spin 0.6s linear infinite; margin-right: 6px; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="page">
  <h1>Roblox username generator</h1>
  <p class="sub">Generate and check username availability in bulk</p>

  <div class="card">
    <div class="notice">
      &#9888;&nbsp;
      Usernames from recently deleted or banned accounts may appear available here but could still be reserved.
      Always verify in Roblox's username change screen before spending Robux.
    </div>

    <div class="grid">
      <div class="field">
        <label for="length">Length (3–20)</label>
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
        <option value="aesthetic">Aesthetic (minimal + underscore)</option>
        <option value="leet">Leet speak (3l33t style)</option>
        <option value="themed">Themed (space / fantasy / gaming)</option>
        <option value="custom">Custom (based on your word)</option>
      </select>
    </div>

    <div class="field" id="base-wrap" style="display:none">
      <label for="base" id="base-label">Base word or theme</label>
      <input type="text" id="base" placeholder="e.g. shadow or space">
    </div>

    <button class="btn" id="gen-btn">Generate &amp; check availability</button>
    <p class="error" id="error-msg" style="display:none"></p>
  </div>

  <div id="results"></div>
</div>

<script>
const styleEl  = document.getElementById('style');
const baseWrap = document.getElementById('base-wrap');
const baseLabel = document.getElementById('base-label');
const genBtn   = document.getElementById('gen-btn');
const errorMsg = document.getElementById('error-msg');
const resultsEl = document.getElementById('results');

// Restore saved prefs
const saved = JSON.parse(localStorage.getItem('rbxGen') || '{}');
['length','count','style','base'].forEach(k => { if (saved[k] !== undefined) document.getElementById(k).value = saved[k]; });
toggleBase();

styleEl.addEventListener('change', () => { toggleBase(); savePrefs(); });
['length','count','base'].forEach(id => document.getElementById(id).addEventListener('input', savePrefs));

function toggleBase() {
  const v = styleEl.value;
  const show = v === 'custom' || v === 'themed';
  baseWrap.style.display = show ? 'block' : 'none';
  baseLabel.textContent = v === 'themed' ? 'Theme (space, fantasy, or gaming)' : 'Your base word';
}

function savePrefs() {
  localStorage.setItem('rbxGen', JSON.stringify({
    length: document.getElementById('length').value,
    count:  document.getElementById('count').value,
    style:  styleEl.value,
    base:   document.getElementById('base').value,
  }));
}

genBtn.addEventListener('click', async () => {
  errorMsg.style.display = 'none';
  genBtn.disabled = true;
  genBtn.innerHTML = '<span class="spinner"></span>Generating…';

  const payload = {
    length: parseInt(document.getElementById('length').value) || 8,
    count:  parseInt(document.getElementById('count').value)  || 10,
    style:  styleEl.value,
    base:   document.getElementById('base').value.trim(),
  };

  try {
    const resp = await fetch('/generate', {
      method:  'POST',
      headers: {'Content-Type': 'application/json'},
      body:    JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error('Server error ' + resp.status);
    const data = await resp.json();
    renderResults(data);
  } catch (err) {
    errorMsg.textContent = 'Something went wrong: ' + err.message;
    errorMsg.style.display = 'block';
  } finally {
    genBtn.disabled = false;
    genBtn.textContent = 'Generate & check availability';
  }
});

function renderResults(data) {
  const availSet = new Set(data.available.map(s => s.toLowerCase()));
  const total = data.generated.length;
  const availCount = data.available.length;

  const rows = data.generated.map(un => {
    const isAvail = availSet.has(un.toLowerCase());
    const copyBtn = isAvail
      ? `<button class="copy-btn" onclick="copyName(this,'${un}')">Copy</button>`
      : '';
    return `<div class="un-row">
      <span class="un-name">${un}</span>
      <div class="un-right">
        <span class="badge ${isAvail ? 'badge-avail' : 'badge-taken'}">${isAvail ? 'Available' : 'Taken'}</span>
        ${copyBtn}
      </div>
    </div>`;
  }).join('');

  resultsEl.innerHTML = `
    <div class="results">
      <div class="results-meta">
        <span>${payload_style(data)} · ${total} generated</span>
        <span>${availCount} available</span>
      </div>
      <div class="un-list">${rows}</div>
      <p class="summary">${availCount} available &middot; ${total - availCount} taken</p>
    </div>`;
}

function payload_style(data) {
  return styleEl.options[styleEl.selectedIndex].text;
}

function copyName(btn, name) {
  navigator.clipboard.writeText(name).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 1500);
  });
}
</script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)