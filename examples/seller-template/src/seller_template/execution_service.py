import asyncio
import logging
import time

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from xy_market.models.execution import ExecutionRequest, ExecutionResult

from seller_template.dependencies import DependencyContainer
from seller_template.task_repository import TaskRepository
from seller_template.xy_archivist.graph import ArchivistGraphBuilder

logger = logging.getLogger(__name__)


class ExecutionService:
    """Service for executing tasks using MCP servers with async pattern."""

    def __init__(
        self,
        dependencies: DependencyContainer,
        default_deadline_seconds: int = 300,
    ):
        """
        Initialize execution service.

        Args:
            dependencies: Dependency container with pre-loaded MCP tools
            default_deadline_seconds: Default deadline for tasks (default: 5 minutes)

        """
        self.dependencies = dependencies
        self.task_repository = TaskRepository(
            default_deadline_seconds=default_deadline_seconds
        )
        self._background_tasks: set[asyncio.Task] = set()

        # Initialize LangGraph
        self.archivist_agent = ArchivistGraphBuilder(dependencies=dependencies).agent

    async def create_task(
        self,
        execution_request: ExecutionRequest,
        deadline_seconds: int | None = None,
    ) -> ExecutionResult:
        """
        Create a task and start async execution.

        Args:
            execution_request: Execution request
            deadline_seconds: Optional deadline override

        Returns:
            Execution result with task_id, buyer_secret, status='in_progress'

        """
        # Create task in storage
        task_id, buyer_secret = await self.task_repository.create_task(
            execution_request, deadline_seconds
        )

        # Start background execution
        task = asyncio.create_task(self._execute_task_async(task_id, execution_request))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        # Return initial response
        task_result = await self.task_repository.get_task(task_id, buyer_secret)
        if not task_result:
            raise RuntimeError(f"Failed to create task: {task_id}")

        return task_result

    async def _execute_task_async(
        self,
        task_id: str,
        execution_request: ExecutionRequest,
    ) -> None:
        """
        Execute task asynchronously in background.

        Args:
            task_id: Task UUID
            execution_request: Execution request

        """
        start_time = time.time()

        try:
            if not self.archivist_agent:
                raise RuntimeError(
                    "Agent not initialized. This should not happen - agent initialization should fail on startup."
                )

            logger.info(f"Executing task {task_id} with LangGraph agent")

            # Import system prompt from graph module
            from seller_template.xy_archivist.graph import SYSTEM_PROMPT

            initial_state = {
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=execution_request.task_description),
                ]
            }
            final_state = await self.archivist_agent.ainvoke(initial_state)

            last_message = final_state["messages"][-1]
            content = last_message.content

            # Extract tool usage info for reporting
            tools_used = []
            for msg in final_state["messages"]:
                if isinstance(msg, ToolMessage):
                    tools_used.append(msg.name)

            # Format result as a dict that will be stored in Task.result
            # This will be converted to ExecutionResult.data in to_execution_result()
            result = {
                "status": "completed",
                "message": "Task executed by agent",
                "result": content,
                "tools_used": list(set(tools_used)),
            }

            execution_time_ms = int((time.time() - start_time) * 1000)

            # Update task with success
            await self.task_repository.update_task(
                task_id=task_id,
                status="done",
                result=result,
                execution_time_ms=execution_time_ms,
                tools_used=list(set(tools_used)),
            )

        except Exception as e:
            logger.error(f"Task execution failed: {e}", exc_info=True)
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Update task with failure
            await self.task_repository.update_task(
                task_id=task_id,
                status="failed",
                error={"message": str(e), "type": type(e).__name__},
                execution_time_ms=execution_time_ms,
            )

    async def get_task_status(
        self,
        task_id: str,
        buyer_secret: str,
    ) -> ExecutionResult | None:
        """
        Get task status for polling.

        Args:
            task_id: Task UUID
            buyer_secret: Buyer secret UUID

        Returns:
            Execution result or None if not found/invalid secret

        """
        return await self.task_repository.get_task(task_id, buyer_secret)

    async def cleanup_expired_tasks(self) -> int:
        """
        Clean up expired tasks.

        Returns:
            Number of tasks cleaned up

        """
        return await self.task_repository.cleanup_expired_tasks()
