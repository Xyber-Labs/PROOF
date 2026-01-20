from __future__ import annotations

import httpx
import pytest_asyncio

from test_buyer.e2e.config import load_e2e_config, require_base_url


@pytest_asyncio.fixture
async def rest_client():
    """Fixture providing a standard HTTP client for e2e tests."""
    config = load_e2e_config()
    require_base_url(config)
    async with httpx.AsyncClient(
        base_url=config.base_url,
        timeout=config.timeout_seconds,
    ) as client:
        yield config, client
