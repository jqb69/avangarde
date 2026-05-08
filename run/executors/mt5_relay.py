# run/executors/mt5_relay.py

import requests

class MT5Relay:
    def __init__(self, config):
        mt5_cfg = config.get('mt5', {})
        self.relay_url = mt5_cfg.get('relay_url', "http://localhost:5000/trade")
        self.timeout = mt5_cfg.get('timeout', 2) # Pulls from YAML, defaults to 2

    def fire(self, decision: dict) -> bool:
        try:
            # We pass self.timeout into the request
            response = requests.post(
                self.relay_url, 
                json=decision, 
                timeout=self.timeout 
            )
            return response.status_code == 200
        except requests.exceptions.Timeout:
            print("🛑 EXECUTION TIMEOUT: MT5 Bridge was too slow.")
            return False
        except Exception as e:
            print(f"❌ EXECUTION FAILED: {e}")
            return False
