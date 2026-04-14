#!/usr/bin/env python3
# main.py
import os
import time
import redis
from flask import Flask, jsonify

# 1. Global Setup (Shared by both modes)
mode = os.getenv('MODE', 'api')
redis_client = redis.from_url(
    os.getenv('REDIS_URL', 'redis://localhost:6379/0'), 
    decode_responses=True
)

# 2. Define the Flask App globally
# This ensures Gunicorn ALWAYS finds "main:app" without crashing
app = Flask(__name__)

def run_agent():
    """Trading logic loop"""
    print(f"🚀 OpenClaw Agent Started in {mode} mode...")
    while True:
        # Your trading logic here
        redis_client.set("agent_heartbeat", time.time())
        print("Agent tick: Heartbeat updated.")
        time.sleep(60)

# 3. Define Routes (Always defined, but only used in API mode)
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

# 4. The Execution Switch
if __name__ == "__main__":
    if mode == 'agent':
        # This runs when you call "python3 main.py" in the agent container
        run_agent()
    else:
        # This runs for local dev/testing
        app.run(host="0.0.0.0", port=80)
