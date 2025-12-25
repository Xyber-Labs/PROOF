"""Unit tests for RateLimitMiddleware.

Tests the rate limiting middleware functionality including
limit enforcement, window management, and path matching.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from xy_market.middleware.ratelimit import RateLimitMiddleware


def create_test_app(limits: dict, window_seconds: int = 60) -> FastAPI:
    """Create a FastAPI app with RateLimitMiddleware for testing."""
    app = FastAPI()

    @app.get("/api/execute")
    async def execute():
        return {"status": "ok"}

    @app.get("/api/tasks/{task_id}")
    async def get_task(task_id: str):
        return {"task_id": task_id}

    @app.get("/api/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/api/admin/status")
    async def admin_status():
        return {"admin": True}

    app.add_middleware(
        RateLimitMiddleware,
        limits=limits,
        window_seconds=window_seconds,
    )

    return app


class TestRateLimitMiddlewareBasicFunctionality:
    """Test suite for basic rate limiting functionality."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create test client with rate limiting middleware."""
        app = create_test_app(
            limits={"/api/execute": 3},
            window_seconds=60,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            yield c

    @pytest.mark.asyncio
    async def test_requests_within_limit_succeed(
        self, client: AsyncClient
    ) -> None:
        """Verify requests within the rate limit succeed.

        Given a rate limit of 3 requests per window,
        When making 3 requests,
        Then all requests should succeed with 200 status.
        """
        for i in range(3):
            response = await client.get("/api/execute")
            assert response.status_code == 200, f"Request {i+1} failed"

    @pytest.mark.asyncio
    async def test_requests_exceeding_limit_get_429(
        self, client: AsyncClient
    ) -> None:
        """Verify requests exceeding the rate limit get 429.

        Given a rate limit of 3 requests per window,
        When making 4 requests,
        Then the 4th request should return 429 status.
        """
        # First 3 requests should succeed
        for _ in range(3):
            response = await client.get("/api/execute")
            assert response.status_code == 200

        # 4th request should be rate limited
        response = await client.get("/api/execute")
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.asyncio
    async def test_rate_limit_response_body(
        self, client: AsyncClient
    ) -> None:
        """Verify rate limit response contains error details.

        Given a request that exceeds the rate limit,
        When the 429 response is received,
        Then it should contain error_code and message.
        """
        # Exceed the limit
        for _ in range(4):
            response = await client.get("/api/execute")

        data = response.json()
        assert data["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert "Rate limit exceeded" in data["message"]
        assert "3 requests" in data["message"]


class TestRateLimitMiddlewarePathMatching:
    """Test suite for path pattern matching functionality."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create test client with multiple rate limits."""
        app = create_test_app(
            limits={
                "/api/execute": 2,
                "/api/health": 10,
                "/api/admin": 1,  # Prefix matching
            },
            window_seconds=60,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            yield c

    @pytest.mark.asyncio
    async def test_different_paths_have_separate_limits(
        self, client: AsyncClient
    ) -> None:
        """Verify different paths have independent rate limits.

        Given rate limits for /api/execute and /api/health,
        When making requests to both paths,
        Then each path should have its own limit counter.
        """
        # Exhaust /api/execute limit (2 requests)
        for _ in range(2):
            response = await client.get("/api/execute")
            assert response.status_code == 200

        # /api/execute should now be limited
        response = await client.get("/api/execute")
        assert response.status_code == 429

        # But /api/health should still work (different limit)
        response = await client.get("/api/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_prefix_matching_for_admin_paths(
        self, client: AsyncClient
    ) -> None:
        """Verify prefix matching works for path patterns.

        Given a rate limit for '/api/admin' prefix,
        When making requests to /api/admin/status,
        Then the prefix limit should apply.
        """
        # First request should succeed
        response = await client.get("/api/admin/status")
        assert response.status_code == 200

        # Second request should be limited (limit is 1)
        response = await client.get("/api/admin/status")
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_unmatched_paths_are_not_limited(
        self, client: AsyncClient
    ) -> None:
        """Verify paths without matching limits are not rate limited.

        Given no rate limit for /api/tasks,
        When making many requests to /api/tasks,
        Then all requests should succeed.
        """
        for _ in range(10):
            response = await client.get("/api/tasks/test-123")
            assert response.status_code == 200


class TestRateLimitMiddlewareRegexPatterns:
    """Test suite for regex pattern matching."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create test client with regex pattern limits."""
        app = create_test_app(
            limits={
                r"^/api/tasks/[^/]+$": 5,  # Regex pattern for task paths
            },
            window_seconds=60,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            yield c

    @pytest.mark.asyncio
    async def test_regex_pattern_matching(
        self, client: AsyncClient
    ) -> None:
        """Verify regex patterns work for rate limiting.

        Given a regex pattern for task paths,
        When making requests that match the pattern,
        Then the rate limit should apply.
        Note: Rate limit key includes the full path, so each unique path
        has its own counter. This test uses the same path for all requests.
        """
        # First 5 requests to same path should succeed
        for i in range(5):
            response = await client.get("/api/tasks/task-1")
            assert response.status_code == 200

        # 6th request to same path should be limited
        response = await client.get("/api/tasks/task-1")
        assert response.status_code == 429


class TestRateLimitMiddlewareWindowReset:
    """Test suite for rate limit window reset functionality."""

    @pytest.mark.asyncio
    async def test_window_resets_after_time(self) -> None:
        """Verify rate limit resets after window expires.

        Given a rate limit with 1 second window,
        When exceeding the limit and waiting for window to expire,
        Then new requests should be allowed.
        """
        app = create_test_app(
            limits={"/api/execute": 2},
            window_seconds=1,  # Short window for testing
        )
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Exhaust the limit
            for _ in range(2):
                response = await client.get("/api/execute")
                assert response.status_code == 200

            # Should be limited now
            response = await client.get("/api/execute")
            assert response.status_code == 429

            # Wait for window to reset
            time.sleep(1.1)

            # Should be allowed again
            response = await client.get("/api/execute")
            assert response.status_code == 200


class TestRateLimitMiddlewareBuyerSecretKey:
    """Test suite for buyer secret based rate limiting."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create test client with task path rate limits."""
        app = create_test_app(
            limits={"/api/tasks": 2},
            window_seconds=60,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            yield c

    @pytest.mark.asyncio
    async def test_buyer_secret_header_used_as_key_for_tasks(
        self, client: AsyncClient
    ) -> None:
        """Verify X-Buyer-Secret header is used as rate limit key for task paths.

        Given requests to /api/tasks with X-Buyer-Secret header,
        When different secrets are used,
        Then each secret should have its own rate limit counter.
        """
        # Requests with secret-1
        for _ in range(2):
            response = await client.get(
                "/api/tasks/task-1",
                headers={"X-Buyer-Secret": "secret-1"},
            )
            assert response.status_code == 200

        # secret-1 should be limited now
        response = await client.get(
            "/api/tasks/task-1",
            headers={"X-Buyer-Secret": "secret-1"},
        )
        assert response.status_code == 429

        # But secret-2 should still work (different key)
        response = await client.get(
            "/api/tasks/task-2",
            headers={"X-Buyer-Secret": "secret-2"},
        )
        assert response.status_code == 200


class TestRateLimitMiddlewareIPBasedKey:
    """Test suite for IP-based rate limiting."""

    @pytest.mark.asyncio
    async def test_same_ip_shares_rate_limit(self) -> None:
        """Verify requests from same IP share rate limit.

        Given multiple requests from the same IP,
        When making requests to the same path,
        Then they should share the same rate limit counter.
        """
        app = create_test_app(
            limits={"/api/execute": 2},
            window_seconds=60,
        )
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # All requests appear to come from same IP (testserver)
            for _ in range(2):
                response = await client.get("/api/execute")
                assert response.status_code == 200

            # Should be limited
            response = await client.get("/api/execute")
            assert response.status_code == 429


class TestRateLimitMiddlewareEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_limit_of_one_allows_single_request(self) -> None:
        """Verify limit of 1 allows exactly one request.

        Given a rate limit of 1,
        When making two requests,
        Then only the first should succeed.
        """
        app = create_test_app(
            limits={"/api/execute": 1},
            window_seconds=60,
        )
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # First request should succeed
            response = await client.get("/api/execute")
            assert response.status_code == 200
            # Second request should be blocked
            response = await client.get("/api/execute")
            assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_high_limit_allows_many_requests(self) -> None:
        """Verify high limit allows many requests.

        Given a high rate limit (1000),
        When making many requests,
        Then all should succeed.
        """
        app = create_test_app(
            limits={"/api/execute": 1000},
            window_seconds=60,
        )
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            for _ in range(100):
                response = await client.get("/api/execute")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_empty_limits_dict_allows_all(self) -> None:
        """Verify empty limits dict allows all requests.

        Given no rate limits configured,
        When making requests,
        Then all requests should succeed.
        """
        app = create_test_app(limits={}, window_seconds=60)
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            for _ in range(100):
                response = await client.get("/api/execute")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_requests_respect_limit(self) -> None:
        """Verify concurrent requests respect the rate limit.

        Given a rate limit of 5,
        When making 10 concurrent requests,
        Then exactly 5 should succeed and 5 should be limited.
        """
        import asyncio

        app = create_test_app(
            limits={"/api/execute": 5},
            window_seconds=60,
        )
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # Make 10 concurrent requests
            tasks = [client.get("/api/execute") for _ in range(10)]
            responses = await asyncio.gather(*tasks)

            success_count = sum(1 for r in responses if r.status_code == 200)
            limited_count = sum(1 for r in responses if r.status_code == 429)

            assert success_count == 5
            assert limited_count == 5


class TestRateLimitMiddlewareInternalMethods:
    """Test suite for internal helper methods."""

    @pytest.fixture
    def middleware(self) -> RateLimitMiddleware:
        """Create a middleware instance for testing internal methods."""
        app = MagicMock()
        return RateLimitMiddleware(
            app=app,
            limits={
                "/api/exact": 10,
                "^/api/regex/.*$": 5,
                "/api/prefix": 3,
            },
            window_seconds=60,
        )

    def test_get_limit_exact_match(self, middleware: RateLimitMiddleware) -> None:
        """Verify _get_limit returns correct limit for exact path match."""
        limit = middleware._get_limit("/api/exact")
        assert limit == 10

    def test_get_limit_prefix_match(self, middleware: RateLimitMiddleware) -> None:
        """Verify _get_limit returns correct limit for prefix match."""
        limit = middleware._get_limit("/api/prefix/subpath")
        assert limit == 3

    def test_get_limit_regex_match(self, middleware: RateLimitMiddleware) -> None:
        """Verify _get_limit returns correct limit for regex match."""
        limit = middleware._get_limit("/api/regex/something")
        assert limit == 5

    def test_get_limit_no_match(self, middleware: RateLimitMiddleware) -> None:
        """Verify _get_limit returns None for unmatched path."""
        limit = middleware._get_limit("/api/unknown")
        assert limit is None

    def test_get_key_with_buyer_secret(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Verify _get_key uses buyer secret for task paths."""
        request = MagicMock()
        request.headers = {"X-Buyer-Secret": "test-secret-123"}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        key = middleware._get_key(request, "/api/tasks/task-1")
        assert key == "secret:test-secret-123"

    def test_get_key_without_buyer_secret(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Verify _get_key uses IP for non-task paths."""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.100"

        key = middleware._get_key(request, "/api/execute")
        assert key == "ip:192.168.1.100:/api/execute"

    def test_get_key_handles_none_client(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Verify _get_key handles None client gracefully."""
        request = MagicMock()
        request.headers = {}
        request.client = None

        key = middleware._get_key(request, "/api/execute")
        assert key == "ip:unknown:/api/execute"

    def test_check_rate_limit_within_limit(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Verify _check_rate_limit returns True within limit."""
        result = middleware._check_rate_limit("test-key", 5)
        assert result is True

        # Second call should still be within limit
        result = middleware._check_rate_limit("test-key", 5)
        assert result is True

    def test_check_rate_limit_at_limit(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Verify _check_rate_limit returns False when limit reached."""
        for _ in range(5):
            middleware._check_rate_limit("limit-key", 5)

        # 6th call should be blocked
        result = middleware._check_rate_limit("limit-key", 5)
        assert result is False


class TestRateLimitMiddlewareHTTPMethods:
    """Test suite for different HTTP methods."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create test client with rate limiting for POST endpoint."""
        app = create_test_app(
            limits={"/api/execute": 2},
            window_seconds=60,
        )

        @app.post("/api/execute")
        async def execute_post():
            return {"method": "POST"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            yield c

    @pytest.mark.asyncio
    async def test_post_requests_are_rate_limited(
        self, client: AsyncClient
    ) -> None:
        """Verify POST requests respect rate limits.

        Given a rate limit on an endpoint,
        When making POST requests,
        Then they should be rate limited like GET requests.
        """
        # First 2 POST requests should succeed
        for _ in range(2):
            response = await client.post("/api/execute")
            assert response.status_code == 200

        # 3rd POST request should be limited
        response = await client.post("/api/execute")
        assert response.status_code == 429


class TestRateLimitMiddleware429ResponseDetails:
    """Test suite for 429 response details."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncClient:
        """Create test client with rate limiting."""
        app = create_test_app(
            limits={"/api/execute": 1},
            window_seconds=120,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as c:
            yield c

    @pytest.mark.asyncio
    async def test_429_response_includes_window_duration(
        self, client: AsyncClient
    ) -> None:
        """Verify 429 response includes window duration information.

        Given a rate limit exceeded,
        When receiving the 429 response,
        Then it should include the window duration in the message.
        """
        # Exceed limit
        await client.get("/api/execute")
        response = await client.get("/api/execute")

        assert response.status_code == 429
        data = response.json()
        assert "120 seconds" in data["message"]

    @pytest.mark.asyncio
    async def test_429_response_json_structure(
        self, client: AsyncClient
    ) -> None:
        """Verify 429 response has correct JSON structure.

        Given a rate limit exceeded,
        When receiving the 429 response,
        Then it should have error_code and message fields.
        """
        await client.get("/api/execute")
        response = await client.get("/api/execute")

        assert response.status_code == 429
        data = response.json()
        assert "error_code" in data
        assert "message" in data
        assert isinstance(data["error_code"], str)
        assert isinstance(data["message"], str)


class TestRateLimitMiddlewareForwardedHeaders:
    """Test suite for X-Forwarded-For header handling."""

    @pytest.mark.asyncio
    async def test_rate_limit_uses_client_ip_from_scope(self) -> None:
        """Verify rate limiting uses client IP from request scope.

        Given requests from the test client,
        When making requests,
        Then the rate limit key should include the client IP.
        """
        app = create_test_app(
            limits={"/api/execute": 2},
            window_seconds=60,
        )
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            for _ in range(2):
                response = await client.get("/api/execute")
                assert response.status_code == 200

            # Should be limited based on client IP
            response = await client.get("/api/execute")
            assert response.status_code == 429


class TestRateLimitMiddlewareCounterCleanup:
    """Test suite for counter cleanup behavior."""

    @pytest.fixture
    def middleware(self) -> RateLimitMiddleware:
        """Create a middleware instance for testing counters."""
        app = MagicMock()
        return RateLimitMiddleware(
            app=app,
            limits={"/api/test": 5},
            window_seconds=1,
        )

    def test_counter_reset_after_window(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Verify counter resets after window expires.

        Given requests that exhaust the limit,
        When the window expires,
        Then the counter should reset.
        """
        key = "test-counter-key"

        # Exhaust the limit
        for _ in range(5):
            assert middleware._check_rate_limit(key, 5) is True

        # Should be blocked
        assert middleware._check_rate_limit(key, 5) is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        assert middleware._check_rate_limit(key, 5) is True

    def test_different_keys_have_separate_counters(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Verify different keys maintain separate counters.

        Given requests with different keys,
        When making requests,
        Then each key should have its own counter.
        """
        key1 = "user-1-key"
        key2 = "user-2-key"

        # Exhaust limit for key1
        for _ in range(5):
            middleware._check_rate_limit(key1, 5)

        # key1 should be blocked
        assert middleware._check_rate_limit(key1, 5) is False

        # key2 should still work
        assert middleware._check_rate_limit(key2, 5) is True


class TestRateLimitMiddlewarePatternPriority:
    """Test suite for pattern matching priority.

    Note: The middleware checks exact matches first, then iterates through
    patterns in dict order. Since Python 3.7+ dicts maintain insertion order,
    patterns are checked in the order they were defined.
    """

    @pytest.fixture
    def middleware(self) -> RateLimitMiddleware:
        """Create a middleware with multiple non-overlapping patterns."""
        app = MagicMock()
        return RateLimitMiddleware(
            app=app,
            limits={
                "/api/users": 10,  # Exact match for /api/users only
                "/api/admin": 5,   # Prefix match for /api/admin/*
                "^/api/items/[0-9]+$": 20,  # Regex pattern for numeric IDs
            },
            window_seconds=60,
        )

    def test_exact_match_returns_configured_limit(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Verify exact match returns the configured limit.

        Given an exact path match,
        When getting the limit,
        Then the configured limit should be returned.
        """
        limit = middleware._get_limit("/api/users")
        assert limit == 10

    def test_prefix_match_for_subpaths(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Verify prefix matching works for subpaths.

        Given a path that matches a prefix pattern,
        When getting the limit,
        Then the prefix limit should be returned.
        """
        limit = middleware._get_limit("/api/admin/settings")
        assert limit == 5

    def test_regex_match_for_numeric_ids(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Verify regex matching works for numeric ID paths.

        Given a path with numeric ID that matches regex,
        When getting the limit,
        Then the regex limit should be returned.
        """
        limit = middleware._get_limit("/api/items/12345")
        assert limit == 20

    def test_no_match_returns_none(
        self, middleware: RateLimitMiddleware
    ) -> None:
        """Verify unmatched path returns None.

        Given a path that matches no patterns,
        When getting the limit,
        Then None should be returned.
        """
        limit = middleware._get_limit("/api/other/path")
        assert limit is None
