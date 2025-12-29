"""Seller HTTP client with x402 payment flow."""

import base64
import logging

import httpx
from x402.clients.httpx import x402HttpxClient
from x402.types import PaymentPayload

from xy_market.clients.base import BaseClient
from xy_market.errors.exceptions import (
    ExecutionFailedError,
    InvalidPaymentProofError,
)
from xy_market.models.execution import ExecutionRequest, ExecutionResult

logger = logging.getLogger(__name__)


class SellerClient(BaseClient):
    """HTTP client for direct Seller communication with x402 payment flow.
    
    This client REQUIRES x402HttpxClient for automatic payment handling.
    x402HttpxClient automatically handles 402 Payment Required responses by:
    1. Parsing the invoice from the 402 response
    2. Creating a payment transaction
    3. Retrying the request with the X-PAYMENT header
    
    Example:
        from eth_account import Account
        from x402.clients.httpx import x402HttpxClient
        from xy_market.clients.seller import SellerClient
        
        account = Account.from_key(private_key)
        x402_client = x402HttpxClient(account=account, base_url=seller_url)
        seller_client = SellerClient(base_url=seller_url, http_client=x402_client)
        
        # Execute task - payment handled automatically
        result = await seller_client.execute_task(execution_request)
    """

    def __init__(
        self,
        base_url: str,
        http_client: x402HttpxClient,
        timeout: float = 60.0,
    ):
        """Initialize Seller client.

        Args:
            base_url: Seller's base URL (HTTPS)
            http_client: x402HttpxClient for automatic payment handling (required).
                This client is tightly coupled to x402 protocol and REQUIRES x402HttpxClient.
                Example:
                    from eth_account import Account
                    from x402.clients.httpx import x402HttpxClient
                    account = Account.from_key(private_key)
                    x402_client = x402HttpxClient(account=account, base_url=base_url)
                    seller_client = SellerClient(base_url, http_client=x402_client)
            timeout: Request timeout in seconds (default 60s for execution)
            
        Raises:
            TypeError: If http_client is not an instance of x402HttpxClient
        """
        if not isinstance(http_client, x402HttpxClient):
            raise TypeError(
                f"SellerClient requires x402HttpxClient, got {type(http_client).__name__}. "
                "SellerClient is tightly coupled to x402 protocol for payment handling."
            )
        super().__init__(base_url, http_client, timeout)

    async def execute_task(
        self,
        execution_request: ExecutionRequest,
        payment_payload: "PaymentPayload | None" = None,
    ) -> ExecutionResult:
        """Execute task with async pattern and x402 payment flow.

        Initial request returns immediately with task_id and buyer_secret.
        Use poll_task_status() to check completion.

        Args:
            execution_request: Execution request
            payment_payload: Optional x402 PaymentPayload (from x402.types) for subscriptions/reuse.
                If provided, encodes it in X-PAYMENT header.

        Returns:
            Execution result with task_id, buyer_secret, status='in_progress'

        Raises:
            InvalidPaymentProofError: If payment proof is invalid or expired
            ExecutionFailedError: If task execution fails
        """

        headers: dict[str, str] = {}
        if payment_payload:
            # Encode PaymentPayload in X-PAYMENT header (x402 format)
            if isinstance(payment_payload, PaymentPayload):
                payload = payment_payload
            elif isinstance(payment_payload, dict):
                payload = PaymentPayload.model_validate(payment_payload)
            else:
                raise ValueError(f"Invalid payment_payload type: {type(payment_payload)}")
            
            # Base64 encode for x402 X-PAYMENT header
            payment_json = payload.model_dump_json(by_alias=True)
            headers["X-PAYMENT"] = base64.b64encode(payment_json.encode("utf-8")).decode("utf-8")

        try:
            response = await self._http_client.post(
                f"{self.base_url}/execute",
                json=execution_request.model_dump(exclude_none=True),
                headers=headers,
                timeout=self.timeout,
            )

            # Handle 402 Payment Required - x402HttpxClient should handle this automatically
            # If we still get 402, it means payment failed or was rejected
            if response.status_code == 402:
                error_data = response.json() if response.content else {}
                error_code = error_data.get("error_code", "")
                if "INVALID_PAYMENT_PROOF" in error_code:
                    raise InvalidPaymentProofError(error_data.get("message", "Invalid payment proof"))
                raise InvalidPaymentProofError("Payment required but could not be processed")

            response.raise_for_status()
            return ExecutionResult.model_validate(response.json())

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 402:
                error_data = e.response.json() if e.response.content else {}
                error_code = error_data.get("error_code", "")
                if "INVALID_PAYMENT_PROOF" in error_code:
                    raise InvalidPaymentProofError(error_data.get("message", "Invalid payment proof"))
                raise InvalidPaymentProofError("Payment required but could not be processed")
            elif e.response.status_code == 500:
                error_data = e.response.json() if e.response.content else {}
                raise ExecutionFailedError(error_data.get("message", "Task execution failed"))
            raise

    async def get_pricing(self) -> dict:
        """Get seller pricing configuration."""
        try:
            response = await self._http_client.get(
                f"{self.base_url}/pricing",
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get pricing from seller: {e}")
            raise

    async def poll_task_status(
        self,
        task_id: str,
        buyer_secret: str,
    ) -> ExecutionResult:
        """Poll task status using task_id and buyer_secret.

        Args:
            task_id: Task UUID from initial execution request
            buyer_secret: Secret UUID from initial execution request

        Returns:
            Execution result with current status

        Raises:
            ValueError: If task not found or secret invalid
            ExecutionFailedError: If task failed
        """
        headers = {"X-Buyer-Secret": buyer_secret}
        
        try:
            response = await self._http_client.get(
                f"{self.base_url}/tasks/{task_id}",
                headers=headers,
                timeout=self.timeout,
            )
            
            if response.status_code == 404:
                raise ValueError(f"Task not found: {task_id}")
            if response.status_code == 403:
                raise ValueError(f"Invalid buyer_secret for task: {task_id}")
            
            response.raise_for_status()
            return ExecutionResult.model_validate(response.json())
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Task not found: {task_id}")
            if e.response.status_code == 403:
                raise ValueError(f"Invalid buyer_secret for task: {task_id}")
            raise
