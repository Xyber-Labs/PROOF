"""Logging middleware with secret masking."""

import json
import logging
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Fields that should be masked in logs
SECRET_FIELDS = ["secrets", "api_key", "password", "token", "private_key", "secret"]


def mask_secrets(data: dict[str, Any], path: str = "") -> dict[str, Any]:
    """Recursively mask secret fields in data.

    Args:
        data: Data dictionary
        path: Current path in nested structure

    Returns:
        Data with secrets masked
    """
    masked = {}
    for key, value in data.items():
        current_path = f"{path}.{key}" if path else key
        if any(secret_field in key.lower() for secret_field in SECRET_FIELDS):
            masked[key] = "***MASKED***"
        elif isinstance(value, dict):
            masked[key] = mask_secrets(value, current_path)
        elif isinstance(value, list):
            masked[key] = [
                mask_secrets(item, current_path) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked[key] = value
    return masked


class SecretMaskingMiddleware(BaseHTTPMiddleware):
    """Middleware that masks secrets in request/response logs."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Process request and mask secrets in logs."""
        # Log request (masking secrets)
        try:
            body = await request.json()
            masked_body = mask_secrets(body)
            logger.debug(
                f"Request: {request.method} {request.url.path} - Body: {json.dumps(masked_body)}"
            )
        except Exception:
            logger.debug(f"Request: {request.method} {request.url.path}")

        # Process request
        response = await call_next(request)

        # Log response (masking secrets in response body if JSON)
        try:
            if hasattr(response, "body"):
                response_body = json.loads(response.body.decode())
                masked_response = mask_secrets(response_body)
                logger.debug(f"Response: {response.status_code} - Body: {json.dumps(masked_response)}")
        except Exception:
            logger.debug(f"Response: {response.status_code}")

        return response

