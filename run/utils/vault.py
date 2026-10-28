# utils/vault.py
import os


class Vault:
    # logical name → env var name
    _MAP = {
        "DEEPSEEK_KEY": "DEEPSEEK_API_KEY",
        "KIMI_KEY": "KIMI_API_KEY",
        "TG_ID": "TG_API_ID",
        "TG_HASH": "TG_API_HASH",
        "TG_SESSION": "TG_SESSION_STR",
        "REDIS_HOST": "REDIS_HOST",
        "REDIS_URL": "REDIS_URL",
    }

    @staticmethod
    def get(key: str, default=None):
        """
        Resolve secret/config from env.
        Unknown keys fall back to using `key` as the env name.
        If default is None and value is missing → EnvironmentError (strict).
        If default is provided → return default when missing.
        """
        if not key or not isinstance(key, str):
            if default is not None:
                return default
            raise EnvironmentError("❌ SECRET MISSING: empty key")

        env_var = Vault._MAP.get(key.upper(), key)
        if not isinstance(env_var, str) or not env_var:
            if default is not None:
                return default
            raise EnvironmentError(f"❌ SECRET MISSING: {key}")

        val = os.getenv(env_var)
        if val is None or val.strip() == "":
            if default is not None:
                return default
            raise EnvironmentError(
                f"❌ SECRET MISSING: {key} (env {env_var})"
            )
        return val.strip()
