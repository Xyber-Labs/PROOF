"""Pytest configuration and fixtures for E2E tests.

This module provides:
- Core fixtures (config, workflow context)
- Step definition imports from the steps/ directory

Step definitions are organized by domain:
- steps/health_steps.py: Service health checks
- steps/registration_steps.py: Seller registration
- steps/execution_steps.py: Task execution
- steps/auth_steps.py: Authentication testing

Note: pytest-bdd does not natively support async step functions.
All async operations in steps are wrapped with asyncio.run().
HTTP client fixtures are not used since each step manages its own client.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.e2e.config import E2ETestConfig, load_e2e_config

# =============================================================================
# Import all step definitions - makes them available to pytest-bdd
# =============================================================================
from tests.e2e.steps.health_steps import *  # noqa: F401, F403
from tests.e2e.steps.registration_steps import *  # noqa: F401, F403
from tests.e2e.steps.execution_steps import *  # noqa: F401, F403
from tests.e2e.steps.auth_steps import *  # noqa: F401, F403
from tests.e2e.steps.marketplace_steps import *  # noqa: F401, F403
from tests.e2e.steps.seller_steps import *  # noqa: F401, F403
from tests.e2e.steps.mcp_server_steps import *  # noqa: F401, F403
from tests.e2e.steps.buyer_steps import *  # noqa: F401, F403


# =============================================================================
# Core Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def e2e_config() -> E2ETestConfig:
    """Load E2E configuration once per session.

    Configuration is loaded from environment variables with E2E_ prefix.
    See tests/.env.tests.example for available options.
    """
    return load_e2e_config()


# =============================================================================
# Test Context Fixture
# =============================================================================


@pytest.fixture
def workflow_context() -> dict[str, Any]:
    """Mutable context for sharing state between BDD steps within a scenario.

    This fixture provides a dictionary that persists across all steps
    in a single scenario. Each scenario gets a fresh context.

    Pre-populated with:
    - seller_id: Default test seller UUID

    Steps can add arbitrary keys to share data:
    - search_data: Results from search operations
    - execution_data: Results from task execution
    - found_seller: Seller found in search results
    - task_id, buyer_secret: Authentication tokens
    """
    return {
        "seller_id": "770e8400-e29b-41d4-a716-446655440002",
        "search_data": None,
        "execution_data": None,
        "found_seller": None,
        "task_id": None,
        "buyer_secret": None,
    }
