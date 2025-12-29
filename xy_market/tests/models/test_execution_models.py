import pytest
from datetime import datetime, timedelta

from xy_market.models.execution import ExecutionRequest, ExecutionResult


def test_execution_request_validation():
    """Test ExecutionRequest validation."""
    request = ExecutionRequest(
        task_description="Execute complex task",
        context={"env": "prod"},
        secrets={"api_key": "secret"}
    )
    assert request.task_description == "Execute complex task"
    assert request.context == {"env": "prod"}
    assert request.secrets == {"api_key": "secret"}


def test_execution_result_validation():
    """Test ExecutionResult validation."""
    deadline = (datetime.utcnow() + timedelta(minutes=5)).isoformat() + "Z"
    
    result = ExecutionResult(
        task_id="550e8400-e29b-41d4-a716-446655440000",
        buyer_secret="880e8400-e29b-41d4-a716-446655440003",
        status="in_progress",
        created_at="2024-01-01T00:00:00Z",
        deadline_at=deadline
    )
    assert result.status == "in_progress"
    assert result.data == {}
    assert result.error is None

    # Test completed result
    result_done = ExecutionResult(
        task_id="550e8400-e29b-41d4-a716-446655440000",
        buyer_secret="880e8400-e29b-41d4-a716-446655440003",
        status="done",
        data={"result": "success"},
        execution_time_ms=100,
        created_at="2024-01-01T00:00:00Z",
        deadline_at=deadline
    )
    assert result_done.status == "done"
    assert result_done.data == {"result": "success"}

    # Test invalid UUID
    with pytest.raises(ValueError):
        ExecutionResult(
            task_id="invalid",
            buyer_secret="880e8400-e29b-41d4-a716-446655440003",
            status="in_progress",
            created_at="2024-01-01T00:00:00Z",
            deadline_at=deadline
        )

