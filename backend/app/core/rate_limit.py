"""
Distributed & In-Memory Rate Limiting Engine (Stage 10.1).
Supports multi-worker application deployments using Redis or thread-safe sliding window.
"""
import time
import threading
import logging
from typing import Dict, List, Optional
from fastapi import HTTPException, status

from backend.app.core.config import settings

logger = logging.getLogger("stockpulse.security.ratelimit")

# In-memory thread-safe store
_LOCK = threading.Lock()
_MEMORY_STORE: Dict[str, List[float]] = {}


class RateLimiter:
    """
    Sliding window rate limiter.
    Connects to Redis if REDIS_URL is configured, otherwise operates
    in-memory with thread synchronization.
    """
    def __init__(self, requests_per_minute: int = 20, window_seconds: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self._redis_client = None

        if settings.REDIS_URL:
            try:
                import redis
                self._redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
                logger.info(f"Connected to Redis distributed rate limiter at {settings.REDIS_URL}")
            except Exception as e:
                logger.warning(f"Could not connect to Redis at {settings.REDIS_URL}: {e}. Falling back to in-memory store.")
                self._redis_client = None

    def check(self, key: str) -> None:
        """
        Records an attempt and raises HTTP 429 if the limit is exceeded.
        """
        now = time.time()
        client_key = f"rate_limit:{key}"

        # 1. Distributed Redis Implementation (Multi-Worker Safe)
        if self._redis_client:
            try:
                pipeline = self._redis_client.pipeline()
                window_start = now - self.window_seconds
                pipeline.zremrangebyscore(client_key, "-inf", window_start)
                pipeline.zadd(client_key, {str(now): now})
                pipeline.zcard(client_key)
                pipeline.expire(client_key, self.window_seconds)
                results = pipeline.execute()

                current_count = results[2]
                if current_count > self.requests_per_minute:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Too many requests. Rate limit is {self.requests_per_minute} requests per minute."
                    )
                return
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Redis rate-limit query failed: {e}. Falling back to memory store.")

        # 2. In-Memory Fallback
        with _LOCK:
            timestamps = _MEMORY_STORE.get(key, [])
            window_start = now - self.window_seconds
            timestamps = [t for t in timestamps if t > window_start]

            if len(timestamps) >= self.requests_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Rate limit is {self.requests_per_minute} attempts per minute."
                )

            timestamps.append(now)
            _MEMORY_STORE[key] = timestamps


# Default auth limiter
auth_rate_limiter = RateLimiter(
    requests_per_minute=settings.AUTH_RATE_LIMIT_PER_MINUTE,
    window_seconds=60
)

