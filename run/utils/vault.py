# utils/vault.py
import os

class Vault:
    @staticmethod
    def get_api_key(provider_name: str) -> str:
        key_map = {
            "deepseek": "DEEPSEEK_API_KEY",
            "kimi": "KIMI_API_KEY",
            "telegram": "TG_API_ID"
        }
        env_var = key_map.get(provider_name.lower())
        val = os.getenv(env_var)
        if not val:
            raise EnvironmentError(f"❌ Missing Secret: {env_var}")
        return val.strip()
