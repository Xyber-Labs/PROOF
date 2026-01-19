"""
This module will usually change as you decide which endpoints should be exposed both as REST routes and as MCP tools for your server.

Main responsibility: Collect hybrid (REST + MCP) FastAPI routers into a single list for inclusion in the main application.
"""

from fastapi import APIRouter

from .execute_router import router as execute_router
from .pricing import router as pricing_router
from .tasks_router import router as tasks_router

routers: list[APIRouter] = [execute_router, tasks_router, pricing_router]
