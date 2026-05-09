# providers/kimi_provider.py

from openai import OpenAI
from typing import Dict, Optional
from providers.base import BaseLLMProvider
from utils.vault import Vault

class KimiProvider(BaseLLMProvider):
    
    
    def __init__(self, config: Dict):
        self.config = config
        api_key = Vault.get("KIMI_KEY")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1"
        )
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

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Kimi Provider Error: {e}")
