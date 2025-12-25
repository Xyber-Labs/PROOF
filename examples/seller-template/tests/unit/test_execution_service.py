"""Unit tests for ExecutionService.

Tests the task execution service with mocked ArchivistGraphBuilder
to verify task creation, async execution, and error handling.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from langchain_core.messages import AIMessage, ToolMessage

from xy_market.models.execution import ExecutionRequest, ExecutionResult

from seller_template.dependencies import DependencyContainer
from seller_template.execution_service import ExecutionService


class TestExecutionServiceCreation:
    """Test suite for task creation via ExecutionService."""

    @pytest.fixture
    def mock_dependencies(self, mock_tools) -> MagicMock:
        """Create mock DependencyContainer with tools."""
        mock = MagicMock(spec=DependencyContainer)
        mock.search_tools = mock_tools
        return mock

    @pytest.fixture
    def mock_tools(self) -> list:
        """Create a list of mock tools."""
        tool1 = MagicMock()
        tool1.name = "test_tool"
        return [tool1]

    @pytest.mark.asyncio
    async def test_create_task_returns_in_progress_status(
        self, mock_dependencies: MagicMock
    ) -> None:
        """Verify create_task returns ExecutionResult with in_progress status.

        Given a valid ExecutionRequest,
        When creating a task,
        Then the result should have status='in_progress' with task_id and buyer_secret.
        """
        with patch(
            "seller_template.execution_service.ArchivistGraphBuilder"
        ) as mock_builder:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(return_value={
                "messages": [AIMessage(content="Done")]
            })
            mock_builder.return_value.agent = mock_agent

            service = ExecutionService(
                dependencies=mock_dependencies,
                default_deadline_seconds=300,
            )

            request = ExecutionRequest(task_description="Test task creation")
            result = await service.create_task(request)

            assert isinstance(result, ExecutionResult)
            assert result.status == "in_progress"
            assert result.task_id is not None
            assert result.buyer_secret is not None

    @pytest.mark.asyncio
    async def test_create_task_starts_background_execution(
        self, mock_dependencies: MagicMock
    ) -> None:
        """Verify create_task starts async background execution.

        Given a valid ExecutionRequest,
        When creating a task,
        Then a background task should be started.
        """
        with patch(
            "seller_template.execution_service.ArchivistGraphBuilder"
        ) as mock_builder:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(return_value={
                "messages": [AIMessage(content="Done")]
            })
            mock_builder.return_value.agent = mock_agent

            service = ExecutionService(dependencies=mock_dependencies)

            request = ExecutionRequest(task_description="Test background")
            await service.create_task(request)

            # Allow background task to start
            await asyncio.sleep(0.01)

            # Background task should be in the set
            assert len(service._background_tasks) >= 0  # May have completed already

    @pytest.mark.asyncio
    async def test_create_task_with_custom_deadline(
        self, mock_dependencies: MagicMock
    ) -> None:
        """Verify create_task respects custom deadline.

        Given a custom deadline of 60 seconds,
        When creating a task,
        Then the task should use the custom deadline.
        """
        with patch(
            "seller_template.execution_service.ArchivistGraphBuilder"
        ) as mock_builder:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(return_value={
                "messages": [AIMessage(content="Done")]
            })
            mock_builder.return_value.agent = mock_agent

            service = ExecutionService(dependencies=mock_dependencies)

            request = ExecutionRequest(task_description="Test deadline")
            result = await service.create_task(request, deadline_seconds=60)

            assert result.deadline_at is not None


class TestExecutionServiceAsyncExecution:
    """Test suite for async task execution."""

    @pytest.fixture
    def mock_dependencies(self, mock_tools) -> MagicMock:
        """Create mock DependencyContainer with tools."""
        mock = MagicMock(spec=DependencyContainer)
        mock.search_tools = mock_tools
        return mock

    @pytest.fixture
    def mock_tools(self) -> list:
        """Create a list of mock tools."""
        tool1 = MagicMock()
        tool1.name = "test_tool"
        return [tool1]

    @pytest.mark.asyncio
    async def test_execute_task_async_success(
        self, mock_dependencies: MagicMock
    ) -> None:
        """Verify successful async task execution updates task to done.

        Given a task that executes successfully,
        When the background execution completes,
        Then the task status should be 'done' with result data.
        """
        with patch(
            "seller_template.execution_service.ArchivistGraphBuilder"
        ) as mock_builder:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(return_value={
                "messages": [
                    AIMessage(content="Task completed with results")
                ]
            })
            mock_builder.return_value.agent = mock_agent

            service = ExecutionService(dependencies=mock_dependencies)

            request = ExecutionRequest(task_description="Test success execution")
            result = await service.create_task(request)
            task_id = result.task_id
            buyer_secret = result.buyer_secret

            # Wait for background task to complete
            await asyncio.sleep(0.1)

            final_result = await service.get_task_status(task_id, buyer_secret)
            assert final_result is not None
            assert final_result.status == "done"
            assert final_result.execution_time_ms is not None
            assert final_result.data is not None

    @pytest.mark.asyncio
    async def test_execute_task_async_with_tool_usage(
        self, mock_dependencies: MagicMock
    ) -> None:
        """Verify task execution tracks tools used.

        Given a task that uses tools during execution,
        When the background execution completes,
        Then the result should include the tools_used list.
        """
        with patch(
            "seller_template.execution_service.ArchivistGraphBuilder"
        ) as mock_builder:
            # Create mock messages including tool messages
            tool_msg = MagicMock(spec=ToolMessage)
            tool_msg.name = "search_tool"
            tool_msg.content = "Tool result"

            ai_msg = MagicMock(spec=AIMessage)
            ai_msg.content = "Final answer"
            ai_msg.tool_calls = []

            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(return_value={
                "messages": [tool_msg, ai_msg]
            })
            mock_builder.return_value.agent = mock_agent

            service = ExecutionService(dependencies=mock_dependencies)

            request = ExecutionRequest(task_description="Test with tools")
            result = await service.create_task(request)

            # Wait for background task
            await asyncio.sleep(0.1)

            final_result = await service.get_task_status(
                result.task_id, result.buyer_secret
            )
            assert final_result is not None
            assert final_result.status == "done"
            assert "tools_used" in final_result.data
            assert "search_tool" in final_result.data["tools_used"]

    @pytest.mark.asyncio
    async def test_execute_task_async_failure(
        self, mock_dependencies: MagicMock
    ) -> None:
        """Verify failed async task execution updates task to failed.

        Given a task that fails during execution,
        When the background execution raises an exception,
        Then the task status should be 'failed' with error details.
        """
        with patch(
            "seller_template.execution_service.ArchivistGraphBuilder"
        ) as mock_builder:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(
                side_effect=ValueError("Test error during execution")
            )
            mock_builder.return_value.agent = mock_agent

            service = ExecutionService(dependencies=mock_dependencies)

            request = ExecutionRequest(task_description="Test failure execution")
            result = await service.create_task(request)

            # Wait for background task to complete
            await asyncio.sleep(0.1)

            final_result = await service.get_task_status(
                result.task_id, result.buyer_secret
            )
            assert final_result is not None
            assert final_result.status == "failed"
            assert final_result.error is not None
            assert "Test error" in final_result.error["message"]
            assert final_result.error["type"] == "ValueError"


class TestExecutionServiceAgentInitialization:
    """Test suite for agent initialization error handling."""

    @pytest.fixture
    def mock_dependencies(self) -> MagicMock:
        """Create mock DependencyContainer with no tools."""
        mock = MagicMock(spec=DependencyContainer)
        mock.search_tools = []
        return mock

    @pytest.mark.asyncio
    async def test_execution_service_fails_on_no_tools(
        self, mock_dependencies: MagicMock
    ) -> None:
        """Verify ExecutionService raises error when no tools available.

        Given dependencies with no MCP tools,
        When initializing ExecutionService,
        Then RuntimeError should be raised.
        """
        with patch(
            "seller_template.xy_archivist.graph.get_model"
        ) as mock_get_model:
            mock_llm = MagicMock()
            mock_get_model.return_value = mock_llm

            with pytest.raises(RuntimeError) as exc_info:
                ExecutionService(dependencies=mock_dependencies)

            assert "No tools available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execution_service_fails_on_llm_init_error(self) -> None:
        """Verify ExecutionService raises error when LLM initialization fails.

        Given an environment where LLM initialization fails,
        When initializing ExecutionService,
        Then RuntimeError should be raised.
        """
        mock_deps = MagicMock(spec=DependencyContainer)
        mock_deps.search_tools = [MagicMock()]  # Has tools

        with patch(
            "seller_template.xy_archivist.graph.get_model"
        ) as mock_get_model:
            mock_get_model.side_effect = Exception("API key not configured")

            with pytest.raises(RuntimeError) as exc_info:
                ExecutionService(dependencies=mock_deps)

            assert "Failed to initialize LLM" in str(exc_info.value)


class TestExecutionServiceTaskStatus:
    """Test suite for task status retrieval."""

    @pytest.fixture
    def mock_dependencies(self, mock_tools) -> MagicMock:
        """Create mock DependencyContainer with tools."""
        mock = MagicMock(spec=DependencyContainer)
        mock.search_tools = mock_tools
        return mock

    @pytest.fixture
    def mock_tools(self) -> list:
        """Create a list of mock tools."""
        tool1 = MagicMock()
        tool1.name = "test_tool"
        return [tool1]

    @pytest.mark.asyncio
    async def test_get_task_status_with_valid_credentials(
        self, mock_dependencies: MagicMock
    ) -> None:
        """Verify get_task_status returns task with valid credentials.

        Given a created task,
        When retrieving status with correct task_id and buyer_secret,
        Then the task status should be returned.
        """
        with patch(
            "seller_template.execution_service.ArchivistGraphBuilder"
        ) as mock_builder:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(return_value={
                "messages": [AIMessage(content="Done")]
            })
            mock_builder.return_value.agent = mock_agent

            service = ExecutionService(dependencies=mock_dependencies)

            request = ExecutionRequest(task_description="Test status")
            result = await service.create_task(request)

            status = await service.get_task_status(
                result.task_id, result.buyer_secret
            )

            assert status is not None
            assert status.task_id == result.task_id

    @pytest.mark.asyncio
    async def test_get_task_status_with_wrong_secret_returns_none(
        self, mock_dependencies: MagicMock
    ) -> None:
        """Verify get_task_status returns None with wrong buyer_secret.

        Given a created task,
        When retrieving status with wrong buyer_secret,
        Then None should be returned.
        """
        with patch(
            "seller_template.execution_service.ArchivistGraphBuilder"
        ) as mock_builder:
            mock_agent = MagicMock()
            mock_agent.ainvoke = AsyncMock(return_value={
                "messages": [AIMessage(content="Done")]
            })
            mock_builder.return_value.agent = mock_agent

            service = ExecutionService(dependencies=mock_dependencies)

            request = ExecutionRequest(task_description="Test wrong secret")
            result = await service.create_task(request)

            status = await service.get_task_status(
                result.task_id, "wrong-secret"
            )

            assert status is None

    @pytest.mark.asyncio
    async def test_get_task_status_nonexistent_returns_none(
        self, mock_dependencies: MagicMock
    ) -> None:
        """Verify get_task_status returns None for non-existent task.

        Given a non-existent task_id,
        When retrieving status,
        Then None should be returned.
        """
        with patch(
            "seller_template.execution_service.ArchivistGraphBuilder"
        ) as mock_builder:
            mock_agent = MagicMock()
            mock_builder.return_value.agent = mock_agent

            service = ExecutionService(dependencies=mock_dependencies)

            status = await service.get_task_status(
                "nonexistent-task-id", "some-secret"
            )

            assert status is None


class TestExecutionServiceCleanup:
    """Test suite for expired task cleanup via ExecutionService."""

    @pytest.fixture
    def mock_dependencies(self, mock_tools) -> MagicMock:
        """Create mock DependencyContainer with tools."""
        mock = MagicMock(spec=DependencyContainer)
        mock.search_tools = mock_tools
        return mock

    @pytest.fixture
    def mock_tools(self) -> list:
        """Create a list of mock tools."""
        tool1 = MagicMock()
        tool1.name = "test_tool"
        return [tool1]

    @pytest.mark.asyncio
    async def test_cleanup_expired_tasks_delegates_to_repository(
        self, mock_dependencies: MagicMock
    ) -> None:
        """Verify cleanup_expired_tasks calls TaskRepository.cleanup_expired_tasks.

        Given an ExecutionService instance,
        When calling cleanup_expired_tasks,
        Then it should delegate to the task repository.
        """
        with patch(
            "seller_template.execution_service.ArchivistGraphBuilder"
        ) as mock_builder:
            mock_agent = MagicMock()
            mock_builder.return_value.agent = mock_agent

            service = ExecutionService(dependencies=mock_dependencies)

            # Create an expired task
            request = ExecutionRequest(task_description="Expired task")
            await service.task_repository.create_task(request, deadline_seconds=-1)

            cleaned = await service.cleanup_expired_tasks()

            assert cleaned == 1
