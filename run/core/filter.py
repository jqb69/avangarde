# run/core/filter.py

import re
from typing import List

class NewsFilter:
    def __init__(self, config):
        self.allowed_assets = config.get('trading', {}).get('assets', [])
        # Keywords that usually mean the news is actionable
        self.action_keywords = ["BREAKING", "URGENT", "FED", "CPI", "RATE", "HIKE", "PUMP"]

    def is_relevant(self, text: str) -> bool:
        text_upper = text.upper()
        
        # 1. Asset Discrimination
        has_asset = any(asset in text_upper for asset in self.allowed_assets)
        
        # 2. Geopolitical / Market Impact check
        has_impact = any(word in text_upper for word in self.action_keywords)
        
        # 3. Simple regex to find price/percentage (signal of volatility)
        has_numbers = bool(re.search(r'\d+(\.\d+)?%', text)) or "$" in text
        
        return has_asset and (has_impact or has_numbers)
