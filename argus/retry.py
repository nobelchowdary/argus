"""Retry utility for Vertex AI rate limit (429) errors."""

import asyncio
import time
from functools import wraps


def retry_on_resource_exhausted(max_retries: int = 5, base_delay: float = 15.0):
    """Decorator that retries on 429 RESOURCE_EXHAUSTED errors with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        last_exception = e
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt)
                            print(f"[retry] Rate limited (attempt {attempt + 1}/{max_retries + 1}), waiting {delay}s...")
                            await asyncio.sleep(delay)
                        else:
                            raise
                    else:
                        raise
            raise last_exception
        return wrapper
    return decorator
