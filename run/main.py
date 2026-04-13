#!/usr/bin/env python3
# main.py
from flask import Flask, jsonify
import time

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"service": "openclaw", "status": "running"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": time.time()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
