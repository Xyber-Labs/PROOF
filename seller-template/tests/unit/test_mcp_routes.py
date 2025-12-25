"""Unit tests for MCP routes.

Tests the MCP-specific endpoints for AI agent functionality.
These tests call the handler functions directly without HTTP.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from seller_template.mcp_routers.analysis import get_analysis, router as analysis_router
from seller_template.mcp_routers.hello_robot import hello_robot, router as hello_router


class TestHelloRobotFunction:
    """Test suite for the hello_robot MCP function."""

    @pytest.mark.asyncio
    async def test_hello_robot_returns_hello(self) -> None:
        """Verify hello_robot returns 'hello' string.

        Given the hello_robot function,
        When calling it,
        Then it should return exactly 'hello'.
        """
        result = await hello_robot()
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_hello_robot_returns_string_type(self) -> None:
        """Verify hello_robot returns a string type.

        Given the hello_robot function,
        When calling it,
        Then the return type should be str.
        """
        result = await hello_robot()
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_hello_robot_is_idempotent(self) -> None:
        """Verify hello_robot returns same result on multiple calls.

        Given multiple calls to hello_robot,
        When comparing results,
        Then all results should be identical.
        """
        results = [await hello_robot() for _ in range(5)]
        assert all(r == "hello" for r in results)


class TestGetAnalysisFunction:
    """Test suite for the get_analysis MCP function."""

    @pytest.mark.asyncio
    async def test_get_analysis_returns_text(self) -> None:
        """Verify get_analysis returns analysis with input.

        Given input data,
        When calling get_analysis,
        Then the response should include the input.
        """
        response = await get_analysis(input_data="test input")
        assert "test input" in response
        assert "Analysis result" in response

    @pytest.mark.asyncio
    async def test_get_analysis_with_empty_input(self) -> None:
        """Verify get_analysis handles empty input.

        Given empty input,
        When calling get_analysis,
        Then it should return a valid response.
        """
        response = await get_analysis(input_data="")
        assert isinstance(response, str)
        assert "Analysis result" in response

    @pytest.mark.asyncio
    async def test_get_analysis_with_long_input(self) -> None:
        """Verify get_analysis handles long input.

        Given very long input,
        When calling get_analysis,
        Then it should return a valid response containing the input.
        """
        long_input = "A" * 10000
        response = await get_analysis(input_data=long_input)
        assert long_input in response

    @pytest.mark.asyncio
    async def test_get_analysis_with_unicode_input(self) -> None:
        """Verify get_analysis handles unicode input.

        Given unicode characters in input,
        When calling get_analysis,
        Then it should process correctly and return them.
        """
        unicode_input = "Test with unicode: cafe"
        response = await get_analysis(input_data=unicode_input)
        assert unicode_input in response

    @pytest.mark.asyncio
    async def test_get_analysis_with_special_characters(self) -> None:
        """Verify get_analysis handles special characters.

        Given special characters in input,
        When calling get_analysis,
        Then it should process correctly.
        """
        special_input = "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        response = await get_analysis(input_data=special_input)
        assert special_input in response

    @pytest.mark.asyncio
    async def test_get_analysis_with_newlines(self) -> None:
        """Verify get_analysis handles newlines in input.

        Given input with newlines,
        When calling get_analysis,
        Then it should process correctly.
        """
        multiline_input = "Line 1\nLine 2\nLine 3"
        response = await get_analysis(input_data=multiline_input)
        assert multiline_input in response


class TestMCPRoutesViaHTTP:
    """Test suite for MCP routes via HTTP endpoints."""

    @pytest_asyncio.fixture
    async def mcp_client(self) -> AsyncClient:
        """Create test client with MCP routers.

        Returns:
            AsyncClient configured to test MCP routes.
        """
        app = FastAPI()
        app.include_router(hello_router, prefix="/mcp")
        app.include_router(analysis_router, prefix="/mcp")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client

    @pytest.mark.asyncio
    async def test_hello_robot_http_endpoint(self, mcp_client: AsyncClient) -> None:
        """Verify hello_robot works via HTTP POST.

        Given the hello_robot endpoint,
        When making a POST request,
        Then it should return 'hello'.
        """
        response = await mcp_client.post("/mcp/hello_robot")
        assert response.status_code == 200
        assert response.json() == "hello"

    @pytest.mark.asyncio
    async def test_hello_robot_get_not_allowed(self, mcp_client: AsyncClient) -> None:
        """Verify GET method is not allowed on hello_robot.

        Given the hello_robot endpoint,
        When making a GET request,
        Then it should return 405 Method Not Allowed.
        """
        response = await mcp_client.get("/mcp/hello_robot")
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_analysis_http_endpoint(self, mcp_client: AsyncClient) -> None:
        """Verify analysis endpoint works via HTTP POST.

        Given the analysis endpoint with input_data query param,
        When making a POST request,
        Then it should return analysis result.
        """
        response = await mcp_client.post(
            "/mcp/analysis",
            params={"input_data": "test data"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "test data" in result

    @pytest.mark.asyncio
    async def test_analysis_missing_input_returns_422(
        self, mcp_client: AsyncClient
    ) -> None:
        """Verify analysis endpoint requires input_data.

        Given the analysis endpoint without input_data,
        When making a POST request,
        Then it should return 422 Unprocessable Entity.
        """
        response = await mcp_client.post("/mcp/analysis")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_analysis_get_not_allowed(self, mcp_client: AsyncClient) -> None:
        """Verify GET method is not allowed on analysis.

        Given the analysis endpoint,
        When making a GET request,
        Then it should return 405 Method Not Allowed.
        """
        response = await mcp_client.get("/mcp/analysis")
        assert response.status_code == 405


class TestMCPRoutesOperationIds:
    """Test suite for operation ID configuration."""

    def test_hello_robot_has_operation_id(self) -> None:
        """Verify hello_robot route has operation_id set.

        Given the hello_robot router,
        When checking its routes,
        Then it should have operation_id 'hello_robot'.
        """
        route = hello_router.routes[0]
        assert hasattr(route, "operation_id")
        assert route.operation_id == "hello_robot"

    def test_analysis_has_operation_id(self) -> None:
        """Verify analysis route has operation_id set.

        Given the analysis router,
        When checking its routes,
        Then it should have operation_id 'get_analysis'.
        """
        route = analysis_router.routes[0]
        assert hasattr(route, "operation_id")
        assert route.operation_id == "get_analysis"
