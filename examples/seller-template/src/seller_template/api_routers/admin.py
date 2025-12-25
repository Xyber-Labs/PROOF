"""
This module you should change to fit your needs (or drop it entirely)
It acts as a template for monetized, human-facing REST endpoints protected by x402 pricing.
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/admin/logs",
    tags=["Admin"],
    # IMPORTANT: The `operation_id` is crucial. It's used by the x402 middleware
    # and the dynamic pricing configuration in `config.py` to identify this
    # specific endpoint for payment. It must be unique across all endpoints.
    operation_id="get_admin_logs",
)
async def get_admin_logs():
    """Retrieves server logs for administrative purposes."""
    logger.info("Paid endpoint '/admin/logs' was accessed successfully.")
    return {
        "logs": [
            {
                "timestamp": "2025-01-01T00:00:00Z",
                "level": "INFO",
                "message": "Server started",
            },
            {
                "timestamp": "2025-01-01T00:01:00Z",
                "level": "INFO",
                "message": "Glad you have read this message",
            },
        ]
    }
