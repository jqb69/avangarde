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
    if not SESSION:
        print("❌ FAIL: TG_SESSION_STR is empty")
        exit(1)
        
    session_str = SESSION.strip() # .strip() removes spaces/newlines

    if not session_str:
        print("❌ FAIL: TG_SESSION_STR is empty")
        exit(1)
    
    # Log the length to debug (The string should be ~350+ chars)
    print(f"DEBUG: Session string length is {len(session_str)}")
    if len(session_str) > 20:
        try:
            # Use the cleaned string
            client = TelegramClient(StringSession(session_str), int(API_ID), API_HASH)
            
            # The 'with' block handles connect and disconnect automatically
            with client:
                if client.is_user_authorized():
                    user = client.get_me()
                    log(f"✅ SESSION VALID: Connected as {user.first_name}")
                    # Create a success flag file for the workflow if needed
                    with open(OUT_FILE, 'w') as f: f.write(session_str)
                    sys.exit(0)
                else:
                    log("⚠️ SESSION EXPIRED: String is valid format but unauthorized.")
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
