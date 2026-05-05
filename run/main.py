#!/usr/bin/env python3
# main.py

import os
import asyncio
import threading
from flask import Flask, jsonify, render_template
from redis import Redis
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Your custom logic imports
from core.llm_router import LLMRouter
from utils.config_loader import APP_CONFIG

# 1. Initialization & Config
# Note: APP_CONFIG is already loaded from config.yaml via your loader
API_ID = int(os.getenv("TG_API_ID", 0))
API_HASH = os.getenv("TG_API_HASH")
SESSION_STR = os.getenv("TG_SESSION_STR")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

# Persistent Connections
r = Redis(host=REDIS_HOST, port=6379, decode_responses=True)
router = LLMRouter(config=APP_CONFIG)
client = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)

app = Flask(__name__, 
            template_folder='web/templates', 
            static_folder='web/static')

# --- TELEGRAM SNIPER LOGIC ---

@client.on(events.NewMessage)
async def handle_new_message(event):
    """Core Sniping Logic"""
    try:
        # 1. Extract raw data
        raw_text = event.raw_text
        
        # 2. Get AI Decision via your Dynamic Router
        # is_emergency can be triggered by keywords or rapid price action
        decision = router.get_decision(
            data=raw_text, 
            context={"peer": str(event.peer_id)}, 
            is_emergency=False 
        )
        
        # 3. Handle Decision (e.g., execute swap, log, or ignore)
        if "BUY" in decision.upper():
            r.incr("total_snipes")
            print(f"🎯 Sniper Action Triggered: {decision}")
            
    except Exception as e:
        print(f"❌ Sniper Error: {e}")

# --- WEB ROUTES (Flask) ---

@app.route('/')
def dashboard():
    snipes = r.get("total_snipes") or 0
    return render_template('dashboard.html', 
                           snipes=snipes, 
                           app_name=APP_CONFIG['app']['name'])

@app.route('/health')
def health():
    try:
        redis_ok = r.ping()
    except:
        redis_ok = False
    return jsonify({
        "status": "running", 
        "redis_connected": redis_ok,
        "primary_llm": APP_CONFIG['llm']['primary']
    }), 200

# --- CONCURRENCY MANAGEMENT ---

def run_flask():
    """Run Flask in a separate thread"""
    # Use 0.0.0.0 so Docker can map the port
    app.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)

async def main():
    """Run Telethon Client"""
    print(f"🚀 Starting {APP_CONFIG['app']['name']}...")
    await client.start()
    print("✅ Telegram Client Online.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    # 1. Start Flask Thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 2. Start Telegram Loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Shutting down...")
