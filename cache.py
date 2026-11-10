"""Redis cache for answers.

Caching is optional: if REDIS_URL is not set, or Redis is down, the API just calls the
model every time and logs the problem.
"""

import hashlib
import logging
import os

import redis
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

_client: redis.Redis | None = None


def _get_client() -> redis.Redis | None:
    global _client
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    if _client is None:
        _client = redis.Redis.from_url(
            url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
        )
    return _client


def _key(question: str) -> str:
    # Same question in different letter case / spacing shares one cache entry
    normalised = " ".join(question.casefold().split())
    return "ask:" + hashlib.sha256(normalised.encode()).hexdigest()


def get_cached(question: str) -> str | None:
    """Return the cached answer, or None on a miss or if Redis is unavailable."""
    client = _get_client()
    if client is None:
        return None
    try:
        return client.get(_key(question))
    except redis.RedisError as e:
        logger.error("Cache read failed: %s", e)
        return None


def set_cached(question: str, answer: str) -> None:
    """Store an answer for CACHE_TTL_SECONDS. Never raises."""
    client = _get_client()
    if client is None:
        return
    try:
        client.set(_key(question), answer, ex=CACHE_TTL_SECONDS)
    except redis.RedisError as e:
        logger.error("Cache write failed: %s", e)
