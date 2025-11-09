import os
import threading
import time
from typing import Any, Dict, Optional, Set

import redis  # type: ignore


class _InMemoryRedis:
    """Minimal Redis substitute for testing environments."""

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}
        self._expirations: Dict[str, float] = {}
        self._sets: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()

    def _purge_if_expired(self, key: str) -> None:
        expires_at = self._expirations.get(key)
        if expires_at and time.time() > expires_at:
            self._store.pop(key, None)
            self._expirations.pop(key, None)

    def ping(self) -> bool:
        return True

    def setex(self, key: str, ttl: int, value: Any) -> None:
        with self._lock:
            self._store[key] = value
            self._expirations[key] = time.time() + ttl

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            self._purge_if_expired(key)
            return self._store.get(key)

    def sadd(self, key: str, member: str) -> None:
        with self._lock:
            if key not in self._sets:
                self._sets[key] = set()
            self._sets[key].add(member)

    def srem(self, key: str, member: str) -> None:
        with self._lock:
            if key in self._sets:
                self._sets[key].discard(member)
                if not self._sets[key]:
                    self._sets.pop(key, None)

    def smembers(self, key: str) -> Set[str]:
        with self._lock:
            return set(self._sets.get(key, set()))

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)
            self._expirations.pop(key, None)
            self._sets.pop(key, None)


_redis_client: Optional[Any] = None


def get_redis_client() -> Any:
    """
    Return a singleton Redis client instance.
    Supports optional REDIS_PASSWORD alongside REDIS_URL.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    redis_password = os.environ.get("REDIS_PASSWORD")

    if redis_password and "redis://" in redis_url:
        if "@" not in redis_url or redis_url.count("@") == 0:
            redis_url = redis_url.replace("redis://", f"redis://:{redis_password}@")
        elif redis_url.count("@") == 1 and not redis_url.split("://")[1].split("@")[0]:
            redis_url = redis_url.replace("redis://@", f"redis://:{redis_password}@")

    try:
        client = redis.from_url(redis_url)
        client.ping()
        _redis_client = client
    except Exception:
        mock = _InMemoryRedis()
        setattr(mock, "_is_mock", True)
        _redis_client = mock
    return _redis_client


