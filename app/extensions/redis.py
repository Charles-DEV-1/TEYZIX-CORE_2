from __future__ import annotations

import time
from typing import Optional

from flask import current_app

try:
    import redis
except ImportError:  # pragma: no cover - requirements include redis
    redis = None


class MemoryRedis:
    """Tiny Redis-like fallback used when Redis is not reachable."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, Optional[float]]] = {}

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        expires_at = time.time() + ex if ex else None
        self._store[key] = (value, expires_at)
        return True

    def get(self, key: str) -> Optional[str]:
        item = self._store.get(key)
        if not item:
            return None
        value, expires_at = item
        if expires_at and expires_at < time.time():
            self._store.pop(key, None)
            return None
        return value


redis_client: MemoryRedis | object = MemoryRedis()


def init_redis(app) -> None:
    global redis_client
    redis_url = app.config.get("REDIS_URL")
    if not redis or not redis_url:
        redis_client = MemoryRedis()
        app.logger.warning("Redis unavailable or not configured; using memory token blacklist.")
        return

    try:
        client = redis.from_url(redis_url, decode_responses=True)
        client.ping()
        redis_client = client
    except Exception as exc:  # noqa: BLE001 - fallback must protect API startup
        redis_client = MemoryRedis()
        app.logger.warning("Redis connection failed; using memory token blacklist. %s", exc)


def blacklist_token(jti: str, expires_in_seconds: int) -> None:
    redis_client.set(f"jwt:{jti}", "revoked", ex=expires_in_seconds)


def is_token_blacklisted(jti: str) -> bool:
    return bool(redis_client.get(f"jwt:{jti}"))
