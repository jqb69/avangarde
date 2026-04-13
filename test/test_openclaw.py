#!/usr/bin/env python3
# test/test_openclaw.py
import sys
import requests
import os

IP = os.getenv("DIGITAL_OCEAN_IP", "localhost")
URL = f"http://{IP}:80"

def test_health():
    try:
        r = requests.get(URL, timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print("✓ OpenClaw is running")
            return 0
        else:
            print(f"✗ Unexpected status: {r.status_code}")
            return 1
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(test_health())

