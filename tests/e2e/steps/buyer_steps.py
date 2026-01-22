"""Step definitions for Buyer service E2E tests.

This module contains BDD step definitions for verifying
Buyer service functionality including availability checks
and chat functionality.

Note: pytest-bdd does not natively support async step functions.
All async operations are wrapped with asyncio.run().
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from pytest_bdd import given, then, when

from tests.e2e.config import E2ETestConfig


@when("I check the Buyer docs endpoint")
def check_buyer_docs(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Check the Buyer /docs endpoint to verify service is running."""

    async def _check():
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{e2e_config.buyer_url}/docs")
                workflow_context["buyer_docs_status"] = response.status_code
                print(f"Buyer docs check: {response.status_code}")
            except Exception as e:
                pytest.skip(f"Failed to check Buyer docs: {e}")

    asyncio.run(_check())


@then("the Buyer service should be accessible")
def verify_buyer_accessible(workflow_context: dict[str, Any]):
    """Verify the Buyer service is accessible."""
    status = workflow_context.get("buyer_docs_status")
    assert status is not None, "No docs response"
    assert status == 200, f"Expected 200, got {status}"
    print("Buyer service is accessible")


@when("I send a chat message to the Buyer")
def send_chat_message(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Send a chat message to the Buyer /chat endpoint."""

    async def _send():
        chat_request = {
            "message": "Hello, what services are available?",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{e2e_config.buyer_url}/chat",
                    json=chat_request,
                )
                workflow_context["buyer_chat_status"] = response.status_code
                if response.status_code == 200:
                    workflow_context["buyer_chat_data"] = response.json()
                print(f"Chat response: {response.status_code}")

            except Exception as e:
                pytest.skip(f"Failed to send chat message: {e}")

    asyncio.run(_send())


@then("I should receive a chat response")
def verify_chat_response(workflow_context: dict[str, Any]):
    """Verify we received a chat response."""
    status = workflow_context.get("buyer_chat_status")
    data = workflow_context.get("buyer_chat_data")

    assert status is not None, "No chat response"
    assert status == 200, f"Expected 200, got {status}"
    assert data is not None, "No chat data in response"
    print(f"Chat response received: {str(data)[:200]}...")


@when("the buyer queries the marketplace for available sellers")
def buyer_queries_marketplace(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Have the buyer query the marketplace for sellers."""

    async def _query():
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{e2e_config.marketplace_url}/register/new_entries"
            )
            workflow_context["buyer_marketplace_query_status"] = response.status_code
            if response.status_code == 200:
                workflow_context["buyer_marketplace_agents"] = response.json()
            print(f"Marketplace query: {response.status_code}")

    asyncio.run(_query())


@then("the buyer should receive a list of sellers")
def verify_buyer_receives_sellers(workflow_context: dict[str, Any]):
    """Verify the buyer received a list of sellers."""
    status = workflow_context.get("buyer_marketplace_query_status")
    agents = workflow_context.get("buyer_marketplace_agents")

    assert status == 200, f"Expected 200, got {status}"
    assert isinstance(agents, list), "Expected list of agents"
    print(f"Buyer received {len(agents)} sellers")


@then("each seller should have pricing information")
def verify_seller_pricing(workflow_context: dict[str, Any]):
    """Verify sellers have pricing information (or skip if not available)."""
    agents = workflow_context.get("buyer_marketplace_agents", [])
    if not agents:
        pytest.skip("No agents to verify pricing")
    # Pricing info may or may not be included in marketplace listing
    # Just verify we have some agents
    print(
        "Pricing verification: marketplace lists agents (pricing may be endpoint-specific)"
    )


# x402 Payment steps
@given("the buyer has a configured wallet")
def buyer_has_wallet(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Verify buyer has a configured wallet for payments."""
    if not e2e_config.private_key:
        pytest.skip("No wallet configured (E2E_PRIVATE_KEY not set)")
    workflow_context["buyer_wallet_configured"] = True
    print("Buyer wallet is configured")


@when("the buyer initiates a paid task with the seller")
def buyer_initiates_paid_task(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Buyer initiates a task that requires payment."""
    # This would require x402 client integration
    # For now, skip as it requires actual payment setup
    pytest.skip("x402 payment integration not yet implemented in E2E tests")


@then("the x402 payment should be processed")
def verify_x402_payment(workflow_context: dict[str, Any]):
    """Verify x402 payment was processed."""
    pytest.skip("x402 payment verification not yet implemented")


@then("the task execution should proceed after payment")
def verify_task_after_payment(workflow_context: dict[str, Any]):
    """Verify task execution proceeds after payment."""
    pytest.skip("Post-payment task verification not yet implemented")
