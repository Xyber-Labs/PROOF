"""Retry utilities with exponential backoff."""

import asyncio
import logging
from collections.abc import Callable
from typing import TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Retry function with exponential backoff."""
    attempt = 0
    delay = initial_delay

    while attempt < max_retries:
        try:
            return await func() if asyncio.iscoroutinefunction(func) else func()
        except exceptions as e:
            attempt += 1
            if attempt >= max_retries:
                logger.error(f"Max retries ({max_retries}) exceeded: {e}")
                raise

            logger.warning(
                f"Attempt {attempt}/{max_retries} failed: {e}. Retrying in {delay}s..."
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)

    raise RuntimeError("Retry logic failed unexpectedly")


def create_retry_decorator(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """Create a retry decorator with exponential backoff."""
    return retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=initial_delay, max=max_delay),
        retry=retry_if_exception_type(exceptions),
        reraise=True,
    )
