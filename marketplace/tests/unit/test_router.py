"""Unit tests for marketplace API router.

Tests the router endpoints with mocked dependencies including:
- POST /register endpoint
- GET /register/new_entries endpoint
- Error handling and response formats
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from xy_market.errors.exceptions import AgentAlreadyRegisteredError, AgentNotFoundError
from xy_market.models.agent import AgentProfile, RegistrationResponse

from marketplace.router import router

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_agent_service():
    """Create a mock AgentService."""
    service = MagicMock()
    return service


@pytest.fixture
def app(mock_agent_service):
    """Create a test FastAPI app with mocked agent service."""
    app = FastAPI()
    app.include_router(router)

    # Store mock service in app state
    app.state.agent_service = mock_agent_service

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


# =============================================================================
# Test: POST /register - Success Cases
# =============================================================================


def test_register_agent_success(client, mock_agent_service):
    """Test successful agent registration."""
    agent_id = str(uuid.uuid4())
    mock_agent_service.register_agent = AsyncMock(
        return_value=RegistrationResponse(
            status="success",
            agent_id=agent_id,
            version=1,
        )
    )

    response = client.post(
        "/register",
        json={
            "agent_name": "TestAgent",
            "base_url": "https://agent.example.com",
            "description": "Test agent",
            "tags": ["test"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["agent_id"] == agent_id
    assert data["version"] == 1


def test_register_agent_with_provided_id(client, mock_agent_service):
    """Test registration with provided agent_id."""
    agent_id = str(uuid.uuid4())
    mock_agent_service.register_agent = AsyncMock(
        return_value=RegistrationResponse(
            status="success",
            agent_id=agent_id,
            version=1,
        )
    )

    response = client.post(
        "/register",
        json={
            "agent_id": agent_id,
            "agent_name": "TestAgent",
            "base_url": "https://agent.example.com",
            "description": "Test agent",
        },
    )

    assert response.status_code == 200
    assert response.json()["agent_id"] == agent_id


# =============================================================================
# Test: POST /register - Error Cases
# =============================================================================


def test_register_duplicate_agent_returns_409(client, mock_agent_service):
    """Test that duplicate agent registration returns 409 Conflict."""
    mock_agent_service.register_agent = AsyncMock(
        side_effect=AgentAlreadyRegisteredError("Agent already registered")
    )

    response = client.post(
        "/register",
        json={
            "agent_name": "TestAgent",
            "base_url": "https://agent.example.com",
            "description": "Test agent",
        },
    )

    assert response.status_code == 409
    data = response.json()
    assert data["detail"]["error_code"] == "AGENT_ALREADY_REGISTERED"


def test_register_agent_not_found_returns_404(client, mock_agent_service):
    """Test that AgentNotFoundError returns 404."""
    mock_agent_service.register_agent = AsyncMock(
        side_effect=AgentNotFoundError("agent-123")
    )

    response = client.post(
        "/register",
        json={
            "agent_name": "TestAgent",
            "base_url": "https://agent.example.com",
            "description": "Test agent",
        },
    )

    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error_code"] == "AGENT_NOT_FOUND"


def test_register_invalid_request_returns_400(client, mock_agent_service):
    """Test that ValueError returns 400 Bad Request."""
    mock_agent_service.register_agent = AsyncMock(
        side_effect=ValueError("Invalid request data")
    )

    response = client.post(
        "/register",
        json={
            "agent_name": "TestAgent",
            "base_url": "https://agent.example.com",
            "description": "Test agent",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error_code"] == "INVALID_REQUEST"


def test_register_missing_required_fields_returns_422(client):
    """Test that missing required fields returns 422 Unprocessable Entity."""
    response = client.post(
        "/register",
        json={
            "agent_name": "TestAgent",
            # Missing base_url and description
        },
    )

    assert response.status_code == 422


def test_register_invalid_url_returns_422(client):
    """Test that invalid URL returns 422 Unprocessable Entity."""
    response = client.post(
        "/register",
        json={
            "agent_name": "TestAgent",
            "base_url": "not-a-valid-url",
            "description": "Test agent",
        },
    )

    assert response.status_code == 422


# =============================================================================
# Test: GET /register/new_entries
# =============================================================================


def test_get_new_entries_success(client, mock_agent_service):
    """Test getting new entries."""
    agent_id = str(uuid.uuid4())
    mock_agent_service.list_agents = AsyncMock(
        return_value=[
            AgentProfile(
                agent_id=agent_id,
                agent_name="TestAgent",
                base_url="https://agent.example.com",
                description="Test agent",
            )
        ]
    )

    response = client.get("/register/new_entries")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["agent_id"] == agent_id


def test_get_new_entries_empty(client, mock_agent_service):
    """Test getting new entries when none exist."""
    mock_agent_service.list_agents = AsyncMock(return_value=[])

    response = client.get("/register/new_entries")

    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_get_new_entries_with_pagination(client, mock_agent_service):
    """Test getting new entries with limit and offset parameters."""
    mock_agent_service.list_agents = AsyncMock(return_value=[])

    response = client.get("/register/new_entries?limit=10&offset=5")

    assert response.status_code == 200
    mock_agent_service.list_agents.assert_called_once_with(limit=10, offset=5)


def test_get_new_entries_default_pagination(client, mock_agent_service):
    """Test default pagination values."""
    mock_agent_service.list_agents = AsyncMock(return_value=[])

    response = client.get("/register/new_entries")

    assert response.status_code == 200
    mock_agent_service.list_agents.assert_called_once_with(limit=100, offset=0)


def test_get_new_entries_internal_error_returns_500(client, mock_agent_service):
    """Test that internal errors return 500."""
    mock_agent_service.list_agents = AsyncMock(
        side_effect=Exception("Database connection failed")
    )

    response = client.get("/register/new_entries")

    assert response.status_code == 500
    data = response.json()
    assert data["detail"]["error_code"] == "INTERNAL_ERROR"
