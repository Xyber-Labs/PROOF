"""Pytest fixtures for E2E tests."""

from __future__ import annotations

import httpx
import pytest_asyncio
from eth_account import Account
from x402.clients.httpx import x402HttpxClient

from tests.e2e.config import load_e2e_config, require_base_url, require_wallet


@pytest_asyncio.fixture(scope="module")
async def marketplace_client():
    """Fixture providing HTTP client for MarketplaceBK."""
    config = load_e2e_config()
    require_base_url(config)
    async with httpx.AsyncClient(
        base_url=config.marketplace_url,
        timeout=config.timeout_seconds,
    ) as client:
        yield config, client


@pytest_asyncio.fixture(scope="module")
async def search_engine_client():
    """Fixture providing HTTP client for SearchEngineBK."""
    config = load_e2e_config()
    require_base_url(config)
    async with httpx.AsyncClient(
        base_url=config.search_engine_url,
        timeout=config.timeout_seconds,
    ) as client:
        yield config, client


@pytest_asyncio.fixture(scope="module")
async def seller_client():
    """Fixture providing HTTP client for Seller (without payment)."""
    config = load_e2e_config()
    require_base_url(config)
    async with httpx.AsyncClient(
        base_url=config.seller_url,
        timeout=config.timeout_seconds,
    ) as client:
        yield config, client


@pytest_asyncio.fixture(scope="module")
async def paid_seller_client():
    """Fixture providing x402-enabled HTTP client for Seller (with automatic payment handling).
    
    This client automatically handles 402 Payment Required responses by:
    1. Parsing the invoice from the 402 response
    2. Creating a payment transaction
    3. Retrying the request with the X-PAYMENT header
    
    Example usage:
        async def test_execute_with_payment(paid_seller_client):
            config, client = paid_seller_client
            response = await client.post(
                f"{config.seller_url}/execute",
                json={"task_description": "..."}
            )
            # Payment handled automatically - no 402 response expected
    """
    config = load_e2e_config()
    require_base_url(config)
    require_wallet(config)
    account = Account.from_key(config.private_key)  # type: ignore[arg-type]
    async with x402HttpxClient(
        account=account,
        base_url=config.seller_url,
        timeout=config.timeout_seconds,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        yield config, client


@pytest_asyncio.fixture(scope="module")
async def rest_client():
    """Fixture providing a standard HTTP client for general E2E tests."""
    config = load_e2e_config()
    require_base_url(config)
    async with httpx.AsyncClient(
        timeout=config.timeout_seconds,
    ) as client:
        yield config, client

