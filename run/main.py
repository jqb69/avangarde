#!/usr/bin/env python3
# main.py

import asyncio
import threading
import time
from flask import Flask, jsonify, render_template
from redis import Redis
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Your custom logic imports
from utils.config_loader import APP_CONFIG
from utils.vault import Vault
from claw_robot import OpenClawRobot

# 1. Initialization & Config
REDIS_HOST = Vault.get("REDIS_HOST") if hasattr(Vault, 'get') else "localhost" # Fallback if Vault isn't fully configured for host yet
TG_API_ID = int(Vault.get("TG_ID"))
TG_API_HASH = Vault.get("TG_HASH")
TG_SESSION_STR = Vault.get("TG_SESSION")

# Persistent Connections
r = Redis(host=REDIS_HOST, port=6379, decode_responses=True)

# Initialize the Brain/Orchestrator
robot = OpenClawRobot(APP_CONFIG, r)

# Initialize Telegram
client = TelegramClient(StringSession(TG_SESSION_STR), TG_API_ID, TG_API_HASH)

app = Flask(__name__, 
            template_folder='web/templates', 
            static_folder='web/static')

# --- TELEGRAM INGESTOR LOGIC ---

@client.on(events.NewMessage)
async def handle_new_message(event):
    """Core Ingestion: Dump to Redis instantly. DO NOT process here."""
    try:
        raw_text = event.raw_text
        # Push to the queue that the Lua script in claw_robot is watching
        r.lpush("breaking_news", raw_text)
        print(f"📥 Ingested new message to queue.")
    except Exception as e:
        print(f"❌ Ingestion Error: {e}")

# --- WEB ROUTES (Flask) ---

@app.route('/')
def dashboard():
    snipes = r.get("total_trades") or 0
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
        "primary_llm": APP_CONFIG['llm']['primary'],
        "queue_depth": r.llen("breaking_news") # Add queue monitoring
    }), 200

# --- CONCURRENCY MANAGEMENT ---

def run_flask():
    """Run Flask in a separate thread"""
    app.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)

def run_robot():
    """Run the Orchestrator tick loop continuously"""
    print("🤖 Claw Robot Core Online.")
    while True:
        try:
            robot.tick()
        except Exception as e:
            print(f"⚠️ Robot Loop Error: {e}")
        # Tiny sleep to prevent 100% CPU lockup when idle
        time.sleep(0.01)

async def main():
    """Run Telethon Client"""
    print(f"🚀 Starting {APP_CONFIG['app']['name']} Ingestor...")
    await client.start()
    print("✅ Telegram Client Online & Listening.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    # 1. Start Flask Thread (Dashboard & Health)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 2. Start Robot Thread (Filter -> LLM -> Risk -> Execute)
    robot_thread = threading.Thread(target=run_robot, daemon=True)
    robot_thread.start()

    # 3. Start Telegram Loop (Main Thread)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Shutting down...")
