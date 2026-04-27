#!/usr/bin/env python3
# main.py
import os
import asyncio
import threading
from flask import Flask, jsonify
from redis import Redis
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from dotenv import load_dotenv

# 1. Initialization
load_dotenv()

# Config from .env
API_ID = int(os.getenv("TG_API_ID", 0))
API_HASH = os.getenv("TG_API_HASH")
SESSION_STR = os.getenv("TG_SESSION_STR")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost") # If redis is in another container, use its name

# Connect to Redis
r = Redis(host=REDIS_HOST, port=6379, decode_responses=True)

# Initialize Telegram Client
client = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)

# Initialize Flask App
app = Flask(__name__)

# --- WEB ROUTES (Flask) ---

@app.route('/health')
def health():
    return jsonify({"status": "running", "redis_connected": r.ping()}), 200

@app.route('/stats')
def stats():
    # Example: Pull sniping stats from Redis
    snipes = r.get("total_snipes") or 0
    return jsonify({"total_snipes": snipes}), 200

# --- SNIPER LOGIC (Telethon) ---

@client.on(events.NewMessage(chats=['TargetChannelAlpha', 'TargetChannelBeta']))
async def handler(event):
    """The actual sniping logic goes here"""
    msg = event.raw_text
    print(f"📩 New Signal Detected: {msg}")
    
    # Example Snipe Logic
    # 1. Parse Token Address
    # 2. Check Redis if we already bought it
    # 3. Execute Trade
    r.incr("total_snipes")
    await client.send_message('me', f"✅ Sniper triggered for: {msg[:20]}...")

async def run_telegram():
    print("🚀 Starting Telegram Sniper Loop...")
    await client.start()
    print("✅ Telegram Connected!")
    await client.run_until_disconnected()

# --- THE GLUE ---

def start_flask():
    """Run Flask in a separate thread"""
    app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)

if __name__ == "__main__":
    # 1. Start Flask in background thread
    threading.Thread(target=start_flask, daemon=True).start()

    # 2. Start Telegram in the main event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_telegram())
    except KeyboardInterrupt:
        print("🛑 Shutting down...")
