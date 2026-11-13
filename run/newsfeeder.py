#!/usr/bin/env python3
"""
newsfeeder.py — callable news fetch for Avangarde.
No main loop. Call fetch_and_push() from claw_robot.
"""
import logging
import os
from typing import List

import feedparser
import redis

logger = logging.getLogger("avangarde.newsfeeder")

RSS_URLS = [
    "https://news.bitcoin.com/feed/",
    "https://crypto.news/feed/",
]
KEYWORDS = ("bitcoin", "btc", "gold","xag", "xau","xbr" ,"fed", "cpi", "etf", "rate", "hike","iran","hormuz","nvidia","chips","tariffs","oil")
MAX_ITEMS = int(os.getenv("NEWS_MAX_ITEMS", "5"))
QUEUE_KEY = os.getenv("NEWS_QUEUE", "breaking_news")


def _is_relevant(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in KEYWORDS)


def fetch_headlines() -> List[str]:
    """Pull recent relevant headlines from free RSS sources."""
    headlines: List[str] = []
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:MAX_ITEMS * 2]:
                title = entry.get("title") or ""
                summary = (entry.get("summary") or entry.get("description") or "")[:300]
                text = f"{title}. {summary}".replace("\n", " ").strip()
                if text and _is_relevant(text):
                    headlines.append(text[:500])
                if len(headlines) >= MAX_ITEMS:
                    return headlines
        except Exception as e:
            logger.warning("rss %s failed: %s", url, e)
    return headlines


def fetch_and_push(redis_client: redis.Redis) -> int:
    """
    Fetch headlines and LPUSH them to the Redis queue.
    Returns number of items pushed.
    Call this from claw_robot.tick() on a timer.
    """
    headlines = fetch_headlines()
    pushed = 0
    for h in headlines:
        try:
            redis_client.lpush(QUEUE_KEY, h)
            pushed += 1
            logger.info("news pushed: %s…", h[:80])
        except Exception as e:
            logger.error("redis push failed: %s", e)
    return pushed
