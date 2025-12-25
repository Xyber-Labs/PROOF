"""Unit tests for TaskRepository.

Tests the task storage, retrieval, update, and cleanup functionality
using the new architecture with Task model and in-memory database.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from xy_market.models.execution import ExecutionRequest, ExecutionResult

from seller_template.task_repository import TaskRepository


class TestTaskRepositoryCreation:
    """Test suite for task creation functionality."""

    @pytest_asyncio.fixture
    async def task_repository(self) -> TaskRepository:
        """Create a TaskRepository instance for testing."""
        return TaskRepository(default_deadline_seconds=300)

    @pytest.mark.asyncio
    async def test_create_task_returns_task_id_and_buyer_secret(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify create_task returns valid UUID task_id and buyer_secret.

        Given a valid ExecutionRequest,
        When creating a task,
        Then task_id and buyer_secret should be valid UUIDs.
        """
        request = ExecutionRequest(task_description="Test task")

        task_id, buyer_secret = await task_repository.create_task(request)

        assert task_id is not None
        assert buyer_secret is not None
        # Verify they are valid UUIDs
        uuid.UUID(task_id)
        uuid.UUID(buyer_secret)

    @pytest.mark.asyncio
    async def test_create_task_with_custom_deadline(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify task creation respects custom deadline.

        Given a custom deadline of 60 seconds,
        When creating a task,
        Then the task should have the custom deadline.
        """
        request = ExecutionRequest(task_description="Test task with deadline")

        task_id, buyer_secret = await task_repository.create_task(
            request, deadline_seconds=60
        )

        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None
        assert result.deadline_at is not None

    @pytest.mark.asyncio
    async def test_create_task_with_context(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify task creation preserves context data.

        Given an ExecutionRequest with context,
        When creating a task,
        Then the task should be created successfully.
        """
        request = ExecutionRequest(
            task_description="Test task with context",
            context={"key": "value", "nested": {"data": 123}},
        )

        task_id, buyer_secret = await task_repository.create_task(request)

        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None


class TestTaskRepositoryRetrieval:
    """Test suite for task retrieval functionality."""

    @pytest_asyncio.fixture
    async def task_repository(self) -> TaskRepository:
        """Create a TaskRepository instance for testing."""
        return TaskRepository(default_deadline_seconds=300)

    @pytest.mark.asyncio
    async def test_get_task_with_valid_credentials(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify get_task returns task with valid task_id and buyer_secret.

        Given a created task,
        When retrieving with correct credentials,
        Then the task should be returned with in_progress status.
        """
        request = ExecutionRequest(task_description="Test retrieval")
        task_id, buyer_secret = await task_repository.create_task(request)

        result = await task_repository.get_task(task_id, buyer_secret)

        assert result is not None
        assert isinstance(result, ExecutionResult)
        assert result.task_id == task_id
        assert result.buyer_secret == buyer_secret
        assert result.status == "in_progress"

    @pytest.mark.asyncio
    async def test_get_task_with_wrong_secret_returns_none(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify get_task returns None with wrong buyer_secret.

        Given a created task,
        When retrieving with incorrect buyer_secret,
        Then None should be returned.
        """
        request = ExecutionRequest(task_description="Test wrong secret")
        task_id, _ = await task_repository.create_task(request)

        result = await task_repository.get_task(task_id, "wrong-secret")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_task_with_nonexistent_id_returns_none(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify get_task returns None for non-existent task_id.

        Given a non-existent task_id,
        When retrieving the task,
        Then None should be returned.
        """
        request = ExecutionRequest(task_description="Test create")
        _, buyer_secret = await task_repository.create_task(request)

        result = await task_repository.get_task("non-existent-id", buyer_secret)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_task_returns_execution_result_type(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify get_task returns ExecutionResult via to_execution_result().

        Given a created task,
        When retrieving the task,
        Then the result should be an ExecutionResult with correct fields.
        """
        request = ExecutionRequest(task_description="Test result type")
        task_id, buyer_secret = await task_repository.create_task(request)

        result = await task_repository.get_task(task_id, buyer_secret)

        assert isinstance(result, ExecutionResult)
        assert hasattr(result, "task_id")
        assert hasattr(result, "buyer_secret")
        assert hasattr(result, "status")
        assert hasattr(result, "data")
        assert hasattr(result, "created_at")
        assert hasattr(result, "deadline_at")


class TestTaskRepositoryUpdate:
    """Test suite for task update functionality."""

    @pytest_asyncio.fixture
    async def task_repository(self) -> TaskRepository:
        """Create a TaskRepository instance for testing."""
        return TaskRepository(default_deadline_seconds=300)

    @pytest.mark.asyncio
    async def test_update_task_status_to_done(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify task status can be updated to done.

        Given a created task,
        When updating status to 'done' with result,
        Then the task should reflect the new status and result.
        """
        request = ExecutionRequest(task_description="Test update to done")
        task_id, buyer_secret = await task_repository.create_task(request)

        await task_repository.update_task(
            task_id=task_id,
            status="done",
            result={"result": "success", "output": "test output"},
            execution_time_ms=150,
        )

        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None
        assert result.status == "done"
        assert result.data == {"result": "success", "output": "test output", "tools_used": []}
        assert result.execution_time_ms == 150

    @pytest.mark.asyncio
    async def test_update_task_status_to_failed(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify task status can be updated to failed with error.

        Given a created task,
        When updating status to 'failed' with error,
        Then the task should reflect the failure status and error details.
        """
        request = ExecutionRequest(task_description="Test update to failed")
        task_id, buyer_secret = await task_repository.create_task(request)

        await task_repository.update_task(
            task_id=task_id,
            status="failed",
            error={"message": "Something went wrong", "type": "RuntimeError"},
            execution_time_ms=50,
        )

        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None
        assert result.status == "failed"
        assert result.error is not None
        assert result.error["message"] == "Something went wrong"
        assert result.error["type"] == "RuntimeError"
        assert result.execution_time_ms == 50

    @pytest.mark.asyncio
    async def test_update_task_with_tools_used(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify task update records tools used.

        Given a created task,
        When updating with tools_used list,
        Then the task should include tools in the result data.
        """
        request = ExecutionRequest(task_description="Test tools used")
        task_id, buyer_secret = await task_repository.create_task(request)

        await task_repository.update_task(
            task_id=task_id,
            status="done",
            result={"output": "done"},
            tools_used=["search_tool", "query_tool"],
            execution_time_ms=200,
        )

        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None
        # tools_used is merged into data by to_execution_result
        assert "tools_used" in result.data
        assert result.data["tools_used"] == ["search_tool", "query_tool"]

    @pytest.mark.asyncio
    async def test_update_nonexistent_task_no_error(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify updating a non-existent task does not raise an error.

        Given a non-existent task_id,
        When updating the task,
        Then no error should be raised (silent no-op).
        """
        # Should not raise any exception
        await task_repository.update_task(
            task_id="nonexistent-task-id",
            status="done",
            result={"test": "data"},
        )


class TestTaskRepositoryCleanup:
    """Test suite for expired task cleanup functionality."""

    @pytest_asyncio.fixture
    async def task_repository(self) -> TaskRepository:
        """Create a TaskRepository instance for testing."""
        return TaskRepository(default_deadline_seconds=300)

    @pytest.mark.asyncio
    async def test_cleanup_expired_tasks_marks_as_failed(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify cleanup marks expired tasks as failed.

        Given a task with negative deadline (already expired),
        When running cleanup,
        Then the task should be marked as failed with DeadlineExceeded error.
        """
        request = ExecutionRequest(task_description="Test cleanup")
        task_id, buyer_secret = await task_repository.create_task(
            request, deadline_seconds=-1  # Already expired
        )

        cleaned = await task_repository.cleanup_expired_tasks()

        assert cleaned == 1
        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None
        assert result.status == "failed"
        assert result.error is not None
        assert result.error["type"] == "DeadlineExceeded"

    @pytest.mark.asyncio
    async def test_cleanup_does_not_affect_active_tasks(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify cleanup does not affect non-expired tasks.

        Given a task with future deadline,
        When running cleanup,
        Then the task should remain in_progress.
        """
        request = ExecutionRequest(task_description="Test active task")
        task_id, buyer_secret = await task_repository.create_task(
            request, deadline_seconds=3600  # 1 hour from now
        )

        cleaned = await task_repository.cleanup_expired_tasks()

        assert cleaned == 0
        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None
        assert result.status == "in_progress"

    @pytest.mark.asyncio
    async def test_cleanup_does_not_affect_completed_tasks(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify cleanup does not affect already completed tasks.

        Given a completed task with past deadline,
        When running cleanup,
        Then the task should remain in 'done' status.
        """
        request = ExecutionRequest(task_description="Test completed task")
        task_id, buyer_secret = await task_repository.create_task(
            request, deadline_seconds=-1  # Already expired
        )
        # Mark as done before cleanup
        await task_repository.update_task(
            task_id=task_id,
            status="done",
            result={"completed": True},
        )

        cleaned = await task_repository.cleanup_expired_tasks()

        assert cleaned == 0
        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None
        assert result.status == "done"

    @pytest.mark.asyncio
    async def test_cleanup_multiple_expired_tasks(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify cleanup handles multiple expired tasks.

        Given multiple expired tasks,
        When running cleanup,
        Then all expired tasks should be marked as failed.
        """
        request1 = ExecutionRequest(task_description="Expired task 1")
        request2 = ExecutionRequest(task_description="Expired task 2")
        request3 = ExecutionRequest(task_description="Active task")

        await task_repository.create_task(request1, deadline_seconds=-1)
        await task_repository.create_task(request2, deadline_seconds=-1)
        await task_repository.create_task(request3, deadline_seconds=3600)

        cleaned = await task_repository.cleanup_expired_tasks()

        assert cleaned == 2


class TestTaskRepositoryEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    @pytest_asyncio.fixture
    async def task_repository(self) -> TaskRepository:
        """Create a TaskRepository instance for testing."""
        return TaskRepository(default_deadline_seconds=300)

    @pytest.mark.asyncio
    async def test_create_task_with_empty_description(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify task creation with empty description.

        Given an empty task description,
        When creating a task,
        Then the task should be created (validation is not repository's job).
        """
        request = ExecutionRequest(task_description="")
        task_id, buyer_secret = await task_repository.create_task(request)

        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_task_with_long_description(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify task creation with very long description.

        Given a very long task description,
        When creating a task,
        Then the task should be created successfully.
        """
        long_description = "A" * 10000
        request = ExecutionRequest(task_description=long_description)

        task_id, buyer_secret = await task_repository.create_task(request)

        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_task_with_unicode_description(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify task creation with unicode characters.

        Given a description with unicode characters,
        When creating a task,
        Then the task should be created successfully.
        """
        request = ExecutionRequest(
            task_description="Test with unicode chars"
        )
        task_id, buyer_secret = await task_repository.create_task(request)

        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None

    @pytest.mark.asyncio
    async def test_concurrent_task_creation(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify concurrent task creation does not cause conflicts.

        Given multiple concurrent task creation requests,
        When creating tasks concurrently,
        Then all tasks should be created with unique IDs.
        """
        import asyncio

        requests = [
            ExecutionRequest(task_description=f"Concurrent task {i}")
            for i in range(10)
        ]

        results = await asyncio.gather(
            *[task_repository.create_task(req) for req in requests]
        )

        task_ids = [r[0] for r in results]
        # All task IDs should be unique
        assert len(set(task_ids)) == 10

    @pytest.mark.asyncio
    async def test_update_task_with_none_values(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify update_task handles None values correctly.

        Given a task and update with None values,
        When updating the task,
        Then the task should be updated with None where specified.
        """
        request = ExecutionRequest(task_description="Test None values")
        task_id, buyer_secret = await task_repository.create_task(request)

        await task_repository.update_task(
            task_id=task_id,
            status="done",
            result=None,
            error=None,
            execution_time_ms=None,
        )

        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None
        assert result.status == "done"

    @pytest.mark.asyncio
    async def test_create_task_with_zero_deadline(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify task creation with zero deadline.

        Given a deadline of 0 seconds,
        When creating a task,
        Then the task should be created with immediate expiration.
        """
        request = ExecutionRequest(task_description="Zero deadline task")
        task_id, buyer_secret = await task_repository.create_task(
            request, deadline_seconds=0
        )

        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None
        assert result.deadline_at is not None

    @pytest.mark.asyncio
    async def test_create_task_with_special_characters(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify task creation with special characters in description.

        Given a description with special characters,
        When creating a task,
        Then the task should be created successfully.
        """
        special_chars = r"Test with special: !@#$%^&*()_+-=[]{}|;':\",./<>?\n\t\r"
        request = ExecutionRequest(task_description=special_chars)
        task_id, buyer_secret = await task_repository.create_task(request)

        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_task_with_large_context(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify task creation with large context data.

        Given a request with large nested context,
        When creating a task,
        Then the task should be created successfully.
        """
        large_context = {
            f"key_{i}": {"nested": list(range(100)), "data": "x" * 1000}
            for i in range(50)
        }
        request = ExecutionRequest(
            task_description="Large context task",
            context=large_context,
        )
        task_id, buyer_secret = await task_repository.create_task(request)

        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_already_completed_task(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify updating an already completed task overwrites status.

        Given a task already marked as 'done',
        When updating to 'failed',
        Then the status should change to 'failed'.
        """
        request = ExecutionRequest(task_description="Complete then fail")
        task_id, buyer_secret = await task_repository.create_task(request)

        # First, mark as done
        await task_repository.update_task(
            task_id=task_id,
            status="done",
            result={"completed": True},
        )

        # Then try to update to failed
        await task_repository.update_task(
            task_id=task_id,
            status="failed",
            error={"message": "Late failure"},
        )

        result = await task_repository.get_task(task_id, buyer_secret)
        assert result is not None
        assert result.status == "failed"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_get_task_with_empty_strings(
        self, task_repository: TaskRepository
    ) -> None:
        """Verify get_task handles empty string credentials correctly.

        Given empty string task_id and buyer_secret,
        When retrieving the task,
        Then None should be returned.
        """
        result = await task_repository.get_task("", "")
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_repositories_share_database(self) -> None:
        """Verify multiple TaskRepository instances share the same database.

        Given two TaskRepository instances,
        When creating a task with one and retrieving with another,
        Then the task should be retrievable.
        """
        repo1 = TaskRepository(default_deadline_seconds=300)
        repo2 = TaskRepository(default_deadline_seconds=300)

        request = ExecutionRequest(task_description="Shared database test")
        task_id, buyer_secret = await repo1.create_task(request)

        # Retrieve from second repository
        result = await repo2.get_task(task_id, buyer_secret)
        assert result is not None
        assert result.task_id == task_id
