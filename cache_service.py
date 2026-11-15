"""
cache_service.py — Sentix Intelligence Platform
------------------------------------------------
Redis-backed TTL cache with namespace support and in-memory fallback.

Why Redis over in-memory:
  - Shared across Gunicorn workers (no cache fragmentation)
  - Survives server restarts (persistence optional via Redis config)
  - Native TTL support — Redis evicts expired keys automatically
  - No memory growth crashes — Redis has maxmemory + eviction policies

Fallback:
  If Redis is unavailable (e.g., local dev without Redis), falls back
  to the original thread-safe in-memory cache automatically.
  Set REDIS_URL env var to enable Redis.

Usage:
  from cache_service import cache
  cache.set("sector_articles", data, ttl=600, namespace="news")
  data = cache.get("sector_articles", namespace="news")
  cache.flush_namespace("news")
"""

import os
import json
import time
import threading
import logging
import pickle
from typing import Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("sentix.cache")


# ---------------------------------------------------------------------------
# Serialization helpers
# pickle handles complex Python objects (nested dicts, lists, dataclasses)
# ---------------------------------------------------------------------------

def _serialize(value: Any) -> bytes:
    return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)


def _deserialize(data: bytes) -> Any:
    return pickle.loads(data)


# ---------------------------------------------------------------------------
# Redis backend
# ---------------------------------------------------------------------------

class _RedisBackend:
    """
    Thin Redis wrapper using redis-py.
    All keys are prefixed with 'sentix:' to avoid collisions with other apps.
    """

    _PREFIX = "sentix"

    def __init__(self, redis_url: str):
        import redis
        self._client = redis.from_url(
            redis_url,
            decode_responses=False,   # We handle binary (pickle)
            socket_connect_timeout=3,
            socket_timeout=3,
            retry_on_timeout=True,
        )
        # Verify connection
        self._client.ping()
        logger.info(f"✅ Redis connected: {redis_url.split('@')[-1]}")  # Hide credentials

    def _key(self, namespace: str, key: str) -> str:
        return f"{self._PREFIX}:{namespace}:{key}"

    def get(self, key: str, namespace: str) -> Optional[Any]:
        try:
            raw = self._client.get(self._key(namespace, key))
            if raw is None:
                return None
            return _deserialize(raw)
        except Exception as exc:
            logger.warning(f"Redis GET error: {exc}")
            return None

    def set(self, key: str, value: Any, ttl: int, namespace: str) -> None:
        try:
            raw = _serialize(value)
            self._client.setex(self._key(namespace, key), ttl, raw)
        except Exception as exc:
            logger.warning(f"Redis SET error: {exc}")

    def invalidate(self, key: str, namespace: str) -> None:
        try:
            self._client.delete(self._key(namespace, key))
        except Exception as exc:
            logger.warning(f"Redis DELETE error: {exc}")

    def flush_namespace(self, namespace: str) -> int:
        """Delete all keys matching sentix:<namespace>:*"""
        try:
            pattern = f"{self._PREFIX}:{namespace}:*"
            keys = list(self._client.scan_iter(pattern, count=500))
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as exc:
            logger.warning(f"Redis FLUSH_NAMESPACE error: {exc}")
            return 0

    def is_fresh(self, key: str, namespace: str) -> bool:
        try:
            return self._client.exists(self._key(namespace, key)) > 0
        except Exception:
            return False

    def get_stats(self) -> dict:
        try:
            info = self._client.info("stats")
            memory = self._client.info("memory")
            keyspace = self._client.info("keyspace")

            # Count only sentix: keys
            sentix_keys = 0
            for db_info in keyspace.values():
                sentix_keys += db_info.get("keys", 0)

            return {
                "backend":          "redis",
                "hits":             info.get("keyspace_hits", 0),
                "misses":           info.get("keyspace_misses", 0),
                "active_keys":      sentix_keys,
                "used_memory_mb":   round(memory.get("used_memory", 0) / 1024 / 1024, 2),
                "evicted_keys":     info.get("evicted_keys", 0),
            }
        except Exception as exc:
            return {"backend": "redis", "error": str(exc)}

    def purge_expired(self) -> int:
        # Redis handles expiry natively — nothing to do here
        return 0


# ---------------------------------------------------------------------------
# In-memory fallback backend (original implementation)
# ---------------------------------------------------------------------------

@dataclass
class _MemEntry:
    value: Any
    expires_at: float
    hits: int = 0


class _MemoryBackend:
    """Thread-safe TTL dict. Used when Redis is unavailable."""

    def __init__(self):
        self._store: dict[str, _MemEntry] = {}
        self._lock = threading.RLock()
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "evictions": 0}
        logger.warning(
            "⚠️  Cache running in IN-MEMORY mode. "
            "Set REDIS_URL env var for production Redis cache."
        )

    def _fk(self, namespace: str, key: str) -> str:
        return f"{namespace}:{key}"

    def get(self, key: str, namespace: str) -> Optional[Any]:
        fk = self._fk(namespace, key)
        with self._lock:
            entry = self._store.get(fk)
            if entry is None:
                self._stats["misses"] += 1
                return None
            if time.time() > entry.expires_at:
                del self._store[fk]
                self._stats["evictions"] += 1
                self._stats["misses"] += 1
                return None
            entry.hits += 1
            self._stats["hits"] += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: int, namespace: str) -> None:
        fk = self._fk(namespace, key)
        with self._lock:
            self._store[fk] = _MemEntry(value=value, expires_at=time.time() + ttl)
            self._stats["sets"] += 1

    def invalidate(self, key: str, namespace: str) -> None:
        with self._lock:
            self._store.pop(self._fk(namespace, key), None)

    def flush_namespace(self, namespace: str) -> int:
        prefix = f"{namespace}:"
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]
            return len(keys)

    def is_fresh(self, key: str, namespace: str) -> bool:
        fk = self._fk(namespace, key)
        with self._lock:
            entry = self._store.get(fk)
            return entry is not None and time.time() <= entry.expires_at

    def get_stats(self) -> dict:
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0
            return {
                "backend":        "memory",
                **self._stats,
                "total_requests": total,
                "hit_rate_pct":   round(hit_rate, 2),
                "active_keys":    len(self._store),
            }

    def purge_expired(self) -> int:
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._store.items() if now > v.expires_at]
            for k in expired:
                del self._store[k]
                self._stats["evictions"] += 1
            return len(expired)


# ---------------------------------------------------------------------------
# CacheService — public API, selects backend automatically
# ---------------------------------------------------------------------------

class CacheService:
    """
    Unified cache interface.
    Automatically uses Redis if REDIS_URL is set, else falls back to memory.

    Environment variables:
      REDIS_URL  — Redis connection string, e.g. redis://localhost:6379/0
                   or redis://:password@host:6379/0
    """

    def __init__(self):
        self._backend = self._init_backend()

    def _init_backend(self):
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                return _RedisBackend(redis_url)
            except Exception as exc:
                logger.error(
                    f"Redis connection failed: {exc}. "
                    f"Falling back to in-memory cache."
                )
        return _MemoryBackend()

    @property
    def is_redis(self) -> bool:
        return isinstance(self._backend, _RedisBackend)

    # ------------------------------------------------------------------
    # Public API — identical to original CacheService
    # ------------------------------------------------------------------

    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        value = self._backend.get(key, namespace)
        if value is not None:
            logger.debug(f"Cache HIT: {namespace}:{key}")
        else:
            logger.debug(f"Cache MISS: {namespace}:{key}")
        return value

    def set(self, key: str, value: Any, ttl: int = 600, namespace: str = "default") -> None:
        """
        Store value with explicit TTL (seconds).
        Default TTL = 600s (10 min) — matches news refresh cycle.
        Redis natively expires the key after TTL — no memory growth risk.
        """
        self._backend.set(key, value, ttl, namespace)
        logger.debug(f"Cache SET: {namespace}:{key} (TTL={ttl}s)")

    def invalidate(self, key: str, namespace: str = "default") -> None:
        self._backend.invalidate(key, namespace)
        logger.info(f"Cache INVALIDATED: {namespace}:{key}")

    def flush_namespace(self, namespace: str) -> int:
        """Remove all keys in a namespace. Returns count removed."""
        removed = self._backend.flush_namespace(namespace)
        logger.info(f"Cache FLUSH namespace='{namespace}' ({removed} keys removed)")
        return removed

    def is_fresh(self, key: str, namespace: str = "default") -> bool:
        return self._backend.is_fresh(key, namespace)

    def get_stats(self) -> dict:
        return self._backend.get_stats()

    def purge_expired(self) -> int:
        """
        For Redis: no-op (Redis handles expiry natively).
        For memory fallback: sweeps expired entries.
        """
        return self._backend.purge_expired()


# ---------------------------------------------------------------------------
# Singleton instance — import this across all services
# ---------------------------------------------------------------------------
cache = CacheService()
