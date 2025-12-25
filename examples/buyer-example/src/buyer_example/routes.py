import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from buyer_example.services import BuyerAgentService

logger = logging.getLogger(__name__)

router = APIRouter()
buyer_service = BuyerAgentService()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    status: str
    response: str
    conversation: list[dict] | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the Buyer Agent to execute a task.
    
    The agent will:
    1. Search for relevant sellers
    2. Present sellers to you
    3. Execute task with selected seller
    4. Poll for completion
    5. Return the result
    """
    try:
        result = await buyer_service.process_user_request(request.message)
        return ChatResponse(
            status=result.get("status", "success"),
            response=result.get("response", "No response"),
            conversation=result.get("conversation"),
        )
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.on_event("shutdown")
async def shutdown_event():
    await buyer_service.close()

