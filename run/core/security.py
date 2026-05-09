# core/security.py

import logging
import hashlib
import hmac
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class SecurityManager:
    """
    Handles payload integrity, audit logging, and sensitive data masking.
    Ensures that signals arriving from Telegram/Redis haven't been tampered with.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.secret_key = os.getenv("INTERNAL_AUTH_SECRET", "default_hft_secret").encode()
        self.audit_log_path = "logs/audit.log"
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        self._setup_audit_logger()

    def _setup_audit_logger(self):
        """Sets up an immutable-style file logger for all financial decisions."""
        self.logger = logging.getLogger("avangarde.security")
        if not self.logger.handlers:
            handler = logging.FileHandler(self.audit_log_path)
            formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def sign_payload(self, data: str) -> str:
        """Generates an HMAC-SHA256 signature for a data string."""
        return hmac.new(self.secret_key, data.encode(), hashlib.sha256).hexdigest()

    def verify_payload(self, data: str, signature: str) -> bool:
        """Verifies that the data matches the provided signature."""
        expected = self.sign_payload(data)
        return hmac.compare_digest(expected, signature)

    def log_decision(self, eid: str, raw_event: str, decision: Dict[str, Any]):
        """
        Permanent audit trail of why a trade was (or wasn't) taken.
        This is critical for debugging why the LLM lost money.
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_id": eid,
            "asset": decision.get("pair", "UNKNOWN"),
            "action": decision.get("decision", "HOLD"),
            "confidence": decision.get("confidence", 0.0),
            "reasoning": decision.get("reasoning", "N/A"),
            "raw_event_hash": hashlib.sha256(raw_event.encode()).hexdigest()
        }
        
        # Log to file
        self.logger.info(f"DECISION_AUDIT: {json.dumps(audit_entry)}")
        
        # If it's a high-confidence trade, mark it clearly
        if audit_entry["confidence"] > 0.9 and audit_entry["action"] != "HOLD":
            self.logger.warning(f"HIGH_CONFIDENCE_EXECUTION: {eid} | {audit_entry['asset']}")

    def mask_sensitive(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Masks API keys or account numbers for UI/Log display."""
        masked = data.copy()
        sensitive_keys = ['api_key', 'secret', 'password', 'token', 'account']
        for k, v in masked.items():
            if any(s in k.lower() for s in sensitive_keys) and isinstance(v, str):
                masked[k] = f"{v[:4]}****{v[-4:]}" if len(v) > 8 else "****"
        return masked

    def check_rate_limit(self, redis_client, user_id: str, limit: int = 5, window: int = 60) -> bool:
        """
        Prevent 'LLM Hallucination loops' from spamming orders.
        Default: Max 5 orders per 60 seconds per user/asset.
        """
        key = f"rate_limit:{user_id}"
        current = redis_client.get(key)
        
        if current and int(current) >= limit:
            self.logger.error(f"RATE_LIMIT_EXCEEDED: {user_id}")
            return False
            
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        pipe.execute()
        return True
