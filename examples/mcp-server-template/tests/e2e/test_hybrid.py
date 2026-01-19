from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from eth_account import Account
from x402.clients.httpx import x402HttpxClient

from tests.e2e.config import (
    load_e2e_config,
    require_base_url,
    require_wallet,
    require_weather_api_key,
)

API_KEY_HEADER = "Weather-Api-Key"


@pytest_asyncio.fixture
async def hybrid_rest_client():
    config = load_e2e_config()
    require_base_url(config)
    async with httpx.AsyncClient(
        base_url=config.base_url,
        timeout=config.timeout_seconds,
    ) as client:
        yield config, client


@pytest_asyncio.fixture
async def hybrid_paid_client():
    config = load_e2e_config()
    require_base_url(config)
    require_wallet(config)
    account = Account.from_key(config.private_key)  # type: ignore[arg-type]
    async with x402HttpxClient(
        account=account,
        base_url=config.base_url,
        timeout=config.timeout_seconds,
        follow_redirects=True,
        trust_env=False,
    ) as client:
        yield config, client


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_hybrid_current_via_rest(hybrid_rest_client) -> None:
    config, client = hybrid_rest_client
    payload = {"latitude": "51.5074", "longitude": "-0.1278"}
    api_key = require_weather_api_key(config)
    response = await client.post(
        "/hybrid/current",
        json=payload,
        headers={API_KEY_HEADER: api_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert "state" in body and "temperature" in body and "humidity" in body


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_hybrid_current_via_rest_missing_header_falls_back_to_config(hybrid_rest_client):
    """Test that missing header falls back to WEATHER_API_KEY config if available."""
    config, client = hybrid_rest_client
    payload = {"latitude": "51.5074", "longitude": "-0.1278"}
    response = await client.post(
        "/hybrid/current",
        json=payload,
    )
    # If server has WEATHER_API_KEY configured, should work (200)
    # If not, should fail with 503
    if response.status_code == 200:
        body = response.json()
        assert "state" in body and "temperature" in body and "humidity" in body
    else:
        # Server doesn't have config key, so should get 503
        assert response.status_code == 503
        body = response.json()
        assert "not configured" in body.get("detail", "").lower() or "api key" in body.get("detail", "").lower()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_hybrid_forecast_requires_payment(hybrid_rest_client) -> None:
    config, client = hybrid_rest_client
    response = await client.post("/hybrid/forecast", params={"days": 5})
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_hybrid_forecast_succeeds_with_x402(hybrid_paid_client) -> None:
    config, client = hybrid_paid_client
    response = await client.post("/hybrid/forecast", params={"days": 5})
    if response.status_code == 402:
        pytest.skip(
            "Hybrid forecast is priced but payment flow is not yet fully configured in this environment."
        )
    response.raise_for_status()
    body = response.json()
    assert body.get("days") == 5
    assert isinstance(body.get("forecast"), list)
