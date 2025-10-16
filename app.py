from flask import Flask, render_template_string, request, jsonify
import requests
import random
import string
import json
import logging
import os

app = Flask(__name__)

# Logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Roblox API endpoint for batch username lookup
ROBLOX_API = 'https://users.roblox.com/v1/usernames/users'

# Word lists for rank-style names
PREFIXES = ['pro', 'elite', 'mega', 'ultra', 'super', 'noob', 'god', 'king', 'queen', 'dark', 'light', 'fire', 'ice', 'shadow', 'storm', 'star', 'galaxy', 'elf', 'dragon', 'ninja', 'samurai']
SUFFIXES = ['gamer', 'player', 'pro', 'master', 'ninja', 'boss', 'hero', 'legend', 'warrior', 'slayer', 'x', 'z', '123', 'star', 'bolt', 'blade', 'flame', 'frost', 'void', 'aura']

# Leet replacements
LEET_MAP = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7'}

def is_valid_username(username):
    """Check if username follows Roblox rules: 3-20 chars, alphanumeric + one _, no leading/trailing _"""
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
    """Generate count usernames based on style, length, optional base"""
    usernames = set()  # Avoid duplicates
    while len(usernames) < count:
        if style == 'unique':
            # Random alphanumeric + occasional _
            chars = string.ascii_lowercase + string.digits
            username = ''.join(random.choices(chars, k=length))
            # Insert _ randomly if length allows
            if random.random() < 0.3 and length > 4:
                pos = random.randint(1, length-2)
                username = username[:pos] + '_' + username[pos:]
                if len(username) > 20:
                    continue
        elif style == 'rank':
            # Prefix + suffix, pad with numbers if needed
            prefix = random.choice(PREFIXES)
            suffix = random.choice(SUFFIXES)
            username = prefix + suffix
            # Add numbers to reach length
            num_chars = length - len(username)
            if num_chars > 0:
                username += ''.join(random.choices(string.digits, k=num_chars))
            elif num_chars < 0:
                username = username[:length]  # Truncate
            # Add _ if fits
            if random.random() < 0.2 and length > 4:
                pos = random.randint(1, len(username)-2)
                username = username[:pos] + '_' + username[pos:]
        elif style == 'aesthetic':
            # Minimal, vowel-less + _ for style
            consonants = 'bcdfghjklmnpqrstvwxyz'
            username = ''.join(random.choices(consonants + string.digits, k=length))
            # Add _ in middle for aesthetic
            if length > 3:
                pos = length // 2
                username = username[:pos] + '_' + username[pos:]
        elif style == 'leet':
            # Base word with leet speak
            base_word = base or ''.join(random.choices(string.ascii_lowercase, k=4))
            username = ''
            for char in base_word.lower():
                username += LEET_MAP.get(char, char)
            # Pad/truncate to length with digits
            num_chars = length - len(username)
            if num_chars > 0:
                username += ''.join(random.choices(string.digits, k=num_chars))
            elif num_chars < 0:
                username = username[:length]
            # Add random _ if fits
            if random.random() < 0.4 and length > 4 and '_' not in username:
                pos = random.randint(1, len(username)-2)
                username = username[:pos] + '_' + username[pos:]
        elif style == 'themed' and base:
            # Themes based on base (e.g., if base='space', use space words)
            themes = {
                'space': ['star', 'galaxy', 'cosmo', 'nova', 'orbit'],
                'fantasy': ['elf', 'dragon', 'wizard', 'quest', 'myth'],
                'gaming': ['pixel', 'level', 'quest', 'spawn', 'glitch']
            }
            theme_words = themes.get(base.lower(), random.choice(list(themes.values())))
            word1 = random.choice(theme_words)
            word2 = random.choice(PREFIXES + SUFFIXES)
            username = word1 + word2
            # Adjust length
            if len(username) > length:
                username = username[:length]
            elif len(username) < length:
                username += ''.join(random.choices(string.digits, k=length - len(username)))
        elif style == 'custom' and base:
            # Variations on base
            variations = [
                base + ''.join(random.choices(string.digits, k=random.randint(1,3))),
                ''.join(random.choices(string.ascii_lowercase, k=1)) + base,
                base + '_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(1,3))),
                base + random.choice(SUFFIXES),
                random.choice(PREFIXES) + base,
            ]
            username = random.choice(variations)
            # Adjust to length
            if len(username) > length:
                username = username[:length]
            elif len(username) < length:
                username += ''.join(random.choices(string.digits, k=length - len(username)))
        else:
            continue
        if is_valid_username(username) and len(usernames) < count:
            usernames.add(username)
    return list(usernames)

def check_availability(usernames):
    """Batch check availability via Roblox API"""
    if not usernames:
        return []
    payload = {
        'usernames': usernames[:20],  # API limit? Batch small
        'excludeBannedUsers': True
    }
    try:
        response = requests.post(ROBLOX_API, json=payload)
        if response.status_code == 200:
            data = response.json()
            taken_usernames = {user['name'].lower() for user in data.get('data', [])}
            available = [un for un in usernames if un.lower() not in taken_usernames]
            return available
        else:
            app.logger.error(f"API error: {response.status_code}")
            return []  # Fallback: assume none available on error
    except Exception as e:
        app.logger.error(f"Availability check failed: {e}")
        return []

@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    if request.method == 'POST':
        length = int(request.form.get('length', 8))
        style = request.form.get('style', 'unique')
        base = request.form.get('base', '') if style in ['custom', 'themed'] else None
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
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Roblox Rare Username Generator</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f4f4f4; }
            form { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            label { display: block; margin: 10px 0 5px; }
            input, select { width: 100%; padding: 8px; margin-bottom: 10px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
            .results { margin-top: 20px; }
            .username { padding: 5px; margin: 2px 0; background: white; border: 1px solid #ddd; border-radius: 4px; }
            .available { border-color: #28a745; background: #d4edda; }
            .taken { border-color: #dc3545; background: #f8d7da; }
        </style>
    </head>
    <body>
        <h1>Roblox Rare Username Generator</h1>
        <form method="POST" id="genForm">
            <label>Username Length (3-20):</label>
            <input type="number" name="length" min="3" max="20" value="8" required>
            
            <label>Style:</label>
            <select name="style" id="style">
                <option value="unique">Unique (Random)</option>
                <option value="rank">Rank Names (e.g., ProGamer)</option>
                <option value="aesthetic">Aesthetic (Minimal + _)</option>
                <option value="leet">Leet Speak (3l33t style)</option>
                <option value="themed">Themed (Enter theme below)</option>
                <option value="custom">Custom (Enter base below)</option>
            </select>
            
            <div id="custom-input" style="display:none;">
                <label>Base/Theme Word (e.g., Roblox or space):</label>
                <input type="text" name="base" placeholder="Enter base word or theme">
            </div>
            
            <label>Number to Generate:</label>
            <input type="number" name="count" min="1" max="50" value="10">
            
            <button type="submit">Generate & Check</button>
        </form>
        
        {% if results %}
        <div class="results">
            <h2>Results for {{ results.style }} style, {{ results.length }} chars:</h2>
            {% for un in results.generated %}
            <div class="username {% if un in results.available %}available{% else %}taken{% endif %}">
                {{ un }} {% if un in results.available %}(Available!){% else %}(Taken){% endif %}
            </div>
            {% endfor %}
            <p><strong>{{ results.available|length }} available out of {{ results.generated|length }}</strong></p>
        </div>
        {% endif %}
        
        <p>More generators for other sites coming soon! Note: Availability can change quickly.</p>
        
        <script>
            const form = document.getElementById('genForm');
            const styleSelect = document.getElementById('style');
            const customInput = document.getElementById('custom-input');
            
            // Load saved values
            function loadSaved() {
                const saved = JSON.parse(localStorage.getItem('usernameGen') || '{}');
                form.length.value = saved.length || 8;
                form.count.value = saved.count || 10;
                styleSelect.value = saved.style || 'unique';
                if (saved.base) {
                    form.base.value = saved.base;
                }
                toggleCustom();
            }
            
            // Save on change
            form.addEventListener('input', function(e) {
                const data = {
                    length: form.length.value,
                    count: form.count.value,
                    style: styleSelect.value,
                    base: form.base ? form.base.value : ''
                };
                localStorage.setItem('usernameGen', JSON.stringify(data));
            });
            
            // Toggle custom input
            function toggleCustom() {
                customInput.style.display = (styleSelect.value === 'custom' || styleSelect.value === 'themed') ? 'block' : 'none';
            }
            
            styleSelect.addEventListener('change', function() {
                toggleCustom();
                // Trigger save
                form.dispatchEvent(new Event('input'));
            });
            
            // Initial load
            loadSaved();
        </script>
    </body>
    </html>
    '''
    return render_template_string(html, results=results)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)