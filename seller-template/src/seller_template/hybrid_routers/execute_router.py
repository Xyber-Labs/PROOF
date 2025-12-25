import logging

from fastapi import APIRouter, HTTPException, Request, status

from xy_market.models.execution import ExecutionRequest

from seller_template.config import get_settings
from seller_template.execution_service import ExecutionService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/execute",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=None,
    operation_id="execute_task",
)
async def execute_task(
    request: Request,
    execution_request: ExecutionRequest,
):
    """Execute a task with async pattern and x402 payment flow."""
    settings = get_settings()
    execution_service: ExecutionService = request.app.state.execution_service

    try:
        result = await execution_service.create_task(
            execution_request=execution_request,
            deadline_seconds=settings.execution_timeout_seconds,
        )
        logger.info(f"Task created: task_id={result.task_id}, status={result.status}")
        return result
    except Exception as e:
        logger.error(f"Task creation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "EXECUTION_FAILED",
                "message": str(e),
            },
        ) from e
