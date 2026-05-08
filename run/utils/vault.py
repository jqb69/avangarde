# utils/vault.py
import os

class Vault:
    @staticmethod
    def get(key: str) -> str:
        # Map logical names to environment variable names
        mapping = {
            "DEEPSEEK_KEY": "DEEPSEEK_API_KEY",
            "KIMI_KEY": "KIMI_API_KEY",
            "TG_ID": "TG_API_ID",
            "TG_HASH": "TG_API_HASH",
            "TG_SESSION": "TG_SESSION_STR"
        }
        env_var = mapping.get(key.upper())
        val = os.getenv(env_var)
        if not val:
            raise EnvironmentError(f"❌ SECRET MISSING: {key} (Check your .env)")
        return val.strip()
