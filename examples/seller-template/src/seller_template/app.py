"""
This module may change slightly as you adapt routing, metadata, and middleware to your own MCP server.

Main responsibility: Compose the FastAPI/MCP application and manage its lifecycle, including startup/shutdown, middleware, and router mounting.
"""

import asyncio
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager

import httpx
from eth_account import Account
from fastapi import FastAPI
from fastmcp import FastMCP
from x402.clients.httpx import x402HttpxClient
from xy_market.middleware.ratelimit import RateLimitMiddleware
from xy_market.vendor.mcp_client import (
    McpClient,
    McpClientConfig,
    get_mcp_client,
    get_mcp_client_config,
)

from seller_template.api_routers import routers as api_routers
from seller_template.config import (
    BuyerX402Settings,
    get_buyer_x402_settings,
    get_marketplace_registration_settings,
    get_settings,
    get_x402_settings,
)
from seller_template.dependencies import DependencyContainer
from seller_template.execution_service import ExecutionService
from seller_template.hybrid_routers import routers as hybrid_routers
from seller_template.mcp_routers import routers as mcp_routers
from seller_template.middlewares import X402WrapperMiddleware
from seller_template.registration import RegistrationService

logger = logging.getLogger(__name__)


def _configure_x402_client(
    buyer_x402_settings: BuyerX402Settings,
) -> (
    Callable[
        [dict[str, str] | None, httpx.Timeout | None, httpx.Auth | None],
        httpx.AsyncClient,
    ]
    | None
):
    """Configures and returns an httpx client factory for x402 payments."""
    if not buyer_x402_settings.wallet_private_key:
        return None

    try:
        account = Account.from_key(buyer_x402_settings.wallet_private_key)
        logger.info(f"Configured x402 buyer wallet: {account.address}")

        def client_factory(
            headers: dict[str, str] | None = None,
            timeout: httpx.Timeout | None = None,
            auth: httpx.Auth | None = None,
        ) -> httpx.AsyncClient:
            """Create x402HttpxClient instance for MCP connections."""
            return x402HttpxClient(
                account=account,
                headers=headers,
                timeout=timeout,
                auth=auth,
            )

        return client_factory
    except ImportError:
        logger.warning(
            "eth_account or x402 not installed, cannot configure x402 client"
        )
    except Exception as e:
        logger.error(f"Failed to configure x402 client: {e}")
    return None


def _configure_mcp_client(
    mcp_config: McpClientConfig,
    httpx_client_factory: (
        Callable[
            [dict[str, str] | None, httpx.Timeout | None, httpx.Auth | None],
            httpx.AsyncClient,
        ]
        | None
    ) = None,
) -> McpClient | None:
    """Configures and returns the MCP client."""
    if mcp_config.servers:
        mcp_client = get_mcp_client(
            mcp_config, httpx_client_factory=httpx_client_factory
        )
        logger.info(f"Initialized MCP client with {len(mcp_config.servers)} servers")
        return mcp_client
    else:
        logger.warning(
            "No MCP servers configured (MCP_SERVERS__* environment variables). Continuing without MCP support."
        )
        return None


# --- Lifespan Management ---
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Manages the application's resources.

    Currently manages:
    - MCP client for connecting to external MCP servers
    - Execution service for task execution
    - Task repository for task management

    Note: The x402 middleware manages its own HTTP client lifecycle using
    context managers, so no external resource management is needed.
    """
    logger.info("Lifespan: Initializing application services...")

    settings = get_settings()
    buyer_x402_settings = get_buyer_x402_settings()
    mcp_config = get_mcp_client_config()

    # Configure x402 client for buyer capabilities
    httpx_client_factory = _configure_x402_client(buyer_x402_settings)

    # Configure MCP client for connecting to external MCP servers
    mcp_client = _configure_mcp_client(mcp_config, httpx_client_factory)

    # Initialize dependencies
    dependencies = await DependencyContainer.create(mcp_client)

    # Initialize execution service
    execution_service = ExecutionService(
        dependencies=dependencies,
        default_deadline_seconds=settings.execution_timeout_seconds,
    )

    # Store in app state
    app.state.dependencies = dependencies
    app.state.execution_service = execution_service

    # Auto-register with marketplace
    registration_settings = get_marketplace_registration_settings()
    registration_service = RegistrationService(registration_settings)
    registration_success = await registration_service.register()

    if not registration_success and registration_settings.enabled:
        logger.warning(
            "Failed to register with marketplace. "
            "Seller will continue running but may not be discoverable."
        )

    # Start background task cleanup (runs every 10 minutes)
    async def cleanup_loop():
        while True:
            try:
                await asyncio.sleep(600)  # Run every 10 minutes
                cleaned = await execution_service.cleanup_expired_tasks()
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} expired tasks")
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)

    cleanup_task = asyncio.create_task(cleanup_loop())

    logger.info("Lifespan: Services initialized successfully.")
    yield
    logger.info("Lifespan: Shutting down application services...")

    # Cancel cleanup task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    logger.info("Lifespan: Services shut down gracefully.")


# --- Application Factory ---
def create_app() -> FastAPI:
    """
    Create and configure the main FastAPI application.

    This factory function:
    1. Creates an MCP server from hybrid and MCP-only routers
    2. Combines lifespans for proper resource management
    3. Configures API routes with appropriate prefixes
    4. Sets up x402 payment middleware
    5. Validates pricing configuration against available routes

    Returns:
        Configured FastAPI application ready to serve requests

    """
    # --- MCP Server Generation ---
    # Create a FastAPI app containing only MCP-exposed endpoints
    mcp_source_app = FastAPI(title="MCP Source")
    for router in hybrid_routers:
        mcp_source_app.include_router(router)
    for router in mcp_routers:
        mcp_source_app.include_router(router)

    # Convert to MCP server
    mcp_server = FastMCP.from_fastapi(app=mcp_source_app, name="MCP")
    mcp_app = mcp_server.http_app(path="/")

    # --- Combined Lifespan ---
    # This correctly manages both our app's resources and FastMCP's internal state.
    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        async with app_lifespan(app):
            async with mcp_app.lifespan(app):
                yield

    # --- Main Application ---
    app = FastAPI(
        title="Seller Template (Hybrid)",
        description="A seller server with REST, MCP, and x402 payment capabilities.",
        version="2.0.0",
        lifespan=combined_lifespan,
    )

    # --- Router Configuration ---
    # API-only routes: accessible via /api/* (REST only)
    for router in api_routers:
        app.include_router(router, prefix="/api")

    # Hybrid routes: accessible via /hybrid/* (REST) and /mcp (MCP)
    for router in hybrid_routers:
        app.include_router(router, prefix="/hybrid")

    # MCP-only routes: NOT mounted as REST endpoints
    # They're only accessible through the /mcp endpoint below

    # Mount the MCP server at /mcp
    app.mount("/mcp", mcp_app)

    # --- Pricing Configuration Validation ---
    # This validates that all priced endpoints actually exist
    # and warns about any misconfiguration
    all_routes = app.routes + mcp_source_app.routes
    x402_settings = get_x402_settings()
    x402_settings.validate_against_routes(all_routes)

    # --- Middleware Configuration ---
    # Rate limiting (applied first, so it runs before payment validation)
    limits = {
        "/hybrid/execute": 100,  # 100 requests/min for execute
        r"^/hybrid/tasks/.*": 30,  # 30 requests/min for task polling
        "/api/admin": 20,  # 20 requests/min for admin endpoints
    }
    app.add_middleware(RateLimitMiddleware, limits=limits, window_seconds=60)
    logger.info("Rate limiting middleware enabled.")

    # x402 payment middleware
    if x402_settings.pricing_mode == "on":
        app.add_middleware(X402WrapperMiddleware, tool_pricing=x402_settings.pricing)
        logger.info("x402 payment middleware enabled.")
    else:
        logger.info("x402 payment middleware disabled (pricing_mode='off').")

    logger.info("Application setup complete.")
    return app
