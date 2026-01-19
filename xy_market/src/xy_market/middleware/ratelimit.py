import logging
import re
import time
from collections.abc import Callable
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""

    def __init__(
        self,
        app: Any,
        limits: dict[str, int],
        window_seconds: int = 60,
    ):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            limits: Dictionary mapping path regex patterns to requests per window
            window_seconds: Time window in seconds (default: 60)

        """
        super().__init__(app)
        self.limits = limits
        self.window_seconds = window_seconds
        # key -> (count, window_start_timestamp)
        self.counters: dict[str, tuple[int, float]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        """Process request and enforce rate limits."""
        path = request.url.path
        limit = self._get_limit(path)

        if limit:
            key = self._get_key(request, path)
            if not self._check_rate_limit(key, limit):
                logger.warning(f"Rate limit exceeded for {key} on {path}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Limit: {limit} requests per {self.window_seconds} seconds.",
                    },
                )

        return await call_next(request)

    def _get_limit(self, path: str) -> int | None:
        """Get rate limit for path."""
        # Check exact matches first
        if path in self.limits:
            return self.limits[path]

        # Check regex matches
        for pattern, limit in self.limits.items():
            # Use strict matching if it looks like a regex
            if "^" in pattern or "\\" in pattern or "{" in pattern or "*" in pattern:
                if re.match(pattern, path):
                    return limit
            # Fallback to simple prefix matching for non-regex patterns
            elif path.startswith(pattern):
                return limit

        return None

    def _get_key(self, request: Request, path: str) -> str:
        """Get rate limit key (IP or specific header)."""
        # Special case for polling tasks
        if "tasks" in path and "X-Buyer-Secret" in request.headers:
            return f"secret:{request.headers['X-Buyer-Secret']}"

        # Default to client IP (handle None case for test environments)
        ip = (
            request.client.host if request.client and request.client.host else "unknown"
        )
        return f"ip:{ip}:{path}"

    def _check_rate_limit(self, key: str, limit: int) -> bool:
        """Check if request is within rate limit."""
        now = time.time()
        count, window_start = self.counters.get(key, (0, now))

        if now - window_start > self.window_seconds:
            # New window
            self.counters[key] = (1, now)
            return True

        if count >= limit:
            return False

        self.counters[key] = (count + 1, window_start)
        return True
