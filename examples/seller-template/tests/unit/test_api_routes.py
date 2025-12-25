"""Unit tests for API routes.

Tests the health and admin endpoints without middleware
to verify basic route functionality.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from seller_template.api_routers import admin, health


@pytest_asyncio.fixture
async def api_client() -> AsyncClient:
    """Create test client with API routers.

    Returns:
        AsyncClient configured to test API routes.
    """
    app = FastAPI()
    app.include_router(health.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


class TestHealthEndpoint:
    """Test suite for the health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_ok(self, api_client: AsyncClient) -> None:
        """Verify health endpoint returns successful status.

        Given the health endpoint,
        When making a GET request,
        Then it should return 200 with status='ok'.
        """
        response = await api_client.get("/api/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["service"] == "xy-seller-template"

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_json(self, api_client: AsyncClient) -> None:
        """Verify health endpoint returns JSON content type.

        Given the health endpoint,
        When making a GET request,
        Then the response should have application/json content type.
        """
        response = await api_client.get("/api/health")
        assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_health_endpoint_has_required_fields(
        self, api_client: AsyncClient
    ) -> None:
        """Verify health response contains all required fields.

        Given the health endpoint,
        When making a GET request,
        Then the response should contain 'status' and 'service' fields.
        """
        response = await api_client.get("/api/health")
        payload = response.json()
        assert "status" in payload
        assert "service" in payload

    @pytest.mark.asyncio
    async def test_health_endpoint_post_not_allowed(
        self, api_client: AsyncClient
    ) -> None:
        """Verify POST method is not allowed on health endpoint.

        Given the health endpoint,
        When making a POST request,
        Then it should return 405 Method Not Allowed.
        """
        response = await api_client.post("/api/health")
        assert response.status_code == 405


class TestAdminLogsEndpoint:
    """Test suite for the admin logs endpoint."""

    @pytest.mark.asyncio
    async def test_admin_logs_returns_log_entries(
        self, api_client: AsyncClient
    ) -> None:
        """Verify admin logs endpoint returns log entries.

        Given the admin logs endpoint,
        When making a GET request,
        Then it should return a list of logs.
        """
        response = await api_client.get("/api/admin/logs")
        assert response.status_code == 200
        payload = response.json()
        assert "logs" in payload
        assert isinstance(payload["logs"], list)

    @pytest.mark.asyncio
    async def test_admin_logs_returns_json(self, api_client: AsyncClient) -> None:
        """Verify admin logs endpoint returns JSON content type.

        Given the admin logs endpoint,
        When making a GET request,
        Then the response should have application/json content type.
        """
        response = await api_client.get("/api/admin/logs")
        assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_admin_logs_entries_have_required_fields(
        self, api_client: AsyncClient
    ) -> None:
        """Verify each log entry has required fields.

        Given the admin logs endpoint,
        When making a GET request,
        Then each log entry should have timestamp, level, and message.
        """
        response = await api_client.get("/api/admin/logs")
        payload = response.json()
        logs = payload["logs"]

        assert len(logs) > 0, "Expected at least one log entry"

        for log_entry in logs:
            assert "timestamp" in log_entry, "Log entry missing timestamp"
            assert "level" in log_entry, "Log entry missing level"
            assert "message" in log_entry, "Log entry missing message"

    @pytest.mark.asyncio
    async def test_admin_logs_timestamp_format(
        self, api_client: AsyncClient
    ) -> None:
        """Verify log timestamps are in ISO 8601 format.

        Given the admin logs endpoint,
        When making a GET request,
        Then timestamps should follow ISO 8601 format.
        """
        from datetime import datetime

        response = await api_client.get("/api/admin/logs")
        payload = response.json()
        logs = payload["logs"]

        for log_entry in logs:
            timestamp = log_entry["timestamp"]
            # Should parse without error
            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                pytest.fail(f"Invalid timestamp format: {timestamp}")

    @pytest.mark.asyncio
    async def test_admin_logs_level_values(
        self, api_client: AsyncClient
    ) -> None:
        """Verify log levels are valid values.

        Given the admin logs endpoint,
        When making a GET request,
        Then log levels should be standard logging levels.
        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

        response = await api_client.get("/api/admin/logs")
        payload = response.json()
        logs = payload["logs"]

        for log_entry in logs:
            level = log_entry["level"]
            assert level in valid_levels, f"Invalid log level: {level}"

    @pytest.mark.asyncio
    async def test_admin_logs_post_not_allowed(
        self, api_client: AsyncClient
    ) -> None:
        """Verify POST method is not allowed on admin logs endpoint.

        Given the admin logs endpoint,
        When making a POST request,
        Then it should return 405 Method Not Allowed.
        """
        response = await api_client.post("/api/admin/logs")
        assert response.status_code == 405


class TestAPIRoutesEdgeCases:
    """Test suite for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_nonexistent_endpoint_returns_404(
        self, api_client: AsyncClient
    ) -> None:
        """Verify nonexistent endpoints return 404.

        Given a nonexistent endpoint,
        When making a GET request,
        Then it should return 404 Not Found.
        """
        response = await api_client.get("/api/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_case_sensitive_routes(
        self, api_client: AsyncClient
    ) -> None:
        """Verify routes are case-sensitive.

        Given an endpoint path with wrong case,
        When making a GET request,
        Then it should return 404 Not Found.
        """
        response = await api_client.get("/api/HEALTH")
        assert response.status_code == 404

        response = await api_client.get("/api/Health")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_trailing_slash_behavior(
        self, api_client: AsyncClient
    ) -> None:
        """Verify trailing slash is handled correctly.

        Given an endpoint with trailing slash,
        When making a GET request,
        Then it should handle the request appropriately.
        """
        # FastAPI redirects trailing slashes by default
        response = await api_client.get("/api/health/", follow_redirects=False)
        # Either 307 redirect or 404 is acceptable
        assert response.status_code in [200, 307, 404]
