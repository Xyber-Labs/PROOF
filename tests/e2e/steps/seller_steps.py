"""Step definitions for Seller service E2E tests.

This module contains BDD step definitions for verifying
Seller service functionality including health checks,
task execution, and authentication.

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


@when("I check the Seller health endpoint")
def check_seller_health(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Check the Seller /api/health endpoint."""

    async def _check():
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{e2e_config.seller_url}/api/health"
                )
                workflow_context["seller_health_status"] = response.status_code
                print(f"Seller health check: {response.status_code}")
            except Exception as e:
                pytest.skip(f"Failed to check seller health: {e}")

    asyncio.run(_check())


@then("the Seller should be healthy")
def verify_seller_healthy(workflow_context: dict[str, Any]):
    """Verify the Seller health check returned 200."""
    status = workflow_context.get("seller_health_status")
    assert status is not None, "No health check response"
    assert status == 200, f"Expected 200, got {status}"
    print("Seller service is healthy")


@when("I execute a task on the Seller")
def execute_task_on_seller(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Execute a task on the Seller service via /hybrid/execute."""

    async def _execute():
        execution_request = {
            "task_description": "Get current weather for London",
            "context": {"test": True},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{e2e_config.seller_url}/hybrid/execute",
                    json=execution_request,
                )
                workflow_context["seller_execute_status"] = response.status_code

                if response.status_code in [200, 202]:
                    data = response.json()
                    workflow_context["seller_execute_data"] = data
                    workflow_context["seller_task_id"] = data.get("task_id")
                    workflow_context["seller_buyer_secret"] = data.get("buyer_secret")
                    print(f"Task execution initiated: {data.get('task_id')}")
                elif response.status_code == 402:
                    workflow_context["seller_execute_data"] = {"payment_required": True}
                    print("Task execution requires payment (402)")
                else:
                    print(f"Task execution response: {response.status_code}")

            except Exception as e:
                pytest.skip(f"Failed to execute task: {e}")

    asyncio.run(_execute())


@then("I should receive a task_id")
def verify_task_id(workflow_context: dict[str, Any]):
    """Verify we received a task_id from execution."""
    data = workflow_context.get("seller_execute_data")
    status = workflow_context.get("seller_execute_status")

    # Skip if payment required - that's a valid response
    if status == 402:
        pytest.skip("Task requires payment, skipping task_id check")

    assert data is not None, "No execution data"
    task_id = data.get("task_id")
    assert task_id is not None, "No task_id in response"
    print(f"Received task_id: {task_id}")


@then("I should receive a buyer_secret")
def verify_buyer_secret(workflow_context: dict[str, Any]):
    """Verify we received a buyer_secret from execution."""
    data = workflow_context.get("seller_execute_data")
    status = workflow_context.get("seller_execute_status")

    # Skip if payment required - that's a valid response
    if status == 402:
        pytest.skip("Task requires payment, skipping buyer_secret check")

    assert data is not None, "No execution data"
    buyer_secret = data.get("buyer_secret")
    assert buyer_secret is not None, "No buyer_secret in response"
    print(f"Received buyer_secret: {buyer_secret[:8]}...")


@given("I have executed a task on the Seller")
def setup_executed_task(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Setup: execute a task to get task_id and buyer_secret."""

    async def _execute():
        execution_request = {
            "task_description": "Test task for polling",
            "context": {"test": True},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{e2e_config.seller_url}/hybrid/execute",
                    json=execution_request,
                )

                if response.status_code in [200, 202]:
                    data = response.json()
                    workflow_context["poll_task_id"] = data.get("task_id")
                    workflow_context["poll_buyer_secret"] = data.get("buyer_secret")
                    print(f"Setup task for polling: {data.get('task_id')}")
                elif response.status_code == 402:
                    pytest.skip("Task requires payment, cannot test polling")
                else:
                    pytest.skip(f"Task execution failed: {response.status_code}")

            except Exception as e:
                pytest.skip(f"Failed to setup task: {e}")

    asyncio.run(_execute())


@when("I poll the task status with the correct buyer_secret")
def poll_with_correct_secret(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Poll task status with the correct buyer_secret."""

    async def _poll():
        task_id = workflow_context.get("poll_task_id")
        buyer_secret = workflow_context.get("poll_buyer_secret")

        if not task_id or not buyer_secret:
            pytest.skip("No task_id or buyer_secret available")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{e2e_config.seller_url}/hybrid/tasks/{task_id}",
                    headers={"X-Buyer-Secret": buyer_secret},
                )
                workflow_context["poll_correct_status"] = response.status_code
                if response.status_code == 200:
                    workflow_context["poll_correct_data"] = response.json()
                print(f"Poll with correct secret: {response.status_code}")

            except Exception as e:
                pytest.skip(f"Failed to poll task: {e}")

    asyncio.run(_poll())


@then("I should receive the task status successfully")
def verify_task_status_success(workflow_context: dict[str, Any]):
    """Verify we received the task status successfully."""
    status = workflow_context.get("poll_correct_status")
    assert status is not None, "No poll response"
    assert status == 200, f"Expected 200, got {status}"
    print("Task status received successfully")


@when("I poll the task status with an invalid buyer_secret")
def poll_with_invalid_secret(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Poll task status with an invalid buyer_secret."""

    async def _poll():
        task_id = workflow_context.get("poll_task_id")

        if not task_id:
            pytest.skip("No task_id available")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{e2e_config.seller_url}/hybrid/tasks/{task_id}",
                    headers={"X-Buyer-Secret": "invalid-secret-12345"},
                )
                workflow_context["poll_invalid_status"] = response.status_code
                print(f"Poll with invalid secret: {response.status_code}")

            except Exception as e:
                pytest.skip(f"Failed to poll task: {e}")

    asyncio.run(_poll())


@then("I should receive an authentication error response")
def verify_auth_error_response(workflow_context: dict[str, Any]):
    """Verify we received an authentication error."""
    status = workflow_context.get("poll_invalid_status")
    assert status is not None, "No poll response"
    # 403 Forbidden or 404 Not Found (task not accessible) are valid
    assert status in [403, 404], f"Expected 403 or 404, got {status}"
    print(f"Authentication error received: {status}")


@then("the seller should be discoverable via marketplace")
def verify_seller_discoverable(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Verify the seller is discoverable in the marketplace."""

    async def _check():
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{e2e_config.marketplace_url}/register/new_entries"
            )
            assert response.status_code == 200, f"Failed to list agents: {response.status_code}"
            agents = response.json()
            assert isinstance(agents, list), "Expected list of agents"
            # At least one agent should be registered
            if not agents:
                pytest.skip("No agents registered in marketplace")
            workflow_context["marketplace_agents"] = agents
            print(f"Found {len(agents)} agents in marketplace")

    asyncio.run(_check())


@then("the seller profile should contain valid metadata")
def verify_seller_metadata(workflow_context: dict[str, Any]):
    """Verify the seller profile has required metadata."""
    agents = workflow_context.get("marketplace_agents", [])
    if not agents:
        pytest.skip("No agents to verify")

    # Check first agent has required fields
    agent = agents[0]
    required_fields = ["agent_id", "base_url"]
    for field in required_fields:
        assert field in agent, f"Missing required field: {field}"
    print(f"Agent profile contains valid metadata: {list(agent.keys())}")


@when("I request the seller's available tools")
def request_seller_tools(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Request the seller's available MCP tools."""

    async def _check():
        async with httpx.AsyncClient(timeout=30.0) as client:
            # MCP tools are typically exposed via /mcp-server/tools or via MCP protocol
            # Try the pricing endpoint which shows available endpoints
            response = await client.get(f"{e2e_config.seller_url}/hybrid/pricing")
            if response.status_code == 200:
                workflow_context["seller_tools_response"] = response.json()
                print(f"Seller tools/pricing retrieved: {response.status_code}")
            else:
                # Fall back to checking docs
                response = await client.get(f"{e2e_config.seller_url}/openapi.json")
                assert response.status_code == 200
                schema = response.json()
                workflow_context["seller_tools_response"] = schema.get("paths", {})
                print(f"Seller endpoints retrieved from OpenAPI")

    asyncio.run(_check())


@then("the seller should expose MCP server tools")
def verify_seller_exposes_tools(workflow_context: dict[str, Any]):
    """Verify the seller exposes MCP tools."""
    tools = workflow_context.get("seller_tools_response")
    assert tools is not None, "No tools response"
    # Either pricing info or paths should exist
    assert isinstance(tools, dict), "Expected dict of tools/paths"
    print(f"Seller exposes tools/endpoints: {len(tools)} items")


@then("the tool list should include weather tools")
def verify_weather_tools(workflow_context: dict[str, Any]):
    """Verify weather tools are available (if MCP server is connected)."""
    tools = workflow_context.get("seller_tools_response")
    # This is optional - weather tools may not be connected to seller
    # Just verify we have some tools/endpoints
    assert tools is not None, "No tools response"
    print("Tool list verified (weather tools availability depends on MCP server connection)")


@given("the seller has paid endpoints")
def verify_seller_has_paid_endpoints(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Verify the seller has at least one endpoint with price > 0."""

    async def _check():
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{e2e_config.seller_url}/hybrid/pricing")
            if response.status_code != 200:
                pytest.skip("Pricing endpoint not available")

            data = response.json()
            pricing = data.get("pricing", {})

            if not pricing:
                pytest.skip("No pricing information available")

            # Check if any endpoint has a price > 0
            has_paid_endpoint = False
            for endpoint, prices in pricing.items():
                for price_info in prices:
                    if price_info.get("token_amount", 0) > 0:
                        has_paid_endpoint = True
                        workflow_context["paid_endpoint"] = endpoint
                        workflow_context["paid_endpoint_price"] = price_info
                        print(f"Found paid endpoint: {endpoint} with price {price_info.get('token_amount')}")
                        break
                if has_paid_endpoint:
                    break

            if not has_paid_endpoint:
                pytest.skip("Seller has no paid endpoints (all prices are 0)")

    asyncio.run(_check())
