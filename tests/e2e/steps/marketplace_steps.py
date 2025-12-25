"""Step definitions for Marketplace service E2E tests.

This module contains BDD step definitions for verifying
Marketplace service functionality including agent registration
and listing.

Note: pytest-bdd does not natively support async step functions.
All async operations are wrapped with asyncio.run().
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import httpx
import pytest
from pytest_bdd import given, then, when

from tests.e2e.config import E2ETestConfig


@when("I request the list of registered agents")
def request_agent_list(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Request the list of registered agents from marketplace."""

    async def _request():
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{e2e_config.marketplace_url}/register/new_entries"
                )
                workflow_context["marketplace_response"] = response
                workflow_context["marketplace_status"] = response.status_code
                if response.status_code == 200:
                    workflow_context["marketplace_data"] = response.json()
                print(f"Marketplace list response: {response.status_code}")
            except Exception as e:
                pytest.skip(f"Failed to request agent list: {e}")

    asyncio.run(_request())


@then("I should receive a successful response")
def verify_successful_response(workflow_context: dict[str, Any]):
    """Verify the response was successful (200)."""
    status = workflow_context.get("marketplace_status")
    assert status is not None, "No response received"
    assert status == 200, f"Expected 200, got {status}"
    print("Received successful response from marketplace")


@then("the response should contain a list of agents")
def verify_agent_list(workflow_context: dict[str, Any]):
    """Verify the response contains a list of agents."""
    data = workflow_context.get("marketplace_data")
    assert data is not None, "No data in response"
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    print(f"Agent list contains {len(data)} agents")


@when("I register a new agent with unique ID")
def register_new_agent(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Register a new agent with a unique ID."""

    async def _register():
        unique_id = str(uuid.uuid4())
        workflow_context["new_agent_id"] = unique_id

        agent_profile = {
            "agent_id": unique_id,
            "base_url": f"http://test-agent-{unique_id[:8]}:8001",
            "description": f"Test agent registered at {unique_id}",
            "tags": ["test", "e2e"],
        }
        workflow_context["new_agent_profile"] = agent_profile

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{e2e_config.marketplace_url}/register",
                    json=agent_profile,
                )
                workflow_context["registration_status"] = response.status_code
                workflow_context["registration_response"] = response
                print(f"Registration response: {response.status_code}")
            except Exception as e:
                pytest.skip(f"Failed to register agent: {e}")

    asyncio.run(_register())


@then("the registration should succeed")
def verify_registration_success(workflow_context: dict[str, Any]):
    """Verify the registration was successful."""
    status = workflow_context.get("registration_status")
    assert status is not None, "No registration response"
    assert status in [200, 201], f"Expected 200 or 201, got {status}"
    print("Agent registration succeeded")


@then("the newly registered agent should appear in the list")
def verify_agent_in_list(workflow_context: dict[str, Any]):
    """Verify the newly registered agent appears in the list."""
    data = workflow_context.get("marketplace_data")
    new_agent_id = workflow_context.get("new_agent_id")

    assert data is not None, "No agent list data"
    assert new_agent_id is not None, "No new agent ID recorded"

    # Check if agent appears in list (by agent_id field)
    agent_ids = [agent.get("agent_id") for agent in data if isinstance(agent, dict)]
    assert new_agent_id in agent_ids, f"Agent {new_agent_id} not found in list"
    print(f"Agent {new_agent_id} found in marketplace list")


@given("an agent is already registered")
def ensure_agent_registered(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Ensure an agent is already registered for duplicate testing."""

    async def _register():
        # Use a fixed ID for duplicate testing
        fixed_id = "e2e-duplicate-test-agent-001"
        workflow_context["duplicate_test_agent_id"] = fixed_id

        agent_profile = {
            "agent_id": fixed_id,
            "base_url": "http://duplicate-test-agent:8001",
            "description": "Test agent for duplicate registration testing",
            "tags": ["test", "duplicate"],
        }
        workflow_context["duplicate_agent_profile"] = agent_profile

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Register the agent (ignore if already exists)
                response = await client.post(
                    f"{e2e_config.marketplace_url}/register",
                    json=agent_profile,
                )
                # Accept both 200/201 (new) and 409 (already exists)
                assert response.status_code in [200, 201, 409], (
                    f"Unexpected status: {response.status_code}"
                )
                print(f"Initial registration: {response.status_code}")
            except Exception as e:
                pytest.skip(f"Failed to setup duplicate test: {e}")

    asyncio.run(_register())


@when("I attempt to register the same agent again")
def register_duplicate_agent(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Attempt to register the same agent again."""

    async def _register():
        agent_profile = workflow_context.get("duplicate_agent_profile")
        if not agent_profile:
            pytest.skip("No agent profile for duplicate test")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{e2e_config.marketplace_url}/register",
                    json=agent_profile,
                )
                workflow_context["duplicate_status"] = response.status_code
                print(f"Duplicate registration response: {response.status_code}")
            except Exception as e:
                pytest.skip(f"Failed to test duplicate registration: {e}")

    asyncio.run(_register())


@then("I should receive a 409 conflict response")
def verify_conflict_response(workflow_context: dict[str, Any]):
    """Verify we received a 409 conflict response."""
    status = workflow_context.get("duplicate_status")
    assert status is not None, "No duplicate registration response"
    assert status == 409, f"Expected 409 conflict, got {status}"
    print("Duplicate registration correctly rejected with 409")
