"""
Oil Trading Desk — Utility Helpers

Shared utilities: retry logic, rate limiting, and data helpers.
"""

import asyncio
import logging
import time
from functools import wraps

logger = logging.getLogger("otd.utils")


def retry_async(max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 60.0):
    """
    Decorator for async functions with exponential backoff retry.
    Used by all data feeds to handle transient API failures.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"[{func.__name__}] Attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
            logger.error(f"[{func.__name__}] All {max_retries} retries exhausted.")
            raise last_exception
        return wrapper
    return decorator


class RateLimiter:
    """Simple rate limiter to avoid hammering external APIs."""

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._last_call = 0.0

    async def wait(self):
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self._last_call = time.monotonic()


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default: int = 0) -> int:
    """Safely convert a value to int, returning default on failure."""
    try:
        if value is None:
            return default
        return int(float(value))
    except (ValueError, TypeError):
        return default
