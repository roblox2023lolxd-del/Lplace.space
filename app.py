from flask import Flask, render_template_string, request
import json
import os
import time
import hashlib
import requests
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# File to store the view count and visit data
COUNTER_FILE = 'view_count.json'

# Threshold in seconds (e.g., 1 hour = 3600) to count as a new view
VIEW_THRESHOLD = 3600

def load_data():
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
                else:
                    return {'total_views': 0, 'visits': {}}
        except (json.JSONDecodeError, ValueError):
            app.logger.error("Invalid JSON in counter file - resetting")
            return {'total_views': 0, 'visits': {}}
    return {'total_views': 0, 'visits': {}}

def save_data(data):
    try:
        with open(COUNTER_FILE, 'w') as f:
            json.dump(data, f)
        app.logger.info("Data saved successfully")
    except Exception as e:
        app.logger.error(f"Failed to save data: {e}")

def get_unique_id(request):
    # Get real IP (handles proxies like Render/Heroku)
    ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    app.logger.info(f"Detected IP: {ip}")
    
    if ip == '127.0.0.1':  # Skip geolocation for local testing
        location = {'city': '', 'country_name': ''}
    else:
        try:
            response = requests.get(f'http://ipapi.co/{ip}/json/', timeout=5)
            if response.status_code == 200:
                location = response.json()
                app.logger.info(f"Location for {ip}: {location.get('city')}, {location.get('country_name')}")
            else:
                location = {'city': '', 'country_name': ''}
                app.logger.warning(f"Geolocation API failed with status {response.status_code}")
        except Exception as e:
            location = {'city': '', 'country_name': ''}
            app.logger.error(f"Geolocation error: {e}")
    
    ua = request.user_agent.string[:200]  # Truncate UA to avoid huge keys
    app.logger.info(f"User Agent: {ua}")
    
    raw_id = f"{ip}:{location.get('city', '')}:{location.get('country_name', '')}:{ua}"
    unique_id = hashlib.md5(raw_id.encode()).hexdigest()
    app.logger.info(f"Generated unique_id: {unique_id} from raw: {raw_id[:50]}...")
    return unique_id

@app.route('/')
def index():
    data = load_data()
    app.logger.info(f"Loaded data - total_views: {data['total_views']}, visits count: {len(data['visits'])}")
    
    unique_id = get_unique_id(request)
    now = time.time()
    
    last_visit = data['visits'].get(unique_id, 0)
    delta = now - last_visit if last_visit > 0 else 'new'
    app.logger.info(f"Last visit timestamp: {last_visit}, Delta: {delta}, Threshold: {VIEW_THRESHOLD}")
    
    if last_visit == 0 or (now - last_visit) > VIEW_THRESHOLD:
        # New or old enough visit: increment
        data['total_views'] += 1
        data['visits'][unique_id] = now
        save_data(data)
        is_new = True
        app.logger.info("Incremented view count")
    else:
        # Recent visit: no increment
        is_new = False
        app.logger.info("Recent visit - no increment")
    
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