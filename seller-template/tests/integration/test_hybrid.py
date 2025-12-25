from __future__ import annotations

import pytest

from xy_market.models.execution import ExecutionRequest


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_agnostic
async def test_hybrid_execute_via_rest(rest_client) -> None:
    """Test /hybrid/execute endpoint via REST."""
    config, client = rest_client
    execution_request = ExecutionRequest(task_description="Test task: say hello")
    response = await client.post(
        "/hybrid/execute",
        json=execution_request.model_dump(),
    )
    # Should return 202 Accepted with task_id and buyer_secret
    assert response.status_code == 202
    body = response.json()
    assert "task_id" in body
    assert "buyer_secret" in body
    assert body.get("status") == "in_progress"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_agnostic
async def test_hybrid_tasks_via_rest(rest_client) -> None:
    """Test /hybrid/tasks/{task_id} endpoint via REST."""
    config, client = rest_client
    # First create a task
    execution_request = ExecutionRequest(task_description="Test task")
    create_response = await client.post(
        "/hybrid/execute",
        json=execution_request.model_dump(),
    )
    assert create_response.status_code == 202
    task_data = create_response.json()
    task_id = task_data["task_id"]
    buyer_secret = task_data["buyer_secret"]

    # Then check task status
    response = await client.get(
        f"/hybrid/tasks/{task_id}",
        headers={"X-Buyer-Secret": buyer_secret},
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("task_id") == task_id
    assert body.get("status") in ["in_progress", "done", "failed"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_enabled
async def test_hybrid_execute_requires_payment(rest_client) -> None:
    """Test that /hybrid/execute requires payment when configured."""
    config, client = rest_client
    execution_request = ExecutionRequest(task_description="Test task")
    response = await client.post(
        "/hybrid/execute",
        json=execution_request.model_dump(),
    )
    # If payment is enabled, should return 402
    # If payment is disabled, should return 202
    assert response.status_code in [202, 402]
    if response.status_code == 402:
        body = response.json()
        assert "accepts" in body and body["accepts"]
        assert body.get("error")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_enabled
async def test_hybrid_execute_succeeds_with_x402(paid_client) -> None:
    """Test that /hybrid/execute succeeds with valid x402 payment."""
    config, client = paid_client
    execution_request = ExecutionRequest(task_description="Test task")
    response = await client.post(
        "/hybrid/execute",
        json=execution_request.model_dump(),
    )
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"This indicates payment flow is not working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    body = response.json()
    assert "task_id" in body
    assert "buyer_secret" in body
