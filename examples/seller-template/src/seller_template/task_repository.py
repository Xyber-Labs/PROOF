import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from xy_market.models.execution import ExecutionRequest, ExecutionResult

from seller_template.db.database import get_database
from seller_template.db.models import Task

logger = __import__("logging").getLogger(__name__)


class TaskRepository:
    """In-memory storage for tracking async task execution."""

    def __init__(self, default_deadline_seconds: int = 300):
        """
        Initialize task storage.

        Args:
            default_deadline_seconds: Default deadline for tasks (default: 5 minutes)

        """
        self._tasks: dict[str, Task] = get_database()["tasks"]
        self._lock = asyncio.Lock()
        self.default_deadline_seconds = default_deadline_seconds

    async def create_task(
        self,
        execution_request: ExecutionRequest,
        deadline_seconds: int | None = None,
    ) -> tuple[str, str]:
        """
        Create a new task and return task_id and buyer_secret.

        Args:
            execution_request: Execution request
            deadline_seconds: Optional deadline override

        Returns:
            Tuple of (task_id, buyer_secret)

        """
        deadline = deadline_seconds or self.default_deadline_seconds

        created_at = datetime.now(UTC)
        expires_at = created_at + timedelta(seconds=deadline)

        task = Task(
            execution_request=execution_request,
            expires_at=expires_at,
        )

        async with self._lock:
            self._tasks[task.task_id] = task

        logger.info(
            f"Created task: task_id={task.task_id}, expires_at={expires_at.isoformat()}"
        )
        return task.task_id, task.buyer_secret

    async def get_task(self, task_id: str, buyer_secret: str) -> ExecutionResult | None:
        """
        Get task by ID and validate buyer_secret.

        Args:
            task_id: Task UUID
            buyer_secret: Buyer secret UUID

        Returns:
            Execution result or None if not found/invalid secret

        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if task and task.buyer_secret == buyer_secret:
                return task.to_execution_result()
            return None

    async def update_task(
        self,
        task_id: str,
        status: str,
        result: Any | None = None,
        error: dict[str, Any] | None = None,
        execution_time_ms: int | None = None,
        tools_used: list[str] | None = None,
    ) -> None:
        """
        Update task status and result.

        Args:
            task_id: Task UUID
            status: New status ('in_progress', 'done', 'failed')
            result: Result data (if status='done')
            error: Error details (if status='failed')
            execution_time_ms: Execution time in milliseconds
            tools_used: List of tools used

        """
        async with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.status = status
                task.result = result
                task.error = error
                task.execution_time_ms = execution_time_ms
                task.tools_used = tools_used or []
                logger.info(f"Updated task {task_id}: status={status}")

    async def cleanup_expired_tasks(self) -> int:
        """
        Clean up expired tasks (past deadline).

        Returns:
            Number of tasks cleaned up

        """
        now = datetime.now(UTC)
        cleaned_count = 0

        async with self._lock:
            for task_id, task in list(
                self._tasks.items()
            ):  # Use list to allow modification during iteration
                if task.expires_at and task.status == "in_progress":
                    if now >= task.expires_at:
                        task.status = "failed"
                        task.error = {
                            "message": "Task deadline exceeded",
                            "type": "DeadlineExceeded",
                        }
                        cleaned_count += 1
                        logger.info(
                            f"Marked task {task_id} as failed due to deadline expiration"
                        )
        return cleaned_count
