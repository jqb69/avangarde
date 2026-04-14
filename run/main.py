#!/usr/bin/env python3
# main.py

import time
import redis
from flask import Flask, jsonify

# Global setup
mode = os.getenv('MODE', 'api')
redis_client = redis.from_url(
    os.getenv('REDIS_URL', 'redis://localhost:6379/0'), 
    decode_responses=True
)

# Flask app always defined (for Gunicorn)
app = Flask(__name__)

def run_agent():
    """Trading logic loop"""
    print(f"🚀 OpenClaw Agent Started...")
    while True:
        redis_client.set("agent_heartbeat", time.time())
        print("Agent tick")
        time.sleep(60)

# Routes always defined
@app.route('/')
def index():
    visits = redis_client.incr('visits')
    last_beat = redis_client.get("agent_heartbeat")
    return jsonify({
        "service": "openclaw",
        "mode": mode,
        "agent_alive": last_beat,
        "visits": visits
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy", 
        "timestamp": time.time(),
        "mode": mode
    })

# Execution switch
if __name__ == "__main__":
    if mode == 'agent':
        run_agent()
    else:
        app.run(host="0.0.0.0", port=80)
