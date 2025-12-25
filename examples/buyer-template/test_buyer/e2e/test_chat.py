"""E2E tests for buyer-template chat endpoint.

These tests require the buyer service to be running.
Start with: docker compose up buyer
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_docs_endpoint_available(rest_client) -> None:
    """Test that /docs endpoint is accessible (service health check)."""
    config, client = rest_client
    response = await client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_openapi_schema_available(rest_client) -> None:
    """Test that OpenAPI schema is accessible."""
    config, client = rest_client
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_chat_endpoint_accepts_message(rest_client) -> None:
    """Test that /chat endpoint accepts and processes a message.

    Note: This test may be slow as it involves LLM processing.
    The response depends on marketplace/seller availability.
    """
    config, client = rest_client
    chat_request = {"message": "Hello, what can you help me with?"}
    response = await client.post("/chat", json=chat_request)

    # Should either succeed or return a clear error
    # 200 = success, 500/503 = service issues (marketplace/seller not available)
    assert response.status_code in [200, 500, 503], (
        f"Unexpected status: {response.status_code}"
    )

    if response.status_code == 200:
        body = response.json()
        assert "status" in body
        assert "response" in body


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_chat_endpoint_rejects_empty_message(rest_client) -> None:
    """Test that /chat endpoint validates request body."""
    config, client = rest_client

    # Empty body
    response = await client.post("/chat", json={})
    assert response.status_code == 422  # Validation error

    # Missing message field
    response = await client.post("/chat", json={"wrong_field": "test"})
    assert response.status_code == 422
