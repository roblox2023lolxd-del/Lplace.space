# app.py
from flask import Flask, render_template_string, request, jsonify
import requests
import random
import string
import logging
from datetime import datetime

app = Flask(__name__)

# Logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

ROBLOX_API = 'https://users.roblox.com/v1/usernames/users'

PREFIXES = ['pro', 'elite', 'mega', 'ultra', 'super', 'noob', 'god', 'king', 'queen', 'dark', 'light', 'fire', 'ice', 'shadow', 'storm', 'star', 'galaxy', 'elf', 'dragon', 'ninja', 'samurai']
SUFFIXES = ['gamer', 'player', 'pro', 'master', 'ninja', 'boss', 'hero', 'legend', 'warrior', 'slayer', 'x', 'z', '123', 'star', 'bolt', 'blade', 'flame', 'frost', 'void', 'aura']
LEET_MAP = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7'}

# -------- VISITOR LOGGING --------
@app.before_request
def log_visitor():
    if request.path.startswith('/static') or request.path == '/api/visitor-log':
        return

    visitor = {
        "timestamp": datetime.utcnow().isoformat(),
        "ip": request.headers.get('X-Forwarded-For', request.remote_addr),
        "method": request.method,
        "path": request.path,
        "user_agent": request.headers.get('User-Agent'),
        "referrer": request.referrer
    }

    app.logger.info("=== VISITOR LOG ===")
    app.logger.info(visitor)
    app.logger.info("===================")

@app.route('/api/visitor-log', methods=['POST'])
def visitor_log():
    data = request.json or {}

    visitor = {
        "timestamp": datetime.utcnow().isoformat(),
        "ip": request.headers.get('X-Forwarded-For', request.remote_addr),
        "user_agent": request.headers.get('User-Agent'),
        "client_data": data
    }

    app.logger.info("=== CLIENT DATA LOG ===")
    app.logger.info(visitor)
    app.logger.info("=======================")

    return jsonify({"status": "ok"}), 200
# --------------------------------

def is_valid_username(username):
    if not 3 <= len(username) <= 20:
        return False
    if username.startswith('_') or username.endswith('_'):
        return False
    if username.count('_') > 1:
        return False
    if not all(c.isalnum() or c == '_' for c in username):
        return False
    return True

def generate_usernames(style, length, base=None, count=10):
    usernames = set()
    while len(usernames) < count:
        if style == 'unique':
            chars = string.ascii_lowercase + string.digits
            username = ''.join(random.choices(chars, k=length))
            if random.random() < 0.3 and length > 4:
                pos = random.randint(1, length-2)
                username = username[:pos] + '_' + username[pos:]
        elif style == 'rank':
            username = random.choice(PREFIXES) + random.choice(SUFFIXES)
        elif style == 'aesthetic':
            consonants = 'bcdfghjklmnpqrstvwxyz'
            username = ''.join(random.choices(consonants + string.digits, k=length))
        elif style == 'leet':
            base_word = base or ''.join(random.choices(string.ascii_lowercase, k=4))
            username = ''.join(LEET_MAP.get(c, c) for c in base_word)
        else:
            username = ''.join(random.choices(string.ascii_lowercase, k=length))

        username = username[:length]
        if is_valid_username(username):
            usernames.add(username)
    return list(usernames)

def check_availability(usernames):
    if not usernames:
        return []
    try:
        res = requests.post(ROBLOX_API, json={
            'usernames': usernames[:20],
            'excludeBannedUsers': True
        })
        if res.status_code == 200:
            taken = {u['name'].lower() for u in res.json().get('data', [])}
            return [u for u in usernames if u.lower() not in taken]
    except Exception as e:
        app.logger.error(e)
    return []

@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    if request.method == 'POST':
        length = int(request.form.get('length', 8))
        style = request.form.get('style', 'unique')
        base = request.form.get('base', '')
        count = int(request.form.get('count', 10))

        generated = generate_usernames(style, length, base, count)
        available = check_availability(generated)

        results = {
            'generated': generated,
            'available': available,
            'style': style,
            'length': length
        }

    html = '''
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Username Generator</h1>
        <form method="POST">
            <input name="length" type="number" value="8">
            <select name="style">
                <option value="unique">Unique</option>
                <option value="rank">Rank</option>
                <option value="aesthetic">Aesthetic</option>
                <option value="leet">Leet</option>
            </select>
            <input name="base" placeholder="base">
            <input name="count" type="number" value="10">
            <button type="submit">Generate</button>
        </form>

        {% if results %}
            {% for u in results.generated %}
                <div>
                    {{ u }} {% if u in results.available %}(Available){% else %}(Taken){% endif %}
                </div>
            {% endfor %}
        {% endif %}

        <script>
        (function () {
            async function send() {
                const data = {
                    screen: screen.width + "x" + screen.height,
                    tz: Intl.DateTimeFormat().resolvedOptions().timeZone
                };
                try {
                    await fetch('/api/visitor-log', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data),
                        keepalive: true
                    });
                } catch {}
            }
            window.addEventListener('load', send);
        })();
        </script>
    </body>
    </html>
    '''
    return render_template_string(html, results=results)

if __name__ == '__main__':
    app.run(debug=True)