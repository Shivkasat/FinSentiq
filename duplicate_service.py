"""
duplicate_service.py — Sentix Intelligence Platform
-----------------------------------------------------
Redis-backed, sliding-window deduplication engine for financial news streams.

Why Redis for dedup:
  - Shared across all Gunicorn workers — no duplicate processing across workers
  - Redis SETNX + EXPIRE = atomic check-and-set, race-condition safe
  - Redis SET maxmemory policy handles bounding automatically
  - Native TTL per key means no manual eviction sweep needed

Fallback:
  If Redis is unavailable, falls back to in-memory OrderedDict (original behavior).

Redis key schema:
  sentix:dedup:<hash>  →  "1"  (value is irrelevant; key existence = seen)
  TTL = window_hours * 3600
"""

import hashlib
import re
import time
import threading
import logging
import os
from collections import OrderedDict
from typing import Optional

logger = logging.getLogger("sentix.dedup")


_STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "its", "it",
    "this", "that", "these", "those", "says", "said", "say", "reports",
    "according", "per", "vs", "s", "nse", "bse"
})


# ---------------------------------------------------------------------------
# Redis dedup backend
# ---------------------------------------------------------------------------

class _RedisDedupBackend:
    """
    Uses Redis SETNX + EXPIRE for atomic deduplication.
    Each seen hash is stored as a Redis key with TTL.
    """

    _PREFIX = "sentix:dedup:"

    def __init__(self, redis_url: str, window_seconds: int):
        import redis
        self._client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        self._client.ping()
        self._window = window_seconds
        self._stats = {"total_checked": 0, "duplicates_caught": 0, "evictions": 0}
        logger.info("✅ Redis dedup backend connected")

    def _rkey(self, h: str) -> str:
        return f"{self._PREFIX}{h}"

    def is_seen(self, h: str) -> bool:
        """Returns True if hash is already in Redis (not expired)."""
        return self._client.exists(self._rkey(h)) > 0

    def register(self, h: str) -> bool:
        """
        Atomic check-and-set using SET NX EX.
        Returns True if this is NEW (was not seen before).
        Returns False if it already existed (duplicate).
        """
        # SET key "1" NX EX ttl → only sets if key doesn't exist
        result = self._client.set(self._rkey(h), "1", nx=True, ex=self._window)
        return result is not None   # None means key already existed

    def reset(self) -> None:
        pattern = f"{self._PREFIX}*"
        keys = list(self._client.scan_iter(pattern, count=1000))
        if keys:
            self._client.delete(*keys)
            logger.info(f"Redis dedup RESET: cleared {len(keys)} keys")

    def purge_expired(self) -> int:
        # Redis handles expiry natively
        return 0

    def get_active_count(self) -> int:
        try:
            count = 0
            for _ in self._client.scan_iter(f"{self._PREFIX}*", count=500):
                count += 1
            return count
        except Exception:
            return -1

    def track_stats(self, duplicate: bool) -> None:
        self._stats["total_checked"] += 1
        if duplicate:
            self._stats["duplicates_caught"] += 1

    def get_stats(self) -> dict:
        total = self._stats["total_checked"]
        dup_rate = (self._stats["duplicates_caught"] / total * 100) if total > 0 else 0.0
        return {
            "backend":             "redis",
            **self._stats,
            "active_hashes":       self.get_active_count(),
            "duplicate_rate_pct":  round(dup_rate, 2),
        }


# ---------------------------------------------------------------------------
# In-memory fallback dedup backend (original implementation)
# ---------------------------------------------------------------------------

class _MemoryDedupBackend:
    """Bounded, TTL-aware in-memory dedup. Used when Redis is unavailable."""

    def __init__(self, window_seconds: int, max_size: int):
        self._window = window_seconds
        self._max_size = max_size
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {"total_checked": 0, "duplicates_caught": 0, "evictions": 0}
        logger.warning("⚠️  Dedup running in IN-MEMORY mode.")

    def _check_hash(self, h: str, now: float) -> bool:
        if h not in self._seen:
            return False
        if now - self._seen[h] > self._window:
            del self._seen[h]
            return False
        self._seen.move_to_end(h)
        return True

    def _register_hash(self, h: str, now: float) -> None:
        if len(self._seen) >= self._max_size:
            oldest_key, _ = next(iter(self._seen.items()))
            del self._seen[oldest_key]
            self._stats["evictions"] += 1
        self._seen[h] = now

    def is_seen(self, h: str) -> bool:
        with self._lock:
            return self._check_hash(h, time.time())

    def register(self, h: str) -> bool:
        """Returns True if NEW (registered), False if duplicate."""
        now = time.time()
        with self._lock:
            if self._check_hash(h, now):
                return False
            self._register_hash(h, now)
            return True

    def reset(self) -> None:
        with self._lock:
            cleared = len(self._seen)
            self._seen.clear()
            logger.info(f"Memory dedup RESET: cleared {cleared} hashes")

    def purge_expired(self) -> int:
        cutoff = time.time() - self._window
        with self._lock:
            expired = [k for k, ts in self._seen.items() if ts < cutoff]
            for k in expired:
                del self._seen[k]
                self._stats["evictions"] += 1
            return len(expired)

    def track_stats(self, duplicate: bool) -> None:
        with self._lock:
            self._stats["total_checked"] += 1
            if duplicate:
                self._stats["duplicates_caught"] += 1

    def get_stats(self) -> dict:
        with self._lock:
            total = self._stats["total_checked"]
            dup_rate = (self._stats["duplicates_caught"] / total * 100) if total > 0 else 0.0
            return {
                "backend":            "memory",
                **self._stats,
                "active_hashes":      len(self._seen),
                "duplicate_rate_pct": round(dup_rate, 2),
            }


# ---------------------------------------------------------------------------
# DuplicateService — public API
# ---------------------------------------------------------------------------

class DuplicateService:
    """
    Unified deduplication service.
    Automatically uses Redis if REDIS_URL is set, else falls back to memory.

    Parameters
    ----------
    window_hours : int
        How long a seen hash is retained before expiry (default 24h).
    max_size : int
        Max hashes in memory mode (ignored by Redis backend).
    """

    def __init__(
        self,
        window_hours: int = 24,
        max_size: int = 50_000,
    ):
        self._window_seconds = window_hours * 3600
        self._backend = self._init_backend(window_hours, max_size)
        logger.info(
            f"DuplicateService initialized "
            f"(window={window_hours}h, backend={'redis' if self.is_redis else 'memory'})"
        )

    def _init_backend(self, window_hours: int, max_size: int):
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                return _RedisDedupBackend(redis_url, window_hours * 3600)
            except Exception as exc:
                logger.error(f"Redis dedup init failed: {exc}. Using memory fallback.")
        return _MemoryDedupBackend(window_hours * 3600, max_size)

    @property
    def is_redis(self) -> bool:
        return isinstance(self._backend, _RedisDedupBackend)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_duplicate(self, title: str, url: str = "") -> bool:
        """
        Returns True if this article has been seen before.
        Registers the article as seen if it's new.
        Thread-safe and atomic in Redis mode.
        """
        title_hash = self._title_hash(title)
        url_hash = self._url_hash(url) if url else None

        # For Redis: register() is atomic (SET NX EX) — no race conditions
        # For memory: protected by internal lock

        title_is_new = self._backend.register(title_hash)

        if not title_is_new:
            self._backend.track_stats(duplicate=True)
            logger.debug(f"DUPLICATE (title hash): {title[:60]}")
            return True

        if url_hash:
            url_is_new = self._backend.register(url_hash)
            if not url_is_new:
                self._backend.track_stats(duplicate=True)
                logger.debug(f"DUPLICATE (url hash): {url[:80]}")
                return True

        self._backend.track_stats(duplicate=False)
        return False

    def reset(self) -> None:
        """Flush all seen hashes."""
        self._backend.reset()

    def purge_expired(self) -> int:
        """For memory backend: sweep expired hashes. For Redis: no-op."""
        return self._backend.purge_expired()

    def get_stats(self) -> dict:
        return self._backend.get_stats()

    # ------------------------------------------------------------------
    # Internal hash helpers (shared by both backends)
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_title(title: str) -> str:
        title = title.lower()
        title = re.sub(r"[^\w\s]", " ", title)
        tokens = title.split()
        tokens = [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]
        tokens.sort()
        return " ".join(tokens)

    @classmethod
    def _title_hash(cls, title: str) -> str:
        normalized = cls._normalize_title(title)
        return "t:" + hashlib.sha256(normalized.encode()).hexdigest()[:16]

    @staticmethod
    def _url_hash(url: str) -> Optional[str]:
        if not url:
            return None
        clean = re.sub(r"[?#].*$", "", url.strip().rstrip("/"))
        return "u:" + hashlib.sha256(clean.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------
dedup = DuplicateService(window_hours=24, max_size=50_000)
