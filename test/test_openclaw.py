#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test/test_openclaw.py
import sys
import requests
import os

ip = os.getenv('DIGITAL_OCEAN_IP')

def test_health():
    try:
        if not ip:
            print("ERROR: DIGITAL_OCEAN_IP environment variable is not set!")
            return 1

        url = "http://{}:80".format(ip)
        r = requests.get(url, timeout=10)
        print("Status:", r.status_code)
        if r.status_code == 200:
            print("OK: OpenClaw is running")
            return 0
        else:
            print("ERROR: Unexpected status:", r.status_code)
            return 1
    except Exception as e:
        print("ERROR: Connection failed:", e)
        return 1

if __name__ == "__main__":
    sys.exit(test_health())
