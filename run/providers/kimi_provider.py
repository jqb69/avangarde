# providers/kimi_provider.py

import requests
import json
from typing import Dict, Optional
from providers.base import BaseLLMProvider
from utils.vault import Vault

class KimiProvider(BaseLLMProvider):
   
    def __init__(self, config: Dict):
        self.config = config
        self.api_key = Vault.get("KIMI_KEY")
        self.base_url = "https://api.moonshot.cn/v1/chat/completions"
        # Typical models: moonshot-v1-8k, moonshot-v1-32k
        self.model = config.get("model", "moonshot-v1-8k")

    def get_decision(self, data: str, context: Optional[Dict] = None) -> str:
        system_prompt = (
            "Act as a Quant Trader. Analyze market news for trading signals. "
            "Output must be a valid JSON object containing: "
            "'decision' (BUY/SELL/HOLD), 'pair', 'confidence', and 'reasoning'."
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        
        if context:
            messages.append({"role": "system", "content": f"Market Context: {context}"})
            
        messages.append({"role": "user", "content": f"Analyze this data: {data}"})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            # Using requests instead of openai package
            response = requests.post(
                self.base_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=15.0
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Kimi API Error: {response.status_code} - {response.text}")
                
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            raise RuntimeError(f"Kimi Provider Error: {e}")
