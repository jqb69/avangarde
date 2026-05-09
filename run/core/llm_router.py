# run/core/llm_router.py
import time
from typing import Dict, Any, Optional
from providers.deepseek_provider import DeepSeekProvider
from providers.kimi_provider import KimiProvider

class LLMRouter:
    def __init__(self, config: Dict[str, Any]):
        # Pull the 'llm' block from config.yaml
        self.llm_cfg = config.get('llm', {})
        
        self.primary_name = self.llm_cfg.get('primary', 'deepseek')
        self.fallback_name = self.llm_cfg.get('fallback', 'kimi')
        
        cb_config = self.llm_cfg.get('circuit_breaker', {})
        self.max_failures = cb_config.get('max_failures', 3)
        self.lockout_time = cb_config.get('lockout_seconds', 30)
        
        self.circuit = {"failures": 0, "open_until": 0}
        
        # Initialize providers once with their specific configs
        self.providers = {
            'deepseek': DeepSeekProvider(self.llm_cfg.get('deepseek', {})),
            'kimi': KimiProvider(self.llm_cfg.get('kimi', {}))
        }

    def get_decision(self, data: str, context: Optional[Dict] = None, is_emergency: bool = False) -> str:
        """
        Routes the request to the appropriate LLM provider with failover logic.
        """
        # 1. Determine Target (Check Circuit Breaker)
        target = self.primary_name
        if time.time() < self.circuit["open_until"]:
            target = self.fallback_name

        # 2. Execution with Failover
        try:
            return self._execute_with_provider(target, data, context)
        except Exception:
            # If primary failed, try fallback immediately
            if target != self.fallback_name:
                return self._execute_with_provider(self.fallback_name, data, context)
            raise

    def _execute_with_provider(self, provider_name: str, data: str, context: Optional[Dict]) -> str:
        provider = self.providers.get(provider_name)
        if not provider:
            raise RuntimeError(f"Provider {provider_name} not initialized")

        try:
            result = provider.get_decision(data, context)
            # Success: Reset circuit
            self.circuit["failures"] = 0
            return result
        except Exception as e:
            # Failure: Trip circuit
            self.circuit["failures"] += 1
            if self.circuit["failures"] >= self.max_failures:
                self.circuit["open_until"] = time.time() + self.lockout_time
            raise e
