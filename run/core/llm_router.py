# run/core/llm_router.py
import os
import time
from typing import Dict, Any, Optional

class LLMRouter:
    def __init__(self, config: Dict[str, Any]):
        # Pull the 'llm' block from config.yaml
        self.config = config.get('llm', {})
        
        # Dynamic targeting
        self.primary = self.config.get('primary', 'deepseek')
        self.fallback = self.config.get('fallback', 'kimi')
        
        # Dynamic Circuit Breaker settings
        cb_config = self.config.get('circuit_breaker', {})
        self.max_failures = cb_config.get('max_failures', 3)
        self.lockout_time = cb_config.get('lockout_seconds', 30)
        
        self.circuit = {"failures": 0, "open_until": 0}
        self.providers = {}
        self._init_providers()

    def _init_providers(self):
        if os.getenv("DEEPSEEK_API_KEY"):
            from providers.deepseek_provider import DeepSeekProvider
            self.providers['deepseek'] = DeepSeekProvider()
            
        if os.getenv("KIMI_API_KEY"):
            from providers.kimi_provider import KimiProvider
            self.providers['kimi'] = KimiProvider()

    def get_decision(self, data: str, context: Optional[Dict], is_emergency: bool):
        target = self.primary if is_emergency and self.primary in self.providers else self.primary
        
        # Check Circuit status
        if time.time() < self.circuit["open_until"]:
            target = self.fallback
            
        try:
            prov = self.providers.get(target) or self.providers.get(self.fallback)
            if not prov: raise Exception("No LLM providers online")
            
            response = prov.get_decision(data, context)
            self.circuit["failures"] = 0 
            return response 
        except Exception as e:
            self.circuit["failures"] += 1
            # Use YAML settings here instead of hardcoded '3' and '30'
            if self.circuit["failures"] >= self.max_failures:
                self.circuit["open_until"] = time.time() + self.lockout_time
            raise e
