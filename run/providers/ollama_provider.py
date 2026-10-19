# run/providers/ollama_provider.py
import json
import logging
from typing import Any, Dict, Optional
import requests

from providers.base import BaseLLMProvider

logger = logging.getLogger("avangarde.providers.ollama")


class OllamaProvider(BaseLLMProvider):
    def __init__(self, config: Dict[str, Any]):
        base_url = str(
            config.get("base_url") or "http://127.0.0.1:11434"
        ).rstrip("/")

        self.chat_url = (
            f"{base_url}/chat/completions"
            if base_url.endswith("/v1")
            else f"{base_url}/v1/chat/completions"
        )
        self.model = config.get("model", "qwen2.5:7b")
        self.timeout = float(config.get("timeout", 60.0))

    def get_decision(
        self, data: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        system_prompt = (
            "You are an HFT trading analysis engine. Analyze the event for "
            "market impact. Return only a JSON object with these fields: "
            '"decision" (BUY, SELL, or HOLD), "pair", '
            '"confidence" (number from 0 to 1), and "reasoning".'
        )

        messages = [{"role": "system", "content": system_prompt}]
        if context:
            messages.append({
                "role": "system",
                "content": f"Market Context: {json.dumps(context)}",
            })
        messages.append({
            "role": "user",
            "content": f"Process this event: {data}",
        })

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "stream": False,
        }

        try:
            response = requests.post(
                self.chat_url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            logger.error("Ollama request failed: %s", exc)
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        except ValueError as exc:
            logger.error("Ollama returned invalid JSON: %s", exc)
            raise ValueError("Ollama returned invalid JSON") from exc

        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("Ollama response has no choices")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Ollama response has empty message content")

        return content.strip()
