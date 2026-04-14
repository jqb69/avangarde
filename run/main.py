#!/usr/bin/env python3
# main.py
from flask import Flask, jsonify
import time
import os
import redis
import threading

app = Flask(__name__)
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'), decode_responses=True)
mode = os.getenv('MODE', 'api')

def run_agent():
    """Single trading agent loop"""
    while True:
        # Your trading logic here - only ONE instance runs this
        print("Agent tick...")
        time.sleep(60)

@app.route('/')
def index():
    visits = redis_client.incr('visits')
    return jsonify({"service": "openclaw", "mode": mode, "visits": visits})

@app.route('/health')
def health():
    try:
        redis_client.ping()
        return jsonify({"status": "healthy", "mode": mode, "timestamp": time.time()})
    except:
        return jsonify({"status": "unhealthy", "mode": mode}), 500

if __name__ == "__main__":
    if mode == 'agent':
        # Agent mode: no web server, just the trading loop
        run_agent()
    else:
        # API mode: web server only, no trading logic
        app.run(host="0.0.0.0", port=80)
