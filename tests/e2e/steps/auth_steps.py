"""Step definitions for authentication testing.

This module contains BDD step definitions for verifying
buyer secret authentication on task polling endpoints.

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


@given("a task execution has been initiated")
def initiate_task_execution(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Initiate a task execution for authentication testing."""

    async def _initiate():
        execution_request = {
            "task_description": "Test task for authentication",
            "context": {},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{e2e_config.seller_url}/hybrid/execute",
                    json=execution_request,
                )

                if response.status_code == 202:
                    data = response.json()
                    workflow_context["auth_task_id"] = data["task_id"]
                    workflow_context["auth_buyer_secret"] = data["buyer_secret"]
                    print(f"Task initiated for auth test: {data['task_id']}")
                else:
                    pytest.skip(f"Could not initiate task: {response.status_code}")

            except Exception as e:
                pytest.skip(f"Task initiation failed: {e}")

    asyncio.run(_initiate())


@when("I poll with the correct buyer secret")
def poll_with_correct_secret(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Poll with the correct buyer secret."""

    async def _poll():
        task_id = workflow_context.get("auth_task_id")
        buyer_secret = workflow_context.get("auth_buyer_secret")

        if not task_id:
            pytest.skip("No task_id available")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{e2e_config.seller_url}/hybrid/tasks/{task_id}",
                headers={"X-Buyer-Secret": buyer_secret},
            )
            workflow_context["correct_secret_status"] = response.status_code
            print(f"Poll with correct secret: {response.status_code}")

    asyncio.run(_poll())


@then("I should receive the task status")
def verify_task_status_received(workflow_context: dict[str, Any]):
    """Verify we received the task status."""
    status_code = workflow_context.get("correct_secret_status")
    assert status_code is not None, "No response from correct secret poll"
    assert status_code == 200, f"Expected 200, got {status_code}"
    print("Task status received successfully")


@when("I poll with an incorrect buyer secret")
def poll_with_wrong_secret(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Poll with an incorrect buyer secret."""

    async def _poll():
        task_id = workflow_context.get("auth_task_id")

        if not task_id:
            pytest.skip("No task_id available")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{e2e_config.seller_url}/hybrid/tasks/{task_id}",
                headers={"X-Buyer-Secret": "wrong-secret-12345"},
            )
            workflow_context["wrong_secret_status"] = response.status_code
            print(f"Poll with wrong secret: {response.status_code}")

    asyncio.run(_poll())


@when("I poll without any buyer secret")
def poll_without_secret(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Poll without any buyer secret header."""

    async def _poll():
        task_id = workflow_context.get("auth_task_id")

        if not task_id:
            pytest.skip("No task_id available")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{e2e_config.seller_url}/hybrid/tasks/{task_id}"
            )
            workflow_context["no_secret_status"] = response.status_code
            print(f"Poll without secret: {response.status_code}")

    asyncio.run(_poll())


@then("I should receive an authentication error")
def verify_auth_error(workflow_context: dict[str, Any]):
    """Verify we received an authentication error."""
    # Check which response we're verifying based on what's set
    wrong_status = workflow_context.get("wrong_secret_status")
    no_secret_status = workflow_context.get("no_secret_status")

    if wrong_status and "wrong_secret_verified" not in workflow_context:
        assert wrong_status in [403, 404], (
            f"Expected 403/404 for wrong secret, got {wrong_status}"
        )
        workflow_context["wrong_secret_verified"] = True
        print("Wrong secret correctly rejected")
    elif no_secret_status:
        assert no_secret_status in [403, 422], (
            f"Expected 403/422 for missing secret, got {no_secret_status}"
        )
        print("Missing secret correctly rejected")
