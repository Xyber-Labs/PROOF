"""Tests for RateLimitMiddleware."""

import time
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from xy_market.middleware.ratelimit import RateLimitMiddleware


@pytest.fixture
def app():
    """Create test app with rate limiting."""
    app = FastAPI()
    
    # Configure limits: 2 req/min for /limited, 5 req/min for /tasks
    limits = {
        "/limited": 2,
        "/tasks": 5,
        r"^/tasks/.*": 5
    }
    
    app.add_middleware(RateLimitMiddleware, limits=limits, window_seconds=1)
    
    @app.get("/limited")
    async def limited():
        return {"status": "ok"}
        
    @app.get("/unlimited")
    async def unlimited():
        return {"status": "ok"}
        
    @app.get("/tasks/{task_id}")
    async def get_task(task_id: str):
        return {"task_id": task_id}

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app, backend="asyncio")


def test_rate_limit_enforced(client):
    """Test rate limit enforcement."""
    # First request - OK
    response = client.get("/limited")
    assert response.status_code == 200
    
    # Second request - OK
    response = client.get("/limited")
    assert response.status_code == 200
    
    # Third request - Exceeded
    response = client.get("/limited")
    assert response.status_code == 429
    assert response.json()["error_code"] == "RATE_LIMIT_EXCEEDED"


def test_rate_limit_reset(client):
    """Test rate limit reset after window."""
    # Exhaust limit
    client.get("/limited")
    client.get("/limited")
    assert client.get("/limited").status_code == 429
    
    # Wait for window to pass
    time.sleep(1.1)
    
    # Should be OK again
    response = client.get("/limited")
    assert response.status_code == 200


def test_unlimited_endpoint(client):
    """Test unlimited endpoint."""
    for _ in range(10):
        response = client.get("/unlimited")
        assert response.status_code == 200


def test_buyer_secret_key(client):
    """Test rate limiting by buyer secret."""
    headers = {"X-Buyer-Secret": "secret1"}
    
    # Exhaust limit for secret1
    for _ in range(5):
        assert client.get("/tasks/123", headers=headers).status_code == 200
        
    assert client.get("/tasks/123", headers=headers).status_code == 429
    
    # secret2 should still work
    headers2 = {"X-Buyer-Secret": "secret2"}
    assert client.get("/tasks/123", headers=headers2).status_code == 200

