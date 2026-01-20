"""E2E tests for Marketplace service.

These tests require the Marketplace service to be running.
Start with: docker compose up marketplace

Note: Tests run sequentially with delays to avoid rate limiting.
"""

from __future__ import annotations

import asyncio
import uuid

import httpx
import pytest
import pytest_asyncio

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

# Rate limit delay between tests (marketplace has aggressive rate limiting)
RATE_LIMIT_DELAY = 0.5


@pytest_asyncio.fixture(loop_scope="function")
async def rest_client():
    """HTTP client for Marketplace service."""
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=TIMEOUT,
    ) as client:
        yield client
    # Rate limit delay after each test
    await asyncio.sleep(RATE_LIMIT_DELAY)


def generate_unique_agent() -> dict:
    """Generate a unique agent registration payload."""
    unique_id = str(uuid.uuid4())
    return {
        "agent_name": f"TestAgent-{unique_id[:8]}",
        "agent_id": unique_id,
        "base_url": f"https://test-agent-{unique_id[:8]}.example.com",
        "description": "Test agent for E2E testing",
        "tags": ["test", "e2e"],
    }


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_docs_endpoint_available(rest_client) -> None:
    """Test that /docs endpoint is accessible (service health check)."""
    response = await rest_client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_openapi_schema_available(rest_client) -> None:
    """Test that OpenAPI schema is accessible."""
    response = await rest_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_list_registered_agents(rest_client) -> None:
    """Test GET /register/new_entries returns list of agents."""
    response = await rest_client.get("/register/new_entries")
    assert response.status_code == 200
    agents = response.json()
    assert isinstance(agents, list)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_list_agents_with_pagination(rest_client) -> None:
    """Test GET /register/new_entries supports pagination."""
    response = await rest_client.get("/register/new_entries", params={"limit": 5, "offset": 0})
    assert response.status_code == 200
    agents = response.json()
    assert isinstance(agents, list)
    assert len(agents) <= 5


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_register_new_agent(rest_client) -> None:
    """Test POST /register creates a new agent."""
    agent_data = generate_unique_agent()
    response = await rest_client.post("/register", json=agent_data)
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "success"
    assert body.get("agent_id") == agent_data["agent_id"]
    assert "version" in body


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_register_agent_appears_in_list(rest_client) -> None:
    """Test that a registered agent appears in the list."""
    agent_data = generate_unique_agent()

    # Register agent
    register_response = await rest_client.post("/register", json=agent_data)
    assert register_response.status_code == 200

    # Check it appears in the list
    list_response = await rest_client.get("/register/new_entries")
    assert list_response.status_code == 200
    agents = list_response.json()

    agent_ids = [a.get("agent_id") for a in agents]
    assert agent_data["agent_id"] in agent_ids


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_duplicate_registration_returns_409(rest_client) -> None:
    """Test that duplicate registration returns 409 Conflict."""
    agent_data = generate_unique_agent()

    # First registration should succeed
    first_response = await rest_client.post("/register", json=agent_data)
    assert first_response.status_code == 200

    # Second registration with same data should fail
    second_response = await rest_client.post("/register", json=agent_data)
    assert second_response.status_code == 409
    body = second_response.json()
    assert "detail" in body
    assert body["detail"].get("error_code") == "AGENT_ALREADY_REGISTERED"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_register_with_invalid_url_returns_422(rest_client) -> None:
    """Test that registration with invalid URL returns validation error."""
    agent_data = generate_unique_agent()
    agent_data["base_url"] = "not-a-valid-url"

    response = await rest_client.post("/register", json=agent_data)
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_register_with_http_url_returns_422(rest_client) -> None:
    """Test that registration with HTTP (not HTTPS) URL returns validation error."""
    agent_data = generate_unique_agent()
    agent_data["base_url"] = "http://insecure.example.com"

    response = await rest_client.post("/register", json=agent_data)
    assert response.status_code == 422  # Must be HTTPS


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_register_with_missing_required_fields_returns_422(rest_client) -> None:
    """Test that registration with missing fields returns validation error."""
    # Missing agent_name
    response = await rest_client.post("/register", json={
        "base_url": "https://example.com",
        "description": "Test",
    })
    assert response.status_code == 422

    # Missing base_url
    response = await rest_client.post("/register", json={
        "agent_name": "Test",
        "description": "Test",
    })
    assert response.status_code == 422

    # Missing description
    response = await rest_client.post("/register", json={
        "agent_name": "Test",
        "base_url": "https://example.com",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_register_with_invalid_uuid_returns_422(rest_client) -> None:
    """Test that registration with invalid UUID format returns validation error."""
    agent_data = generate_unique_agent()
    agent_data["agent_id"] = "not-a-valid-uuid"

    response = await rest_client.post("/register", json=agent_data)
    assert response.status_code == 422
