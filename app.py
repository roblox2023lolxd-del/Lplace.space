from flask import Flask, render_template_string, request
import json
import os

app = Flask(__name__)

# File to store the view count
COUNTER_FILE = 'view_count.json'

def load_count():
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, 'r') as f:
            data = json.load(f)
            return data.get('total_views', 0)
    return 0

def save_count(count):
    with open(COUNTER_FILE, 'w') as f:
        json.dump({'total_views': count}, f)

@app.route('/')
def index():
    # Increment count (simple anti-bot: check for user-agent or JS, but for now basic)
    count = load_count() + 1
    save_count(count)
    
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
        </style>
    </head>
    <body>
        <h1>Welcome to the View Counter!</h1>
        <div class="counter">Total Views: {{ total_views }}</div>
        <div class="position">You are the {{ total_views }}th visitor!</div>
        <p>Refresh to see the updated count (but don't bot it! 😊)</p>
    </body>
    </html>
    '''
    return render_template_string(html, total_views=count)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)