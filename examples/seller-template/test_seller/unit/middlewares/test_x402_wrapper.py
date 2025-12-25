"""Unit tests for X402WrapperMiddleware.

Tests the x402 payment middleware functionality including payment
header validation, facilitator integration, and error handling.
"""

from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio
from eth_account import Account
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from x402.clients.base import x402Client
from x402.types import PaymentPayload, PaymentRequirements, x402PaymentRequiredResponse

from seller_template.config import PaymentOption
from seller_template.middlewares import X402WrapperMiddleware

# ============================================================================
# Test Fixtures
# ============================================================================


class DummyFacilitator:
    """Mock facilitator for testing x402 payment flow."""

    def __init__(self) -> None:
        self.verify_calls: list[tuple[PaymentPayload, PaymentRequirements]] = []
        self.settle_calls: list[tuple[PaymentPayload, PaymentRequirements]] = []
        self.verify_response = SimpleNamespace(is_valid=True, invalid_reason=None)
        self.settle_success = True

    async def verify(self, payment: Any, requirements: Any) -> SimpleNamespace:
        """Record verify call and return configured response."""
        self.verify_calls.append((payment, requirements))
        return self.verify_response

    async def settle(self, payment: Any, requirements: Any) -> Any:
        """Record settle call and return configured response."""
        self.settle_calls.append((payment, requirements))
        payload = {"status": "ok" if self.settle_success else "failed"}

        class Result:
            success = self.settle_success

            def model_dump_json(self, **kwargs: Any) -> str:
                return json.dumps(payload)

        Result.success = self.settle_success
        return Result()


@pytest.fixture
def pricing() -> dict[str, list[PaymentOption]]:
    """Create default pricing configuration for tests."""
    return {
        "get_weather_forecast": [
            PaymentOption(
                chain_id=8453,
                token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                token_amount=1000,
            )
        ]
    }


@pytest.fixture
def multi_option_pricing() -> dict[str, list[PaymentOption]]:
    """Create pricing with multiple payment options."""
    return {
        "get_weather_forecast": [
            PaymentOption(
                chain_id=8453,
                token_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                token_amount=1000,
            ),
            PaymentOption(
                chain_id=1,  # Ethereum mainnet
                token_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                token_amount=2000,
            ),
        ]
    }


@pytest_asyncio.fixture
async def payment_app(
    monkeypatch: pytest.MonkeyPatch, pricing: dict[str, list[PaymentOption]]
):
    """Return (client, facilitator_stub) tuple for middleware tests."""

    facilitator = DummyFacilitator()

    settings = SimpleNamespace(
        facilitator_config={"url": "https://facilitator"},
        payee_wallet_address="0xD23ef9BAf3A2A9a9feb8035e4b3Be41878faF515",
    )
    monkeypatch.setattr(
        "seller_template.middlewares.x402_wrapper.get_x402_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "seller_template.middlewares.x402_wrapper.FacilitatorClient",
        lambda config: facilitator,
    )

    app = FastAPI()

    @app.post("/hybrid/forecast", operation_id="get_weather_forecast")
    async def forecast_endpoint():
        return {"ok": True}

    @app.get("/api/free", operation_id="free_endpoint")
    async def free_endpoint():
        return {"free": True}

    app.add_middleware(X402WrapperMiddleware, tool_pricing=pricing)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, facilitator


# ============================================================================
# Test Classes
# ============================================================================


class TestX402MissingPaymentHeader:
    """Test suite for missing payment header scenarios."""

    @pytest.mark.asyncio
    async def test_missing_payment_header_returns_402(self, payment_app) -> None:
        """Verify missing X-PAYMENT header returns 402.

        Given a paid endpoint,
        When requesting without X-PAYMENT header,
        Then it should return 402 with payment requirements.
        """
        client, _ = payment_app
        response = await client.post("/hybrid/forecast")
        assert response.status_code == 402
        payload = response.json()
        assert payload["error"] == "No X-PAYMENT header provided"
        assert payload["accepts"]

    @pytest.mark.asyncio
    async def test_402_response_includes_x402_version(self, payment_app) -> None:
        """Verify 402 response includes x402 protocol version.

        Given a paid endpoint,
        When requesting without payment,
        Then the response should include x402Version field (camelCase per x402 spec).
        """
        client, _ = payment_app
        response = await client.post("/hybrid/forecast")
        payload = response.json()
        assert "x402Version" in payload

    @pytest.mark.asyncio
    async def test_402_response_includes_payment_options(self, payment_app) -> None:
        """Verify 402 response includes payment options.

        Given a paid endpoint with configured pricing,
        When requesting without payment,
        Then the response should list available payment options (using camelCase per x402 spec).
        """
        client, _ = payment_app
        response = await client.post("/hybrid/forecast")
        payload = response.json()
        accepts = payload["accepts"]
        assert len(accepts) > 0
        # x402 uses camelCase for field names
        assert "payTo" in accepts[0]
        assert "maxAmountRequired" in accepts[0]


class TestX402InvalidPaymentHeader:
    """Test suite for invalid payment header scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_payment_header_returns_402(self, payment_app) -> None:
        """Verify invalid X-PAYMENT header returns 402.

        Given a paid endpoint,
        When providing malformed X-PAYMENT header,
        Then it should return 402 with format error.
        """
        client, _ = payment_app
        headers = {"X-PAYMENT": base64.b64encode(b"not-json").decode("utf-8")}
        response = await client.post("/hybrid/forecast", headers=headers)
        assert response.status_code == 402
        payload = response.json()
        assert payload["error"] == "Invalid payment header format"

    @pytest.mark.asyncio
    async def test_non_base64_header_returns_402(self, payment_app) -> None:
        """Verify non-base64 X-PAYMENT header returns 402.

        Given a paid endpoint,
        When providing non-base64 encoded header,
        Then it should return 402 with format error.
        """
        client, _ = payment_app
        headers = {"X-PAYMENT": "not-base64-encoded"}
        response = await client.post("/hybrid/forecast", headers=headers)
        assert response.status_code == 402
        payload = response.json()
        assert "Invalid" in payload["error"] or "error" in payload

    @pytest.mark.asyncio
    async def test_empty_json_header_returns_402(self, payment_app) -> None:
        """Verify empty JSON object in header returns 402.

        Given a paid endpoint,
        When providing empty JSON object in X-PAYMENT,
        Then it should return 402 with error.
        """
        client, _ = payment_app
        empty_json = base64.b64encode(b"{}").decode("utf-8")
        headers = {"X-PAYMENT": empty_json}
        response = await client.post("/hybrid/forecast", headers=headers)
        assert response.status_code == 402


class TestX402ValidPayment:
    """Test suite for valid payment scenarios."""

    @pytest.mark.asyncio
    async def test_valid_payment_header_allows_request_and_sets_response_header(
        self,
        payment_app,
    ) -> None:
        """Verify valid payment allows request with response header.

        Given a paid endpoint with valid X-PAYMENT,
        When making the request,
        Then it should succeed and include X-PAYMENT-RESPONSE header.
        """
        client, facilitator = payment_app

        # First call without header to obtain payment requirements
        resp_402 = await client.post("/hybrid/forecast")
        assert resp_402.status_code == 402
        body = resp_402.json()
        payment_response = x402PaymentRequiredResponse(**body)
        assert payment_response.accepts

        # Use x402Client logic to construct a real X-PAYMENT header
        account = Account.create()
        xclient = x402Client(account=account)
        selected_req = payment_response.accepts[0]
        header_value = xclient.create_payment_header(
            payment_requirements=selected_req,
            x402_version=payment_response.x402_version,
        )

        headers = {"X-PAYMENT": header_value}
        resp_paid = await client.post("/hybrid/forecast", headers=headers)
        assert resp_paid.status_code == 200
        assert resp_paid.headers.get("X-PAYMENT-RESPONSE")

        # Verify facilitator was invoked
        assert facilitator.verify_calls
        assert facilitator.settle_calls

    @pytest.mark.asyncio
    async def test_valid_payment_calls_facilitator_verify(
        self,
        payment_app,
    ) -> None:
        """Verify payment flow calls facilitator verify.

        Given a valid payment,
        When processing the request,
        Then the facilitator's verify method should be called.
        """
        client, facilitator = payment_app

        resp_402 = await client.post("/hybrid/forecast")
        body = resp_402.json()
        payment_response = x402PaymentRequiredResponse(**body)

        account = Account.create()
        xclient = x402Client(account=account)
        header_value = xclient.create_payment_header(
            payment_requirements=payment_response.accepts[0],
            x402_version=payment_response.x402_version,
        )

        await client.post("/hybrid/forecast", headers={"X-PAYMENT": header_value})

        assert len(facilitator.verify_calls) == 1

    @pytest.mark.asyncio
    async def test_valid_payment_calls_facilitator_settle(
        self,
        payment_app,
    ) -> None:
        """Verify payment flow calls facilitator settle after verify.

        Given a valid and verified payment,
        When the request succeeds,
        Then the facilitator's settle method should be called.
        """
        client, facilitator = payment_app

        resp_402 = await client.post("/hybrid/forecast")
        body = resp_402.json()
        payment_response = x402PaymentRequiredResponse(**body)

        account = Account.create()
        xclient = x402Client(account=account)
        header_value = xclient.create_payment_header(
            payment_requirements=payment_response.accepts[0],
            x402_version=payment_response.x402_version,
        )

        await client.post("/hybrid/forecast", headers={"X-PAYMENT": header_value})

        assert len(facilitator.settle_calls) == 1


class TestX402NetworkMismatch:
    """Test suite for network mismatch scenarios."""

    @pytest.mark.asyncio
    async def test_payment_header_with_wrong_network_returns_no_matching(
        self,
        payment_app,
    ) -> None:
        """Verify wrong network in payment returns no matching.

        Given a payment with mismatched network,
        When processing the request,
        Then it should return 402 with no matching error.
        """
        client, _ = payment_app

        # Obtain real payment requirements via 402
        resp_402 = await client.post("/hybrid/forecast")
        assert resp_402.status_code == 402
        body = resp_402.json()

        # Build a valid header, then tamper with the network field
        payment_response = x402PaymentRequiredResponse(**body)
        account = Account.create()
        xclient = x402Client(account=account)
        selected_req = payment_response.accepts[0]
        header_value = xclient.create_payment_header(
            payment_requirements=selected_req,
            x402_version=payment_response.x402_version,
        )

        # Decode, modify network, and re-encode
        raw = json.loads(base64.b64decode(header_value).decode("utf-8"))
        raw["network"] = "base-sepolia"  # mismatch the configured "base"
        tampered_header = base64.b64encode(json.dumps(raw).encode("utf-8")).decode(
            "utf-8"
        )

        resp = await client.post(
            "/hybrid/forecast", headers={"X-PAYMENT": tampered_header}
        )
        assert resp.status_code == 402
        payload = resp.json()
        assert payload["error"] == "No matching payment requirements found"


class TestX402VerificationFailure:
    """Test suite for verification failure scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_payment_verification_returns_402(
        self, monkeypatch: pytest.MonkeyPatch, pricing: dict[str, list[PaymentOption]]
    ) -> None:
        """Verify failed verification returns 402.

        Given a payment that fails verification,
        When processing the request,
        Then it should return 402 with invalid payment error.
        """
        facilitator = DummyFacilitator()
        facilitator.verify_response = SimpleNamespace(
            is_valid=False, invalid_reason="Insufficient funds"
        )

        settings = SimpleNamespace(
            facilitator_config={"url": "https://facilitator"},
            payee_wallet_address="0xD23ef9BAf3A2A9a9feb8035e4b3Be41878faF515",
        )
        monkeypatch.setattr(
            "seller_template.middlewares.x402_wrapper.get_x402_settings",
            lambda: settings,
        )
        monkeypatch.setattr(
            "seller_template.middlewares.x402_wrapper.FacilitatorClient",
            lambda config: facilitator,
        )

        app = FastAPI()

        @app.post("/hybrid/forecast", operation_id="get_weather_forecast")
        async def forecast_endpoint():
            return {"ok": True}

        app.add_middleware(X402WrapperMiddleware, tool_pricing=pricing)

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            # Get payment requirements
            resp_402 = await client.post("/hybrid/forecast")
            body = resp_402.json()
            payment_response = x402PaymentRequiredResponse(**body)

            # Create valid payment header
            account = Account.create()
            xclient = x402Client(account=account)
            header_value = xclient.create_payment_header(
                payment_requirements=payment_response.accepts[0],
                x402_version=payment_response.x402_version,
            )

            # Should fail verification
            resp = await client.post(
                "/hybrid/forecast", headers={"X-PAYMENT": header_value}
            )
            assert resp.status_code == 402
            payload = resp.json()
            assert "Invalid payment" in payload["error"]
            assert "Insufficient funds" in payload["error"]


class TestX402FreeEndpoints:
    """Test suite for non-priced endpoints."""

    @pytest.mark.asyncio
    async def test_free_endpoint_does_not_require_payment(
        self,
        payment_app,
    ) -> None:
        """Verify non-priced endpoints work without payment.

        Given an endpoint without pricing configuration,
        When making a request without X-PAYMENT,
        Then it should succeed.
        """
        client, _ = payment_app
        response = await client.get("/api/free")
        assert response.status_code == 200
        payload = response.json()
        assert payload["free"] is True


class TestX402DisabledMiddleware:
    """Test suite for disabled middleware scenarios."""

    @pytest.mark.asyncio
    async def test_middleware_disabled_without_facilitator_config(
        self, monkeypatch: pytest.MonkeyPatch, pricing: dict[str, list[PaymentOption]]
    ) -> None:
        """Verify middleware passes through when facilitator not configured.

        Given no facilitator configuration,
        When making a request to a priced endpoint,
        Then it should succeed without payment.
        """
        settings = SimpleNamespace(
            facilitator_config=None,
            payee_wallet_address="0xD23ef9BAf3A2A9a9feb8035e4b3Be41878faF515",
        )
        monkeypatch.setattr(
            "seller_template.middlewares.x402_wrapper.get_x402_settings",
            lambda: settings,
        )

        app = FastAPI()

        @app.post("/hybrid/forecast", operation_id="get_weather_forecast")
        async def forecast_endpoint():
            return {"ok": True}

        app.add_middleware(X402WrapperMiddleware, tool_pricing=pricing)

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            response = await client.post("/hybrid/forecast")
            # Should pass through without requiring payment
            assert response.status_code == 200


class TestX402ResponseFormat:
    """Test suite for 402 response format validation."""

    @pytest.mark.asyncio
    async def test_402_response_is_valid_json(self, payment_app) -> None:
        """Verify 402 response is valid JSON.

        Given a priced endpoint without payment,
        When receiving 402 response,
        Then it should be valid JSON.
        """
        client, _ = payment_app
        response = await client.post("/hybrid/forecast")
        assert response.status_code == 402
        # Should not raise
        payload = response.json()
        assert isinstance(payload, dict)

    @pytest.mark.asyncio
    async def test_402_response_content_type(self, payment_app) -> None:
        """Verify 402 response has JSON content type.

        Given a priced endpoint without payment,
        When receiving 402 response,
        Then content-type should be application/json.
        """
        client, _ = payment_app
        response = await client.post("/hybrid/forecast")
        assert response.status_code == 402
        assert "application/json" in response.headers.get("content-type", "")
