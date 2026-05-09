# ingestors/telegram_client.py

import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from utils.vault import Vault

logger = logging.getLogger("avangarde.ingestors.telegram")

class TelegramIngestor:
    """
    Connects to Telegram via Telethon, listens for breaking news,
    and instantly pushes it to the Redis processing queue.
    """
    def __init__(self, config, redis_client):
        self.config = config.get('ingestors', {}).get('telegram', {})
        self.redis = redis_client
        
        # Use Vault for secrets - NO hardcoded API keys
        self.api_id = int(Vault.get("TG_ID"))
        self.api_hash = Vault.get("TG_HASH")
        self.session_str = Vault.get("TG_SESSION")
        
        self.client = TelegramClient(
            StringSession(self.session_str), 
            self.api_id, 
            self.api_hash
        )

    async def start(self):
        """Starts the Telegram client and listens for specific channels."""
        target_channels = self.config.get('channels', [])
        
        # If target_channels is empty, it listens to ALL incoming messages.
        # It is highly recommended to specify channel IDs in config.yaml.
        @self.client.on(events.NewMessage(chats=target_channels if target_channels else None))
        async def handler(event):
            try:
                raw_text = event.raw_text
                if raw_text:
                    # Push directly to the Orchestrator's main queue (O(1) operation)
                    self.redis.lpush("breaking_news", raw_text)
                    logger.info(f"📥 [Telegram] Ingested message from {event.chat_id}")
            except Exception as e:
                logger.error(f"❌ [Telegram] Ingestion Error: {e}")

        logger.info("🚀 Starting Telegram Ingestor...")
        await self.client.start()
        logger.info("✅ Telegram Ingestor Online & Listening.")
        await self.client.run_until_disconnected()
