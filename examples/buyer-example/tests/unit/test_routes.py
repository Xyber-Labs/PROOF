"""Unit tests for buyer_example API routes.

Tests the router endpoints with mocked dependencies including:
- POST /chat endpoint
- Error handling
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from buyer_example.routes import router, ChatRequest, ChatResponse


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_buyer_service():
    """Create a mock BuyerAgentService."""
    service = MagicMock()
    service.process_user_request = AsyncMock(return_value={
        "status": "success",
        "response": "I found 3 sellers for your task.",
        "conversation": [
            {"role": "user", "content": "Find AI news"},
            {"role": "assistant", "content": "I found 3 sellers for your task."},
        ],
    })
    service.close = AsyncMock()
    return service


@pytest.fixture
def app(mock_buyer_service):
    """Create a test FastAPI app with mocked service."""
    with patch("buyer_example.routes.buyer_service", mock_buyer_service):
        app = FastAPI()
        app.include_router(router)
        yield app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


# =============================================================================
# Test: POST /chat - Success Cases
# =============================================================================


def test_chat_success(client, mock_buyer_service):
    """Test successful chat request."""
    with patch("buyer_example.routes.buyer_service", mock_buyer_service):
        response = client.post(
            "/chat",
            json={"message": "Find AI news services"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "response" in data


def test_chat_returns_response_text(client, mock_buyer_service):
    """Test that chat returns response text."""
    with patch("buyer_example.routes.buyer_service", mock_buyer_service):
        response = client.post(
            "/chat",
            json={"message": "Find AI news services"},
        )

    data = response.json()
    assert data["response"] == "I found 3 sellers for your task."


def test_chat_returns_conversation(client, mock_buyer_service):
    """Test that chat returns conversation history."""
    with patch("buyer_example.routes.buyer_service", mock_buyer_service):
        response = client.post(
            "/chat",
            json={"message": "Find AI news services"},
        )

    data = response.json()
    assert "conversation" in data
    assert len(data["conversation"]) == 2


def test_chat_calls_service(client, mock_buyer_service):
    """Test that chat calls the buyer service."""
    with patch("buyer_example.routes.buyer_service", mock_buyer_service):
        client.post(
            "/chat",
            json={"message": "Find AI news services"},
        )

    mock_buyer_service.process_user_request.assert_called_once_with(
        "Find AI news services"
    )


# =============================================================================
# Test: POST /chat - Error Cases
# =============================================================================


def test_chat_missing_message_returns_422(client, mock_buyer_service):
    """Test that missing message returns 422."""
    with patch("buyer_example.routes.buyer_service", mock_buyer_service):
        response = client.post("/chat", json={})

    assert response.status_code == 422


def test_chat_empty_message_accepted(client, mock_buyer_service):
    """Test that empty message is accepted (validation at service level)."""
    with patch("buyer_example.routes.buyer_service", mock_buyer_service):
        response = client.post(
            "/chat",
            json={"message": ""},
        )

    # Empty string is valid for Pydantic str field
    assert response.status_code == 200


def test_chat_service_error_returns_500(client, mock_buyer_service):
    """Test that service error returns 500."""
    mock_buyer_service.process_user_request = AsyncMock(
        side_effect=Exception("LLM API error")
    )

    with patch("buyer_example.routes.buyer_service", mock_buyer_service):
        response = client.post(
            "/chat",
            json={"message": "Find services"},
        )

    assert response.status_code == 500
    assert "LLM API error" in response.json()["detail"]


# =============================================================================
# Test: Request/Response Models
# =============================================================================


def test_chat_request_model():
    """Test ChatRequest model validation."""
    request = ChatRequest(message="Test message")
    assert request.message == "Test message"


def test_chat_response_model():
    """Test ChatResponse model validation."""
    response = ChatResponse(
        status="success",
        response="Test response",
        conversation=[{"role": "user", "content": "test"}],
    )
    assert response.status == "success"
    assert response.response == "Test response"
    assert len(response.conversation) == 1


def test_chat_response_optional_conversation():
    """Test that conversation is optional in ChatResponse."""
    response = ChatResponse(
        status="success",
        response="Test response",
    )
    assert response.conversation is None
