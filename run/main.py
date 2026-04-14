#!/usr/bin/env python3
# main.py
import os
import time
import redis
from flask import Flask, jsonify

app = Flask(__name__)
mode = os.getenv('MODE', 'api')

# Connect to Redis
redis_client = redis.from_url(
    os.getenv('REDIS_URL', 'redis://localhost:6379/0'), 
    decode_responses=True
)

def run_agent():
    """Trading logic loop"""
    print("🚀 OpenClaw Agent Started...")
    while True:
        # Example: Log a heartbeat to Redis so the API knows the agent is alive
        redis_client.set("agent_heartbeat", time.time())
        time.sleep(60)

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

# This logic handles the "MODE" branching
if __name__ == "__main__":
    if mode == 'agent':
        run_agent()
    else:
        # This only runs if you do 'python main.py' manually
        app.run(host="0.0.0.0", port=80)
