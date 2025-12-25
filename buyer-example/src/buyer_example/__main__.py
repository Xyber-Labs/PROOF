import argparse
import logging

import uvicorn

from buyer_example.config import get_settings

logger = logging.getLogger(__name__)


# --- Uvicorn Runner ---
if __name__ == "__main__":
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run the Buyer Agent Example service.")
    parser.add_argument("--host", default=settings.host, help="Host to bind to.")
    parser.add_argument(
        "--port", type=int, default=settings.port, help="Port to listen on."
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable hot reload.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, settings.logging_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info(f"Starting Buyer Agent service on {args.host}:{args.port}")
    uvicorn.run(
        "buyer_example.app:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )
