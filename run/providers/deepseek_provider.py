# run/providers/deepseek_provider.py

import requests
import json
import logging
from typing import Dict, Optional
from providers.base import BaseLLMProvider
from utils.vault import Vault

logger = logging.getLogger("avangarde.providers.deepseek")

class DeepSeekProvider(BaseLLMProvider):
   
    def __init__(self, config: Dict):
        self.config = config
        # Pulling from Vault - no hardcoded environment vars
        self.api_key = Vault.get("DEEPSEEK_KEY")
        self.base_url = "https://api.deepseek.com/chat/completions"
        
        # 'deepseek-reasoner' for logic, 'deepseek-chat' for speed
        self.model = config.get("model", "deepseek-chat")
        self.timeout = float(config.get("timeout", 15.0))

    def get_decision(self, data: str, context: Optional[Dict] = None) -> str:
        """
        Executes a decision request via raw POST to DeepSeek API.
        """
        system_prompt = (
            "You are an HFT Trading Engine. Analyze news for market impact. "
            "Return ONLY a JSON object with: 'decision' (BUY/SELL/HOLD), "
            "'pair', 'confidence' (0.0-1.0), and 'reasoning'."
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        
        if context:
            messages.append({"role": "system", "content": f"Market Context: {json.dumps(context)}"})
            
        messages.append({"role": "user", "content": f"Process this event: {data}"})

        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 1000
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=self.timeout
            )
            
            # Handle rate limits or server errors before parsing
            if response.status_code == 429:
                raise RuntimeError("DeepSeek Rate Limit Hit")
                
            if response.status_code != 200:
                raise RuntimeError(f"DeepSeek API Error {response.status_code}: {response.text}")
                
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            if not content:
                raise ValueError("Empty response from DeepSeek API")
                
            return content
            
        except requests.exceptions.Timeout:
            logger.error("⏱️ DeepSeek request timed out.")
            raise
        except Exception as e:
            logger.error(f"❌ DeepSeek Provider critical failure: {e}")
            raise RuntimeError(f"DeepSeek Provider Error: {e}")
