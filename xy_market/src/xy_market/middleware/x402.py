"""x402 payment middleware for Seller agents."""

import asyncio
import base64
import json
import logging
from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match
from x402.chains import NETWORK_TO_ID, get_token_name, get_token_version
from x402.common import find_matching_payment_requirements, x402_VERSION
from x402.encoding import safe_base64_decode
from x402.facilitator import FacilitatorClient
from x402.types import (
    PaymentPayload,
    PaymentRequirements,
    VerifyResponse,
    x402PaymentRequiredResponse,
)

from xy_market.config import PaymentOption, SellerX402Config, get_seller_x402_settings

logger = logging.getLogger(__name__)

ID_TO_NETWORK_NAME = {int(v): k for k, v in NETWORK_TO_ID.items()}


class X402PaymentMiddleware(BaseHTTPMiddleware):
    """x402 payment enforcement middleware for Seller agents.

    Similar to mcp-server-template's X402WrapperMiddleware, but reusable
    for any Seller agent endpoint.
    """

    FACILITATOR_VERIFY_MAX_RETRIES = 5
    FACILITATOR_VERIFY_RETRY_DELAY_SECONDS = 1.0

    def __init__(
        self,
        app: Any,
        tool_pricing: dict[str, list[PaymentOption]],
        settings: SellerX402Config | None = None,
    ):
        """Initialize x402 payment middleware.

        Args:
            app: FastAPI/Starlette application
            tool_pricing: Pricing configuration mapping operation_id to payment options
            facilitator_config: x402 facilitator configuration (None for mock/test mode)
        """
        super().__init__(app)
        self.tool_pricing = tool_pricing
        self.settings = settings or get_seller_x402_settings()
        self.facilitator = (
            FacilitatorClient(self.settings.facilitator_config)
            if self.settings.facilitator_config
            else None
        )

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Process request with x402 payment validation."""
        if not self.facilitator:
            # No facilitator configured - skip payment validation (test mode)
            return await call_next(request)

        operation_id = await self._get_operation_id(request)
        pricing_options = self.tool_pricing.get(operation_id) if operation_id else None

        if not operation_id or not pricing_options:
            # No pricing configured for this endpoint - allow through
            return await call_next(request)

        payment_requirements = self._build_payment_requirements(pricing_options, request)

        # Check for payment header
        payment_header = request.headers.get("X-PAYMENT") or request.headers.get("X-Payment-Proof")
        if not payment_header:
            logger.warning(f"Payment header missing for '{operation_id}'")
            return self._create_402_response(payment_requirements, "No X-PAYMENT header provided")

        # Parse payment header
        try:
            if payment_header.startswith("{"):
                # JSON-encoded payment proof
                payment_dict = json.loads(payment_header)
            else:
                # Base64-encoded x402 payment
                payment_dict = json.loads(safe_base64_decode(payment_header))
            payment = PaymentPayload(**payment_dict)
        except Exception as e:
            logger.warning(f"Invalid payment header from {request.client.host}: {e}")
            return self._create_402_response(payment_requirements, "Invalid payment header format")

        # Find matching payment requirement
        selected_req = find_matching_payment_requirements(payment_requirements, payment)
        if not selected_req:
            return self._create_402_response(
                payment_requirements, "No matching payment requirements found"
            )

        # Verify payment
        try:
            verify_response = await self._verify_with_retry(
                payment,
                selected_req,
                max_retries=self.FACILITATOR_VERIFY_MAX_RETRIES,
                retry_delay_seconds=self.FACILITATOR_VERIFY_RETRY_DELAY_SECONDS,
            )
        except httpx.HTTPError as exc:
            logger.error(
                f"Payment verification failed after {self.FACILITATOR_VERIFY_MAX_RETRIES} attempts for '{operation_id}': {exc}"
            )
            return self._create_402_response(
                payment_requirements, "Payment verification failed; please try again later."
            )

        if not verify_response.is_valid:
            reason = verify_response.invalid_reason or "Unknown reason"
            return self._create_402_response(payment_requirements, f"Invalid payment: {reason}")

        # Payment valid - proceed with request
        response = await call_next(request)

        # Settle payment on success
        if 200 <= response.status_code < 300:
            try:
                settle_response = await self.facilitator.settle(payment, selected_req)
                if settle_response.success:
                    response.headers["X-PAYMENT-RESPONSE"] = base64.b64encode(
                        settle_response.model_dump_json(by_alias=True).encode("utf-8")
                    ).decode("utf-8")
                else:
                    reason = settle_response.error_reason or "Unknown"
                    logger.error(f"Payment settlement failed for '{operation_id}': {reason}")
            except Exception as e:
                logger.error(f"Exception during settlement for '{operation_id}': {e}")

        return response

    async def _verify_with_retry(
        self,
        payment: PaymentPayload,
        payment_requirements: PaymentRequirements,
        max_retries: int = 5,
        retry_delay_seconds: float = 1.0,
    ) -> VerifyResponse:
        """Verify payment with retry logic."""
        last_error: httpx.HTTPError | None = None
        for attempt in range(1, max_retries + 1):
            try:
                return await self.facilitator.verify(payment, payment_requirements)
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(f"Facilitator verify attempt {attempt}/{max_retries} failed: {exc}")
                if attempt < max_retries:
                    delay = retry_delay_seconds * (2 ** (attempt - 1))
                    logger.info(f"Retrying payment verification in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
        assert last_error is not None
        raise last_error

    def _create_402_response(
        self, requirements: list[PaymentRequirements], error: str
    ) -> JSONResponse:
        """Create 402 Payment Required response."""
        response_data = x402PaymentRequiredResponse(
            x402_version=x402_VERSION,
            accepts=requirements,
            error=error,
        ).model_dump(by_alias=True)
        return JSONResponse(content=response_data, status_code=402)

    async def _get_operation_id(self, request: Request) -> str | None:
        """Get operation ID from request (endpoint path or MCP tool name)."""
        path = request.url.path
        if path.startswith("/api/") or path.startswith("/hybrid/") or path.startswith("/execute"):
            # Extract from path or route
            for route in request.app.routes:
                match, _ = route.matches(request.scope)
                if match != Match.NONE and hasattr(route, "operation_id"):
                    return route.operation_id
            # Fallback: use path
            return path.strip("/").replace("/", "_")
        elif "mcp" in path and request.method == "POST":
            try:
                body = await request.json()
                return (body.get("params") or {}).get("name")
            except json.JSONDecodeError:
                logger.warning("Could not decode JSON body for MCP request.")
                return None
        return None

    def _build_payment_requirements(
        self, options: list[PaymentOption], request: Request
    ) -> list[PaymentRequirements]:
        """Build x402 PaymentRequirements from payment options."""
        accepts: list[PaymentRequirements] = []
        for option in options:
            network_name = ID_TO_NETWORK_NAME.get(option.chain_id)
            if not network_name:
                logger.warning(
                    f"Unknown chain_id '{option.chain_id}' found in pricing config. Skipping."
                )
                continue

            chain_id_str = str(option.chain_id)
            token_name = get_token_name(chain_id_str, option.token_address)
            token_version = get_token_version(chain_id_str, option.token_address)

            accepts.append(
                PaymentRequirements(
                    scheme="exact",
                    network=network_name,
                    asset=option.token_address,
                    max_amount_required=str(option.token_amount),
                    resource=str(request.url),
                    description=f"Payment for {request.url.path}",
                    mime_type=request.headers.get("content-type", ""),
                    pay_to=self.settings.payee_wallet_address,
                    max_timeout_seconds=60,
                    extra={
                        "name": token_name,
                        "version": token_version,
                    },
                )
            )
        return accepts

