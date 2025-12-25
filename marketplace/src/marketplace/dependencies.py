from fastapi import Request

from marketplace.agent_service import AgentService


def get_agent_service(request: Request) -> AgentService:
    """
    Dependency to get the AgentService instance.

    The AgentService is initialized in the app lifespan and stored in app.state,
    so that it's shared across all requests.
    """
    return request.app.state.agent_service
