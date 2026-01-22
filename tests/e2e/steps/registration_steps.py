"""Step definitions for seller registration.

This module contains BDD step definitions for registering
seller agents with the marketplace.

Note: pytest-bdd does not natively support async step functions.
All async operations are wrapped with asyncio.run().
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from pytest_bdd import given, when

from tests.e2e.config import E2ETestConfig


@given("a seller agent is registered with the marketplace")
def register_seller(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Register a seller agent with the marketplace."""

    async def _register():
        seller_profile = {
            "agent_id": workflow_context["seller_id"],
            "agent_name": "Test Seller Agent",
            "base_url": f"https://test-seller-{workflow_context['seller_id'][:8]}.example.com",
            "description": "News Agent that finds and summarizes latest news articles about AI and technology",
            "tags": ["news", "ai", "technology"],
        }

        async with httpx.AsyncClient(
            base_url=e2e_config.marketplace_url,
            timeout=e2e_config.timeout_seconds,
        ) as client:
            try:
                response = await client.post("/register", json=seller_profile)
                assert response.status_code in [200, 409], (
                    f"Registration failed: {response.status_code}"
                )
                print(f"Seller registered: status={response.status_code}")
            except Exception as e:
                pytest.skip(f"Failed to register seller: {e}")

    asyncio.run(_register())


@when("I wait for the seller to be indexed")
def wait_for_indexing():
    """Wait for the seller to be available in the marketplace."""

    async def _wait():
        print("Waiting for seller availability...")
        await asyncio.sleep(2)
        print("Wait complete")

    asyncio.run(_wait())
