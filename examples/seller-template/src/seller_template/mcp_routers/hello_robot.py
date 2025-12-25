"""
This module should be changed to define MCP-only tools that fit your agent's needs, using this free example as a starting template.

Main responsibility: Provide an example free MCP-only router for AI agents.
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/hello_robot",
    tags=["Agent Utilities"],
    # IMPORTANT: The `operation_id` provides a unique, stable identifier for this
    # tool. While optional in FastAPI, it is CRUCIAL for this template as it's
    # used by the pricing system and other integrations. Always define one.
    operation_id="hello_robot",
)
async def hello_robot() -> str:
    """A simple hello endpoint for MCP agents."""
    logger.info("Hello MCP called")
    return "hello"
