from __future__ import annotations

import pytest

from tests.integration.config import load_e2e_config, require_base_url
from tests.integration.utils import (
    call_mcp_tool,
    initialize_mcp_session,
    negotiate_mcp_session_id,
)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_agnostic
async def test_mcp_hello_robot_tool() -> None:
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="hello_robot",
        arguments={},
    )
    assert response.status_code == 200
    payload = response.text
    assert "hello" in payload.lower()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_enabled
async def test_mcp_analysis_tool_requires_payment() -> None:
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        session_id,
        name="get_analysis",
        arguments={"input_data": "test"},
    )
    # Currently priced; we expect 402 until payment flow is wired for MCP tools.
    assert response.status_code == 402
