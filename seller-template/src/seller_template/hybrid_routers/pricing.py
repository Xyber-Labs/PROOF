import logging

from fastapi import APIRouter, status
import yaml

from seller_template.config import get_x402_settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/pricing", status_code=status.HTTP_200_OK)
async def get_pricing() -> dict:
    """Get tool pricing configuration."""
    settings = get_x402_settings()
    try:
        if not settings.pricing_config_path.exists():
            return {"error": "Pricing configuration not found", "pricing": {}}
            
        with open(settings.pricing_config_path, "r") as f:
            pricing_data = yaml.safe_load(f) or {}
            
        return {"pricing": pricing_data}
    except Exception as e:
        logger.error(f"Error reading pricing config: {e}")
        return {"error": "Failed to load pricing configuration", "pricing": {}}
