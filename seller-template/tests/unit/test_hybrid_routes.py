from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from seller_template.hybrid_routers.execute_router import router as execute_router
from seller_template.hybrid_routers.tasks_router import router as tasks_router
from xy_market.models.execution import ExecutionRequest


@pytest_asyncio.fixture
async def hybrid_client() -> AsyncClient:
    """HTTP-level client for hybrid routers to exercise validation rules."""

    app = FastAPI()
    app.include_router(execute_router, prefix="/hybrid")
    app.include_router(tasks_router, prefix="/hybrid")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_execute_endpoint_requires_execution_service(hybrid_client: AsyncClient) -> None:
    """Test that /execute endpoint requires execution service in app state."""
    execution_request = ExecutionRequest(task_description="Test task")
    response = await hybrid_client.post("/hybrid/execute", json=execution_request.model_dump())
    # Should fail with 500 since execution_service is not in app state
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_execute_endpoint_validates_request(hybrid_client: AsyncClient) -> None:
    """Test that /execute endpoint validates request body."""
    response = await hybrid_client.post("/hybrid/execute", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_tasks_endpoint_requires_buyer_secret(hybrid_client: AsyncClient) -> None:
    """Test that /tasks endpoint requires X-Buyer-Secret header."""
    response = await hybrid_client.get("/hybrid/tasks/test-task-id")
    assert response.status_code == 422  # Missing required header


@pytest.mark.asyncio
async def test_tasks_endpoint_validates_task_id(hybrid_client: AsyncClient) -> None:
    """Test that /tasks endpoint validates task_id format."""
    response = await hybrid_client.get(
        "/hybrid/tasks/invalid-task-id",
        headers={"X-Buyer-Secret": "test-secret"},
    )
    # Should return 404 or 500 depending on implementation
    assert response.status_code in [404, 500]
