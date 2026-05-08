import logging
import time
import hashlib
import json
from typing import Dict, Any

from core.filter import NewsFilter
from core.llm_router import LLMRouter
from core.risk_manager import RiskManager
from executors.mt5_relay import MT5Relay
from utils.parsers import extract_json

logger = logging.getLogger("openclaw.robot")

class OpenClawRobot:
    def __init__(self, config: Dict[str, Any], redis_client):
        self.config = config
        self.redis = redis_client
        
        # 1. Pipeline Components
        self.filter = NewsFilter(config)
        self.brain = LLMRouter(config)
        self.risk = RiskManager(config.get('trading', {}).get('risk', {}))
        self.executor = MT5Relay(config)

        # 2. Redis Keys
        self.Q_MAIN = "breaking_news"
        self.Q_PROC = "processing_buffer" 
        self.Q_RETRY = "retry_schedule"   
        self.Q_RDATA = "retry_data"       
        self.Q_DLQ = "dead_letter_queue"
        
        # 3. Setup Logic (Hiding the ugly stuff)
        self._init_lua_scripts()

    def _init_lua_scripts(self):
        """Define and register the Fresh-First priority logic."""
        lua_script = """
        local retry_key, retry_data_key, main_key = KEYS[1], KEYS[2], KEYS[3]
        local now = ARGV[1]

        -- 1. HOT PATH: Fresh news is king (O(1))
        local fresh_data = redis.call('RPOP', main_key)
        if fresh_data then return fresh_data end

        -- 2. IDLE PATH: Only check retries if the main queue is dry
        local due = redis.call('ZRANGEBYSCORE', retry_key, 0, now, 'LIMIT', 0, 1)
        if #due > 0 then
            local eid = due[1]
            local data = redis.call('HGET', retry_data_key, eid)
            redis.call('ZREM', retry_key, eid)
            redis.call('HDEL', retry_data_key, eid)
            return data
        end
        return nil
        """
        self.lua_tick = self.redis.register_script(lua_script)

    def tick(self, is_emergency: bool = False):
        """Executes one processing cycle."""
        # Clean call using the registered script
        event = self.lua_tick(
            keys=[self.Q_RETRY, self.Q_RDATA, self.Q_MAIN], 
            args=[time.time()]
        )
        
        if not event:
            return

        eid = hashlib.md5(f"{event}{time.time()}".encode()).hexdigest()
        self.redis.hset(self.Q_PROC, eid, event)

        try:
            self._execute_pipeline(eid, event, is_emergency)
            # Atomic Cleanup
            pipe = self.redis.pipeline()
            pipe.hdel(self.Q_PROC, eid)
            pipe.hdel("retry_counts", eid)
            pipe.execute()
        except Exception as e:
            logger.error(f"🔥 Pipeline Error {eid}: {e}")
            self._handle_failure(eid, event)

    def _execute_pipeline(self, eid, raw_data, is_emergency):
        """Filter -> Brain -> Risk -> Execute"""
        if not self.filter.is_relevant(raw_data):
            return

        raw_res = self.brain.get_decision(raw_data, context=None, is_emergency=is_emergency)
        res = extract_json(raw_res) if isinstance(raw_res, str) else raw_res

        if res and res.get('decision') not in ["HOLD", None]:
            current_lots = float(self.redis.get("active_exposure") or 0)
            if self.risk.validate_trade(res, current_lots):
                if self.executor.fire(res):
                    self._log_trade(res)

    def _log_trade(self, res):
        """Minimalist logging to Redis for the UI."""
        self.redis.incr("total_trades")
        self.redis.lpush("trade_history", json.dumps({
            "t": time.time(), "d": res['decision'], "p": res['pair'], "c": res['confidence']
        }))
        self.redis.ltrim("trade_history", 0, 99)

    def _handle_failure(self, eid, event):
        """Exponential backoff for retries."""
        count = int(self.redis.hget("retry_counts", eid) or 0) + 1
        if count > 3: # MAX_RETRIES
            self.redis.lpush(self.Q_DLQ, event)
        else:
            delay = (2 ** count) * 2.0 # BASE_DELAY
            pipe = self.redis.pipeline()
            pipe.zadd(self.Q_RETRY, {eid: time.time() + delay})
            pipe.hset(self.Q_RDATA, eid, event)
            pipe.hset("retry_counts", eid, count)
            pipe.execute()
        self.redis.hdel(self.Q_PROC, eid)
