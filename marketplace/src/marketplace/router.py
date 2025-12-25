from fastapi import APIRouter, Depends, HTTPException, status
from xy_market.errors.exceptions import (
    AgentAlreadyRegisteredError,
    AgentNotFoundError,
    RateLimitError,
)
from xy_market.models.agent import (
    AgentProfile,
    AgentRegistrationRequest,
    RegistrationResponse,
)

from marketplace.agent_service import AgentService
from marketplace.dependencies import get_agent_service

router = APIRouter(prefix="/register", tags=["agents"])


@router.post("", response_model=RegistrationResponse, status_code=status.HTTP_200_OK)
async def register_agent(
    request: AgentRegistrationRequest,
    agent_service: AgentService = Depends(get_agent_service),
) -> RegistrationResponse:
    """
    Register agent with MarketplaceBK.

    Per SRS 3.1: Sellers register with MarketplaceBK via this endpoint.
    Returns 409 Conflict if seller is already registered (by UUID, name, or base_url).
    """
    try:
        response = await agent_service.register_agent(request)
        return response
    except AgentAlreadyRegisteredError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "AGENT_ALREADY_REGISTERED", "message": str(e)},
        )
    except AgentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "AGENT_NOT_FOUND", "message": str(e)},
        )
    except RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error_code": "RATE_LIMIT_EXCEEDED", "message": str(e)},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_REQUEST", "message": str(e)},
        )


@router.get("/new_entries", status_code=status.HTTP_200_OK)
async def get_new_entries(
    agent_service: AgentService = Depends(get_agent_service),
    limit: int = 100,
    offset: int = 0,
) -> list[AgentProfile]:
    """
    Get registered agent entries.

    Returns list of agent profiles for buyers to discover available sellers.

    Args:
        limit: Maximum number of entries to return (default: 100)
        offset: Offset for pagination (default: 0)

    Returns:
        List of seller profiles

    """
    try:
        agents = await agent_service.list_agents(limit=limit, offset=offset)
        return agents
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "message": str(e)},
        )
