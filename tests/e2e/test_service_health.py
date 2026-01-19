"""BDD tests for Service Health checks.

This module tests that all ecosystem services are healthy and reachable.
Uses pytest-bdd with scenarios defined in features/service_health.feature.

Scenarios:
- All core services are reachable: Verifies Marketplace, Seller, MCP Server, Buyer
"""

import pytest
from pytest_bdd import scenario


# =============================================================================
# Service Health Check Tests
#
# These tests ensure all required services are running and responding
# before other E2E tests execute. They serve as a quick smoke test
# for the infrastructure.
#
# Services checked:
# - Marketplace (agent registry)
# - Seller (task execution)
# - MCP Server (weather tools)
# - Buyer (agent service)
# =============================================================================


@pytest.mark.e2e
@scenario("service_health.feature", "All core services are reachable")
def test_all_core_services_reachable():
    """Verify all core services respond to health check endpoints.

    Flow:
    1. Check Marketplace /docs endpoint
    2. Check Seller /api/health endpoint
    3. Check MCP Server /health endpoint
    4. Check Buyer /health endpoint
    5. Verify all checks passed
    """
    pass
