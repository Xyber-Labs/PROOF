"""Entry point for MarketplaceBK."""

import argparse
import logging

import uvicorn

from marketplace.config import get_settings

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Run MarketplaceBK - Agent Swarms Marketplace"
    )
    parser.add_argument(
        "--host", default=settings.marketplace_host, help="Host to bind to"
    )
    parser.add_argument(
        "--port", type=int, default=settings.marketplace_port, help="Port to listen on"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.marketplace_hot_reload,
        help="Enable hot reload",
    )
    args = parser.parse_args()

    logger.info(f"Starting MarketplaceBK on {args.host}:{args.port}")
    uvicorn.run(
        "marketplace.app:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=settings.logging_level.lower(),
        factory=True,
    )
