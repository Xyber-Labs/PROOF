"""Main FastAPI application for MarketplaceBK."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from xy_market.logging_config import configure_logging
from xy_market.middleware.ratelimit import RateLimitMiddleware

from marketplace.agent_service import AgentService
from marketplace.repository import JsonAgentRepository
from marketplace.router import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's resources.

    Currently manages:
    - AgentService for agent registration and management
    - JsonAgentRepository for storing agent profiles
    """
    logger.info("Lifespan: Initializing MarketplaceBK services...")

    # Initialize repository
    agent_repository = JsonAgentRepository()

    # Initialize service
    agent_service = AgentService(agent_repository)
    app.state.agent_service = agent_service

    logger.info("Lifespan: Services initialized successfully.")
    yield
    logger.info("Lifespan: Shutting down MarketplaceBK services...")
    logger.info("Lifespan: Services shut down gracefully.")


def create_app() -> FastAPI:
    """
    Create and configure the main FastAPI application.

    This factory function:
    1. Creates FastAPI app with lifespan management
    2. Includes router for agent registration and polling endpoints
    3. Sets up health check endpoint

    Returns:
        Configured FastAPI application ready to serve requests

    """
    configure_logging()
    app = FastAPI(
        title="MarketplaceBK",
        description="Discovery and registry service for Agent Swarms - handles seller registration and provides agent listing endpoint",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Include router
    app.include_router(router)

    # Rate limiting
    limits = {
        "/register": 10,
    }
    app.add_middleware(RateLimitMiddleware, limits=limits, window_seconds=60)

    logger.info("MarketplaceBK application setup complete.")
    return app
