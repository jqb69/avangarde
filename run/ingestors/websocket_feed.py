# ingestors/websocket_feed.py

import asyncio
import logging
import aiohttp
from utils.vault import Vault

logger = logging.getLogger("avangarde.ingestors.websocket")

class WebsocketIngestor:
    """
    Connects to a real-time financial websocket (e.g., Binance, Alpaca, Polygon).
    Formats raw ticks into strings and pushes them to the Redis processing queue.
    """
    def __init__(self, config, redis_client):
        self.config = config.get('ingestors', {}).get('websocket', {})
        self.redis = redis_client
        
        # Defaulting to Binance BTC/USDT trade stream as a fallback example
        self.ws_url = self.config.get('url', "wss://stream.binance.com:9443/ws/btcusdt@trade")
        self.reconnect_delay = float(self.config.get('reconnect_delay', 5.0))
        
        # If your WS requires an API key (like Polygon.io), pull it from Vault
        # self.api_key = Vault.get("WS_API_KEY") 

    async def start(self):
        """Connects to the websocket and streams data continuously."""
        logger.info(f"🚀 Starting Websocket Ingestor for {self.ws_url}...")
        
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(self.ws_url) as ws:
                        logger.info("✅ Websocket Connected.")
                        
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = msg.data
                                
                                # Format it so the LLM understands context
                                event_payload = f"MARKET_TICK: {data}"
                                
                                # Push to Orchestrator's main queue
                                self.redis.lpush("breaking_news", event_payload)
                                
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                logger.warning("⚠️ Websocket connection closed by server.")
                                break
                                
            except Exception as e:
                logger.error(f"❌ [Websocket] Connection Error: {e}")
            
            logger.warning(f"🔄 Reconnecting to Websocket in {self.reconnect_delay}s...")
            await asyncio.sleep(self.reconnect_delay)
