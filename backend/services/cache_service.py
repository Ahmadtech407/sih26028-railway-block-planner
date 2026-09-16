"""
Unified High-Performance Cache Service (In-Memory + Optional Redis)
==================================================================
Provides fast, thread-safe, TTL-backed caching for real-time railway telemetry,
dynamic ETA calculations, weather observations, and disruption state.
"""

import os
import time
import json
import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default TTL durations (seconds)
TTL_TRAIN_POSITIONS = 10
TTL_TRAIN_ETA = 15
TTL_DISRUPTIONS = 60
TTL_WEATHER = 300


class CacheService:
    """Thread-safe In-Memory TTL Cache with optional Redis backend fallback."""

    def __init__(self):
        self._lock = threading.RLock()
        self._store: Dict[str, Dict[str, Any]] = {}
        self._redis_client = None
        self._init_redis()

    def _init_redis(self):
        redis_url = os.getenv("REDIS_URL", "").strip()
        if redis_url:
            try:
                import redis
                self._redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
                self._redis_client.ping()
                logger.info("Connected to external Redis cache at %s", redis_url)
            except Exception as exc:
                logger.warning("Redis connection failed (%s); operating in local memory cache mode.", exc)
                self._redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value if not expired."""
        if self._redis_client:
            try:
                val = self._redis_client.get(key)
                if val is not None:
                    return json.loads(val)
            except Exception as exc:
                logger.debug("Redis get error for %s: %s", key, exc)

        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            if time.time() > entry["expires_at"]:
                del self._store[key]
                return None
            return entry["value"]

    def set(self, key: str, value: Any, ttl_seconds: int = 60) -> bool:
        """Store a value with an expiration TTL."""
        if self._redis_client:
            try:
                self._redis_client.setex(key, ttl_seconds, json.dumps(value, default=str))
            except Exception as exc:
                logger.debug("Redis set error for %s: %s", key, exc)

        with self._lock:
            self._store[key] = {
                "value": value,
                "expires_at": time.time() + ttl_seconds,
                "created_at": time.time(),
                "ttl": ttl_seconds,
            }
            return True

    def delete(self, key: str) -> bool:
        """Remove a key from cache."""
        if self._redis_client:
            try:
                self._redis_client.delete(key)
            except Exception:
                pass
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> None:
        """Purge all cached entries."""
        if self._redis_client:
            try:
                self._redis_client.flushdb()
            except Exception:
                pass
        with self._lock:
            self._store.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Return cache health and size statistics."""
        with self._lock:
            now = time.time()
            valid_keys = sum(1 for e in self._store.values() if e["expires_at"] > now)
            return {
                "backend": "Redis" if self._redis_client else "In-Memory TTL",
                "active_entries": valid_keys,
                "total_stored": len(self._store),
                "status": "OPERATIONAL",
            }


# Global singleton cache instance
cache = CacheService()


def get(key: str) -> Optional[Any]:
    return cache.get(key)


def set(key: str, value: Any, ttl_seconds: int = 60) -> bool:
    return cache.set(key, value, ttl_seconds)


def delete(key: str) -> bool:
    return cache.delete(key)


def clear() -> None:
    cache.clear()


def get_stats() -> Dict[str, Any]:
    return cache.get_stats()
