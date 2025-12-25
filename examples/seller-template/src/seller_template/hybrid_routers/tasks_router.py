import logging

from fastapi import APIRouter, Header, HTTPException, Request, status

from xy_market.models.execution import ExecutionResult

from seller_template.execution_service import ExecutionService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/tasks/{task_id}", status_code=status.HTTP_200_OK)
async def get_task_status(
    task_id: str,
    request: Request,
    x_buyer_secret: str = Header(..., alias="X-Buyer-Secret", description="Buyer secret for task access"),
) -> ExecutionResult:
    """Poll task status using task_id and buyer_secret."""
    execution_service: ExecutionService = request.app.state.execution_service

    try:
        result = await execution_service.get_task_status(task_id, x_buyer_secret)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "TASK_NOT_FOUND",
                    "message": f"Task not found or invalid secret: {task_id}",
                },
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": str(e),
            },
        ) from e
