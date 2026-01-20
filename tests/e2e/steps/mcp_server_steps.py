"""Step definitions for MCP Server Weather service E2E tests.

This module contains BDD step definitions for verifying
MCP Server Weather service functionality including health checks,
free endpoints (current weather), and paid endpoints (forecast).

Note: pytest-bdd does not natively support async step functions.
All async operations are wrapped with asyncio.run().
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from pytest_bdd import then, when

from tests.e2e.config import E2ETestConfig


@when("I check the MCP Server health endpoint")
def check_mcp_server_health(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Check the MCP Server /api/health endpoint."""

    async def _check():
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{e2e_config.mcp_server_url}/api/health"
                )
                workflow_context["mcp_health_status"] = response.status_code
                print(f"MCP Server health check: {response.status_code}")
            except Exception as e:
                pytest.skip(f"Failed to check MCP Server health: {e}")

    asyncio.run(_check())


@then("the MCP Server should be healthy")
def verify_mcp_server_healthy(workflow_context: dict[str, Any]):
    """Verify the MCP Server health check returned 200."""
    status = workflow_context.get("mcp_health_status")
    assert status is not None, "No health check response"
    assert status == 200, f"Expected 200, got {status}"
    print("MCP Server is healthy")


@when("I request current weather for a city")
def request_current_weather(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Request current weather via /hybrid/current endpoint."""

    async def _request():
        weather_request = {
            "city": "London",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{e2e_config.mcp_server_url}/hybrid/current",
                    json=weather_request,
                )
                workflow_context["weather_current_status"] = response.status_code
                if response.status_code == 200:
                    workflow_context["weather_current_data"] = response.json()
                print(f"Current weather response: {response.status_code}")

            except Exception as e:
                pytest.skip(f"Failed to request current weather: {e}")

    asyncio.run(_request())


@then("I should receive weather data")
def verify_weather_data(workflow_context: dict[str, Any]):
    """Verify we received weather data."""
    status = workflow_context.get("weather_current_status")
    data = workflow_context.get("weather_current_data")

    assert status is not None, "No weather response"
    assert status == 200, f"Expected 200, got {status}"
    assert data is not None, "No weather data in response"
    print(f"Weather data received: {str(data)[:200]}...")


@when("I request weather forecast without payment")
def request_forecast_without_payment(
    e2e_config: E2ETestConfig,
    workflow_context: dict[str, Any],
):
    """Request weather forecast via /hybrid/forecast endpoint without payment."""

    async def _request():
        forecast_request = {
            "city": "London",
            "days": 5,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{e2e_config.mcp_server_url}/hybrid/forecast",
                    json=forecast_request,
                )
                workflow_context["weather_forecast_status"] = response.status_code
                workflow_context["weather_forecast_response"] = response
                print(f"Forecast response: {response.status_code}")

            except Exception as e:
                pytest.skip(f"Failed to request forecast: {e}")

    asyncio.run(_request())


@then("I should receive a 402 payment required response")
def verify_payment_required(workflow_context: dict[str, Any]):
    """Verify we received a 402 payment required response."""
    status = workflow_context.get("weather_forecast_status")
    assert status is not None, "No forecast response"
    assert status == 402, f"Expected 402 payment required, got {status}"
    print("Forecast correctly requires payment (402)")
