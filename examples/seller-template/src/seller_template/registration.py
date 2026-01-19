"""Marketplace registration service for auto-registering seller on startup."""

import asyncio
import logging

import httpx

from seller_template.config import MarketplaceRegistrationSettings

logger = logging.getLogger(__name__)


class RegistrationService:
    """Handles seller registration with marketplace."""

    def __init__(self, settings: MarketplaceRegistrationSettings):
        """
        Initialize registration service.

        Args:
            settings: Marketplace registration settings

        """
        self.settings = settings
        self._registered = False

    async def register(self) -> bool:
        """
        Register seller with marketplace.

        Returns:
            True if registration successful or already registered, False otherwise.

        """
        if not self.settings.enabled:
            logger.info("Marketplace registration disabled, skipping.")
            return True

        registration_data = {
            "agent_name": self.settings.agent_name,
            "base_url": self.settings.seller_base_url,
            "description": self.settings.description,
            "tags": self.settings.tags,
        }

        for attempt in range(1, self.settings.retry_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.settings.marketplace_base_url}/register",
                        json=registration_data,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        logger.info(
                            f"Successfully registered with marketplace: "
                            f"agent_id={data.get('agent_id')}"
                        )
                        self._registered = True
                        return True

                    elif response.status_code == 409:
                        # Already registered - this is fine
                        logger.info(
                            "Seller already registered with marketplace (409 Conflict)"
                        )
                        self._registered = True
                        return True

                    else:
                        logger.warning(
                            f"Registration attempt {attempt} failed: "
                            f"status={response.status_code}, body={response.text}"
                        )

            except httpx.RequestError as e:
                logger.warning(f"Registration attempt {attempt} failed with error: {e}")

            if attempt < self.settings.retry_attempts:
                await asyncio.sleep(self.settings.retry_delay_seconds)

        logger.error(
            f"Failed to register with marketplace after "
            f"{self.settings.retry_attempts} attempts"
        )
        return False

    @property
    def is_registered(self) -> bool:
        """Check if registration was successful."""
        return self._registered
