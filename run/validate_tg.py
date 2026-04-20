#!/usr/bin/python3
# run/validate_tg.py
import os, sys
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# Config from Envs
API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
SESSION = os.getenv("TG_SESSION_STR")
OUT_FILE = "tg_session_report.txt"

def log(msg):
    with open(OUT_FILE, "a") as f:
        f.write(msg + "\n")
    print(msg)

def run_logic():
    if os.path.exists(OUT_FILE): os.remove(OUT_FILE)
    
    if not API_ID or not API_HASH:
        log("❌ CRITICAL: TG_API_ID or TG_API_HASH missing from secrets.")
        sys.exit(1)

    # STEP 1: VALIDATE EXISTING
    if SESSION and len(SESSION) > 20:
        try:
            client = TelegramClient(StringSession(SESSION), int(API_ID), API_HASH)
            client.connect()
            if client.is_user_authorized():
                log(f"✅ SESSION VALID: Connected as {client.get_me().first_name}")
                sys.exit(0)
            log("⚠️ SESSION EXPIRED: Attempting to generate new one...")
        except Exception as e:
            log(f"⚠️ VALIDATION FAILED: {e}")

    # STEP 2: GENERATE NEW
    log("🚀 GENERATION MODE: Starting fresh session...")
    try:
        # If in GitHub, this will timeout/fail, which we capture.
        # If on your laptop, this will prompt for Phone/SMS.
        client = TelegramClient(StringSession(), int(API_ID), API_HASH)
        
        # start() handles the interactive login
        client.start() 
        
        new_session = client.session.save()
        log("✨ NEW SESSION GENERATED SUCCESSFULLY!")
        log(f"TG_SESSION_STR={new_session}")
        log("⬆️ COPY THE LINE ABOVE TO GITHUB SECRETS.")
        
    except EOFError:
        log("❌ FAIL: Script needs SMS code but terminal is non-interactive (GitHub).")
        log("👉 FIX: Run 'python run/validate_tg.py' on your LOCAL laptop.")
        sys.exit(1)
    except Exception as e:
        log(f"🛑 FATAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_logic()
