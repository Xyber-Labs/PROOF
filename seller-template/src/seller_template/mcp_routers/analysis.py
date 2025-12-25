"""
This module should be changed to implement your own monetized MCP-only tools, using this paid example and its x402 integration as a reference.

Main responsibility: Define an example paid MCP-only router for AI agents, protected by x402 pricing.
"""

import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/analysis",
    tags=["Agent Utilities"],
    # IMPORTANT: The `operation_id` is crucial. It's used by the x402 middleware
    # and the dynamic pricing configuration in `config.py` to identify this
    # specific tool for payment. It must be unique across all endpoints.
    operation_id="get_analysis",
)
async def get_analysis(input_data: str) -> str:
    """
    Provides a detailed analysis for AI agents.

    This premium tool performs comprehensive analysis optimized for AI agent consumption.
    It requires x402 payment and is not exposed as a REST endpoint because it's
    specifically designed for Agentic access.
    """
    try:
        logger.info(f"Performing paid analysis for: {input_data}")
        analysis = f"Analysis result for: {input_data}"

        return analysis

    except Exception as e:
        logger.error(f"Error in get_analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to generate analysis."
        ) from e
