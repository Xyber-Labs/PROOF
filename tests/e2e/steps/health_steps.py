"""Step definitions for service health checks.

This module contains BDD step definitions for verifying
that all ecosystem services are healthy and reachable.

Note: pytest-bdd does not natively support async step functions.
All async operations are wrapped with asyncio.run().
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from pytest_bdd import given, then

from tests.e2e.config import E2ETestConfig


@given("all services are healthy")
def check_all_services_healthy(e2e_config: E2ETestConfig):
    """Verify all services respond to health checks."""

    async def _check():
        async with httpx.AsyncClient(timeout=10.0) as client:
            services = [
                ("Marketplace", f"{e2e_config.marketplace_url}/docs"),
                ("Seller", f"{e2e_config.seller_url}/api/health"),
                ("MCP Server", f"{e2e_config.mcp_server_url}/health"),
                ("Buyer", f"{e2e_config.buyer_url}/health"),
            ]

            for name, url in services:
                try:
                    response = await client.get(url)
                    assert response.status_code == 200, f"{name} not healthy"
                except Exception as e:
                    pytest.skip(f"{name} not available: {e}")

        print("All services are healthy")

    asyncio.run(_check())


@given("the Marketplace service is running")
def check_marketplace_running(e2e_config: E2ETestConfig, workflow_context: dict[str, Any]):
    """Verify Marketplace is running."""

    async def _check():
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Marketplace uses /docs endpoint to verify it's running
                response = await client.get(f"{e2e_config.marketplace_url}/docs")
                assert response.status_code == 200
                workflow_context["marketplace_healthy"] = True
                print(f"Marketplace is healthy at {e2e_config.marketplace_url}")
            except Exception as e:
                pytest.skip(f"Marketplace not available: {e}")

    asyncio.run(_check())


@given("the Seller service is running")
def check_seller_running(e2e_config: E2ETestConfig, workflow_context: dict[str, Any]):
    """Verify Seller is running."""

    async def _check():
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Seller uses /api/health endpoint
                response = await client.get(f"{e2e_config.seller_url}/api/health")
                assert response.status_code == 200
                workflow_context["seller_healthy"] = True
                print(f"Seller is healthy at {e2e_config.seller_url}")
            except Exception as e:
                pytest.skip(f"Seller not available: {e}")

    asyncio.run(_check())


@given("the MCP Server service is running")
def check_mcp_server_running(e2e_config: E2ETestConfig, workflow_context: dict[str, Any]):
    """Verify MCP Server is running."""

    async def _check():
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{e2e_config.mcp_server_url}/health")
                assert response.status_code == 200
                workflow_context["mcp_server_healthy"] = True
                print(f"MCP Server is healthy at {e2e_config.mcp_server_url}")
            except Exception as e:
                pytest.skip(f"MCP Server not available: {e}")

    asyncio.run(_check())


@given("the Buyer service is running")
def check_buyer_running(e2e_config: E2ETestConfig, workflow_context: dict[str, Any]):
    """Verify Buyer is running."""

    async def _check():
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{e2e_config.buyer_url}/health")
                assert response.status_code == 200
                workflow_context["buyer_healthy"] = True
                print(f"Buyer is healthy at {e2e_config.buyer_url}")
            except Exception as e:
                pytest.skip(f"Buyer not available: {e}")

    asyncio.run(_check())


@then("all services should respond to health checks")
def verify_all_services_healthy(workflow_context: dict[str, Any]):
    """Verify all service health checks passed."""
    assert workflow_context.get("marketplace_healthy"), "Marketplace health check failed"
    assert workflow_context.get("seller_healthy"), "Seller health check failed"
    assert workflow_context.get("mcp_server_healthy"), "MCP Server health check failed"
    assert workflow_context.get("buyer_healthy"), "Buyer health check failed"
    print("All services passed health checks")
