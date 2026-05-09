# run/providers/deepseek_provider.py

from openai import OpenAI
from typing import Dict, Optional
from providers.base import BaseLLMProvider
from utils.vault import Vault

class DeepSeekProvider(BaseLLMProvider):
    def __init__(self, config: Dict):
        self.config = config
        # Pulling from Vault instead of raw os.getenv
        api_key = Vault.get("DEEPSEEK_KEY")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        # deepseek-reasoner is better for logic, deepseek-chat is faster
        self.model = config.get("model", "deepseek-chat")

    def get_decision(self, data: str, context: Optional[Dict] = None) -> str:
        system_prompt = (
            "You are an HFT Trading Engine. Analyze news for market impact. "
            "Return ONLY a JSON object with: 'decision' (BUY/SELL/HOLD), "
            "'pair', 'confidence' (0.0-1.0), and 'reasoning'."
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        
        if context:
            messages.append({"role": "system", "content": f"Market Context: {context}"})
            
        messages.append({"role": "user", "content": f"Process this event: {data}"})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
                timeout=15.0 # Don't let the bot hang
            )
            return response.choices[0].message.content
        except Exception as e:
            # Re-raise to be handled by the Robot's retry logic
            raise RuntimeError(f"DeepSeek Provider Error: {e}")
