from flask import Flask, render_template_string, request
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import hashlib
import requests
import logging
import os

app = Flask(__name__)

# Supabase connection (replace with yours from Step 1)
DB_URI = os.environ.get('DATABASE_URL', 'your_supabase_connection_string_here')  # Use env var in Render!

# Threshold in seconds (1 hour)
VIEW_THRESHOLD = 3600

# Logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

def get_db_connection():
    return psycopg2.connect(DB_URI, sslmode='require')

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Create tables if not exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value INTEGER
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            unique_id TEXT PRIMARY KEY,
            last_visit TIMESTAMP
        );
    """)
    # Init total_views to 0 if missing
    cur.execute("INSERT INTO settings (key, value) VALUES ('total_views', 0) ON CONFLICT (key) DO NOTHING;")
    conn.commit()
    cur.close()
    conn.close()

def get_unique_id(request):
    ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    app.logger.info(f"Detected IP: {ip}")
    
    if ip == '127.0.0.1':
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
    
    ua = request.user_agent.string[:200]
    raw_id = f"{ip}:{location.get('city', '')}:{location.get('country_name', '')}:{ua}"
    return hashlib.md5(raw_id.encode()).hexdigest()

@app.route('/')
def index():
    # Init on first run
    init_db()
    
    unique_id = get_unique_id(request)
    now = time.time()
    app.logger.info(f"Unique ID: {unique_id}")
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check last visit
    cur.execute("SELECT last_visit FROM visits WHERE unique_id = %s;", (unique_id,))
    row = cur.fetchone()
    last_visit = row['last_visit'].timestamp() if row else 0
    delta = now - last_visit if last_visit > 0 else 'new'
    app.logger.info(f"Last visit: {last_visit}, Delta: {delta}s")
    
    is_new = False
    if last_visit == 0 or (now - last_visit) > VIEW_THRESHOLD:
        # Increment total
        cur.execute("UPDATE settings SET value = value + 1 WHERE key = 'total_views';")
        # Upsert visit
        cur.execute("""
            INSERT INTO visits (unique_id, last_visit) 
            VALUES (%s, NOW()) 
            ON CONFLICT (unique_id) DO UPDATE SET last_visit = NOW();
        """)
        conn.commit()
        is_new = True
        app.logger.info("Incremented view!")
    
    # Get current total
    cur.execute("SELECT value FROM settings WHERE key = 'total_views';")
    total_views = cur.fetchone()['value']
    
    cur.close()
    conn.close()
    
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
        <p>Views persist forever now—unique per device/IP/location within 1 hour. No more resets! 😊</p>
    </body>
    </html>
    '''
    return render_template_string(html, total_views=total_views, is_new=is_new)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)