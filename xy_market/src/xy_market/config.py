from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from cdp.x402 import create_facilitator_config
from pydantic import BaseModel, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from x402.facilitator import FacilitatorConfig

logger = __import__("logging").getLogger(__name__)


class PaymentOption(BaseModel):
    """Defines a single pricing option for x402-protected endpoints."""

    chain_id: int
    token_address: str
    token_amount: int = Field(ge=0)


class SellerX402Config(BaseSettings):
    """Configuration for sellers using x402 payment protocol.
    
    Sellers need facilitator configuration to verify payments from buyers.
    This config is used when an agent acts as a seller (receiving payments).
    """

    model_config = SettingsConfigDict(
        env_prefix="SELLER_X402_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    pricing_mode: Literal["off", "on"] = "on"
    payee_wallet_address: str | None = None
    facilitator_url: str | None = None
    cdp_api_key_id: str | None = None
    cdp_api_key_secret: str | None = None

    pricing_config_path: Path = Path("tool_pricing.yaml")

    @computed_field
    @property
    def facilitator_config(self) -> FacilitatorConfig | None:
        if self.cdp_api_key_id and self.cdp_api_key_secret:
            logger.info("CDP API keys found, configuring for mainnet facilitator.")
            return create_facilitator_config(
                api_key_id=self.cdp_api_key_id,
                api_key_secret=self.cdp_api_key_secret,
            )
        if self.facilitator_url:
            logger.info(f"Using public facilitator at {self.facilitator_url}")
            return {"url": self.facilitator_url}
        return None

    @computed_field
    @property
    def pricing(self) -> dict[str, list[PaymentOption]]:
        if not self.pricing_config_path.is_file():
            logger.warning(
                f"Pricing config file not found at '{self.pricing_config_path}'. No endpoints will be monetized."
            )
            return {}

        try:
            with open(self.pricing_config_path) as f:
                pricing_data = yaml.safe_load(f)
                if not pricing_data:
                    return {}
                validated = {
                    op_id: [PaymentOption(**opt) for opt in opts]
                    for op_id, opts in pricing_data.items()
                }
                logger.info(f"Loaded pricing for {len(validated)} tools.")
                return validated
        except (yaml.YAMLError, TypeError, ValueError) as exc:
            logger.error(f"Failed to parse pricing config '{self.pricing_config_path}': {exc}")
            return {}


class BuyerX402Config(BaseSettings):
    """Configuration for buyers using x402 payment protocol.
    
    Buyers need a wallet private key to make payments to sellers or MCP servers.
    This config is used when an agent acts as a buyer (e.g., Seller agents paying for MCP tools).
    
    Note: Facilitator configuration is only needed by sellers (for payment verification).
    Buyers only need their wallet private key to sign and send payments.
    """

    model_config = SettingsConfigDict(
        env_prefix="BUYER_X402_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    wallet_private_key: str | None = None
    """Private key for the buyer's wallet (used to create eth_account.Account for payments)."""


class AppSettings(BaseSettings):
    """Application settings shared by XY Market services."""

    model_config = SettingsConfigDict(
        env_prefix="XY_MARKET_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


@lru_cache()
def get_app_settings() -> AppSettings:
    return AppSettings()


@lru_cache(maxsize=1)
def get_seller_x402_settings() -> SellerX402Config:
    """Get seller x402 settings for payment verification."""
    return SellerX402Config()


@lru_cache(maxsize=1)
def get_buyer_x402_settings() -> BuyerX402Config:
    """Get buyer x402 settings for making payments."""
    return BuyerX402Config()


