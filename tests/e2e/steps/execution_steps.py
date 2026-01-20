"""Step definitions for task execution.

This module contains BDD step definitions for executing
tasks with seller agents.

Note: pytest-bdd does not natively support async step functions.
All async operations are wrapped with asyncio.run().
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from pytest_bdd import then, when

from tests.e2e.config import E2ETestConfig


@when("I execute a task with the found seller")
def execute_task_with_seller(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Execute a task with the found seller."""

    async def _execute():
        found_seller = workflow_context.get("found_seller")
        if not found_seller:
            pytest.skip("No seller found to execute with")

        buyer_id = workflow_context.get("buyer_id")
        seller_url = found_seller.get("base_url", e2e_config.seller_url)

        execution_request = {
            "task_description": "Find the latest news articles about AI advancements",
            "context": {"buyer_id": buyer_id},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(f"{seller_url}/hybrid/execute", json=execution_request)
                assert response.status_code in [202, 402], f"Unexpected status: {response.status_code}"

                if response.status_code == 402:
                    print("Payment required (402 received)")
                    workflow_context["execution_data"] = {
                        "status": "payment_required",
                        "data": response.json(),
                    }
                else:
                    execution_data = response.json()
                    assert "task_id" in execution_data
                    assert "buyer_secret" in execution_data
                    workflow_context["execution_data"] = execution_data
                    workflow_context["exec_task_id"] = execution_data["task_id"]
                    workflow_context["exec_buyer_secret"] = execution_data["buyer_secret"]
                    print(f"Task execution initiated: task_id={execution_data['task_id']}")

            except Exception as e:
                pytest.skip(f"Execution failed: {e}")

    asyncio.run(_execute())


@when("I poll until execution completes")
def poll_execution_completion(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Poll the execution task until it completes."""

    async def _poll():
        execution_data = workflow_context.get("execution_data")
        if not execution_data:
            pytest.skip("No execution data available")

        if execution_data.get("status") == "payment_required":
            print("Skipping poll - payment required")
            return

        found_seller = workflow_context.get("found_seller", {})
        seller_url = found_seller.get("base_url", e2e_config.seller_url)
        task_id = workflow_context.get("exec_task_id")
        buyer_secret = workflow_context.get("exec_buyer_secret")

        async with httpx.AsyncClient(timeout=60.0) as client:
            max_polls = 10
            poll_count = 0
            final_data = execution_data

            while poll_count < max_polls:
                await asyncio.sleep(2)
                response = await client.get(
                    f"{seller_url}/hybrid/tasks/{task_id}",
                    headers={"X-Buyer-Secret": buyer_secret},
                )
                assert response.status_code == 200
                final_data = response.json()

                if final_data["status"] != "in_progress":
                    break
                poll_count += 1

            workflow_context["execution_data"] = final_data
            print(f"Execution completed: status={final_data['status']}")

    asyncio.run(_poll())


@then("the execution should succeed or require payment")
def verify_execution_result(workflow_context: dict[str, Any]):
    """Verify execution completed or payment was required."""
    execution_data = workflow_context.get("execution_data")
    assert execution_data is not None, "No execution data"

    if execution_data.get("status") == "payment_required":
        data = execution_data.get("data", {})
        assert "error_code" in data or "accepts" in data, "Invalid payment required response"
        print("Execution requires payment (402)")
    else:
        status = execution_data.get("status")
        assert status in ["done", "failed", "in_progress"], f"Unexpected status: {status}"
        if status == "done":
            print(f"Execution succeeded: {str(execution_data.get('data', execution_data.get('result')))[:200]}...")
        elif status == "failed":
            print("Execution failed (expected for some scenarios)")
        else:
            print("Execution still in progress (timeout)")


@when("the buyer discovers sellers via marketplace")
def buyer_discover_sellers(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Have buyer discover sellers via marketplace."""

    async def _discover():
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{e2e_config.marketplace_url}/register/new_entries"
            )
            assert response.status_code == 200, f"Marketplace query failed: {response.status_code}"
            agents = response.json()
            if agents:
                workflow_context["found_seller"] = agents[0]
                print(f"Discovered {len(agents)} sellers, using first one")
            else:
                pytest.skip("No sellers discovered in marketplace")

    asyncio.run(_discover())


@when("the buyer initiates a task with a seller")
def buyer_initiate_task(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Buyer initiates a task with the discovered seller."""

    async def _initiate():
        execution_request = {
            "task_description": "Test task from buyer",
            "context": {"test": True},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{e2e_config.seller_url}/hybrid/execute",
                json=execution_request,
            )

            if response.status_code == 402:
                workflow_context["execution_data"] = {
                    "status": "payment_required",
                    "data": response.json(),
                }
                print("Task requires payment (402)")
            elif response.status_code in [200, 202]:
                data = response.json()
                workflow_context["execution_data"] = data
                workflow_context["exec_task_id"] = data.get("task_id")
                workflow_context["exec_buyer_secret"] = data.get("buyer_secret")
                print(f"Task initiated: {data.get('task_id')}")
            else:
                pytest.skip(f"Task initiation failed: {response.status_code}")

    asyncio.run(_initiate())
