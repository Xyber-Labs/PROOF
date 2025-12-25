"""Base HTTP client with retry logic."""

import logging
from typing import Any

import httpx

from xy_market.utils.retry import create_retry_decorator

logger = logging.getLogger(__name__)


class BaseClient:
    """Base HTTP client with retry logic and error handling."""

    def __init__(
        self,
        base_url: str,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize base client.

        Args:
            base_url: Base URL for API
            http_client: Optional httpx.AsyncClient (creates new one if not provided).
                Can be httpx.AsyncClient or x402HttpxClient for automatic payment handling.
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries

        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._http_client = http_client or httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=100),
        )

    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    @create_retry_decorator(max_retries=3, initial_delay=1.0, max_delay=60.0)
    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        url = f"{self.base_url}{path}"
        headers = headers or {}

        logger.debug(f"{method} {url}")

        try:
            response = await self._http_client.request(
                method=method,
                url=url,
                json=json,
                headers=headers,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise

    async def get(self, path: str, **kwargs) -> httpx.Response:
        """GET request."""
        return await self._request("GET", path, **kwargs)

    async def post(
        self, path: str, json: dict[str, Any] | None = None, **kwargs
    ) -> httpx.Response:
        """POST request."""
        return await self._request("POST", path, json=json, **kwargs)

    async def put(
        self, path: str, json: dict[str, Any] | None = None, **kwargs
    ) -> httpx.Response:
        """PUT request."""
        return await self._request("PUT", path, json=json, **kwargs)

    async def delete(self, path: str, **kwargs) -> httpx.Response:
        """DELETE request."""
        return await self._request("DELETE", path, **kwargs)
