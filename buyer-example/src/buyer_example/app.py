import logging
from fastapi import FastAPI

from buyer_example.routes import router
from xy_market.logging_config import configure_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.
    
    This factory function:
    1. Creates FastAPI app
    2. Includes router for chat endpoint
    
    Returns:
        Configured FastAPI application ready to serve requests
    """
    configure_logging()
    app = FastAPI(
        title="Buyer Agent Example",
        description="LangGraph-based Buyer Agent with Google LLM integration",
        version="0.1.0",
    )
    app.include_router(router)
    
    logger.info("Buyer Agent application setup complete.")
    return app

