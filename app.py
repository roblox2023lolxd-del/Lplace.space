from flask import Flask, render_template_string, request
import json
import os
import time
import hashlib
import requests

app = Flask(__name__)

# File to store the view count and visit data
COUNTER_FILE = 'view_count.json'

# Threshold in seconds (e.g., 1 hour = 3600) to count as a new view
VIEW_THRESHOLD = 86400

def load_data():
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, 'r') as f:
            return json.load(f)
    return {'total_views': 0, 'visits': {}}

def save_data(data):
    with open(COUNTER_FILE, 'w') as f:
        json.dump(data, f)

def get_unique_id(request):
    # Get real IP (handles proxies like Render/Heroku)
    ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    if ip == '127.0.0.1':  # Skip geolocation for local testing
        location = {'city': '', 'country_name': ''}
    else:
        try:
            response = requests.get(f'http://ipapi.co/{ip}/json/', timeout=5)
            if response.status_code == 200:
                location = response.json()
            else:
                location = {'city': '', 'country_name': ''}
        except:
            location = {'city': '', 'country_name': ''}
    
    ua = request.user_agent.string[:200]  # Truncate UA to avoid huge keys
    raw_id = f"{ip}:{location.get('city', '')}:{location.get('country_name', '')}:{ua}"
    # Hash for shorter key
    unique_id = hashlib.md5(raw_id.encode()).hexdigest()
    return unique_id

@app.route('/')
def index():
    data = load_data()
    unique_id = get_unique_id(request)
    now = time.time()
    
    last_visit = data['visits'].get(unique_id, 0)
    if last_visit == 0 or (now - last_visit) > VIEW_THRESHOLD:
        # New or old enough visit: increment
        data['total_views'] += 1
        data['visits'][unique_id] = now
        save_data(data)
        is_new = True
    else:
        # Recent visit: no increment
        is_new = False
    
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>View Counter</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f0f0f0; }
            .counter { font-size: 48px; color: #333; margin: 20px; }
            .position { font-size: 24px; color: #666; }
            .status { font-size: 18px; color: #007bff; margin: 10px; }
        </style>
    </head>
    <body>
        <h1>Welcome to the View Counter!</h1>
        <div class="counter">Total Views: {{ total_views }}</div>
        <div class="position">You are the {{ total_views }}th visitor!</div>
        <div class="status">{% if is_new %}New view counted!{% else %}Recent visit - not counted again.{% endif %}</div>
        <p>Views are unique per device/IP/location within 1 hour. Refreshing won't inflate it! 😊</p>
    </body>
    </html>
    '''
    return render_template_string(html, total_views=data['total_views'], is_new=is_new)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)