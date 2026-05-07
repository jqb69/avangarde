import os
import time
import hashlib
import random
import json
import logging
from typing import Dict, Any

# Ensure you use your parser to handle the LLM string output
from utils.parsers import extract_json 

logger = logging.getLogger("openclaw.robot")

class OpenClawRobot:
    MAX_RETRIES = 3
    BASE_DELAY = 2.0
    
    def __init__(self, config: Dict[str, Any], redis_client):
        self.config = config
        self.redis = redis_client
        # Register script once
        self.lua_tick = self.redis.register_script(LUA_TICK_SCRIPT)
        
        self.Q_MAIN = "breaking_news"
        self.Q_PROC = "processing_buffer" 
        self.Q_RETRY = "retry_schedule"   
        self.Q_RDATA = "retry_data"       
        self.Q_DLQ = "dead_letter_queue"
        
        from core.llm_router import LLMRouter
        self.brain = LLMRouter(config)
        
        # Immediate recovery on startup
        self._recover_stale_processing()

    def tick(self, is_emergency: bool = False):
        # 1. Atomic Pop via Lua (Now batch-limited)
        event = self.lua_tick(keys=[self.Q_RETRY, self.Q_RDATA, self.Q_MAIN], args=[time.time()])
        if not event: 
            return

        # 2. Unique Tracking ID (Full MD5 for safety)
        eid = hashlib.md5(f"{event}{time.time()}".encode()).hexdigest()
        self.redis.hset(self.Q_PROC, eid, event)

        try:
            # 3. Decision Logic
            raw_res = self.brain.get_decision(event, None, is_emergency)
            
            # Robust parsing (don't trust the LLM to return perfect JSON)
            res = extract_json(raw_res) if isinstance(raw_res, str) else raw_res
            
            if res and res.get('decision') not in ["HOLD", None]:
                if res.get('confidence', 0) >= 0.6:
                    # Log the trade to Redis for the Dashboard to see
                    trade_log = json.dumps({
                        "t": time.time(),
                        "d": res['decision'],
                        "c": res['confidence']
                    })
                    self.redis.lpush("trade_history", trade_log)
                    self.redis.ltrim("trade_history", 0, 99) # Keep last 100

            # 4. Success Cleanup
            pipe = self.redis.pipeline()
            pipe.hdel(self.Q_PROC, eid)
            pipe.hdel("retry_counts", eid)
            pipe.execute()

        except Exception as e:
            logger.error(f"🔥 Critical Failure for {eid}: {e}")
            self._handle_failure(eid, event)
